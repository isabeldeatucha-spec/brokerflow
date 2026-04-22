"""Per-agent route pages for the book-of-business workspace.

render_per_agent_page(agent_key) is the single entry point.
agent_key: "retailer_pitcher" | "admin_ops"
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st


_AGENT_META = {
    "retailer_pitcher": {
        "label":       "Retailer Pitcher",
        "description": "Tailors the brand's story to each buyer and tracks submission windows.",
        "color":       "#1E40AF",
        "bg":          "#DBEAFE",
    },
    "admin_ops": {
        "label":       "Admin & Ops",
        "description": "Handles new-item forms, POs, deductions, and demo spend — hands-free.",
        "color":       "#065F46",
        "bg":          "#D1FAE5",
    },
}

_STATUS_COLORS = {
    "completed":       ("#D1FAE5", "#065F46"),
    "awaiting_review": ("#FEF3C7", "#92400E"),
    "in_progress":     ("#DBEAFE", "#1E40AF"),
    "idle":            ("#F3F4F6", "#6B7280"),
}


def _ago_str(iso: str) -> str:
    try:
        ts = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - ts
        secs = delta.total_seconds()
        if secs < 60:
            return "just now"
        if secs < 3600:
            return f"{int(secs / 60)} min ago"
        if secs < 86400:
            return f"{int(secs / 3600)} hr ago"
        return f"{delta.days}d ago"
    except Exception:
        return ""


def _date_group(iso: str) -> str:
    try:
        ts = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - ts
        days = delta.days
        if days == 0:
            return "Today"
        if days == 1:
            return "Yesterday"
        if days <= 7:
            return "This week"
        return "Earlier"
    except Exception:
        return "Earlier"


def render_per_agent_page(agent_key: str) -> None:
    if agent_key not in _AGENT_META:
        st.error(f"Unknown agent: {agent_key!r}")
        return

    meta = _AGENT_META[agent_key]

    # Back navigation
    if st.button("← Your book of business", key="back_to_book"):
        st.session_state["workspace"] = "existing_business"
        st.rerun()

    st.markdown(
        f'<p style="font-size:12px; color:#8B8A83; margin-bottom:0;">'
        f'Your book of business / {meta["label"]}</p>',
        unsafe_allow_html=True,
    )

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown(
        f'<h1 style="font-family:\'Instrument Serif\', Georgia, serif; '
        f'font-size:40px; font-weight:400; margin:12px 0 4px;">{meta["label"]}</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="font-size:15px; color:#6b6b6b; margin-bottom:24px;">{meta["description"]}</p>',
        unsafe_allow_html=True,
    )

    # Load all messages for this agent
    client = None
    messages = []
    brand_name_map: dict[str, str] = {}
    try:
        from memory import _get_client
        client = _get_client()
        res = (
            client.table("coordination_messages")
            .select("brand_id, from_agent, message_type, payload, created_at")
            .eq("from_agent", agent_key)
            .neq("message_type", "agent_memory")
            .neq("message_type", "idle")
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        messages = res.data or []

        # Build brand_id → brand_name map
        brand_ids = list({m["brand_id"] for m in messages if m.get("brand_id")})
        if brand_ids:
            br = client.table("brands").select("id, brand_name").in_("id", brand_ids).execute()
            brand_name_map = {r["id"]: r["brand_name"] for r in (br.data or [])}
    except Exception:
        pass

    # Stats row
    total_brands = len({m["brand_id"] for m in messages if m.get("brand_id")})
    review_items = [
        m for m in messages
        if (m.get("payload") or {}).get("agent_status") == "awaiting_review"
    ]
    activity_items = [
        m for m in messages
        if (m.get("payload") or {}).get("agent_status") != "awaiting_review"
    ]

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown(
            f'<div style="text-align:center;">'
            f'<div style="font-size:28px; font-weight:600; color:#1A1A18;">{total_brands}</div>'
            f'<div style="font-size:12px; color:#8B8A83;">brands</div></div>',
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(
            f'<div style="text-align:center;">'
            f'<div style="font-size:28px; font-weight:600; color:#1A1A18;">{len(activity_items)}</div>'
            f'<div style="font-size:12px; color:#8B8A83;">actions completed</div></div>',
            unsafe_allow_html=True,
        )
    with col_c:
        st.markdown(
            f'<div style="text-align:center;">'
            f'<div style="font-size:28px; font-weight:600; color:#92400E;">{len(review_items)}</div>'
            f'<div style="font-size:12px; color:#8B8A83;">pending your review</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin:24px 0 8px; height:1px; background:#EAEAEA;'></div>",
                unsafe_allow_html=True)

    # ── Pending review (Admin & Ops only) ────────────────────────────────────
    if agent_key == "admin_ops" and review_items:
        st.markdown(
            '<p style="font-size:11px; font-weight:600; letter-spacing:0.08em; '
            'color:#92400E; margin-bottom:8px;">NEEDS YOUR REVIEW</p>',
            unsafe_allow_html=True,
        )
        for item in review_items:
            payload = item.get("payload") or {}
            bn = brand_name_map.get(item.get("brand_id", ""), "?")
            action = payload.get("action_label", item.get("message_type", "").replace("_", " "))
            ago = _ago_str(item.get("created_at", ""))
            col_info, col_lnk = st.columns([5, 1])
            with col_info:
                st.markdown(
                    f'<div style="padding:8px 12px; background:#FFFBEB; border:0.5px solid #FDE68A; '
                    f'border-radius:8px; margin-bottom:6px;">'
                    f'<span style="font-weight:500; color:#1A1A18;">{bn}</span>'
                    f'<span style="color:#8B8A83; margin:0 6px;">·</span>'
                    f'<span style="color:#57564F;">{action}</span>'
                    f'<span style="color:#B0AFA8; font-size:11px; margin-left:8px;">{ago}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_lnk:
                if st.button("Review →", key=f"pa_review_{item.get('brand_id', '')}",
                             use_container_width=True):
                    st.session_state["workspace"] = "existing_business"
                    st.session_state[
                        f"expand_{item.get('brand_id', '')}_{agent_key}"
                    ] = True
                    st.rerun()

        st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    # ── Activity timeline ─────────────────────────────────────────────────────
    st.markdown(
        '<h2 style="font-family:\'Instrument Serif\', Georgia, serif; '
        'font-size:24px; font-weight:400; margin-bottom:4px;">Activity timeline</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="font-size:13px; color:#8B8A83; margin-bottom:16px;">'
        f'Everything {meta["label"]} has done across your book, most recent first.</p>',
        unsafe_allow_html=True,
    )

    if not messages:
        st.markdown(
            '<p style="color:#8B8A83; font-size:14px;">No activity yet.</p>',
            unsafe_allow_html=True,
        )
    else:
        current_group = None
        for msg in messages:
            group = _date_group(msg.get("created_at", ""))
            if group != current_group:
                current_group = group
                st.markdown(
                    f'<p style="font-size:11px; font-weight:600; letter-spacing:0.08em; '
                    f'color:#8B8A83; margin:20px 0 6px;">{group.upper()}</p>',
                    unsafe_allow_html=True,
                )

            payload = msg.get("payload") or {}
            status = payload.get("agent_status", "idle")
            action = payload.get("action_label", msg.get("message_type", "").replace("_", " "))
            bn = brand_name_map.get(msg.get("brand_id", ""), "?")
            ago = _ago_str(msg.get("created_at", ""))
            bg, fg = _STATUS_COLORS.get(status, _STATUS_COLORS["idle"])
            pending = payload.get("pending_review_count", 0)
            status_lbl = {
                "completed":       "done",
                "awaiting_review": f"review ×{pending}" if pending else "review",
                "in_progress":     "running",
                "idle":            "idle",
            }.get(status, status)

            col_brand, col_action, col_badge, col_time = st.columns([2, 4, 2, 1])
            with col_brand:
                st.markdown(
                    f'<span style="font-weight:500; color:#1A1A18; font-size:14px;">{bn}</span>',
                    unsafe_allow_html=True,
                )
            with col_action:
                st.markdown(
                    f'<span style="color:#57564F; font-size:14px;">{action}</span>',
                    unsafe_allow_html=True,
                )
            with col_badge:
                st.markdown(
                    f'<span style="background:{bg}; color:{fg}; font-size:11px; '
                    f'padding:2px 8px; border-radius:99px;">{status_lbl}</span>',
                    unsafe_allow_html=True,
                )
            with col_time:
                st.markdown(
                    f'<span style="color:#B0AFA8; font-size:12px;">{ago}</span>',
                    unsafe_allow_html=True,
                )

            st.markdown(
                "<div style='height:1px; background:#F3F3F0; margin:4px 0;'></div>",
                unsafe_allow_html=True,
            )
