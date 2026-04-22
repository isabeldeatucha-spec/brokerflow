"""
Sedge — unified multi-agent entry point.

Run:
    cd /Users/isabelatucha/sedge
    streamlit run ui/sedge_app.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# llm_shim must be imported before any anthropic import
import agents.llm_shim  # noqa: F401, E402

import streamlit as st

from memory import _get_client

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Sedge",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif !important; }

.stApp { background: #F7F5F2; }

.main { overflow-y: auto !important; }
.block-container {
    overflow-y: auto !important;
    max-height: none !important;
    padding-bottom: 120px !important;
}
section[data-testid="stMain"]       { overflow-y: auto !important; }
section[data-testid="stMain"] > div { overflow-y: auto !important; }
.element-container                  { overflow: visible !important; }

section[data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-right: 1px solid #E5E5E5 !important;
    min-width: 260px !important;
    transform: none !important;
    left: 0 !important;
    visibility: visible !important;
}
section[data-testid="stSidebar"] > div {
    background: #FFFFFF !important;
    padding: 24px 16px 80px 16px !important;
}
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

.badge-established { background:#FEF3C7; color:#92400E; padding:4px 12px; border-radius:20px; font-size:13px; font-weight:600; }
.badge-ready       { background:#D1FAE5; color:#065F46; padding:4px 12px; border-radius:20px; font-size:13px; font-weight:600; }
.badge-early       { background:#FEE2E2; color:#991B1B; padding:4px 12px; border-radius:20px; font-size:13px; font-weight:600; }

.category-pill { background:#EBF5FB; color:#1B4F72; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:500; }

/* Sidebar nav radio */
section[data-testid="stSidebar"] .stRadio > div { gap: 4px !important; }
section[data-testid="stSidebar"] .stRadio label {
    color: #4A4A4A !important;
    font-size: 14px !important;
    padding: 6px 8px !important;
    border-radius: 8px !important;
    cursor: pointer !important;
}
section[data-testid="stSidebar"] .stRadio input[type="radio"] {
    accent-color: #1B4F72 !important;
}

/* All buttons navy */
.stButton > button,
div[data-testid="stButton"] button {
    background: #1B4F72 !important;
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
}
.stButton > button *,
div[data-testid="stButton"] button * {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

section[data-testid="stSidebar"] .stButton > button {
    background: #1B4F72 !important;
    color: white !important;
    -webkit-text-fill-color: white !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    width: 100% !important;
}

/* Input */
.stTextInput input {
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
    background-color: #FFFFFF !important;
    border-radius: 10px !important;
    border: 1.5px solid #E5E7EB !important;
    padding: 10px 14px !important;
    font-size: 14px !important;
}
.stTextInput input:focus {
    border-color: #1B4F72 !important;
    box-shadow: 0 0 0 3px rgba(27,79,114,0.08) !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Sidebar nav ───────────────────────────────────────────────────────────────

NAV_OPTIONS = [
    "🏠  Dashboard",
    "🔍  Brand Scout",
    "📬  Retailer Pitcher",
    "📋  Admin & Ops",
    "📊  Portfolio Mgr",
]

# _nav_idx is a plain state key (not a widget key), so it can be written freely.
if "_nav_idx" not in st.session_state:
    st.session_state["_nav_idx"] = 0

# Handle forced navigation before sidebar renders so the radio shows the right selection.
_forced = st.session_state.pop("forced_page", None)
if _forced and _forced in NAV_OPTIONS:
    st.session_state["_nav_idx"] = NAV_OPTIONS.index(_forced)

with st.sidebar:
    st.markdown(
        '<p style="font-size:20px; font-weight:700; color:#111111; '
        'letter-spacing:-0.3px; margin-bottom:4px;">🌾 Sedge</p>'
        '<p style="font-size:11px; color:#9CA3AF; margin-bottom:24px;">'
        "AI tools for independent food brokers</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-size:11px; font-weight:700; color:#9CA3AF; '
        'text-transform:uppercase; letter-spacing:0.1em; margin-bottom:8px;">Navigation</p>',
        unsafe_allow_html=True,
    )
    # Use index= (not key=) so we can freely write _nav_idx from outside.
    _nav_selected = st.radio(
        "nav",
        options=NAV_OPTIONS,
        index=st.session_state["_nav_idx"],
        label_visibility="collapsed",
    )
    # Sync user's direct radio click back into _nav_idx.
    st.session_state["_nav_idx"] = NAV_OPTIONS.index(_nav_selected)

    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    st.markdown(
        '<p style="font-size:11px; font-weight:700; color:#9CA3AF; text-transform:uppercase; '
        'letter-spacing:0.1em; margin-bottom:8px;">Settings</p>',
        unsafe_allow_html=True,
    )
    demo_on = st.toggle(
        "Demo mode",
        value=st.session_state.get("demo_mode", False),
        key="_demo_toggle",
        help="Uses cached results for Chomps, Fishwife, and Graza — no live LLM calls.",
    )
    st.session_state["demo_mode"] = demo_on
    if demo_on:
        st.caption("🎬 Cached results active")

# ── Dashboard ─────────────────────────────────────────────────────────────────

def _fetch_stats() -> dict:
    """Pull live counts from Supabase. Each table is queried independently so a
    missing table (e.g. new_item_forms before first run) doesn't kill the rest."""
    defaults = {
        "brands_evaluated": 0,
        "pitches_drafted": 0,
        "forms_filled": 0,
        "recent_activity": [],
    }
    evaluations: list[dict] = []
    pitches: list[dict] = []
    forms: list[dict] = []

    try:
        client = _get_client()
    except Exception as exc:
        print(f"[Dashboard] Supabase client failed: {exc}")
        return defaults

    try:
        ev_res = client.table("brand_evaluations").select("brand_name, score, verdict, evaluated_at").order("evaluated_at", desc=True).limit(50).execute()
        evaluations = ev_res.data or []
        defaults["brands_evaluated"] = len(evaluations)
    except Exception as exc:
        print(f"[Dashboard] brand_evaluations query failed: {exc}")

    try:
        pitch_res = client.table("retailer_pitches").select("brand_name, buyer, created_at").order("created_at", desc=True).limit(50).execute()
        pitches = pitch_res.data or []
        defaults["pitches_drafted"] = len(pitches)
    except Exception as exc:
        print(f"[Dashboard] retailer_pitches query failed: {exc}")

    try:
        form_res = client.table("new_item_forms").select("brand_name, retailer, generated_at").order("generated_at", desc=True).limit(50).execute()
        forms = form_res.data or []
        defaults["forms_filled"] = len(forms)
    except Exception as exc:
        print(f"[Dashboard] new_item_forms query failed: {exc}")

    activity: list[dict] = []
    for row in evaluations[:5]:
        activity.append({
            "label": f"Brand Scout evaluated {row['brand_name']} — {row['score']}/100",
            "ts": (row.get("evaluated_at") or "")[:10],
            "icon": "🔍",
        })
    for row in pitches[:5]:
        activity.append({
            "label": f"Retailer Pitcher drafted pitch for {row['brand_name']} → {row.get('buyer') or '—'}",
            "ts": (row.get("created_at") or "")[:10],
            "icon": "📬",
        })
    for row in forms[:5]:
        activity.append({
            "label": f"Admin & Ops filled WFM form for {row['brand_name']} / {row.get('retailer') or '—'}",
            "ts": (row.get("generated_at") or "")[:10],
            "icon": "📋",
        })
    activity.sort(key=lambda x: x["ts"], reverse=True)
    defaults["recent_activity"] = activity[:10]
    return defaults


