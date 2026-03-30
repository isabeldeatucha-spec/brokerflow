"""
Brand Scout — Broker UI
Redesigned with magicpath.ai-inspired aesthetic.

Run:
    cd /Users/isabelatucha && python3 -m streamlit run sedge/ui/app.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import uuid
import streamlit as st
from langgraph.types import Command

from sedge.agents.brand_scout.graph import graph
from sedge.memory import get_config, retrieve_all_evaluations

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Brand Scout · Sedge",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif !important; }

.stApp { background: #F7F5F2; }
section[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #EBEBEB; }
[data-testid="collapsedControl"] { display: none !important; }

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

h1 { font-size: 28px !important; font-weight: 700 !important; color: #1A1A1A !important; letter-spacing: -0.5px !important; }
h2 { font-size: 20px !important; font-weight: 600 !important; color: #1A1A1A !important; }
h3 { font-size: 16px !important; font-weight: 600 !important; color: #1A1A1A !important; }
p, li { color: #4A4A4A !important; font-size: 14px !important; line-height: 1.6 !important; }

.sedge-card {
    background: #FFFFFF;
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    border: 1px solid #F0EDEA;
    margin-bottom: 16px;
}

.criterion-card {
    background: #FFFFFF;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 1px 8px rgba(0,0,0,0.05);
    border: 1px solid #F0EDEA;
    text-align: center;
}

.badge-ready    { background: #D1FAE5; color: #065F46; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; }
.badge-promising { background: #FEF3C7; color: #92400E; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; }
.badge-early    { background: #FEE2E2; color: #991B1B; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; }

.category-pill { background: #EBF5FB; color: #1B4F72; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 500; }

.progress-track        { background: #F3F4F6; border-radius: 99px; height: 6px; width: 100%; margin: 8px 0; }
.progress-fill-green   { background: #10B981; border-radius: 99px; height: 6px; }
.progress-fill-yellow  { background: #F59E0B; border-radius: 99px; height: 6px; }
.progress-fill-red     { background: #EF4444; border-radius: 99px; height: 6px; }

.stButton > button {
    background: #1B4F72 !important;
    color: white !important;
    border-radius: 10px !important;
    border: none !important;
    padding: 10px 20px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    width: 100% !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

.approve-btn > button { background: #10B981 !important; }

.stTextInput > div > div > input {
    border-radius: 10px !important;
    border: 1.5px solid #E5E7EB !important;
    padding: 10px 14px !important;
    font-size: 14px !important;
    background: #FAFAFA !important;
}
.stTextInput > div > div > input:focus {
    border-color: #1B4F72 !important;
    box-shadow: 0 0 0 3px rgba(27,79,114,0.08) !important;
}

.stRadio label { font-size: 14px !important; color: #4A4A4A !important; }

.gap-item {
    background: #FFFBEB;
    border-left: 3px solid #F59E0B;
    padding: 10px 14px;
    border-radius: 0 8px 8px 0;
    margin-bottom: 8px;
    font-size: 13px;
    color: #4A4A4A;
}

.reflection-item {
    border-left: 2px solid #E5E7EB;
    padding-left: 16px;
    margin-bottom: 12px;
    font-size: 13px;
    color: #6B6B6B;
}
.reflection-label {
    font-size: 11px;
    font-weight: 600;
    color: #1B4F72;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}

.watchlist-card {
    background: #EBF5FB;
    border-radius: 12px;
    padding: 20px;
    border: 1px solid #D6EAF8;
    text-align: center;
}

.score-big   { font-size: 56px; font-weight: 700; color: #1A1A1A; line-height: 1; }
.score-label { font-size: 13px; color: #9CA3AF; font-weight: 500; margin-top: 4px; }

.recent-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #F3F4F6; font-size: 13px; }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "phase" not in st.session_state:
    st.session_state.phase = "idle"
if "interrupt_data" not in st.session_state:
    st.session_state.interrupt_data = None
if "final_state" not in st.session_state:
    st.session_state.final_state = None


def reset():
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.phase = "idle"
    st.session_state.interrupt_data = None
    st.session_state.final_state = None


def run_graph_to_completion(brand_name: str, website_url: str):
    """Stream the graph. Stops at human_approval interrupt or runs to END."""
    config = get_config(st.session_state.thread_id)
    initial_state = {
        "brand_name": brand_name,
        "website_url": website_url,
        "sources_checked": [],
        "signals_found": {},
        "follow_up_queries": [],
        "reflection_count": 0,
        "reflection_notes": [],
        "category": "",
        "benchmark": {},
        "score": {},
        "verdict": "",
        "founder_name": "",
        "founder_email": "",
        "email_draft": "",
        "approved": None,
        "rejection_reason": None,
    }

    interrupt_data = None
    progress_slot = st.empty()
    _NODE_LABELS = {
        "discover_brands":      "🔍 Discovering brands…",
        "research_brand":       "📊 Researching signals…",
        "reflect_and_decide":   "🤔 Checking for gaps…",
        "detect_category_node": "🏷️ Detecting category…",
        "score_brand":          "🎯 Scoring brand…",
        "store_memory":         "💾 Saving to memory…",
        "draft_outreach":       "✍️ Drafting email…",
    }

    for chunk in graph.stream(initial_state, config=config, stream_mode="updates"):
        for node in chunk:
            label = _NODE_LABELS.get(node, f"⚙️ {node}…")
            progress_slot.markdown(
                f'<div class="sedge-card" style="text-align:center;padding:16px;">'
                f'<p style="color:#1B4F72;font-weight:500;margin:0;">{label}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )

        state_snapshot = graph.get_state(config)
        if state_snapshot.next and "human_approval" in state_snapshot.next:
            for task in (state_snapshot.tasks or []):
                if hasattr(task, "interrupts") and task.interrupts:
                    interrupt_data = task.interrupts[0].value
            break

    progress_slot.empty()
    final = graph.get_state(config).values
    return interrupt_data, final


def resume_graph(approved: bool, rejection_reason: str = ""):
    config = get_config(st.session_state.thread_id)
    return graph.invoke(
        Command(resume={"approved": approved, "rejection_reason": rejection_reason}),
        config=config,
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Evaluate a Brand")
    brand_name_input = st.text_input("Brand name", placeholder="e.g. Sourmilk", key="brand_input")
    brand_url_input = st.text_input("Website URL", placeholder="optional but faster", key="url_input")
    mode = st.radio("Mode", ["Manual — enter a brand", "Auto-discover new arrivals"], key="mode_radio")

    if st.button("Run Brand Scout", key="run_btn"):
        if mode.startswith("Manual") and not brand_name_input.strip():
            st.warning("Enter a brand name first.")
        else:
            st.session_state["_brand_name"] = brand_name_input.strip()
            st.session_state["_website_url"] = brand_url_input.strip()
            st.session_state.phase = "running"
            st.rerun()

    st.markdown("<hr style='border:none;border-top:1px solid #EBEBEB;margin:20px 0'>", unsafe_allow_html=True)
    st.markdown("### 📋 Recent Evaluations")

    try:
        recent = retrieve_all_evaluations()[:5]
    except Exception:
        recent = []

    if recent:
        for ev in recent:
            total = ev["score"]
            emoji = "🟢" if total >= 70 else "🟡" if total >= 45 else "🔴"
            st.markdown(
                f'<div class="recent-item">'
                f'<span>{emoji} <strong>{ev["brand_name"]}</strong></span>'
                f'<span style="color:#9CA3AF;">{total}/100</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown('<p style="color:#9CA3AF;font-size:13px;">No evaluations yet.</p>', unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid #EBEBEB;margin:20px 0'>", unsafe_allow_html=True)
    if st.session_state.phase != "idle":
        if st.button("↺ New Search", key="new_search_btn"):
            reset()
            st.rerun()


# ── Shared result renderer (defined before phase chain) ───────────────────────

def render_results(state: dict, show_outreach: bool = True):
    """Render the full scorecard UI for a completed evaluation."""
    brand_name = state.get("brand_name", "Unknown")
    category   = state.get("category", "unknown").replace("_", " ").title()
    score_obj  = state.get("score", {})
    total      = score_obj.get("total", 0)
    detail     = state.get("signals_found", {}).get("score_detail", {})
    broker_brief       = detail.get("broker_brief", "No brief available.")
    key_gaps           = detail.get("key_gaps", [])
    reflection_notes   = state.get("reflection_notes", [])

    def pts(key: str) -> int:
        entry = detail.get(key, {})
        return entry.get("score", score_obj.get(key, 0)) if isinstance(entry, dict) else score_obj.get(key, 0)

    velocity     = pts("velocity_proof")
    distribution = pts("distribution_density")
    margin       = pts("margin_viability")
    story        = pts("brand_story_clarity")
    promo        = pts("promotional_independence")

    # ── Brand header ──────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(f"""
        <div>
            <h1 style="margin-bottom:6px;">{brand_name}</h1>
            <span class="category-pill">{category}</span>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div style="text-align:center;">
            <div class="score-big">{total}</div>
            <div class="score-label">out of 100</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        badge_class = "badge-ready" if total >= 70 else "badge-promising" if total >= 45 else "badge-early"
        badge_label = "Broker Ready 🟢" if total >= 70 else "Promising 🟡" if total >= 45 else "Too Early 🔴"
        st.markdown(
            f'<div style="padding-top:12px;"><span class="{badge_class}">{badge_label}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin:24px 0 8px;'></div>", unsafe_allow_html=True)

    # ── Scorecard row ─────────────────────────────────────────────────────────
    criteria = [
        ("Velocity Proof",     velocity,     25),
        ("Distribution",       distribution, 20),
        ("Margin Viability",   margin,       20),
        ("Brand Story",        story,        20),
        ("Promo Independence", promo,        15),
    ]
    cols = st.columns(5)
    for i, (name, score, max_score) in enumerate(criteria):
        pct   = score / max_score
        color = "green" if pct >= 0.7 else "yellow" if pct >= 0.4 else "red"
        with cols[i]:
            st.markdown(f"""
            <div class="criterion-card">
                <div style="font-size:12px;color:#9CA3AF;font-weight:500;margin-bottom:4px;">{name}</div>
                <div style="font-size:22px;font-weight:700;color:#1A1A1A;">{score}<span style="font-size:13px;color:#9CA3AF;">/{max_score}</span></div>
                <div class="progress-track">
                    <div class="progress-fill-{color}" style="width:{int(pct*100)}%"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

    # ── Bottom two-column section ─────────────────────────────────────────────
    left, right = st.columns([1.5, 1])

    with left:
        # Single unified card: Broker Brief + divider + Key Gaps
        gaps_html = "".join(f'<div class="gap-item">⚠️ {g}</div>' for g in key_gaps) or "<p style='color:#9CA3AF;margin:0;'>None identified.</p>"
        st.markdown(f"""
        <div class="sedge-card">
            <h3>📝 Broker Brief</h3>
            <p style="margin-bottom:0;">{broker_brief}</p>
            <hr style="border:none;border-top:1px solid #F0EDEA;margin:16px 0;">
            <h3>🚨 Key Gaps</h3>
            {gaps_html}
        </div>
        """, unsafe_allow_html=True)

        with st.expander("🧠 Agent Reasoning Chain"):
            if reflection_notes:
                for i, note in enumerate(reflection_notes):
                    st.markdown(f"""
                    <div class="reflection-item">
                        <div class="reflection-label">Round {i+1}</div>
                        <p>{note}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown('<p style="color:#9CA3AF;">No reflection loops required.</p>', unsafe_allow_html=True)

    with right:
        if show_outreach and total >= 70:
            founder_name  = state.get("founder_name", "")
            founder_email = state.get("founder_email", "")
            email_draft   = state.get("email_draft", "")

            st.markdown('<div class="sedge-card"><h3>💌 Outreach Draft</h3>', unsafe_allow_html=True)
            st.markdown(f'<p style="font-size:12px;color:#9CA3AF;">To: {founder_name} &lt;{founder_email}&gt;</p>', unsafe_allow_html=True)
            edited_draft = st.text_area("", value=email_draft, height=280, key="email_draft_area", label_visibility="collapsed")
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown('<div class="approve-btn">', unsafe_allow_html=True)
                approve = st.button("Approve & Send", key="approve_btn")
                st.markdown('</div>', unsafe_allow_html=True)
            with col_b:
                reject = st.button("Reject", key="reject_btn")
            st.markdown('</div>', unsafe_allow_html=True)
            return {"approve": approve, "reject": reject, "edited_draft": edited_draft}

        else:
            memory_previous   = state.get("signals_found", {}).get("brand_history", "") or "None"
            comparable_brands = ""
            try:
                from sedge.memory import retrieve_similar_brands
                cat = state.get("category", "unknown")
                comparable_brands = retrieve_similar_brands(cat, (max(0, total - 15), total + 15)) or "None yet"
            except Exception:
                comparable_brands = "Unavailable"

            st.markdown(f"""
            <div class="watchlist-card">
                <h3 style="color:#1B4F72;margin-top:0;">Added to Watch List</h3>
                <p style="color:#4A6A7A;">This brand scored {total}/100 — below the 70-point broker-ready threshold.
                Check back in 3–6 months as they build distribution and velocity.</p>
                <hr style="border:none;border-top:1px solid #AED6F1;margin:14px 0;">
                <p style="font-size:11px;color:#7FB3D3;margin:0;">Previously evaluated: {memory_previous} · Comparable brands: {comparable_brands}</p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            st.button("Set Reminder", key="reminder_btn")

    return {}


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
    <h1 style="margin:0;">Brand Scout</h1>
    <span style="color:#9CA3AF; font-size:14px; margin-left:4px;">by Sedge</span>
</div>
<p style="color:#9CA3AF; margin-top:0; margin-bottom:24px;">AI-powered brand evaluation for CPG brokers</p>
<hr style="border:none; border-top:1px solid #EBEBEB; margin-bottom:32px;">
""", unsafe_allow_html=True)


# ── Phase: idle ───────────────────────────────────────────────────────────────
if st.session_state.phase == "idle":
    st.markdown("""
    <div style="text-align:center; padding:80px 40px;">
        <h2 style="color:#1A1A1A;">Ready to scout brands</h2>
        <p style="color:#9CA3AF; max-width:360px; margin:0 auto;">
            Enter a brand name to research across 10+ sources and get a full
            broker-readiness scorecard in under 60 seconds.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ── Phase: running ────────────────────────────────────────────────────────────
elif st.session_state.phase == "running":
    b_name = st.session_state.get("_brand_name", "")
    b_url  = st.session_state.get("_website_url", "")

    st.markdown(
        f'<div class="sedge-card" style="text-align:center;padding:32px;">'
        f'<div style="font-size:32px;margin-bottom:12px;">🔍</div>'
        f'<h2 style="margin-bottom:4px;">Researching {b_name or "brand"}…</h2>'
        f'<p style="color:#9CA3AF;">This takes about 30–60 seconds.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    interrupt_data, final = run_graph_to_completion(b_name, b_url)
    st.session_state.final_state = final

    if interrupt_data:
        st.session_state.interrupt_data = interrupt_data
        st.session_state.phase = "awaiting_approval"
    else:
        verdict = (final or {}).get("verdict", "below_threshold")
        st.session_state.phase = verdict if verdict in ("promising", "below_threshold") else "done"

    st.rerun()


# ── Phase: awaiting_approval ──────────────────────────────────────────────────
elif st.session_state.phase == "awaiting_approval":
    data  = st.session_state.interrupt_data or {}
    final = st.session_state.final_state or {}
    # Merge interrupt data into final so render_results has everything
    merged = {**final, **data}

    actions = render_results(merged, show_outreach=True)

    if actions.get("approve"):
        with st.spinner("Sending email…"):
            resume_graph(approved=True)
        st.session_state.phase = "done"
        st.rerun()
    elif actions.get("reject"):
        resume_graph(approved=False, rejection_reason="Rejected via UI")
        st.session_state.phase = "rejected"
        st.rerun()


# ── Phase: promising / below_threshold ───────────────────────────────────────
elif st.session_state.phase in ("promising", "below_threshold"):
    final = st.session_state.final_state or {}
    render_results(final, show_outreach=False)


# ── Phase: done ───────────────────────────────────────────────────────────────
elif st.session_state.phase == "done":
    data = st.session_state.interrupt_data or {}
    st.markdown(f"""
    <div class="sedge-card" style="text-align:center;padding:40px;">
        <div style="font-size:36px;margin-bottom:12px;">✅</div>
        <h2>Email sent successfully</h2>
        <p style="color:#9CA3AF;">Outreach sent to <strong>{data.get('founder_name','')}</strong>
        at <code>{data.get('founder_email','')}</code></p>
    </div>
    """, unsafe_allow_html=True)


# ── Phase: rejected ───────────────────────────────────────────────────────────
elif st.session_state.phase == "rejected":
    st.markdown("""
    <div class="sedge-card" style="text-align:center;padding:40px;">
        <div style="font-size:36px;margin-bottom:12px;">❌</div>
        <h2>Brand rejected</h2>
        <p style="color:#9CA3AF;">No email was sent.</p>
    </div>
    """, unsafe_allow_html=True)
