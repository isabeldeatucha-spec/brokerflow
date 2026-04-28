"""Fleet Mode — per-brand chain progress grid.

Renders one row per brand showing the SCP coordination chain stage:
  onboarded → pitched → form filled → PO received → PO outcome

Reads coordination_messages directly so the dots reflect the live blackboard.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

import streamlit as st


# Five-dot chain stages for the demo workflow
_STAGES = [
    ("onboarded",    {"v1.brand_onboarded"}),
    ("pitched",      {"v1.pitch_drafted", "v1.pitch_failed"}),
    ("form_filled",  {"v1.form_filled", "v1.form_gaps_flagged"}),
    ("po_received",  {"v1.po_received"}),
    ("po_outcome",   {"v1.po_validated", "v1.po_dispute_needed"}),
]
_STAGE_LABELS = {
    "onboarded":    "Onboarded",
    "pitched":      "Pitched",
    "form_filled":  "Form filled",
    "po_received":  "PO inbound",
    "po_outcome":   "PO outcome",
}

# Stable color palette — assigned per brand_id via hash
_BRAND_PALETTE = [
    ("#FEF3C7", "#92400E"),  # amber
    ("#DBEAFE", "#1E40AF"),  # blue
    ("#D1FAE5", "#065F46"),  # green
    ("#EDE9FE", "#5B21B6"),  # purple
    ("#FFE4E6", "#9F1239"),  # rose
    ("#E0F2FE", "#075985"),  # sky
    ("#FCE7F3", "#9D174D"),  # pink
    ("#F0FDF4", "#166534"),  # mint
]


def brand_color(brand_id: str) -> tuple[str, str]:
    """Stable (bg, fg) color for a given brand_id, hashed from id."""
    if not brand_id:
        return ("#F3F4F6", "#374151")
    h = int(hashlib.md5(brand_id.encode()).hexdigest(), 16)
    return _BRAND_PALETTE[h % len(_BRAND_PALETTE)]


def brand_pill(brand_name: str, brand_id: str) -> str:
    bg, fg = brand_color(brand_id)
    return (
        f'<span style="background:{bg}; color:{fg}; font-size:11px; '
        f'font-weight:600; padding:2px 8px; border-radius:99px; '
        f'white-space:nowrap;">{brand_name}</span>'
    )


def _load_chain_state(client, brand_ids: list[str], window_minutes: int = 30) -> dict:
    """For each brand, compute which stages are reached + the latest event.

    Returns: {brand_id: {
        "stages_reached": set[str],
        "latest_event":   dict or None,
        "latest_status":  "running" | "done" | "review" | "failed" | "idle",
        "latest_label":   str,
        "active":         bool   (has unconsumed v1.* msgs)
    }}
    """
    if not brand_ids:
        return {}
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).isoformat()
    try:
        res = (
            client.table("coordination_messages")
            .select("brand_id, from_agent, to_agent, message_type, payload, "
                    "created_at, consumed_at")
            .in_("brand_id", brand_ids)
            .like("message_type", "v1.%")
            .gte("created_at", cutoff)
            .order("created_at", desc=False)
            .execute()
        )
        rows = res.data or []
    except Exception:
        return {}

    # Initialise empty state per brand
    state: dict = {
        bid: {
            "stages_reached": set(),
            "latest_event":   None,
            "latest_status":  "idle",
            "latest_label":   "",
            "active":         False,
        }
        for bid in brand_ids
    }

    for r in rows:
        bid = r.get("brand_id")
        if bid not in state:
            continue
        mtype = r.get("message_type", "")
        for stage, types in _STAGES:
            if mtype in types:
                state[bid]["stages_reached"].add(stage)
                break
        state[bid]["latest_event"] = r
        if not r.get("consumed_at"):
            state[bid]["active"] = True

    # Derive latest status & label from the latest event
    for bid, s in state.items():
        ev = s["latest_event"]
        if not ev:
            continue
        payload = ev.get("payload") or {}
        mtype   = ev.get("message_type", "")
        agent_status = payload.get("agent_status", "")
        s["latest_label"] = payload.get("action_label", "") or mtype.replace("v1.", "").replace("_", " ")
        if mtype in ("v1.pitch_failed", "v1.handler_failed"):
            s["latest_status"] = "failed"
        elif mtype == "v1.po_dispute_needed" or agent_status == "awaiting_review":
            s["latest_status"] = "review"
        elif agent_status == "in_progress" or mtype.endswith("_requested"):
            s["latest_status"] = "running"
        elif mtype in ("v1.po_validated", "v1.po_dispute_needed"):
            s["latest_status"] = "done"
        elif s["active"]:
            s["latest_status"] = "running"
        else:
            s["latest_status"] = "done"

    return state


def _dot(reached: bool, status: str = "") -> str:
    if not reached:
        return ('<span style="display:inline-block; width:10px; height:10px; '
                'border:1.5px solid #D1D5DB; border-radius:50%; '
                'margin:0 3px;"></span>')
    color = "#10B981"  # green = done
    if status == "running":
        color = "#3B82F6"  # blue
    elif status == "review":
        color = "#F59E0B"  # amber
    elif status == "failed":
        color = "#EF4444"  # red
    return (f'<span style="display:inline-block; width:10px; height:10px; '
            f'background:{color}; border-radius:50%; margin:0 3px;"></span>')


def _ago(iso: str) -> str:
    try:
        ts = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        secs = (datetime.now(timezone.utc) - ts).total_seconds()
        if secs < 60:
            return f"{int(secs)}s ago"
        if secs < 3600:
            return f"{int(secs / 60)}m ago"
        return f"{int(secs / 3600)}h ago"
    except Exception:
        return ""


def render_fleet_view(client, brands: list[dict]) -> None:
    """Render the per-brand chain progress grid."""
    if not brands:
        return

    brand_ids = [b["id"] for b in brands if b.get("id")]
    state = _load_chain_state(client, brand_ids)

    # Header
    n_active = sum(1 for s in state.values() if s["active"])
    n_done   = sum(
        1 for s in state.values()
        if "po_outcome" in s["stages_reached"]
    )
    st.markdown(
        f'<div style="display:flex; align-items:baseline; justify-content:space-between; '
        f'margin-bottom:10px;">'
        f'<h2 style="font-family:\'Instrument Serif\', Georgia, serif; '
        f'font-size:22px; font-weight:400; color:#1A1A18; margin:0;">'
        f'Fleet — chain status across your book</h2>'
        f'<span style="font-size:12px; color:#8B8A83;">'
        f'{n_active} active · {n_done} complete · {len(brands)} brands tracked</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Header row: stage labels
    st.markdown(
        f'<div style="display:flex; padding:6px 12px; '
        f'border-bottom:1px solid #EAEAE4; margin-bottom:4px;">'
        f'<div style="flex:0 0 140px; font-size:11px; color:#8B8A83; font-weight:600;">BRAND</div>'
        f'<div style="flex:0 0 200px; font-size:11px; color:#8B8A83; font-weight:600; '
        f'text-align:center;">CHAIN STAGE</div>'
        f'<div style="flex:1; font-size:11px; color:#8B8A83; font-weight:600;">CURRENT</div>'
        f'<div style="flex:0 0 80px; font-size:11px; color:#8B8A83; font-weight:600; '
        f'text-align:right;">UPDATED</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    for b in brands:
        bid    = b["id"]
        bname  = b.get("brand_name", "?")
        s      = state.get(bid, {})
        reached = s.get("stages_reached", set())
        status  = s.get("latest_status", "idle")
        label   = s.get("latest_label", "")
        ev      = s.get("latest_event")
        ago     = _ago(ev["created_at"]) if ev else "—"

        dots_html = "".join(
            _dot(stage in reached, status if (stage in reached and stage == _last_stage(reached)) else "done")
            for stage, _ in _STAGES
        )
        b_pill = brand_pill(bname, bid)

        # Status indicator
        status_dot_color = {
            "running": "#3B82F6",
            "done":    "#10B981",
            "review":  "#F59E0B",
            "failed":  "#EF4444",
            "idle":    "#D1D5DB",
        }.get(status, "#D1D5DB")
        anim = ' animation:scp-pulse 1.4s infinite;' if status == "running" else ''

        st.markdown(
            f'<style>@keyframes scp-pulse {{0%,100%{{opacity:1}}50%{{opacity:0.4}}}}</style>'
            f'<div style="display:flex; align-items:center; padding:8px 12px; '
            f'border-bottom:0.5px solid #F3F3F0;">'
            f'<div style="flex:0 0 140px;">{b_pill}</div>'
            f'<div style="flex:0 0 200px; text-align:center;">{dots_html}</div>'
            f'<div style="flex:1; display:flex; align-items:center; gap:6px; min-width:0;">'
            f'<span style="width:6px; height:6px; border-radius:50%; '
            f'background:{status_dot_color};{anim} flex-shrink:0;"></span>'
            f'<span style="font-size:12px; color:#57564F; '
            f'overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{label or "—"}</span>'
            f'</div>'
            f'<div style="flex:0 0 80px; text-align:right; font-size:11px; color:#B0AFA8;">{ago}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _last_stage(reached: set) -> str:
    """Return the rightmost reached stage for status colouring."""
    for stage, _ in reversed(_STAGES):
        if stage in reached:
            return stage
    return ""