def render_dashboard() -> None:
    st.markdown(
        """
<div style="padding: 8px 0 4px 0;">
    <span style="font-size:26px; font-weight:700; color:#111111;">Dashboard</span>
    <span style="font-size:14px; color:#9CA3AF; margin-left:8px;">by Sedge</span>
</div>
<p style="color:#9CA3AF; font-size:13px; margin-top:2px; margin-bottom:0;">AI tools for independent food brokers</p>
<hr style="border:none; border-top:1px solid #EBEBEB; margin-top:16px; margin-bottom:32px;">
""",
        unsafe_allow_html=True,
    )

    stats = _fetch_stats()

    # ── Hero stat row ─────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    for col, label, value, color in [
        (c1, "Brands Evaluated", stats["brands_evaluated"], "#1B4F72"),
        (c2, "Pitches Drafted",  stats["pitches_drafted"],  "#065F46"),
        (c3, "WFM Forms Filled", stats["forms_filled"],     "#92400E"),
        (c4, "Agents Active",    3,                          "#6B21A8"),
    ]:
        with col:
            col.markdown(
                f'<div class="sedge-card" style="text-align:center;padding:20px 16px;">'
                f'<div style="font-size:36px;font-weight:700;color:{color};line-height:1;">'
                f'{value}</div>'
                f'<div style="font-size:12px;color:#9CA3AF;margin-top:6px;font-weight:500;">'
                f'{label}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

    # ── Demo query bar ────────────────────────────────────────────────────────
    st.markdown(
        '<div class="sedge-card" style="padding:20px 24px;margin-bottom:8px;">'
        '<p style="font-size:13px;font-weight:700;color:#111111;margin:0 0 10px 0;">'
        '🚀 Try it live</p>',
        unsafe_allow_html=True,
    )
    _qcol, _bcol = st.columns([6, 1])
    with _qcol:
        _demo_brand = st.text_input(
            "",
            placeholder="Enter any CPG brand name…  (try: Fishwife, Graza, Chomps)",
            key="dash_query_input",
            label_visibility="collapsed",
        )
    with _bcol:
        _demo_go = st.button("▶", key="dash_query_go", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if _demo_go:
        _brand = _demo_brand.strip()
        if _brand:
            st.session_state["handoff_brand"] = _brand.title()
            st.session_state["_brand_name"] = _brand
            st.session_state["_website_url"] = ""
            st.session_state["_auto_run"] = True
            st.session_state["forced_page"] = "🔍  Brand Scout"
            # Reset brand scout phase so it doesn't show stale results
            st.session_state["phase"] = "idle"
            st.rerun()
        else:
            st.warning("Enter a brand name first.")

    # ── Agent cards ───────────────────────────────────────────────────────────
    AGENTS = [
        {
            "icon": "🔍",
            "title": "Brand Scout",
            "desc": "Research any CPG brand across 10+ sources in under 60 seconds. Get a scored brief and personalized outreach draft.",
            "stat": f"{stats['brands_evaluated']} brands evaluated",
            "nav": "🔍  Brand Scout",
            "btn": "Open Brand Scout",
        },
        {
            "icon": "📬",
            "title": "Retailer Pitcher",
            "desc": "Draft a buyer-specific outreach email and 1-page sell sheet for any brand in your book.",
            "stat": f"{stats['pitches_drafted']} pitches drafted",
            "nav": "📬  Retailer Pitcher",
            "btn": "Open Retailer Pitcher",
        },
        {
            "icon": "📋",
            "title": "Admin & Ops",
            "desc": "Auto-fill the Whole Foods New Item Setup Form from Brand Scout data. Flag gaps before your buyer meeting.",
            "stat": f"{stats['forms_filled']} forms filled",
            "nav": "📋  Admin & Ops",
            "btn": "Open Admin & Ops",
        },
        {
            "icon": "📊",
            "title": "Portfolio Manager",
            "desc": "Track your full brand book, set reminder cadences, and surface re-evaluation alerts across your pipeline.",
            "stat": "Coming soon",
            "nav": "📊  Portfolio Mgr",
            "btn": "Coming soon",
            "disabled": True,
        },
    ]

    cols = st.columns(4)
    for col, agent in zip(cols, AGENTS):
        with col:
            col.markdown(
                f'<div class="sedge-card" style="padding:20px;min-height:200px;">'
                f'<div style="font-size:28px;margin-bottom:8px;">{agent["icon"]}</div>'
                f'<div style="font-size:15px;font-weight:700;color:#111111;margin-bottom:6px;">{agent["title"]}</div>'
                f'<p style="font-size:12px;color:#6B6B6B;line-height:1.5;margin-bottom:12px;">{agent["desc"]}</p>'
                f'<div style="font-size:11px;font-weight:600;color:#9CA3AF;">{agent["stat"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if not agent.get("disabled"):
                if col.button(agent["btn"], key=f"dash_btn_{agent['title']}", use_container_width=True):
                    st.session_state["_nav_idx"] = NAV_OPTIONS.index(agent["nav"])
                    st.rerun()
            else:
                col.markdown(
                    '<div style="background:#F3F4F6;border-radius:10px;padding:12px;text-align:center;'
                    'font-size:13px;font-weight:600;color:#9CA3AF;">Coming soon</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

    # ── Recent activity ───────────────────────────────────────────────────────
    st.markdown(
        '<p style="font-size:13px;font-weight:700;color:#111111;margin-bottom:12px;">Recent Activity</p>',
        unsafe_allow_html=True,
    )
    activity = stats["recent_activity"]
    if activity:
        rows_html = "".join(
            f'<div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #F3F4F6;">'
            f'<span style="font-size:16px;">{a["icon"]}</span>'
            f'<span style="font-size:13px;color:#4A4A4A;flex:1;">{a["label"]}</span>'
            f'<span style="font-size:11px;color:#9CA3AF;white-space:nowrap;">{a["ts"]}</span>'
            f'</div>'
            for a in activity
        )
        st.markdown(
            f'<div class="sedge-card" style="padding:16px 20px;">{rows_html}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="sedge-card" style="text-align:center;padding:32px;">'
            '<p style="color:#9CA3AF;margin:0;">No activity yet — run Brand Scout to get started.</p>'
            '</div>',
            unsafe_allow_html=True,
        )


# ── Coming soon ───────────────────────────────────────────────────────────────

def render_coming_soon(title: str) -> None:
    st.markdown(
        f'<div style="padding:8px 0 4px 0;">'
        f'<span style="font-size:26px;font-weight:700;color:#111111;">{title}</span>'
        f'</div>'
        f'<hr style="border:none;border-top:1px solid #EBEBEB;margin-top:16px;margin-bottom:32px;">',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sedge-card" style="text-align:center;padding:60px 40px;">'
        '<div style="font-size:48px;margin-bottom:16px;">🚧</div>'
        f'<h2>{title}</h2>'
        '<p style="color:#9CA3AF;max-width:400px;margin:0 auto;">This agent is coming soon. '
        "Check back after Phase 1 ships.</p>"
        '</div>',
        unsafe_allow_html=True,
    )


# ── Router ────────────────────────────────────────────────────────────────────

def _error_card(exc: Exception) -> None:
    import traceback, sys
    print(traceback.format_exc(), file=sys.stderr)
    with st.expander("Debug details", expanded=False):
        st.code(traceback.format_exc())
    st.error("Something went wrong. The team has been notified.")


page = NAV_OPTIONS[st.session_state["_nav_idx"]]

try:
    if page == "🏠  Dashboard":
        render_dashboard()

    elif page == "🔍  Brand Scout":
        from ui.brand_scout_page import render_brand_scout_page
        render_brand_scout_page()

    elif page == "📬  Retailer Pitcher":
        from ui.retailer_pitcher_page import render_retailer_pitcher_page
        render_retailer_pitcher_page()

    elif page == "📋  Admin & Ops":
        from ui.admin_ops_page import render_admin_ops_page
        render_admin_ops_page()

    elif page == "📊  Portfolio Mgr":
        render_coming_soon("Portfolio Manager")

except Exception as _page_exc:
    _error_card(_page_exc)
