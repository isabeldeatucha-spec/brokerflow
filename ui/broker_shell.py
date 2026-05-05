"""Shared broker app shell.

Renders a fixed left sidebar (BrokerFlow wordmark, QUEUE / AGENTS / BRANDS
sections) and a main content area. All authenticated broker views — the queue
and the agent pages — wrap their content in render_shell(...).

Navigation is driven by URL query params (?nav=...). The router in
brokerflow_app.py catches them, sets st.session_state.workspace, and reruns.
This keeps sidebar links as plain <a target="_self"> tags so we control the
look fully without fighting Streamlit's button widget.
"""
from __future__ import annotations

from typing import Callable

import streamlit as st


# ── Seed brand book (used for sidebar counts + queue filtering) ──────────────

BROKER_BRANDS: list[tuple[str, int]] = [
    ("Brami",        1),
    ("Olipop",       1),
    ("Spudsy",       1),
    ("Tia Lupita",   1),
    ("Banza",        0),
]


def _shell_css() -> str:
    return """
    <style>
    /* Make room for the fixed sidebar on every shell-wrapped page.
       Override global_css's 980px cap so the queue + agent pages can
       fill modern desktop widths up to 1440px. !important wins by
       source order since shell CSS injects after global. */
    .stApp .main .block-container,
    .stApp [data-testid="stMain"] .block-container,
    .stApp [data-testid="stMainBlockContainer"],
    .stApp .block-container {
        padding-left: 288px !important;   /* 240 sidebar + 48 gap */
        padding-right: 48px !important;
        padding-top: 32px !important;
        max-width: 1440px !important;
    }

    /* ── Sidebar ─────────────────────────────────────────────────────── */
    .bf-shell-sidebar {
        position: fixed;
        top: 0;
        left: 0;
        width: 240px;
        height: 100vh;
        background: #FAFAF7;
        border-right: 1px solid #EAEAE4;
        padding: 28px 18px 24px 22px;
        overflow-y: auto;
        z-index: 90;
        font-family: 'Inter', sans-serif;
    }
    .bf-shell-sidebar::-webkit-scrollbar { width: 4px; }
    .bf-shell-sidebar::-webkit-scrollbar-thumb { background: #EAEAE4; border-radius: 99px; }

    .bf-shell-wordmark,
    .bf-shell-wordmark:link,
    .bf-shell-wordmark:visited {
        display: block;
        font-family: 'Instrument Serif', Georgia, serif;
        font-size: 22px;
        font-weight: 400;
        color: #1A1A18;
        text-decoration: none;
        letter-spacing: -0.01em;
        margin-bottom: 28px;
    }
    .bf-shell-wordmark:hover { color: #1A1A18; opacity: 0.7; }

    .bf-shell-section {
        font-family: 'Inter', sans-serif;
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: #B0AFA8;
        margin: 22px 0 8px;
    }

    .bf-shell-link,
    .bf-shell-link:link,
    .bf-shell-link:visited {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        padding: 7px 10px;
        border-radius: 6px;
        font-family: 'Inter', sans-serif;
        font-size: 13.5px;
        font-weight: 400;
        color: #57564F;
        text-decoration: none;
        line-height: 1.4;
        margin: 1px 0;
        transition: background 0.12s ease, color 0.12s ease;
    }
    .bf-shell-link:hover {
        background: #F2F2EE;
        color: #1A1A18;
    }
    .bf-shell-link--active {
        background: #EFEFEA;
        color: #1A1A18 !important;
        font-weight: 600 !important;
    }
    .bf-shell-link--muted {
        color: #B0AFA8 !important;
        cursor: default;
        opacity: 0.6;
    }
    .bf-shell-link--muted:hover { background: transparent; color: #B0AFA8 !important; }

    .bf-shell-link-label { display: flex; align-items: center; gap: 8px; }

    .bf-shell-count {
        font-family: 'JetBrains Mono', 'SF Mono', monospace;
        font-feature-settings: "tnum";
        font-variant-numeric: tabular-nums;
        font-size: 11.5px;
        color: #8B8A83;
        background: transparent;
    }
    .bf-shell-link--active .bf-shell-count { color: #1A1A18; }

    .bf-shell-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #4A8A5C;
        display: inline-block;
        flex-shrink: 0;
    }

    /* ── Main top bar (breadcrumb only — ask bar lives in queue body) ─ */
    .bf-shell-topbar {
        padding: 0 0 18px;
        margin-bottom: 24px;
        border-bottom: 1px solid #F2F2EE;
    }
    .bf-crumb {
        font-family: 'Instrument Serif', Georgia, serif;
        font-size: 16px;
        line-height: 1.2;
        color: #1A1A18;
    }
    .bf-crumb-muted { color: #B0AFA8; font-style: italic; }
    .bf-crumb-bold  { font-weight: 500; }

    /* ── Mobile collapse ─────────────────────────────────────────────── */
    @media (max-width: 820px) {
        .bf-shell-sidebar {
            position: static;
            width: 100%;
            height: auto;
            border-right: none;
            border-bottom: 1px solid #EAEAE4;
            padding: 16px 20px;
            overflow-y: visible;
        }
        .stApp .block-container {
            padding-left: 1.2rem !important;
            padding-right: 1.2rem !important;
        }
        .bf-shell-topbar {
            flex-direction: column;
            align-items: flex-start;
            gap: 14px;
        }
        .bf-ask { flex: 1 1 auto; width: 100%; }
    }
    </style>
    """


