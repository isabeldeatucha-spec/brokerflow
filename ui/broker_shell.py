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
    ("Brami",        4),
    ("Olipop",       1),
    ("Spudsy",       1),
    ("Banza",        0),
    ("Tia Lupita",   0),
]


def _shell_css() -> str:
    return """
    <style>
    /* Make room for the fixed sidebar on every shell-wrapped page */
    .stApp .block-container {
        padding-left: 280px !important;
        max-width: 1100px !important;
        padding-top: 32px !important;
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

    /* ── Main top bar (breadcrumb + ask bar) ────────────────────────── */
    .bf-shell-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 24px;
        padding: 0 0 22px;
        border-bottom: 1px solid #F2F2EE;
        margin-bottom: 28px;
    }
    .bf-crumb {
        font-family: 'Instrument Serif', Georgia, serif;
        font-size: 17px;
        line-height: 1.2;
        color: #1A1A18;
    }
    .bf-crumb-muted { color: #B0AFA8; font-style: italic; }
    .bf-crumb-bold  { font-weight: 500; }

    .bf-ask {
        position: relative;
        flex: 0 1 460px;
    }
    .bf-ask input {
        width: 100%;
        background: #FFFFFF;
        border: 1px solid #EAEAE4;
        border-radius: 999px;
        padding: 9px 60px 9px 16px;
        font-family: 'Inter', sans-serif;
        font-size: 13px;
        color: #1A1A18;
        outline: none;
    }
    .bf-ask input::placeholder { color: #A8A8A8; }
    .bf-ask input:focus { border-color: #1A1A18; }
    .bf-ask-kbd {
        position: absolute;
        right: 8px; top: 50%;
        transform: translateY(-50%);
        font-family: 'JetBrains Mono', monospace;
        font-size: 10.5px;
        color: #8B8A83;
        background: #F2F2EE;
        padding: 3px 7px;
        border-radius: 5px;
        pointer-events: none;
    }

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
        "needs_you": 3,
        "drafted":   14,
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
    ask_html = ""
    if show_ask:
        ask_html = (
            '<form class="bf-ask" onsubmit="return false;">'
            '<input type="text" placeholder="Ask BrokerFlow anything... '
            'e.g. How much Olipop accrual is left this year?" disabled>'
            '<span class="bf-ask-kbd">&#8984;K</span>'
            '</form>'
        )
    st.markdown(
        '<div class="bf-shell-topbar">'
        f'{_crumb_html(crumb_parts)}'
        f'{ask_html}'
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
) -> None:
    """Wrap a page in the shared broker shell.

    active_route: "queue" | "brand_scout" | "retailer_pitcher" | "admin_ops"
    crumb_parts:  list of (text, is_bold) tuples for the breadcrumb
    body:         zero-arg callable that renders the main page content
    """
    st.markdown(_shell_css(), unsafe_allow_html=True)
    _render_sidebar(active_route, active_filter, active_brand)
    _render_topbar(crumb_parts, show_ask=show_ask)
    body()


def consume_nav_query_param() -> bool:
    """Translate ?nav=... and ?expand=... query params into session state.
    Returns True if the page should immediately rerun."""
    nav      = st.query_params.get("nav")
    filter_q = st.query_params.get("filter")
    brand_q  = st.query_params.get("brand")
    expand_q = st.query_params.get("expand")

    if not nav and not expand_q:
        return False

    if nav == "queue":
        st.session_state["workspace"]    = "queue"
        st.session_state["queue_filter"] = filter_q or "today"
        st.session_state["queue_brand"]  = brand_q
        # Only clear expansion when not navigating *into* a specific card.
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
    else:
        return False

    st.query_params.clear()
    return True
