"""
Brand Scout — Broker UI
Redesigned with magicpath.ai-inspired aesthetic.

Run:
    cd /Users/isabelatucha && python3 -m streamlit run sedge/ui/app.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uuid
import streamlit as st
from langgraph.types import Command

from agents.brand_scout.graph import graph
from memory import get_config, retrieve_all_evaluations

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

/* Scroll fix */
.main { overflow-y: auto !important; }
.block-container {
    overflow-y: auto !important;
    max-height: none !important;
    padding-bottom: 120px !important;
}
section[data-testid="stMain"] { overflow-y: auto !important; }
section[data-testid="stMain"] > div { overflow-y: auto !important; }
.element-container { overflow: visible !important; }
section[data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-right: 1px solid #E5E5E5 !important;
    min-width: 260px !important;
}
section[data-testid="stSidebar"] > div {
    background: #FFFFFF !important;
    padding: 24px 16px 80px 16px !important;
}
/* Keep sidebar always on-screen regardless of viewport width or user toggle */
section[data-testid="stSidebar"] {
    transform: none !important;
    left: 0 !important;
    visibility: visible !important;
}
/* Hide both the collapse (×) button inside the expanded sidebar
   AND the expand (›) button shown when collapsed */
[data-testid="stSidebarCollapseButton"],
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

.badge-established { background: #FEF3C7; color: #92400E; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; }
.badge-ready    { background: #D1FAE5; color: #065F46; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; }
.badge-early    { background: #FEE2E2; color: #991B1B; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; }

.category-pill { background: #EBF5FB; color: #1B4F72; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 500; }

.progress-track        { background: #F3F4F6; border-radius: 99px; height: 6px; width: 100%; margin: 8px 0; }
.progress-fill-green   { background: #10B981; border-radius: 99px; height: 6px; }
.progress-fill-yellow  { background: #F59E0B; border-radius: 99px; height: 6px; }
.progress-fill-red     { background: #EF4444; border-radius: 99px; height: 6px; }

/* Force all buttons navy with white text */
.stButton > button,
div[data-testid="stButton"] button {
    background: #1B4F72 !important;
    background-color: #1B4F72 !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 12px 16px !important;
    width: 100% !important;
    cursor: pointer !important;
}
.stButton > button:hover,
div[data-testid="stButton"] button:hover {
    background: #154360 !important;
    background-color: #154360 !important;
}
.stButton > button *,
div[data-testid="stButton"] button *,
.stButton > button p,
div[data-testid="stButton"] button p,
.stButton > button span,
div[data-testid="stButton"] button span {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

.approve-btn > button { background: #10B981 !important; }

/* Input text color */
.stTextInput input {
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
    background-color: #FFFFFF !important;
    caret-color: #111111 !important;
    border-radius: 10px !important;
    border: 1.5px solid #E5E7EB !important;
    padding: 10px 14px !important;
    font-size: 14px !important;
}
.stTextInput input::placeholder {
    color: #9CA3AF !important;
    -webkit-text-fill-color: #9CA3AF !important;
}
.stTextInput input:focus {
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
    background-color: #FFFFFF !important;
    border-color: #1B4F72 !important;
    box-shadow: 0 0 0 3px rgba(27,79,114,0.08) !important;
}
section[data-testid="stSidebar"] .stTextInput input {
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
    background: #FAFAFA !important;
}

div[data-testid="stRadio"] input[type="radio"] { accent-color: #1B4F72 !important; }
div[data-testid="stRadio"] label { font-size: 14px !important; color: #4A4A4A !important; }

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

.email-panel {
    background: #FFFFFF;
    border: 1px solid #E5E5E5;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    margin-bottom: 12px;
}
.email-to {
    font-size: 13px;
    color: #4A4A4A;
    padding: 8px 0;
    border-bottom: 1px solid #F3F4F6;
    margin-bottom: 8px;
}
.email-subject {
    font-size: 13px;
    font-weight: 600;
    color: #111111;
    padding: 8px 0;
    border-bottom: 1px solid #F3F4F6;
    margin-bottom: 12px;
}

.recent-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #F3F4F6; font-size: 13px; }

/* Suppress keyboard_arrow_right and other Material Icons glyph names
   that render as literal text when the icon font fails to load.
   Targets the raw text node inside the expander summary arrow span. */
.material-icons, .material-symbols-rounded, .material-symbols-outlined,
[class*="material-icon"] { font-size: 0 !important; line-height: 0 !important; }

/* Hide the literal "keyboard_arrow_right" text Streamlit injects
   into st.expander toggle icons via Material Icons <span> elements.
   Targets both the stable Emotion hash class and the structural pattern. */
span.ejhh0er0,
[data-testid="stExpanderToggleIcon"],
details > summary > span:first-child > span:first-child > span:first-child {
    font-size: 0 !important;
    width: 0 !important;
    overflow: hidden !important;
    display: inline-block !important;
}

/* Hide Streamlit's built-in sidebar collapse arrow and any stray
   navigation / shortcut-hint UI chrome we don't want */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stTextAreaResizeHandle"] ~ span { display: none !important; }

/* Hide textarea keyboard shortcut badge (⌘⏎ / Ctrl+Enter hint) */
.stTextArea [data-baseweb="textarea"] ~ div[aria-label],
.stTextArea div[class*="shortcut"] { display: none !important; }

/* Approve / reject button colours */
button[data-testid="approve_btn"] { background: #1B7A4A !important; }
button[data-testid="reject_btn"]  { background: #C0392B !important; }

/* Criterion card buttons — look like cards, not buttons */
div[data-testid^="stButton"] button {
    background: #FFFFFF !important;
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
    border: 1px solid #F0EDEA !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 8px rgba(0,0,0,0.05) !important;
    padding: 16px !important;
    text-align: center !important;
    font-weight: 400 !important;
    white-space: pre-line !important;
}
div[data-testid^="stButton"] button:hover {
    background: #F7F5F2 !important;
    border-color: #1B4F72 !important;
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
}
div[data-testid^="stButton"] button p {
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
}

/* Force action buttons (Run, Approve, Reject, New Search) to stay navy — must be last */
button[kind="primary"],
div[data-testid="stButton-run_btn"] button,
div[data-testid="stButton-new_search_btn"] button,
div[data-testid="stButton-approve_btn"] button,
div[data-testid="stButton-reject_btn"] button,
div[data-testid="stButton-reminder_btn"] button {
    background: #1B4F72 !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    font-weight: 600 !important;
}
div[data-testid="stButton-approve_btn"] button { background: #1B7A4A !important; }
div[data-testid="stButton-reject_btn"] button  { background: #C0392B !important; }
div[data-testid="stButton-run_btn"] button p,
div[data-testid="stButton-new_search_btn"] button p,
div[data-testid="stButton-approve_btn"] button p,
div[data-testid="stButton-reject_btn"] button p,
div[data-testid="stButton-reminder_btn"] button p {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

/* Run Brand Scout button — force navy background white text */
section[data-testid="stSidebar"] .stButton > button {
    background: #1B4F72 !important;
    background-color: #1B4F72 !important;
    color: white !important;
    -webkit-text-fill-color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    width: 100% !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: #154360 !important;
    background-color: #154360 !important;
}
section[data-testid="stSidebar"] .stButton > button p,
section[data-testid="stSidebar"] .stButton > button span,
section[data-testid="stSidebar"] .stButton > button div {
    color: white !important;
    -webkit-text-fill-color: white !important;
}

/* Radio buttons — fix black filled circle */
section[data-testid="stSidebar"] .stRadio > div {
    gap: 8px !important;
}
section[data-testid="stSidebar"] .stRadio input[type="radio"] {
    accent-color: #1B4F72 !important;
    width: 16px !important;
    height: 16px !important;
}
section[data-testid="stSidebar"] .stRadio label {
    color: #4A4A4A !important;
    font-size: 14px !important;
}
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
if "selected_criterion" not in st.session_state:
    st.session_state.selected_criterion = None
if "extracted_fields" not in st.session_state:
    st.session_state.extracted_fields = {}


def reset():
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.phase = "idle"
    st.session_state.interrupt_data = None
    st.session_state.final_state = None
    st.session_state.selected_criterion = None
    st.session_state.extracted_fields = {}


def run_graph_to_completion(brand_name: str, website_url: str):
    """
    Stream the graph, showing live node progress.
    After streaming ends, checks for an interrupt (human_approval does not emit
    a chunk — it only pauses the graph, so we must check state post-loop).
    Returns (interrupt_data | None, final_state).
    """
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
        "extracted_fields": {},
        "score": {},
        "verdict": "",
        "founder_name": "",
        "founder_email": "",
        "email_draft": "",
        "approved": None,
        "rejection_reason": None,
    }

    _NODE_LABELS = {
        "discover_brands":      "🔍 Discovering brands…",
        "research_brand":       "📊 Researching signals…",
        "reflect_and_decide":   "🤔 Checking for gaps…",
        "detect_category_node": "🏷️ Detecting category…",
        "extract_fields":       "🔬 Extracting structured fields…",
        "score_brand":          "🎯 Scoring brand…",
        "store_memory":         "💾 Saving to memory…",
        "draft_outreach":       "✍️ Drafting email…",
    }

    progress_slot = st.empty()
    completed_labels: list[str] = []

    for chunk in graph.stream(initial_state, config=config, stream_mode="updates"):
        for node in chunk:
            label = _NODE_LABELS.get(node, f"⚙️ {node}…")
            completed_labels.append(label)
            cards_html = "".join(
                f'<div style="background:#FFFFFF;border-radius:12px;padding:12px 20px;'
                f'box-shadow:0 1px 6px rgba(0,0,0,0.05);border:1px solid #F0EDEA;'
                f'margin-bottom:8px;display:flex;align-items:center;gap:10px;">'
                f'<span style="color:#10B981;font-size:16px;">✓</span>'
                f'<p style="color:#4A4A4A;font-weight:500;margin:0;font-size:14px;">{lbl}</p>'
                f'</div>'
                for lbl in completed_labels
            )
            progress_slot.markdown(cards_html, unsafe_allow_html=True)

    # Stream exhausted — now check if graph paused at an interrupt.
    # human_approval calls interrupt() which stops the stream without emitting
    # a chunk, so this check must happen outside the loop.
    progress_slot.empty()
    state_snapshot = graph.get_state(config)
    final = state_snapshot.values

    interrupt_data = None
    if state_snapshot.next:
        for task in (state_snapshot.tasks or []):
            if hasattr(task, "interrupts") and task.interrupts:
                interrupt_data = task.interrupts[0].value
                break

    return interrupt_data, final


def resume_graph(approved: bool, rejection_reason: str = ""):
    config = get_config(st.session_state.thread_id)
    return graph.invoke(
        Command(resume={"approved": approved, "rejection_reason": rejection_reason}),
        config=config,
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p style="font-size:11px; font-weight:700; color:#9CA3AF; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:16px;">Brand Scout</p>', unsafe_allow_html=True)

    mode = st.radio(
        "Mode",
        ["🔍  Research a brand", "🌐  Discover new brands"],
        key="mode_radio",
        label_visibility="collapsed",
    )

    if mode == "🔍  Research a brand":
        brand_name_input = st.text_input("Brand name", placeholder="Brand name", key="brand_input")
        brand_url_input = st.text_input("Website URL", placeholder="Website URL — speeds up research", key="url_input")
    else:
        brand_name_input = ""
        brand_url_input = ""
        st.markdown("""
