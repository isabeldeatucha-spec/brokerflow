"""
Global CSS injection for every Sedge page.
Call inject_global_css() once at the top of any render function.
This is the single source of truth — do NOT add <style> blocks elsewhere.
"""
from __future__ import annotations

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Kill Streamlit chrome ──────────────────────────────────────────────── */
#MainMenu, footer,
header[data-testid="stHeader"],
.stDeployButton,
[data-testid="stToolbar"],
[data-testid="stStatusWidget"],
[data-testid="stDecoration"],
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] { display: none !important; }

/* Kill material-icon text leak */
span[data-baseweb="icon"],
span.material-icons, span.material-icons-outlined,
span.material-symbols-rounded, span.material-symbols-outlined,
[class*="material-icon"],
[class*="ejhh0er"],
[data-testid="stExpanderToggleIcon"],
details > summary > span:first-child > span:first-child > span:first-child {
    font-size: 0 !important;
    width: 0 !important;
    overflow: hidden !important;
    display: inline-block !important;
    line-height: 0 !important;
}

/* ── Canvas ─────────────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }

.stApp,
.main,
section[data-testid="stMain"],
section[data-testid="stMain"] > div,
[data-testid="stAppViewContainer"] {
    background: #FAFAF7 !important;
    font-family: 'Inter', -apple-system, system-ui, sans-serif !important;
    color: #1A1A18 !important;
}

.block-container {
    padding-top: 48px !important;
    padding-bottom: 96px !important;
    max-width: 960px !important;
    overflow-y: auto !important;
    max-height: none !important;
}

.element-container { overflow: visible !important; }
section[data-testid="stMain"] { overflow-y: auto !important; }

/* ── Sidebar ────────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-right: 1px solid #EAEAE4 !important;
    min-width: 220px !important;
    max-width: 240px !important;
    transform: none !important;
    left: 0 !important;
    visibility: visible !important;
}
section[data-testid="stSidebar"] > div {
    background: #FFFFFF !important;
    padding: 0 !important;
}

/* Sidebar radio — styled as editorial nav */
section[data-testid="stSidebar"] [data-testid="stRadio"] > label {
    display: none !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {
    display: flex !important;
    flex-direction: column !important;
    gap: 1px !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] [data-baseweb="radio"] {
    width: 100% !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] [data-baseweb="radio"] > div:first-child {
    display: none !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    color: #57564F !important;
    padding: 8px 12px !important;
    border-radius: 6px !important;
    width: 100% !important;
    cursor: pointer !important;
    font-weight: 400 !important;
    transition: background 0.1s, color 0.1s !important;
    letter-spacing: 0 !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: #F2F2EE !important;
    color: #1A1A18 !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] input[type="radio"]:checked ~ div label,
section[data-testid="stSidebar"] [data-testid="stRadio"] [aria-checked="true"] label {
    background: #E8EDE9 !important;
    color: #0F3530 !important;
    font-weight: 500 !important;
}

/* Sidebar toggle */
section[data-testid="stSidebar"] .stToggle label {
    font-size: 13px !important;
    color: #57564F !important;
}
section[data-testid="stSidebar"] .stToggle {
    padding: 8px 12px !important;
}
section[data-testid="stSidebar"] .stCaption p {
    font-size: 12px !important;
    color: #8B8A83 !important;
    padding-left: 12px !important;
}

/* ── Typography ─────────────────────────────────────────────────────────── */
h1, h2, h3, h4 {
    font-family: 'Inter', sans-serif !important;
    color: #1A1A18 !important;
    font-weight: 600 !important;
    line-height: 1.25 !important;
}
p, li, span {
    font-family: 'Inter', sans-serif !important;
    color: #57564F !important;
    font-size: 14px !important;
    line-height: 1.6 !important;
}

/* Semantic type classes */
.sedge-h1 {
    font-family: 'Instrument Serif', Georgia, serif !important;
    font-size: 52px !important;
    font-weight: 400 !important;
    line-height: 1.05 !important;
    letter-spacing: -0.02em !important;
    color: #1A1A18 !important;
    margin: 0 0 8px 0 !important;
}
.sedge-subtitle {
    font-family: 'Instrument Serif', Georgia, serif !important;
    font-size: 20px !important;
    font-style: italic !important;
    font-weight: 400 !important;
    color: #57564F !important;
    line-height: 1.4 !important;
    margin: 0 0 48px 0 !important;
}
.sedge-section-title {
    font-family: 'Inter', sans-serif !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    color: #8B8A83 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    margin: 0 0 16px 0 !important;
}
.sedge-body {
    font-family: 'Inter', sans-serif !important;
    font-size: 15px !important;
    line-height: 1.65 !important;
    color: #1A1A18 !important;
}
.sedge-caption {
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    color: #8B8A83 !important;
    line-height: 1.5 !important;
}
.sedge-number {
    font-family: 'JetBrains Mono', 'SF Mono', monospace !important;
    font-feature-settings: "tnum" !important;
    font-variant-numeric: tabular-nums !important;
}

/* Brand headline on result pages */
.sedge-brand-h1 {
    font-family: 'Instrument Serif', Georgia, serif !important;
    font-size: 52px !important;
    font-weight: 400 !important;
    letter-spacing: -0.02em !important;
    color: #1A1A18 !important;
    line-height: 1.05 !important;
    margin: 4px 0 16px 0 !important;
}
.sedge-score-display {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 52px !important;
    font-weight: 400 !important;
    color: #1A1A18 !important;
    line-height: 1 !important;
}
.sedge-broker-brief {
    font-family: 'Instrument Serif', Georgia, serif !important;
    font-size: 18px !important;
    font-style: italic !important;
    color: #57564F !important;
    line-height: 1.65 !important;
}

/* ── Cards — hairline borders, zero shadow ─────────────────────────────── */
.sedge-card {
    background: #FFFFFF !important;
    border: 1px solid #EAEAE4 !important;
    border-radius: 10px !important;
    padding: 24px !important;
    box-shadow: none !important;
    margin-bottom: 12px !important;
}
.sedge-card-hover:hover {
    border-color: #1A1A18 !important;
    transition: border-color 0.15s ease !important;
}

/* Legacy classes — remap to hairline style */
.criterion-card,
.email-panel,
.watchlist-card {
    background: #FFFFFF !important;
    border: 1px solid #EAEAE4 !important;
    border-radius: 10px !important;
    padding: 20px !important;
    box-shadow: none !important;
    margin-bottom: 12px !important;
}

/* ── Pills / verdicts ───────────────────────────────────────────────────── */
.sedge-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 99px;
    font-size: 12px;
    font-weight: 500;
    font-family: 'Inter', sans-serif;
    border: 1px solid;
}
.sedge-pill-established {
    background: #FEF9E7;
    border-color: #F4E4A8;
    color: #6B5414;
}
.sedge-pill-ready {
    background: #E8EDE9;
    border-color: #C5D1C8;
    color: #1A3F2A;
}
.sedge-pill-early {
    background: #FBEAEA;
    border-color: #E8C5C5;
    color: #6B1F1F;
}

/* Legacy badge classes → same as pills */
.badge-established { background: #FEF9E7; color: #6B5414; padding: 4px 10px; border-radius: 99px; font-size: 12px; font-weight: 500; border: 1px solid #F4E4A8; }
.badge-ready       { background: #E8EDE9; color: #1A3F2A; padding: 4px 10px; border-radius: 99px; font-size: 12px; font-weight: 500; border: 1px solid #C5D1C8; }
.badge-early       { background: #FBEAEA; color: #6B1F1F; padding: 4px 10px; border-radius: 99px; font-size: 12px; font-weight: 500; border: 1px solid #E8C5C5; }
.category-pill     { background: #F2F2EE; color: #57564F; padding: 3px 10px; border-radius: 99px; font-size: 12px; font-weight: 500; border: 1px solid #EAEAE4; }

/* ── Buttons — near-black primary ──────────────────────────────────────── */
.stButton > button,
div[data-testid="stButton"] button,
div[data-testid^="stButton"] button {
    background: #1A1A18 !important;
    background-color: #1A1A18 !important;
    color: #FAFAF7 !important;
    -webkit-text-fill-color: #FAFAF7 !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 10px 16px !important;
    cursor: pointer !important;
    transition: background 0.15s !important;
    box-shadow: none !important;
}
.stButton > button:hover,
div[data-testid="stButton"] button:hover,
div[data-testid^="stButton"] button:hover {
    background: #2D2D2A !important;
    background-color: #2D2D2A !important;
}
.stButton > button p,
.stButton > button span,
div[data-testid="stButton"] button p,
div[data-testid="stButton"] button span,
div[data-testid^="stButton"] button p,
div[data-testid^="stButton"] button span {
    color: #FAFAF7 !important;
    -webkit-text-fill-color: #FAFAF7 !important;
}

/* Secondary/ghost buttons: approve/reject/discard get accent colors */
div[data-testid="stButton-approve_btn"] button { background: #2D5F3F !important; background-color: #2D5F3F !important; }
div[data-testid="stButton-reject_btn"] button,
div[data-testid="stButton-reject_btn"] button  { background: #8B2F2F !important; background-color: #8B2F2F !important; }
div[data-testid="stButton-approve_btn"] button p,
div[data-testid="stButton-reject_btn"] button p { color: #FAFAF7 !important; -webkit-text-fill-color: #FAFAF7 !important; }

/* Sidebar button override */
section[data-testid="stSidebar"] .stButton > button {
    background: #1A1A18 !important;
    color: #FAFAF7 !important;
    -webkit-text-fill-color: #FAFAF7 !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
}

/* Download buttons */
.stDownloadButton > button {
    background: #1A1A18 !important;
    color: #FAFAF7 !important;
    -webkit-text-fill-color: #FAFAF7 !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    box-shadow: none !important;
}

/* ── Inputs ─────────────────────────────────────────────────────────────── */
.stTextInput input,
.stTextInput input:focus {
    font-family: 'Inter', sans-serif !important;
    color: #1A1A18 !important;
    -webkit-text-fill-color: #1A1A18 !important;
    background-color: #FFFFFF !important;
    caret-color: #1A1A18 !important;
    border-radius: 6px !important;
    border: 1px solid #EAEAE4 !important;
    padding: 10px 14px !important;
    font-size: 14px !important;
    box-shadow: none !important;
}
.stTextInput input:focus {
    border-color: #1A1A18 !important;
    box-shadow: none !important;
}
.stTextInput input::placeholder {
    color: #8B8A83 !important;
    -webkit-text-fill-color: #8B8A83 !important;
}
.stTextArea textarea {
    font-family: 'Inter', sans-serif !important;
    color: #1A1A18 !important;
    -webkit-text-fill-color: #1A1A18 !important;
    background: #FFFFFF !important;
    border: 1px solid #EAEAE4 !important;
    border-radius: 6px !important;
    font-size: 14px !important;
    line-height: 1.6 !important;
    box-shadow: none !important;
}
.stTextArea textarea:focus {
    border-color: #1A1A18 !important;
    box-shadow: none !important;
}
[data-testid="stTextAreaResizeHandle"] ~ span { display: none !important; }
.stTextArea div[class*="shortcut"] { display: none !important; }

/* ── Selectbox / Radio / Checkbox ───────────────────────────────────────── */
div[data-testid="stRadio"] label {
    font-size: 14px !important;
    color: #57564F !important;
    font-family: 'Inter', sans-serif !important;
}
div[data-testid="stRadio"] input[type="radio"] {
    accent-color: #0F3530 !important;
}
div[data-testid="stCheckbox"] label {
    font-size: 14px !important;
    color: #1A1A18 !important;
    font-family: 'Inter', sans-serif !important;
}
div[data-testid="stCheckbox"] input[type="checkbox"] {
    accent-color: #0F3530 !important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] {
    background: #FFFFFF !important;
    border: 1px solid #EAEAE4 !important;
    border-radius: 6px !important;
    font-size: 14px !important;
    box-shadow: none !important;
}

/* ── Expanders ──────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #EAEAE4 !important;
    border-radius: 6px !important;
    background: #FFFFFF !important;
    box-shadow: none !important;
}
[data-testid="stExpander"] summary {
    font-size: 14px !important;
    font-weight: 500 !important;
    color: #1A1A18 !important;
    font-family: 'Inter', sans-serif !important;
    padding: 12px 16px !important;
}

/* ── Info/Warning/Error banners ─────────────────────────────────────────── */
[data-testid="stAlertContainer"],
.stAlert {
    border-radius: 6px !important;
    border-width: 1px !important;
    box-shadow: none !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
}

/* ── Progress / score bars ──────────────────────────────────────────────── */
.sedge-progress-track { background: #F2F2EE; border-radius: 99px; height: 4px; width: 100%; }
.sedge-progress-fill  { border-radius: 99px; height: 4px; }

/* ── Gap items ─────────────────────────────────────────────────────────── */
.gap-item {
    border-left: 2px solid #8B6914;
    padding: 8px 12px;
    border-radius: 0 6px 6px 0;
    margin-bottom: 8px;
    font-size: 13px;
    color: #57564F;
    background: #FAFAF7;
}

/* ── Reflection items ───────────────────────────────────────────────────── */
.reflection-item {
    border-left: 2px solid #EAEAE4;
    padding-left: 16px;
    margin-bottom: 12px;
    font-size: 13px;
    color: #57564F;
}
.reflection-label {
    font-size: 11px;
    font-weight: 600;
    color: #0F3530;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 4px;
    font-family: 'Inter', sans-serif;
}

/* ── Score/criterion rows ───────────────────────────────────────────────── */
.score-big {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 52px !important;
    font-weight: 400 !important;
    color: #1A1A18 !important;
    line-height: 1 !important;
}
.score-label {
    font-size: 12px !important;
    color: #8B8A83 !important;
    font-family: 'Inter', sans-serif !important;
    margin-top: 4px !important;
}

/* ── Micro-animations ───────────────────────────────────────────────────── */
@keyframes sedge-fade-in {
    from { opacity: 0; transform: translateY(4px); }
    to   { opacity: 1; transform: translateY(0); }
}
.sedge-fade-in { animation: sedge-fade-in 0.3s ease-out; }

@keyframes sedge-spin {
    to { transform: rotate(360deg); }
}
.sedge-spin { animation: sedge-spin 0.8s linear infinite; }
.sedge-spin svg { animation: sedge-spin 0.8s linear infinite; }

/* ── Pipeline progress rows ─────────────────────────────────────────────── */
.sedge-pipeline-row {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 14px 0;
    border-bottom: 1px solid #F2F2EE;
}
.sedge-pipeline-row:last-child { border-bottom: none; }
.sedge-pipeline-icon { width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.sedge-pipeline-label { font-size: 14px; font-weight: 500; color: #1A1A18; font-family: 'Inter', sans-serif; }
.sedge-pipeline-msg   { font-size: 13px; color: #8B8A83; margin-top: 2px; font-family: 'Inter', sans-serif; }

/* ── Recent activity list ───────────────────────────────────────────────── */
.sedge-activity-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid #F2F2EE;
}
.sedge-activity-row:last-child { border-bottom: none; }

/* ── Tabs ───────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    color: #57564F !important;
}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
    color: #1A1A18 !important;
    border-bottom-color: #1A1A18 !important;
}

/* ── Scrollbar — thin editorial ─────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #EAEAE4; border-radius: 99px; }
</style>
"""


def inject_global_css() -> None:
    """Inject the Sedge design system CSS into the current Streamlit page."""
    import streamlit as st
    st.markdown(_CSS, unsafe_allow_html=True)
