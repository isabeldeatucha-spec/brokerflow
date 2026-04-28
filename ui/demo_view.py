"""Coordination Protocol Demo view.

Standalone page showcasing the SCP v1 protocol — banner, brand picker,
live metrics, fleet grid, coord log.

Routed from brokerflow_app.py via workspace == "demo".
"""
from __future__ import annotations

import streamlit as st


_ALL_BRANDS_LABEL = "All brands (run in parallel)"


def _live_metrics_strip() -> None:
    """Auto-refreshing metrics strip. Reruns every 2s."""
    from agents.runner import status as runner_status
    rs = runner_status()
    avg_ms     = rs.get("avg_ms", 0.0)
    msgs_min   = rs.get("msgs_per_minute", 0)
    active_n   = rs.get("active_chains", 0)
    failures   = rs.get("failures_last_hour", 0)
    samples    = rs.get("samples", 0)

    st.markdown(
        f'<div style="background:#0F0F0E; color:#FAFAF7; border-radius:0 0 14px 14px; '
        f'padding:0 24px 18px;">'
        f'<div style="display:flex; gap:24px; flex-wrap:wrap;">'
        f'<div style="text-align:left;">'
        f'<div style="font-size:22px; font-weight:600; color:#FAFAF7; line-height:1;">{active_n}</div>'
        f'<div style="font-size:10px; color:#9CA3AF; letter-spacing:0.05em; '
        f'text-transform:uppercase; margin-top:4px;">Active chains</div>'
        f'</div>'
        f'<div>'
        f'<div style="font-size:22px; font-weight:600; color:#FAFAF7; line-height:1;">{msgs_min}</div>'
        f'<div style="font-size:10px; color:#9CA3AF; letter-spacing:0.05em; '
        f'text-transform:uppercase; margin-top:4px;">Msgs / min</div>'
        f'</div>'
        f'<div>'
        f'<div style="font-size:22px; font-weight:600; color:#FAFAF7; line-height:1;">'
        f'{int(avg_ms)}<span style="font-size:13px; color:#9CA3AF;">ms</span></div>'
        f'<div style="font-size:10px; color:#9CA3AF; letter-spacing:0.05em; '
        f'text-transform:uppercase; margin-top:4px;">Avg handler ({samples}n)</div>'
        f'</div>'
        f'<div>'
        f'<div style="font-size:22px; font-weight:600; color:'
        f'{"#FCA5A5" if failures else "#FAFAF7"}; line-height:1;">{failures}</div>'
        f'<div style="font-size:10px; color:#9CA3AF; letter-spacing:0.05em; '
        f'text-transform:uppercase; margin-top:4px;">Failures (1h)</div>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _live_dashboard(brands_list: list) -> None:
    """Auto-refreshing fleet grid + coord log."""
    from memory import _get_client
    try:
        client = _get_client()
    except Exception:
        return

    if brands_list:
        with st.container(border=True):
            from ui.fleet_view import render_fleet_view
            render_fleet_view(client, brands_list)

    if st.session_state.get("_show_coord_log", True):
        st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            from ui.coordination_log import render_coordination_log
            render_coordination_log(brand_id=None, limit=30)


# Wrap with st.fragment for auto-refresh — done inside render_demo_view so we
# can keep the picker/buttons static and only refresh the live parts.
_live_metrics_strip = st.fragment(run_every=2)(_live_metrics_strip)
_live_dashboard     = st.fragment(run_every=2)(_live_dashboard)


def _kick_chain(brands: list[dict]) -> None:
    """Publish BRAND_ONBOARDED for each brand. Runner picks them up."""
    try:
        from agents.coordination.protocol import EventType, publish as scp_publish
        kicked = 0
        for b in brands:
            if not b.get("id"):
                continue
            scp_publish(
                from_agent="user",
                to_agent="*",
                brand_id=b["id"],
                event_type=EventType.BRAND_ONBOARDED,
                payload={
                    "brand_name":   b.get("brand_name"),
                    "category":     b.get("category"),
                    "trigger":      "manual_demo",
                    "action_label": f"Demo: kicked off coordination chain for {b.get('brand_name')}",
                    "agent_status": "completed",
                },
            )
            kicked += 1
        st.session_state["_show_coord_log"] = True
        st.toast(
            f"▶ Kicked off {kicked} chain{'s' if kicked != 1 else ''} — "
            "live fleet grid + log below auto-refresh every 2s",
            icon="🚀",
        )
    except Exception as exc:
        st.error(f"Failed to kick chain(s): {exc}")


def render_demo_view() -> None:
    """The main demo view — banner, brand picker, live dashboard."""

    # ── Back nav ───────────────────────────────────────────────────────────
    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← BrokerFlow", key="demo_back_btn"):
            st.session_state["workspace"] = None
            st.rerun()

    # ── Load brands ────────────────────────────────────────────────────────
    brands_list: list = []
    try:
        from memory import _get_client
        client = _get_client()
        result = (
            client.table("brands")
            .select("id, brand_name, category")
            .order("brand_name")
            .limit(50)
            .execute()
        )
        brands_list = result.data or []
    except Exception:
        pass

    # ── Static header ──────────────────────────────────────────────────────
    st.markdown(
        '<div style="background:#0F0F0E; color:#FAFAF7; border-radius:14px 14px 0 0; '
        'padding:18px 24px 14px; margin-top:18px;">'
        '<div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">'
        '<span style="width:8px; height:8px; border-radius:50%; background:#22C55E;"></span>'
        '<span style="font-size:11px; font-weight:600; letter-spacing:0.08em; '
        'color:#9CA3AF; text-transform:uppercase;">BrokerFlow Coordination Protocol v1</span>'
        '</div>'
        '<div style="font-family:\'Instrument Serif\', Georgia, serif; '
        'font-size:28px; font-weight:400;">Fleet mode — autonomous chains across your book</div>'
        '<div style="font-size:13px; color:#A1A09B; margin-top:6px;">'
        'Onboard → Pitcher → Admin &amp; Ops → PO Processing &nbsp;·&nbsp; '
        'pub-sub, ack/consume, parallel handlers, failure-resilient</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Live metrics strip (auto-refresh) ──────────────────────────────────
    _live_metrics_strip()

    # ── Brand picker + Run button (static) ─────────────────────────────────
    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)

    options: list[str] = []
    if len(brands_list) > 1:
        options.append(_ALL_BRANDS_LABEL)
    options.extend([b["brand_name"] for b in brands_list])

    if not options:
        st.warning(
            "No brands in your book yet. Onboard one from the book of business page first."
        )
        return

    col_pick, col_run, col_log = st.columns([2, 1, 1])
    with col_pick:
        default_idx = 0
        if "Olipop" in options:
            default_idx = options.index("Olipop")
        elif _ALL_BRANDS_LABEL in options:
            default_idx = options.index(_ALL_BRANDS_LABEL)
        selection = st.selectbox(
            "Demo target",
            options=options,
            index=default_idx,
            key="demo_brand_pick",
            label_visibility="collapsed",
        )
    with col_run:
        kick = st.button(
            "▶ Run demo chain",
            key="run_demo_chain_btn",
            type="primary",
            use_container_width=True,
        )
        if kick:
            if selection == _ALL_BRANDS_LABEL:
                _kick_chain(brands_list)
            else:
                target = next((b for b in brands_list if b.get("brand_name") == selection), None)
                if target:
                    _kick_chain([target])
    with col_log:
        if st.button(
            ("Hide log" if st.session_state.get("_show_coord_log", True) else "Show log"),
            key="open_coord_log_btn",
            use_container_width=True,
        ):
            st.session_state["_show_coord_log"] = not st.session_state.get("_show_coord_log", True)
            st.rerun()

    # ── Live fleet grid + coord log (auto-refresh) ─────────────────────────
    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
    _live_dashboard(brands_list)
