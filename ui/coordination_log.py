"""Live coordination protocol log — UI component.

Renders the SCP message bus in real-time so the user (and judges) can see
typed events flowing between agents: who published what, when, who consumed it.
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st


# Colour each agent consistently
_AGENT_COLORS: dict[str, tuple[str, str]] = {
    # bg, fg
    "brand_onboarding":     ("#EDE9FE", "#5B21B6"),
    "retailer_pitcher":     ("#DBEAFE", "#1E40AF"),
    "admin_ops":            ("#D1FAE5", "#065F46"),
    "po_processing":        ("#FEF3C7", "#92400E"),
    "whole_foods_retailer": ("#F3F4F6", "#1F2937"),
    "scp_runner":           ("#FFE4E6", "#9F1239"),
    "*":                    ("#F3F4F6", "#6B7280"),
    "user":                 ("#F3F4F6", "#6B7280"),
}


def _agent_pill(name: str) -> str:
    bg, fg = _AGENT_COLORS.get(name, ("#F3F4F6", "#374151"))
    label = name.replace("_", " ").title() if name not in ("*",) else "broadcast"
    return (
        f'<span style="background:{bg}; color:{fg}; font-size:11px; '
        f'font-weight:500; padding:2px 8px; border-radius:99px; '
        f'white-space:nowrap;">{label}</span>'
    )


def _ago(iso: str) -> str:
    try:
        ts = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        secs = (datetime.now(timezone.utc) - ts).total_seconds()
        if secs < 1:
            return "just now"
        if secs < 60:
            return f"{int(secs)}s ago"
        if secs < 3600:
            return f"{int(secs / 60)}m ago"
        if secs < 86400:
            return f"{int(secs / 3600)}h ago"
        return f"{int(secs / 86400)}d ago"
    except Exception:
        return ""


def render_coordination_log(brand_id: str | None = None, limit: int = 25) -> None:
    """Render the SCP live message log."""
    from agents.coordination.protocol import recent_traffic, list_subscriptions
    from agents.runner import status as runner_status

    rs = runner_status()
    running = rs["running"]

    # Header with runner status
    dot_color = "#22C55E" if running else "#9CA3AF"
    dot_anim = (
        ' animation:scp-pulse 1.4s infinite;' if running else ''
    )
    st.markdown(
        f'<style>@keyframes scp-pulse {{0%,100%{{opacity:1}}50%{{opacity:0.4}}}}</style>'
        f'<div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">'
        f'<span style="width:8px; height:8px; border-radius:50%; background:{dot_color};{dot_anim}"></span>'
        f'<span style="font-family:\'Instrument Serif\', Georgia, serif; '
        f'font-size:22px; font-weight:400; color:#1A1A18;">Coordination protocol — live</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="font-size:12px; color:#8B8A83; margin-bottom:14px;">'
        f'SCP runner {"running" if running else "stopped"} · '
        f'tick {rs["tick_seconds"]:.0f}s · '
        f'{rs["ticks"]} ticks · '
        f'{rs["dispatched"]} messages dispatched</p>',
        unsafe_allow_html=True,
    )

    # Subscription table
    subs = list_subscriptions()
    if subs:
        with st.expander(f"Subscriptions ({len(subs)} event types)", expanded=False):
            for evt, subscribers in sorted(subs.items()):
                st.markdown(
                    f'<div style="font-size:12px; padding:3px 0; color:#57564F;">'
                    f'<code style="font-size:11px; background:#F3F4F6; padding:1px 6px; '
                    f'border-radius:4px;">{evt}</code> &nbsp; → &nbsp; '
                    f'{", ".join(subscribers)}</div>',
                    unsafe_allow_html=True,
                )

    # Live traffic
    events = recent_traffic(brand_id=brand_id, limit=limit)
    if not events:
        st.markdown(
            '<p style="font-size:13px; color:#8B8A83;">No protocol traffic yet — '
            'onboard a brand or run the demo to see messages.</p>',
            unsafe_allow_html=True,
        )
        return

    for ev in events:
        consumed   = bool(ev.consumed_at)
        ago        = _ago(ev.created_at)
        action     = (ev.payload or {}).get("action_label") or ev.message_type
        from_pill  = _agent_pill(ev.from_agent or "*")
        to_pill    = _agent_pill(ev.to_agent or "*")
        evt_label  = ev.message_type
        # Strip the v1. prefix for display
        if evt_label.startswith("v1."):
            evt_label = evt_label[3:].replace("_", " ")
        else:
            evt_label = evt_label.replace("_", " ")
        consume_badge = (
            '<span style="background:#D1FAE5; color:#065F46; font-size:10px; '
            'padding:1px 6px; border-radius:99px;">consumed</span>'
            if consumed
            else '<span style="background:#FEF3C7; color:#92400E; font-size:10px; '
                 'padding:1px 6px; border-radius:99px;">pending</span>'
        )

        st.markdown(
            f'<div style="border-left:2px solid #EAEAE4; padding:8px 0 8px 12px; '
            f'margin-bottom:6px;">'
            f'<div style="display:flex; align-items:center; gap:6px; margin-bottom:4px; '
            f'flex-wrap:wrap;">'
            f'{from_pill}'
            f'<span style="color:#9CA3AF; font-size:14px;">→</span>'
            f'{to_pill}'
            f'<span style="color:#1A1A18; font-size:11px; font-family:monospace; '
            f'background:#F9FAFB; padding:1px 8px; border-radius:4px; margin-left:4px;">'
            f'{evt_label}</span>'
            f'{consume_badge}'
            f'<span style="color:#B0AFA8; font-size:11px; margin-left:auto;">{ago}</span>'
            f'</div>'
            f'<div style="font-size:13px; color:#57564F;">{action}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