# ── Sidebar items ────────────────────────────────────────────────────────────

def _queue_count(filter_key: str) -> int:
    """Counts shown next to each Queue sidebar item."""
    counts = {
        "today":     6,
        "needs_you": 2,
        "drafted":   4,
        "sent":      st.session_state.get("queue_sent_count", 0),
        "skipped":   st.session_state.get("queue_skipped_count", 0),
    }
    return counts.get(filter_key, 0)


def _link(
    href: str,
    label: str,
    *,
    count: int | None = None,
    active: bool = False,
    muted: bool = False,
    dot: bool = False,
) -> str:
    classes = ["bf-shell-link"]
    if active:
        classes.append("bf-shell-link--active")
    if muted:
        classes.append("bf-shell-link--muted")

    dot_html = '<span class="bf-shell-dot"></span>' if dot else ""
    count_html = (
        f'<span class="bf-shell-count">{count}</span>'
        if count is not None else ""
    )

    if muted:
        return (
            f'<div class="{" ".join(classes)}">'
            f'<span class="bf-shell-link-label">{label}</span>'
            f'</div>'
        )

    return (
        f'<a class="{" ".join(classes)}" href="{href}" target="_self">'
        f'<span class="bf-shell-link-label">{dot_html}{label}</span>'
        f'{count_html}</a>'
    )


def _render_sidebar(active_route: str, active_filter: str | None,
                    active_brand: str | None) -> None:
    queue_items = [
        ("today",     "Today"),
        ("needs_you", "Needs you"),
        ("drafted",   "Drafted"),
        ("sent",      "Sent"),
        ("skipped",   "Skipped"),
    ]

    queue_html = "".join(
        _link(
            f"?nav=queue&filter={key}",
            label,
            count=_queue_count(key),
            active=(active_route == "queue" and (
                (active_filter or "today") == key
            ) and not active_brand),
        )
        for key, label in queue_items
    )

    agents = [
        ("brand_scout",      "Brand Scout"),
        ("retailer_pitcher", "Retailer Pitcher"),
        ("admin_ops",        "New Item Forms"),
    ]
    agents_html = "".join(
        _link(
            f"?nav={key}",
            label,
            active=(active_route == key),
            dot=True,
        )
        for key, label in agents
    ) + _link("#", "+ more coming soon", muted=True)

    brand_count_lookup = {b: c for b, c in BROKER_BRANDS}
    brands_html = "".join(
        _link(
            f"?nav=queue&brand={brand}",
            brand,
            count=brand_count_lookup[brand],
            active=(active_route == "queue" and active_brand == brand),
        )
        for brand, _ in BROKER_BRANDS
    )

    sidebar_html = (
        '<aside class="bf-shell-sidebar">'
        '<a class="bf-shell-wordmark" href="?goto=landing" target="_self">BrokerFlow</a>'
        '<div class="bf-shell-section">QUEUE</div>'
        f'{queue_html}'
        '<div class="bf-shell-section">AGENTS</div>'
        f'{agents_html}'
        '<div class="bf-shell-section">BRANDS</div>'
        f'{brands_html}'
        '</aside>'
    )
    st.markdown(sidebar_html, unsafe_allow_html=True)