<div style="background:#EBF5FB; border-radius:8px; padding:12px; font-size:13px; color:#1B4F72; line-height:1.5;">
    Scans Whole Foods, Sprouts, Target and Walmart for brands just hitting shelves.
    Evaluates the top picks and surfaces the ones worth your time.
</div>
""", unsafe_allow_html=True)

    if st.button("▶ Run", key="run_btn", use_container_width=True):
        if mode == "🔍  Research a brand" and not brand_name_input.strip():
            st.warning("Enter a brand name first.")
        else:
            st.session_state["_brand_name"] = brand_name_input.strip()
            st.session_state["_website_url"] = brand_url_input.strip()
            st.session_state.phase = "running"
            st.rerun()

    st.markdown("<hr style='border:none;border-top:1px solid #EBEBEB;margin:20px 0'>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:11px; font-weight:700; color:#9CA3AF; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:8px;'>Recent Evaluations</p>", unsafe_allow_html=True)

    try:
        recent = retrieve_all_evaluations()
        if recent:
            for item in recent[:5]:
                score = item.get("score", 0)
                name  = item.get("brand_name", "Unknown")
                dot   = "🟡" if score >= 70 else "🟢" if score >= 45 else "🔴"
                if st.button(
                    f"{dot} {name}   {score}/100",
                    key=f"recent_{name}",
                    use_container_width=True,
                ):
                    detail = item.get("score_breakdown", {})
                    st.session_state.phase          = "awaiting_approval" if score >= 45 else "too_early"
                    st.session_state.final_state     = {
                        "brand_name":       name,
                        "score":            {"total": score, **{
                            k: (detail.get(k, {}).get("score", 0) if isinstance(detail.get(k), dict) else 0)
                            for k in ("velocity_proof", "distribution_density", "margin_viability",
                                      "brand_story_clarity", "promotional_independence")
                        }},
                        "verdict":          item.get("verdict", ""),
                        "category":         item.get("category", ""),
                        "reflection_notes": item.get("reflection_notes") or [],
                        "email_draft":      item.get("email_draft", ""),
                        "founder_name":     item.get("founder_name", ""),
                        "founder_email":    item.get("founder_email", ""),
                        "signals_found":    {
                            "score_detail": {
                                **detail,
                                "broker_brief": item.get("broker_brief", ""),
                                "key_gaps":     item.get("key_gaps") or [],
                            }
                        },
                    }
                    st.session_state.interrupt_data  = st.session_state.final_state
                    st.session_state.extracted_fields = {}
                    st.rerun()
        else:
            st.markdown("<p style='font-size:13px; color:#9CA3AF;'>No evaluations yet.</p>", unsafe_allow_html=True)
    except Exception as _e:
        st.markdown(f"<p style='font-size:11px; color:#EF4444;'>Error: {_e}</p>", unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid #EBEBEB;margin:20px 0'>", unsafe_allow_html=True)
    if st.session_state.phase != "idle":
        st.markdown('<div style="margin-top:8px; padding-bottom:40px;">', unsafe_allow_html=True)
        if st.button("↺ New Search", key="new_search_btn"):
            reset()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# ── Shared result renderer (defined before phase chain) ───────────────────────

def _criterion_breakdown_rows(criterion: str, fields: dict) -> list:
    """
    Returns list of (label, value_display, points_awarded) for each sub-factor
    of the given criterion, mirroring the calculate_score formula exactly.
    """
    rows = []

    if criterion == "velocity_proof":
        reviews = fields.get("amazon_review_count")
        if reviews is None: pts = 5
        elif reviews >= 1000: pts = 10
        elif reviews >= 500: pts = 8
        elif reviews >= 200: pts = 6
        elif reviews >= 50: pts = 3
        else: pts = 1
        val = f"{reviews:,}" if reviews is not None else "not found"
        rows.append(("Amazon reviews", val, pts))

        rating = fields.get("amazon_rating")
        if rating is None: pts = 2
        elif rating >= 4.5: pts = 5
        elif rating >= 4.2: pts = 4
        elif rating >= 4.0: pts = 3
        elif rating >= 3.5: pts = 1
        else: pts = 0
        rows.append(("Amazon rating", str(rating) if rating is not None else "not found", pts))

        ss = fields.get("amazon_subscribe_save")
        if ss is None: pts = 2
        elif ss: pts = 4
        else: pts = 0
        rows.append(("Subscribe & Save", "Yes" if ss else ("No" if ss is not None else "not found"), pts))

        banners = fields.get("instacart_banner_count")
        if banners is None: pts = 1
        elif banners >= 3: pts = 3
        elif banners >= 1: pts = 2
        else: pts = 0
        rows.append(("Instacart banners", str(banners) if banners is not None else "not found", pts))

        spins = fields.get("spins_mentioned")
        sell = fields.get("sell_through_press")
        if spins: pts = 3
        elif sell: pts = 2
        else: pts = 1
        press_val = "SPINS mentioned" if spins else ("Sell-through press" if sell else "None found")
        rows.append(("SPINS / press", press_val, pts))

    elif criterion == "distribution_density":
        doors = fields.get("estimated_door_count")
        if doors is None: pts = 4
        elif 50 <= doors <= 300: pts = 8
        elif 20 <= doors < 50: pts = 5
        elif 300 < doors <= 800: pts = 6
        elif doors > 800: pts = 2
        else: pts = 1
        rows.append(("Est. door count", f"{doors:,}" if doors is not None else "not found", pts))

        retailer_pts = 0
        retailer_parts = []
        if fields.get("whole_foods_confirmed"): retailer_pts += 3; retailer_parts.append("Whole Foods")
        if fields.get("sprouts_confirmed"): retailer_pts += 2; retailer_parts.append("Sprouts")
        if fields.get("target_confirmed"): retailer_pts += 2; retailer_parts.append("Target")
        if fields.get("costco_confirmed"): retailer_pts += 2; retailer_parts.append("Costco")
        if fields.get("walmart_confirmed"): retailer_pts += 1; retailer_parts.append("Walmart")
        retailer_pts = min(retailer_pts, 8)
        nationals = sum(bool(fields.get(k)) for k in ["whole_foods_confirmed", "target_confirmed", "walmart_confirmed", "costco_confirmed"])
        if nationals >= 4: retailer_pts = max(retailer_pts - 4, 2)
        rows.append(("Retail chains", ", ".join(retailer_parts) if retailer_parts else "None confirmed", retailer_pts))

        faire_listed = fields.get("faire_listed")
        if faire_listed is None: pts = 2
        elif faire_listed: pts = 4
        else: pts = 0
        rows.append(("Faire listed", "Yes" if faire_listed else ("No" if faire_listed is not None else "not found"), pts))

    elif criterion == "margin_viability":
        srp = fields.get("srp_hero") or fields.get("srp_min")
        category = fields.get("category", "unknown")
        _benchmarks = {
            "beverage_rtd": (3.50, 6.00), "snack_bar": (2.50, 5.00),
            "condiment_sauce": (7.00, 16.00), "frozen_food": (6.00, 14.00),
            "supplement_functional": (20.00, 65.00), "olive_oil_cooking_oil": (12.00, 35.00),
            "dairy_alternative": (5.00, 12.00), "meat_snack_protein": (2.00, 5.00),
            "unknown": (6.00, 20.00),
        }
        low, _ = _benchmarks.get(category, (6.00, 20.00))
        if srp is None: pts = 5
        elif srp >= low * 1.2: pts = 10
        elif srp >= low: pts = 7
        elif srp >= low * 0.8: pts = 4
        else: pts = 1
        rows.append(("SRP", f"${srp:.2f}" if srp is not None else "not found", pts))

        funding = fields.get("funding_amount_usd")
        if funding is None: pts = 3
        elif funding >= 5_000_000: pts = 6
        elif funding >= 1_000_000: pts = 4
        elif funding > 0: pts = 2
        else: pts = 1
        rows.append(("Funding raised", f"${funding:,}" if funding is not None else "not found", pts))

        faire_listed = fields.get("faire_listed")
        if faire_listed is None: pts = 2
        elif faire_listed: pts = 3
        else: pts = 1
        rows.append(("Faire listed", "Yes" if faire_listed else ("No" if faire_listed is not None else "not found"), pts))

    elif criterion == "brand_story_clarity":
        hero = fields.get("hero_product_clear")
        if hero is None: pts = 2
        elif hero: pts = 4
        else: pts = 0
        rows.append(("Hero product clear", "Yes" if hero else ("No" if hero is not None else "not found"), pts))

        founder = fields.get("founder_story_clear")
        if founder is None: pts = 1
        elif founder: pts = 3
        else: pts = 0
        rows.append(("Founder story clear", "Yes" if founder else ("No" if founder is not None else "not found"), pts))

        ig = fields.get("instagram_followers") or 0
        tt = fields.get("tiktok_followers") or 0
        social_max = max(ig, tt)
        if fields.get("instagram_followers") is None and fields.get("tiktok_followers") is None: pts = 2
        elif social_max >= 100_000: pts = 5
        elif social_max >= 50_000: pts = 4
        elif social_max >= 10_000: pts = 3
        elif social_max >= 1_000: pts = 2
        else: pts = 1
        rows.append(("Social following", f"{social_max:,}" if social_max > 0 else "not found", pts))

        trade = fields.get("press_trade_mentions") or 0
        if fields.get("press_trade_mentions") is None: pts = 2
        elif trade >= 3: pts = 4
        elif trade >= 1: pts = 3
        else: pts = 1
        rows.append(("Trade press mentions", str(trade) if fields.get("press_trade_mentions") is not None else "not found", pts))

        certs = fields.get("certifications") or []
        if fields.get("certifications") is None: pts = 1
        elif len(certs) >= 2: pts = 2
        elif len(certs) >= 1: pts = 1
        else: pts = 0
        cert_val = ", ".join(certs) if certs else ("None found" if fields.get("certifications") is not None else "not found")
        rows.append(("Certifications", cert_val, pts))

        expo = fields.get("expo_west_confirmed")
        if expo is None: pts = 1
        elif expo: pts = 2
        else: pts = 0
        rows.append(("ExpoWest", "Confirmed" if expo else ("No" if expo is not None else "not found"), pts))

    elif criterion == "promotional_independence":
        ig = fields.get("instagram_followers") or 0
        tt = fields.get("tiktok_followers") or 0
        social_max = max(ig, tt)

        dtc = fields.get("dtc_channel")
        sub = fields.get("subscription_available")
        if dtc is None: pts = 2
        elif dtc:
            pts = 4 if sub else 3
        else: pts = 0
        dtc_val = ("Yes + subscription" if (dtc and sub) else "Yes" if dtc else ("No" if dtc is not None else "not found"))
        rows.append(("DTC channel", dtc_val, pts))

        if fields.get("instagram_followers") is None and fields.get("tiktok_followers") is None: pts = 2
        elif social_max >= 100_000: pts = 4
        elif social_max >= 50_000: pts = 3
        elif social_max >= 10_000: pts = 2
        elif social_max >= 1_000: pts = 1
        else: pts = 0
        rows.append(("Social following", f"{social_max:,}" if social_max > 0 else "not found", pts))

        tprs = fields.get("promo_frequency_tpr_per_year")
        bogo = fields.get("bogo_detected", False)
        if tprs is None: pts = 2
        elif tprs <= 2: pts = 4
        elif tprs <= 4: pts = 3
        elif tprs <= 6: pts = 1
        else: pts = 0
        if bogo: pts = max(pts - 2, 0)
        tpr_val = (f"{tprs}/yr" if tprs is not None else "not found") + (" (BOGO detected −2pts)" if bogo else "")
        rows.append(("TPR frequency", tpr_val, pts))

        ss = fields.get("amazon_subscribe_save")
        if ss is None: pts = 1
        elif ss: pts = 3
        else: pts = 0
        rows.append(("Subscribe & Save", "Yes" if ss else ("No" if ss is not None else "not found"), pts))

    return rows


def render_results(state: dict, show_outreach: bool = True):
    """Render the full scorecard UI for a completed evaluation."""
    brand_name   = state.get("brand_name", "Unknown")
    display_name = brand_name.strip().title()
    category     = state.get("category", "unknown").replace("_", " ").title()
    score_obj    = state.get("score", {})
    total        = score_obj.get("total", 0)
    detail       = state.get("signals_found", {}).get("score_detail", {})
    broker_brief     = detail.get("broker_brief", "No brief available.")
    key_gaps         = detail.get("key_gaps", [])
    reflection_notes = state.get("reflection_notes", [])

    # Clearbit logo
    brand_url  = state.get("website_url", "")
    domain     = (brand_url.replace("https://", "").replace("http://", "")
                  .replace("www.", "").split("/")[0]) if brand_url else ""
    logo_url   = f"https://logo.clearbit.com/{domain}" if domain else ""

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
        logo_img = f'<img src="https://logo.clearbit.com/{domain}" style="width:40px;height:40px;border-radius:8px;object-fit:contain;background:#F3F4F6;">' if domain else ""
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">'
            f'{logo_img}'
            f'<div>'
            f'<h1 style="margin:0 0 4px 0;font-size:32px;font-weight:700;color:#111111;">{display_name}</h1>'
            f'<span class="category-pill">{category}</span>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(f"""
        <div style="text-align:center;">
            <div class="score-big">{total}</div>
            <div class="score-label">out of 100</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        badge_class = "badge-established" if total >= 70 else "badge-ready" if total >= 45 else "badge-early"
        badge_label = "Established 🟡" if total >= 70 else "Broker Ready 🟢" if total >= 45 else "Too Early 🔴"
        st.markdown(
            f'<div style="padding-top:12px;"><span class="{badge_class}">{badge_label}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin:24px 0 8px;'></div>", unsafe_allow_html=True)

    # ── Scorecard row — compact cards, detail panel below ────────────────────
    criteria_data = [
        ("Velocity Proof",     velocity,     25, "velocity_proof"),
        ("Distribution",       distribution, 20, "distribution_density"),
        ("Margin Viability",   margin,       20, "margin_viability"),
        ("Brand Story",        story,        20, "brand_story_clarity"),
        ("Promo Independence", promo,        15, "promotional_independence"),
    ]
    cols = st.columns(5)
    for i, (cname, cscore, cmax, ckey) in enumerate(criteria_data):
        pct   = cscore / cmax if cmax else 0
        color = "#10B981" if pct >= 0.7 else "#F59E0B" if pct >= 0.4 else "#EF4444"
        with cols[i]:
            if st.button(f"{cname}\n{cscore}/{cmax}", key=f"card_{ckey}", use_container_width=True):
                if st.session_state.get("selected_criterion") == ckey:
                    st.session_state.selected_criterion = None
                else:
                    st.session_state.selected_criterion = ckey
            st.markdown(f"""
            <div style="height:4px; background:#F3F4F6; border-radius:99px; margin-top:-8px;">
                <div style="height:4px; width:{int(pct*100)}%; background:{color}; border-radius:99px;"></div>
            </div>
            """, unsafe_allow_html=True)

    # ── How scoring works expander ────────────────────────────────────────────
    with st.expander("ℹ️ How scoring works"):
        st.markdown("""
        <div style="padding:8px 0;">
            <p style="font-size:13px; color:#4A4A4A; margin-bottom:16px; line-height:1.6;">
                Brand Scout scores brands on five criteria drawn from 150+ interviews with independent
                food brokers, CPG founders, distributors, and retail buyers.
                Total is out of 100.
            </p>
            <div style="display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap;">
                <span style="background:#FEF3C7; color:#92400E; padding:3px 10px; border-radius:99px; font-size:12px; font-weight:600;">🟡 Established = 70+</span>
                <span style="background:#D1FAE5; color:#065F46; padding:3px 10px; border-radius:99px; font-size:12px; font-weight:600;">🟢 Broker Ready = 45–69</span>
                <span style="background:#FEE2E2; color:#991B1B; padding:3px 10px; border-radius:99px; font-size:12px; font-weight:600;">🔴 Too Early = below 45</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        rubric = [
            (
                "Velocity Proof", 25,
                "The most important signal. Has this brand proven that real consumers buy it repeatedly without heavy promotional support? Brokers need evidence that product moves off shelf on its own.",
                "Amazon reviews & rating, Subscribe & Save, Instacart banner presence, SPINS/NIQ mentions, trade press sell-through data"
            ),
            (
                "Distribution Density", 20,
                "Is the brand in the right number of doors — enough to prove viability, not so many that a broker adds no value? Sweet spot is 20–300 doors with regional traction, not yet in all major nationals.",
                "Brand website store locator, Whole Foods / Target / Walmart / Sprouts / Costco listings, Faire door count, Instacart banners"
            ),
            (
                "Margin Viability", 20,
                "Can this brand survive the full retail cost stack: distributor markup (12–28%), broker commission (5%), free fill, and slotting fees? Brands need minimum 50% gross margin to survive.",
                "SRP vs category benchmarks, Faire wholesale pricing, funding signals (can they absorb slotting costs?)"
            ),
            (
                "Brand Story Clarity", 20,
                "Can a broker rep explain this brand to a retail buyer in 30 seconds? Clear hero product, specific consumer, defined differentiation vs. incumbents — packaging that sells itself.",
                "Brand website, Instagram & TikTok following, trade press (NOSH, FoodNavigator), Expo West presence, certifications"
            ),
            (
                "Promotional Independence", 15,
                "Can this brand generate consumer demand without relying entirely on the broker to fund promos? Brands that only sell on promotion are a liability. Healthy brands survive on regular pricing.",
                "DTC channel & subscription model, organic social following, TPR frequency, Amazon Subscribe & Save, promotional history"
            ),
        ]

        for name, pts_val, description, sources in rubric:
            st.markdown(f"""
            <div style="padding:12px 0; border-bottom:1px solid #F3F4F6;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="font-size:13px; font-weight:600; color:#111111;">{name}</span>
                    <span style="font-size:12px; font-weight:600; color:#1B4F72; background:#EBF5FB; padding:2px 10px; border-radius:99px;">{pts_val} pts</span>
                </div>
                <p style="font-size:12px; color:#4A4A4A; margin:0 0 4px 0; line-height:1.5;">{description}</p>
                <p style="font-size:11px; color:#9CA3AF; margin:0;">Sources: {sources}</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <p style="font-size:11px; color:#9CA3AF; margin-top:12px; font-style:italic; line-height:1.5;">
            Missing data scores at 50% of max — absence of information is treated as neutral, not negative.
            Only active negative signals (confirmed over-distribution, below-viable pricing, promotional dependency)
            reduce scores below the neutral floor.
        </p>
        """, unsafe_allow_html=True)

    # Detail panel — renders below the row when a card is selected
    selected = st.session_state.get("selected_criterion")
    if selected:
        name_map = {
            "velocity_proof":           "Velocity Proof",
            "distribution_density":     "Distribution Density",
            "margin_viability":         "Margin Viability",
            "brand_story_clarity":      "Brand Story Clarity",
            "promotional_independence": "Promotional Independence",
        }
        extracted = state.get("extracted_fields") or st.session_state.get("extracted_fields") or {}
        rows = _criterion_breakdown_rows(selected, extracted) if extracted else []

        if rows:
            rows_html = "".join(
                f'<div style="display:flex; justify-content:space-between; align-items:center; '
                f'padding:8px 0; border-bottom:1px solid #F3F4F6;">'
                f'<span style="font-size:13px; color:#4A4A4A;">{label}</span>'
                f'<span style="font-size:13px; color:#6B6B6B; flex:1; text-align:center; padding:0 12px;">{val}</span>'
                f'<span style="font-size:13px; font-weight:600; color:#1B4F72; min-width:48px; text-align:right;">{pts} pts</span>'
                f'</div>'
                for label, val, pts in rows
            )
        else:
            crit_detail = detail.get(selected, {})
            reasoning = crit_detail.get("reasoning", "No detail available.") if isinstance(crit_detail, dict) else "No detail available."
            sentences = [s.strip() for s in reasoning.replace(". ", ".|").split("|") if s.strip() and len(s.strip()) > 10]
            rows_html = "".join(
                f'<p style="font-size:13px; color:#4A4A4A; margin:4px 0; padding-left:12px; border-left:2px solid #E5E5E5;">• {s}</p>'
                for s in sentences[:4]
            )

        st.markdown(f"""
        <div style="background:#FFFFFF; border:1px solid #E5E5E5; border-radius:12px; padding:20px; margin:8px 0 16px 0; box-shadow:0 2px 8px rgba(0,0,0,0.06);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <p style="font-weight:600; font-size:14px; color:#111111; margin:0;">{name_map.get(selected, selected)}</p>
                <p style="font-size:12px; color:#9CA3AF; margin:0;">Click card again to close</p>
            </div>
            {rows_html}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

    # ── Bottom two-column section ─────────────────────────────────────────────
    left, right = st.columns([1.5, 1])

    with left:
        # Single unified card: Broker Brief + divider + Key Gaps
        gaps_html = "".join(f'<div class="gap-item">⚠️ {g}</div>' for g in key_gaps) or "<p style='color:#9CA3AF;margin:0;'>None identified.</p>"
        st.markdown(f"""
        <div class="sedge-card">
            <h3>Broker Brief</h3>
            <p style="margin-bottom:0;">{broker_brief}</p>
            <hr style="border:none;border-top:1px solid #F0EDEA;margin:16px 0;">
            <h3>Key Gaps</h3>
            {gaps_html}
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Agent Reasoning"):
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
        if show_outreach and total >= 45:
            founder_name    = state.get("founder_name", "") or "Founder"
            founder_email   = state.get("founder_email", "")
            email_draft     = state.get("email_draft", "")
            outreach_angle  = state.get("signals_found", {}).get("score_detail", {}).get("outreach_angle", "")

            # Parse subject from draft (first "Subject: " line) or default
            email_subject = f"Partnership Opportunity — {display_name}"
            email_body    = email_draft
            for line in email_draft.splitlines():
                if line.lower().startswith("subject:"):
                    email_subject = line.split(":", 1)[1].strip()
                    email_body = email_draft[email_draft.index(line) + len(line):].lstrip("\n")
                    break

            angle_html = f'<div style="font-size:12px; color:#6B7280; font-style:italic; margin-bottom:10px;">💡 {outreach_angle}</div>' if outreach_angle else ""
            st.html(f"""
<div style="background:#FFFFFF; border:1px solid #E5E5E5; border-radius:12px; padding:16px 20px; margin-bottom:8px;">
<div style="font-size:11px; font-weight:700; color:#9CA3AF; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:8px;">Outreach Draft</div>
{angle_html}
<div style="padding:8px 0; border-bottom:1px solid #F3F4F6;">
<span style="font-size:12px; color:#9CA3AF;">To</span>
<span style="font-size:13px; font-weight:500; color:#111111; margin-left:16px;">{founder_name}</span>
<span style="font-size:12px; color:#9CA3AF; margin-left:8px;">— verify email before sending</span>
</div>
<div style="padding:8px 0;">
<span style="font-size:12px; color:#9CA3AF;">Subject</span>
<span style="font-size:13px; color:#111111; margin-left:16px;">{email_subject}</span>
</div>
</div>
""")

            edited_body = st.text_area(
                "",
                value=email_body,
                height=220,
                key="email_draft_area",
                label_visibility="collapsed",
            )

            copy_js = edited_body.replace("`", "\\`").replace("\n", "\\n")
            st.html(f"""
<script>
function copyDraft() {{
navigator.clipboard.writeText(`{copy_js}`).then(function() {{
document.getElementById('copy-btn').innerText = '✓ Copied to clipboard';
document.getElementById('copy-btn').style.background = '#1B7A4A';
setTimeout(() => {{
document.getElementById('copy-btn').innerText = '📋 Copy to clipboard';
document.getElementById('copy-btn').style.background = '#1B4F72';
}}, 2500);
}});
}}
</script>
<div style="margin-top:8px;">
<button id="copy-btn" onclick="copyDraft()" style="width:100%; background:#1B4F72; color:#FFFFFF; border:none; border-radius:8px; padding:11px 16px; font-size:14px; font-weight:600; cursor:pointer; font-family:Inter,sans-serif; margin-bottom:8px;">📋 Copy to clipboard</button>
</div>
""")

            reject = st.button("✗ Discard", key="reject_btn", use_container_width=True)
            return {"approve": False, "reject": reject, "edited_draft": edited_body}

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
                <p style="color:#4A6A7A;">This brand scored {total}/100 — below the 45-point threshold.
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
<div style="padding: 8px 0 4px 0;">
    <span style="font-size:26px; font-weight:700; color:#111111; font-family:Inter,sans-serif;">Brand Scout</span>
    <span style="font-size:14px; color:#9CA3AF; margin-left:8px; font-family:Inter,sans-serif;">by Sedge</span>
</div>
<p style="color:#9CA3AF; font-size:13px; margin-top:2px; margin-bottom:0;">AI-powered brand evaluation for CPG brokers</p>
<hr style="border:none; border-top:1px solid #EBEBEB; margin-top:16px; margin-bottom:32px;">
""", unsafe_allow_html=True)


# ── Phase: idle ───────────────────────────────────────────────────────────────
if st.session_state.phase == "idle":
    st.html("""
<div style="padding: 40px 60px;">

    <div style="text-align:center; margin-bottom:48px;">
        <p style="font-size:11px; font-weight:700; color:#9CA3AF; text-transform:uppercase; letter-spacing:0.12em; margin-bottom:12px;">Brand Scout by Sedge</p>
        <h2 style="font-size:28px; font-weight:700; color:#111111; margin:0 0 12px 0; letter-spacing:-0.5px;">AI-powered brand evaluation for CPG brokers</h2>
        <p style="font-size:15px; color:#6B6B6B; max-width:480px; margin:0 auto; line-height:1.6;">
            Research any brand across 10+ sources in under 60 seconds.
            Get a scored brief, know exactly where it fits, and send a personalized outreach — all in one workflow.
        </p>
    </div>

    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; margin-bottom:48px;">

        <div style="background:#ECFDF5; border-radius:12px; padding:20px; border:1px solid #6EE7B7;">
            <div style="font-size:20px; margin-bottom:8px;">🟢</div>
            <div style="font-size:14px; font-weight:700; color:#065F46; margin-bottom:4px;">Broker Ready · 45–69</div>
            <div style="font-size:12px; color:#047857; font-weight:500; margin-bottom:8px;">Reach out now</div>
            <p style="font-size:12px; color:#4A4A4A; margin:0; line-height:1.5;">
                Emerging brand in the sweet spot — enough traction to be credible, not yet locked into national distribution.
                Your window to open doors they don't have yet.
            </p>
        </div>

        <div style="background:#FFFBEB; border-radius:12px; padding:20px; border:1px solid #FDE68A;">
            <div style="font-size:20px; margin-bottom:8px;">🟡</div>
            <div style="font-size:14px; font-weight:700; color:#92400E; margin-bottom:4px;">Established · 70+</div>
            <div style="font-size:12px; color:#B45309; font-weight:500; margin-bottom:8px;">Verify broker need first</div>
            <p style="font-size:12px; color:#4A4A4A; margin:0; line-height:1.5;">
                Proven brand, likely already working with brokers.
                Pitch angle: why you're better than their current broker — deeper relationships, more attentive service, better data.
            </p>
        </div>

        <div style="background:#FEF2F2; border-radius:12px; padding:20px; border:1px solid #FECACA;">
            <div style="font-size:20px; margin-bottom:8px;">🔴</div>
            <div style="font-size:14px; font-weight:700; color:#991B1B; margin-bottom:4px;">Too Early · below 45</div>
            <div style="font-size:12px; color:#B91C1C; font-weight:500; margin-bottom:8px;">Check back in 6 months</div>
            <p style="font-size:12px; color:#4A4A4A; margin:0; line-height:1.5;">
                Not enough traction yet. Missing velocity proof, distribution, or brand story clarity.
                No outreach drafted — invest your time elsewhere.
            </p>
        </div>

    </div>

    <div style="background:#FFFFFF; border:1px solid #E5E5E5; border-radius:12px; padding:24px; margin-bottom:32px;">
        <p style="font-size:11px; font-weight:700; color:#9CA3AF; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:16px;">How Scoring Works</p>
        <p style="font-size:13px; color:#4A4A4A; margin-bottom:20px; line-height:1.6;">
            Built from 150+ interviews with independent food brokers, CPG founders, distributors, and retail buyers.
        </p>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">

            <div style="padding:14px; background:#F9FAFB; border-radius:8px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                    <span style="font-size:13px; font-weight:600; color:#111111;">Velocity Proof</span>
                    <span style="font-size:12px; font-weight:600; color:#1B4F72; background:#EBF5FB; padding:2px 8px; border-radius:99px;">25 pts</span>
                </div>
                <p style="font-size:12px; color:#6B6B6B; margin:0; line-height:1.5;">Has this brand proven real consumers buy it repeatedly without heavy promos? Amazon reviews, Subscribe &amp; Save, Instacart presence, trade press sell-through.</p>
            </div>

            <div style="padding:14px; background:#F9FAFB; border-radius:8px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                    <span style="font-size:13px; font-weight:600; color:#111111;">Distribution Density</span>
                    <span style="font-size:12px; font-weight:600; color:#1B4F72; background:#EBF5FB; padding:2px 8px; border-radius:99px;">20 pts</span>
                </div>
                <p style="font-size:12px; color:#6B6B6B; margin:0; line-height:1.5;">Rewards proven retail footprint at any scale. More doors and national chain presence = higher score. Whole Foods, Target, Walmart, Sprouts, Costco, Faire.</p>
            </div>

            <div style="padding:14px; background:#F9FAFB; border-radius:8px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                    <span style="font-size:13px; font-weight:600; color:#111111;">Margin Viability</span>
                    <span style="font-size:12px; font-weight:600; color:#1B4F72; background:#EBF5FB; padding:2px 8px; border-radius:99px;">20 pts</span>
                </div>
                <p style="font-size:12px; color:#6B6B6B; margin:0; line-height:1.5;">Can this brand survive the retail cost stack — distributor markup (12–28%), broker commission (5%), free fill, slotting fees? Minimum 50% gross margin needed.</p>
            </div>

            <div style="padding:14px; background:#F9FAFB; border-radius:8px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                    <span style="font-size:13px; font-weight:600; color:#111111;">Brand Story Clarity</span>
                    <span style="font-size:12px; font-weight:600; color:#1B4F72; background:#EBF5FB; padding:2px 8px; border-radius:99px;">20 pts</span>
                </div>
                <p style="font-size:12px; color:#6B6B6B; margin:0; line-height:1.5;">Can a broker rep explain this brand to a buyer in 30 seconds? Clear hero product, specific consumer, defined differentiation. Instagram following, trade press, Expo West.</p>
            </div>

            <div style="padding:14px; background:#F9FAFB; border-radius:8px; grid-column:1/-1;">
                <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                    <span style="font-size:13px; font-weight:600; color:#111111;">Promotional Independence</span>
                    <span style="font-size:12px; font-weight:600; color:#1B4F72; background:#EBF5FB; padding:2px 8px; border-radius:99px;">15 pts</span>
                </div>
                <p style="font-size:12px; color:#6B6B6B; margin:0; line-height:1.5;">Can this brand generate demand without the broker funding every promo? DTC channel, subscription model, organic social following, low TPR frequency, Subscribe &amp; Save.</p>
            </div>

        </div>

        <p style="font-size:11px; color:#9CA3AF; margin-top:16px; font-style:italic;">
            Missing data scores at 50% of max — absence of information is neutral, not negative. Only active negative signals reduce scores below the neutral floor.
        </p>
    </div>

</div>
    """)


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
    st.session_state.extracted_fields = (final or {}).get("extracted_fields", {})

    if interrupt_data:
        st.session_state.interrupt_data = interrupt_data
        st.session_state.phase = "awaiting_approval"
    else:
        verdict = (final or {}).get("verdict", "below_threshold")
        st.session_state.phase = "too_early" if verdict == "below_threshold" else "done"

    st.rerun()


# ── Phase: awaiting_approval ──────────────────────────────────────────────────
elif st.session_state.phase == "awaiting_approval":
    data  = st.session_state.interrupt_data or {}
    final = st.session_state.final_state or {}
    # Merge interrupt data into final so render_results has everything
    merged = {**final, **data}

    actions = render_results(merged, show_outreach=True)

    if actions.get("reject"):
        st.session_state.phase = "rejected"
        st.rerun()


# ── Phase: too_early ─────────────────────────────────────────────────────────
elif st.session_state.phase in ("too_early", "below_threshold"):
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