# ── Top bar (breadcrumb + ask bar) ───────────────────────────────────────────

def _crumb_html(parts: list[tuple[str, bool]]) -> str:
    pieces = []
    for i, (text, bold) in enumerate(parts):
        cls = "bf-crumb-bold" if bold else "bf-crumb-muted"
        pieces.append(f'<span class="{cls}">{text}</span>')
    return (
        '<div class="bf-crumb">'
        + ' <span style="color:#D6D6D2;">/</span> '.join(pieces)
        + '</div>'
    )


def _render_topbar(crumb_parts: list[tuple[str, bool]],
                   show_ask: bool = True) -> None:
    # show_ask is retained for API compat but the ask input is now rendered
    # by the queue body so it can drive a stateful response card.
    st.markdown(
        '<div class="bf-shell-topbar">'
        f'{_crumb_html(crumb_parts)}'
        '</div>',
        unsafe_allow_html=True,
    )


# ── Public API ───────────────────────────────────────────────────────────────

def render_shell(
    active_route: str,
    crumb_parts: list[tuple[str, bool]],
    body: Callable[[], None],
    *,
    active_filter: str | None = None,
    active_brand: str | None = None,
    show_ask: bool = True,
    custom_topbar: Callable[[list[tuple[str, bool]]], None] | None = None,
) -> None:
    """Wrap a page in the shared broker shell.

    active_route: "queue" | "brand_scout" | "retailer_pitcher" | "admin_ops"
    crumb_parts:  list of (text, is_bold) tuples for the breadcrumb
    body:         zero-arg callable that renders the main page content
    custom_topbar: optional callable that takes crumb_parts and renders a
                   custom topbar instead of the default breadcrumb-only row.
                   Used by the queue to put the ask bar on the same row.
    """
    st.markdown(_shell_css(), unsafe_allow_html=True)
    _render_sidebar(active_route, active_filter, active_brand)
    if custom_topbar:
        custom_topbar(crumb_parts)
    else:
        _render_topbar(crumb_parts, show_ask=show_ask)
    body()


def render_crumb_html(crumb_parts: list[tuple[str, bool]]) -> str:
    """Public helper so a custom topbar can reuse the same breadcrumb
    style as the default one."""
    return _crumb_html(crumb_parts)


def consume_nav_query_param() -> bool:
    """Translate ?nav=... ?expand=... ?open_doc=... ?close_doc=...
    ?chat_close=... ?chat_clear=... query params into session state in
    a single pass. Returns True if the page should immediately rerun."""
    nav        = st.query_params.get("nav")
    filter_q   = st.query_params.get("filter")
    brand_q    = st.query_params.get("brand")
    expand_q   = st.query_params.get("expand")
    open_doc   = st.query_params.get("open_doc")
    close_doc  = st.query_params.get("close_doc")
    chat_close = st.query_params.get("chat_close")
    chat_clear = st.query_params.get("chat_clear")

    if not any([nav, expand_q, open_doc, close_doc, chat_close, chat_clear]):
        return False

    if nav == "queue":
        st.session_state["workspace"]    = "queue"
        st.session_state["queue_filter"] = filter_q or "today"
        st.session_state["queue_brand"]  = brand_q
        # Preserve expansion when only opening/closing a doc — otherwise
        # clear it (no expand_q in URL means "navigate to top of queue").
        if not (open_doc or close_doc):
            st.session_state["expanded_card"] = expand_q or None
    elif nav == "brand_scout":
        st.session_state["workspace"] = "brand_scout"
    elif nav == "retailer_pitcher":
        st.session_state["workspace"] = "retailer_pitcher"
    elif nav == "admin_ops":
        st.session_state["workspace"] = "admin_ops"
    elif expand_q and not nav:
        # ?expand=card-id with no nav — just set expansion in current view.
        st.session_state["expanded_card"] = expand_q

    if open_doc:
        st.session_state["doc_open"] = open_doc
    if close_doc == "1":
        st.session_state.pop("doc_open", None)
    if chat_close == "1":
        st.session_state["chat_open"] = False
        st.session_state.pop("chat_pending_query", None)
    if chat_clear == "1":
        st.session_state["ask_conversation"] = []
        st.session_state.pop("chat_pending_query", None)
        st.session_state["bf_chat_followup_last"] = ""

    st.query_params.clear()
    return True
