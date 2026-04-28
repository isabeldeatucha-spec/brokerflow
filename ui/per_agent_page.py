"""Per-agent route pages for the book-of-business workspace.

render_per_agent_page(agent_key) is the single entry point.
agent_key: "retailer_pitcher" | "admin_ops"
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import streamlit as st


def _fetch_recent_admin_forms(client, limit: int = 5) -> list[dict]:
    """Most recent rows from new_item_forms, newest first. Returns []."""
    if not client:
        return []
    try:
        client.table("new_item_forms").select("id").limit(1).execute()
    except Exception:
        return []
    try:
        res = (
            client.table("new_item_forms")
            .select("brand_name, retailer, gaps, output_status, generated_at")
            .order("generated_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


# ── Metadata ───────────────────────────────────────────────────────────────────

_AGENT_META = {
    "retailer_pitcher": {
        "label":       "Retailer Pitcher",
        "description": "Tailors the brand's story to each buyer and tracks submission windows.",
        "color":       "#1E40AF",
        "bg":          "#DBEAFE",
    },
    "admin_ops": {
        "label":       "Admin & Ops",
        "description": "The paperwork side of your job, handled.",
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

_BUYER_OPTIONS = {
    "Whole Foods Market":    "whole_foods",
    "Sprouts Farmers Market": "sprouts",
    "Erewhon Market":        "erewhon",
}

_COMING_SOON: dict[str, list[tuple[str, str, str]]] = {
    "retailer_pitcher": [
        (
            "Q3",
            "Multi-buyer batch pitches",
            "Pitch one brand to every relevant buyer in a single run. "
            "Each email tailored to the buyer's persona — sent in one go.",
        ),
        (
            "Q3",
            "Pitch performance",
            "Track which pitches landed meetings, which got ghosted, and "
            "what proof points moved the needle. Learn what works for each buyer.",
        ),
        (
            "Q4",
            "Buyer relationship tracking",
            "Remember every interaction with every buyer across every brand. "
            "Know when you last talked, what you pitched, what they liked, "
            "and when to follow up.",
        ),
    ],
    "admin_ops": [
        (
            "Q2",
            "PO processing",
            "Parse POs from email or EDI. Check pricing against the brand's "
            "cost sheet. Confirm with the brand. Send back to the retailer.",
        ),
        (
            "Q2",
            "Deduction tracking",
            "Pull deduction reports from distributors. Tag each one (slotting, "
            "MCB, freight, damage). Flag the ones worth disputing — and draft the dispute.",
        ),
        (
            "Q3",
            "Demo spend reconciliation",
            "Track demo schedule, cost per event, and sales lift. Reconcile "
            "retailer-reported demo charges against actuals.",
        ),
        (
            "Q3",
            "Commission reconciliation",
            "Match commissions paid against POs shipped. Catch underpayments. "
            "Generate dispute packages automatically.",
        ),
        (
            "Q3",
            "SLA tracking",
            "Track every brand's distribution, reorder velocity, and open actions. "
            "Flag underperformers. Weekly digest to the broker.",
        ),
    ],
}


# ── Utility ────────────────────────────────────────────────────────────────────

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
        days = (datetime.now(timezone.utc) - ts).days
        if days == 0:
            return "Today"
        if days == 1:
            return "Yesterday"
        if days <= 7:
            return "This week"
        return "Earlier"
    except Exception:
        return "Earlier"


def _section_heading(title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<h2 style="font-family:\'Instrument Serif\', Georgia, serif; '
        f'font-size:24px; font-weight:400; margin:32px 0 2px 0;">{title}</h2>',
        unsafe_allow_html=True,
    )
    if subtitle:
        st.markdown(
            f'<p style="font-size:13px; color:#8B8A83; margin-bottom:16px;">{subtitle}</p>',
            unsafe_allow_html=True,
        )


def _divider() -> None:
    st.markdown(
        "<div style='height:1px; background:#EAEAE4; margin:28px 0;'></div>",
        unsafe_allow_html=True,
    )


def _load_brands(client) -> list[dict]:
    try:
        res = (
            client.table("brands")
            .select("id, brand_name, category")
            .order("brand_name")
            .execute()
        )
        return res.data or []
    except Exception:
        return []


# ── Coming soon cards ──────────────────────────────────────────────────────────

def _render_coming_soon(agent_key: str) -> None:
    _divider()
    _section_heading(
        "Coming soon",
        f"What {_AGENT_META[agent_key]['label']} will do next.",
    )
    cards = _COMING_SOON.get(agent_key, [])
    cols = st.columns(len(cards) if len(cards) <= 3 else 3)
    for i, (eyebrow, title, body) in enumerate(cards):
        with cols[i % 3]:
            st.markdown(
                f'<div style="border:0.5px solid #EAEAE4; border-radius:12px; '
                f'padding:20px 24px; background:#FAFAF8; margin-bottom:12px;">'
                f'<p style="font-size:10px; font-weight:600; letter-spacing:0.1em; '
                f'color:#B0AFA8; margin:0 0 8px 0; text-transform:uppercase;">{eyebrow}</p>'
                f'<h3 style="font-family:\'Instrument Serif\', Georgia, serif; '
                f'font-size:18px; font-weight:400; margin:0 0 8px 0; color:#1A1A18;">{title}</h3>'
                f'<p style="font-size:13px; color:#8B8A83; line-height:1.6; margin:0;">{body}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Activity timeline (shared) ─────────────────────────────────────────────────

def _render_activity_timeline(messages: list[dict], brand_name_map: dict) -> None:
    _section_heading(
        "Recent activity",
        "Everything this agent has done across your book, most recent first.",
    )

    if not messages:
        st.markdown(
            '<p style="color:#8B8A83; font-size:14px;">No activity yet.</p>',
            unsafe_allow_html=True,
        )
        return

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

        payload  = msg.get("payload") or {}
        status   = payload.get("agent_status", "idle")
        action   = payload.get("action_label", msg.get("message_type", "").replace("_", " "))
        bn       = brand_name_map.get(msg.get("brand_id", ""), "?")
        ago      = _ago_str(msg.get("created_at", ""))
        bg, fg   = _STATUS_COLORS.get(status, _STATUS_COLORS["idle"])
        pending  = payload.get("pending_review_count", 0)
        status_lbl = {
            "completed":       "done",
            "awaiting_review": f"review \xd7{pending}" if pending else "review",
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


# ── Retailer Pitcher action interface ─────────────────────────────────────────

def _render_pitcher_action(client) -> None:
    _divider()
    _section_heading(
        "Draft a pitch",
        "Pick a brand from your book and a buyer. "
        "We'll draft the email and one-pager.",
    )

    brands = _load_brands(client)
    if not brands:
        st.markdown(
            '<p style="color:#8B8A83; font-size:14px;">'
            'No brands in your book yet. Onboard one first.</p>',
            unsafe_allow_html=True,
        )
        return

    brand_names = [b["brand_name"] for b in brands]
    buyer_labels = list(_BUYER_OPTIONS.keys())

    col_brand, col_buyer = st.columns(2, gap="medium")
    with col_brand:
        st.markdown(
            '<p style="font-size:12px; font-weight:500; color:#1A1A18; margin-bottom:4px;">Brand</p>',
            unsafe_allow_html=True,
        )
        sel_brand = st.selectbox(
            "Brand",
            ["— pick a brand —"] + brand_names,
            key="pitcher_brand_pick",
            label_visibility="collapsed",
        )
    with col_buyer:
        st.markdown(
            '<p style="font-size:12px; font-weight:500; color:#1A1A18; margin-bottom:4px;">Buyer</p>',
            unsafe_allow_html=True,
        )
        sel_buyer_label = st.selectbox(
            "Buyer",
            ["— pick a buyer —"] + buyer_labels,
            key="pitcher_buyer_pick",
            label_visibility="collapsed",
        )

    brand_ok  = sel_brand != "— pick a brand —"
    buyer_ok  = sel_buyer_label != "— pick a buyer —"
    buyer_key = _BUYER_OPTIONS.get(sel_buyer_label, "")
    ready     = brand_ok and buyer_ok

    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        run = st.button(
            "Draft pitch →",
            key="pitcher_draft_btn",
            disabled=not ready,
            type="primary",
            use_container_width=True,
        )

    if run and ready:
        with st.spinner(f"Drafting pitch for {sel_brand} → {sel_buyer_label}…"):
            try:
                from agents.orchestrator.pipeline import _run_pitcher_with_framing
                result = _run_pitcher_with_framing(sel_brand, buyer_key, "")
                st.session_state["_pitcher_result"] = dict(result)
                st.session_state["_pitcher_result_brand"] = sel_brand
                st.session_state["_pitcher_result_buyer"] = buyer_key
            except Exception as exc:
                st.error(f"Pitch draft failed: {exc}")

    result = st.session_state.get("_pitcher_result")
    r_brand = st.session_state.get("_pitcher_result_brand")
    r_buyer = st.session_state.get("_pitcher_result_buyer")

    if result and r_brand == sel_brand and r_buyer == buyer_key:
        _render_pitcher_result(result, sel_brand, sel_buyer_label)


def _render_pitcher_result(result: dict, brand_name: str, buyer_label: str) -> None:
    subject        = result.get("email_subject", "")
    body           = result.get("email_body", "")
    sell_sheet     = result.get("sell_sheet_html", "")
    artifact_status = result.get("artifact_status", "")

    st.markdown(
        "<div style='height:1px; background:#EAEAE4; margin:20px 0 16px;'></div>",
        unsafe_allow_html=True,
    )

    if artifact_status == "miss":
        st.warning(
            f"No context found for **{brand_name}** in the book. "
            "Make sure the brand is onboarded before drafting a pitch."
        )
        return

    tab_email, tab_sheet = st.tabs(["Email to buyer", "One-pager"])

    with tab_email:
        if subject:
            st.markdown(
                f'<p style="font-size:11px; font-weight:600; letter-spacing:0.08em; '
                f'color:#8B8A83; margin-bottom:4px;">SUBJECT</p>'
                f'<p style="font-size:14px; font-weight:500; color:#1A1A18; '
                f'margin-bottom:16px;">{subject}</p>',
                unsafe_allow_html=True,
            )
        if body:
            st.text_area(
                "Email body",
                value=body,
                height=320,
                key="pitcher_email_body_display",
                label_visibility="collapsed",
            )
            st.caption("Select all and copy, or use the Download button below.")
            st.download_button(
                "Download email (.txt)",
                data=f"Subject: {subject}\n\n{body}",
                file_name=f"{brand_name}_{buyer_label.split()[0]}_pitch.txt",
                mime="text/plain",
                key="pitcher_dl_email",
            )
        else:
            st.info("No email was generated.")

    with tab_sheet:
        if sell_sheet:
            st.components.v1.html(sell_sheet, height=820, scrolling=True)
            st.download_button(
                "Download one-pager (.html)",
                data=sell_sheet,
                file_name=f"{brand_name}_sellsheet.html",
                mime="text/html",
                key="pitcher_dl_sheet",
            )
        else:
            st.info("No sell sheet was generated.")

    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
    if st.button("Draft another →", key="pitcher_reset_btn"):
        for k in ("_pitcher_result", "_pitcher_result_brand", "_pitcher_result_buyer"):
            st.session_state.pop(k, None)
        st.rerun()


# ── Admin & Ops action interface ───────────────────────────────────────────────

_RETAILER_OPTIONS = [
    ("Whole Foods Market",  "whole_foods", True),
    ("Sprouts Farmers Market", "sprouts",  False),
    ("KeHE",                "kehe",        False),
    ("UNFI",                "unfi",        False),
    ("Costco",              "costco",      False),
]


def _render_admin_pending_review(messages: list[dict], brand_name_map: dict) -> None:
    review_items = [
        m for m in messages
        if (m.get("payload") or {}).get("agent_status") == "awaiting_review"
    ]
    if not review_items:
        st.markdown(
            '<p style="font-size:13px; color:#8B8A83; margin-bottom:8px;">'
            "Nothing flagged right now. Agents are running.</p>",
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f'<p style="font-size:13px; color:#8B8A83; margin-bottom:12px;">'
        f'{len(review_items)} item{"s" if len(review_items) != 1 else ""} '
        f'flagged — review before the next run.</p>',
        unsafe_allow_html=True,
    )
    for item in review_items:
        payload = item.get("payload") or {}
        bn      = brand_name_map.get(item.get("brand_id", ""), "?")
        action  = payload.get("action_label", item.get("message_type", "").replace("_", " "))
        ago     = _ago_str(item.get("created_at", ""))
        col_info, col_btn = st.columns([6, 1])
        with col_info:
            st.markdown(
                f'<div style="padding:8px 12px; background:#FFFBEB; '
                f'border:0.5px solid #FDE68A; border-radius:8px; margin-bottom:6px;">'
                f'<span style="font-weight:500; color:#1A1A18;">{bn}</span>'
                f'<span style="color:#8B8A83; margin:0 6px;">·</span>'
                f'<span style="color:#57564F;">{action}</span>'
                f'<span style="color:#B0AFA8; font-size:11px; margin-left:8px;">{ago}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_btn:
            if st.button("Review →",
                         key=f"pa_review_{item.get('brand_id', '')}_{item.get('created_at','')}",
                         use_container_width=True):
                st.session_state["workspace"] = "existing_business"
                st.session_state[f"expand_{item.get('brand_id', '')}_admin_ops"] = True
                st.rerun()


def _render_admin_action(client) -> None:
    _divider()
    _section_heading(
        "Fill a new-item form",
        "Pick a brand from your book and a retailer. We'll fill the form using "
        "everything we know and flag what's missing before you submit.",
    )

    brands = _load_brands(client)
    if not brands:
        st.markdown(
            '<p style="color:#8B8A83; font-size:14px;">'
            'No brands in your book yet. Onboard one first.</p>',
            unsafe_allow_html=True,
        )
        return

    brand_names = [b["brand_name"] for b in brands]
    retailer_display = [
        label if active else f"{label} (coming soon)"
        for label, _, active in _RETAILER_OPTIONS
    ]

    col_brand, col_retailer = st.columns(2, gap="medium")
    with col_brand:
        st.markdown(
            '<p style="font-size:12px; font-weight:500; color:#1A1A18; margin-bottom:4px;">Brand</p>',
            unsafe_allow_html=True,
        )
        sel_brand = st.selectbox(
            "Brand",
            ["— pick a brand —"] + brand_names,
            key="admin_brand_pick",
            label_visibility="collapsed",
        )
    with col_retailer:
        st.markdown(
            '<p style="font-size:12px; font-weight:500; color:#1A1A18; margin-bottom:4px;">Retailer</p>',
            unsafe_allow_html=True,
        )
        sel_retailer_display = st.selectbox(
            "Retailer",
            retailer_display,
            key="admin_retailer_pick",
            label_visibility="collapsed",
        )

    # Resolve to retailer_key; only whole_foods is active
    retailer_key   = None
    retailer_active = False
    for label, key, active in _RETAILER_OPTIONS:
        if sel_retailer_display.startswith(label):
            retailer_key    = key
            retailer_active = active
            break

    brand_ok = sel_brand != "— pick a brand —"
    ready    = brand_ok and retailer_active

    if brand_ok and not retailer_active:
        st.markdown(
            '<p style="font-size:12px; color:#8B8A83; margin-top:4px;">'
            'This retailer is coming soon. Select Whole Foods to fill a form now.</p>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        run = st.button(
            "Fill form →",
            key="admin_fill_btn",
            disabled=not ready,
            type="primary",
            use_container_width=True,
        )

    if run and ready:
        with st.spinner(f"Filling WFM form for {sel_brand}…"):
            try:
                from agents.admin_ops.graph import run_admin_ops
                result = dict(run_admin_ops(sel_brand, retailer=retailer_key))
                xlsx_path = result.get("output_xlsx_path") or ""
                if xlsx_path and Path(xlsx_path).exists():
                    result["output_xlsx_bytes"] = Path(xlsx_path).read_bytes()
                st.session_state["_admin_form_result"] = result
                st.session_state["_admin_form_brand"]  = sel_brand
            except Exception as exc:
                st.error(f"Form fill failed: {exc}")

    result  = st.session_state.get("_admin_form_result")
    r_brand = st.session_state.get("_admin_form_brand")

    if result and r_brand == sel_brand:
        _render_admin_result(result, sel_brand)


def _render_admin_result(result: dict, brand_name: str) -> None:
    filled     = result.get("filled_fields") or {}
    gaps       = result.get("gaps") or []
    xlsx_path  = result.get("output_xlsx_path") or ""
    out_status = result.get("output_status", "")

    if out_status == "miss":
        st.warning(
            f"No context found for **{brand_name}**. "
            "Make sure the brand is onboarded before filling a form."
        )
        return

    total = len(filled) + len(gaps)
    pct   = round(100 * len(filled) / total) if total else 0

    pct_color = "#065F46" if pct >= 70 else ("#92400E" if pct >= 40 else "#8B2F2F")
    st.markdown(
        f'<div style="background:#F9F8F5; border:0.5px solid #EAEAE4; '
        f'border-radius:8px; padding:12px 20px; margin:16px 0; '
        f'display:flex; gap:32px; align-items:center;">'
        f'<span style="font-size:22px; font-weight:600; color:{pct_color};">{pct}%</span>'
        f'<span style="font-size:13px; color:#57564F;">'
        f'{len(filled)} of {total} fields autofilled &nbsp;·&nbsp; '
        f'{len(gaps)} gap{"s" if len(gaps) != 1 else ""} flagged</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    tab_preview, tab_gaps = st.tabs([
        f"Form preview ({len(filled)} fields)",
        f"Gaps to fill ({len(gaps)})",
    ])

    with tab_preview:
        if filled:
            rows_html = "".join(
                f'<tr>'
                f'<td style="padding:5px 16px 5px 0; font-size:12px; color:#8B8A83; '
                f'white-space:nowrap; vertical-align:top;">'
                f'{fid.replace("_", " ").title()}</td>'
                f'<td style="padding:5px 0; font-size:13px; color:#1A1A18;">{val}</td>'
                f'</tr>'
                for fid, val in list(filled.items())
            )
            st.markdown(
                f'<table style="width:100%; border-collapse:collapse;">{rows_html}</table>',
                unsafe_allow_html=True,
            )
        else:
            st.info("No fields were autofilled.")

    with tab_gaps:
        if gaps:
            for gap in gaps:
                label  = gap.get("label") or gap.get("field_id", "?")
                sec    = gap.get("section", "")
                hint   = gap.get("suggested_action") or gap.get("reason", "")
                req    = gap.get("required", False)
                req_tag = (
                    ' <span style="font-size:10px; background:#FEE2E2; color:#991B1B; '
                    'padding:1px 6px; border-radius:99px;">required</span>'
                    if req else ""
                )
                hint_html = (
                    f'<br><span style="font-size:12px; color:#57564F;">{hint}</span>'
                    if hint else ""
                )
                st.markdown(
                    f'<div style="padding:6px 0; border-bottom:0.5px solid #F3F3F0;">'
                    f'<span style="font-size:13px; font-weight:500; color:#1A1A18;">'
                    f'{label}{req_tag}</span>'
                    f'<span style="font-size:11px; color:#8B8A83; margin-left:8px;">{sec}</span>'
                    f'{hint_html}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.success("No gaps — all fields autofilled.")

    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
    dl_col, reset_col, _ = st.columns([1, 1, 3])

    xlsx_bytes = result.get("output_xlsx_bytes")
    if not xlsx_bytes and xlsx_path and Path(xlsx_path).exists():
        # Fallback: re-read from /tmp if the file is still around. Backfill the
        # cache so subsequent reruns don't depend on /tmp persisting.
        try:
            xlsx_bytes = Path(xlsx_path).read_bytes()
            result["output_xlsx_bytes"] = xlsx_bytes
        except OSError:
            xlsx_bytes = None

    with dl_col:
        if xlsx_bytes:
            st.download_button(
                "Download filled form",
                data=xlsx_bytes,
                file_name=f"WFM_NewItem_{brand_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="admin_dl_form",
                use_container_width=True,
            )
        else:
            err_msgs = result.get("artifact_errors") or []
            err_text = "; ".join(err_msgs) if err_msgs else (
                "Excel file is no longer available. Click Regenerate to rebuild it."
            )
            st.button(
                "Download filled form",
                key="admin_dl_form_disabled",
                disabled=True,
                use_container_width=True,
                help=err_text,
            )
            st.caption(err_text)

    with reset_col:
        if st.button("Fill another →", key="admin_reset_btn", use_container_width=True):
            for k in ("_admin_form_result", "_admin_form_brand"):
                st.session_state.pop(k, None)
            st.rerun()


# ── Main entry point ───────────────────────────────────────────────────────────

def render_per_agent_page(agent_key: str) -> None:
    if agent_key not in _AGENT_META:
        st.error(f"Unknown agent: {agent_key!r}")
        return

    meta = _AGENT_META[agent_key]

    # ── Back navigation ────────────────────────────────────────────────────────
    if st.button("← Your book of business", key="back_to_book"):
        st.session_state["workspace"] = "existing_business"
        st.rerun()

    st.markdown(
        f'<p style="font-size:12px; color:#8B8A83; margin-bottom:0;">'
        f'Your book of business / {meta["label"]}</p>',
        unsafe_allow_html=True,
    )

    # ── Hero ───────────────────────────────────────────────────────────────────
    st.markdown(
        f'<h1 style="font-family:\'Instrument Serif\', Georgia, serif; '
        f'font-size:40px; font-weight:400; margin:12px 0 4px;">{meta["label"]}</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="font-size:15px; color:#6b6b6b; margin-bottom:24px;">'
        f'{meta["description"]}</p>',
        unsafe_allow_html=True,
    )

    # ── Load activity data ─────────────────────────────────────────────────────
    client = None
    messages: list[dict] = []
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
        brand_ids = list({m["brand_id"] for m in messages if m.get("brand_id")})
        if brand_ids:
            br = (
                client.table("brands")
                .select("id, brand_name")
                .in_("id", brand_ids)
                .execute()
            )
            brand_name_map = {r["id"]: r["brand_name"] for r in (br.data or [])}
    except Exception:
        pass

    # ── Stats row ──────────────────────────────────────────────────────────────
    total_brands  = len({m["brand_id"] for m in messages if m.get("brand_id")})
    review_items  = [
        m for m in messages
        if (m.get("payload") or {}).get("agent_status") == "awaiting_review"
    ]
    activity_items = [m for m in messages if m not in review_items]

    stat_b_label = "pitches drafted" if agent_key == "retailer_pitcher" else "forms filled"
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
            f'<div style="font-size:28px; font-weight:600; color:#1A1A18;">'
            f'{len(activity_items)}</div>'
            f'<div style="font-size:12px; color:#8B8A83;">{stat_b_label}</div></div>',
            unsafe_allow_html=True,
        )
    with col_c:
        st.markdown(
            f'<div style="text-align:center;">'
            f'<div style="font-size:28px; font-weight:600; color:#92400E;">'
            f'{len(review_items)}</div>'
            f'<div style="font-size:12px; color:#8B8A83;">pending your review</div></div>',
            unsafe_allow_html=True,
        )

    # ── Admin & Ops: recent forms, then pending review ────────────────────────
    if agent_key == "admin_ops":
        _divider()
        _section_heading("Recent New Item Forms")
        recent_forms = _fetch_recent_admin_forms(client) if client else []
        if recent_forms:
            for row in recent_forms:
                brand_nm  = row.get("brand_name") or "—"
                retailer  = (row.get("retailer") or "whole_foods").replace("_", " ").title()
                gap_count = len(row.get("gaps") or [])
                ago       = _ago_str(row.get("generated_at", ""))
                gap_html  = (
                    f'<span style="color:#8B8A83; margin:0 6px;">·</span>'
                    f'<span style="color:#92400E;">{gap_count} gap'
                    f'{"s" if gap_count != 1 else ""} to review</span>'
                    if gap_count else ""
                )
                ago_html = (
                    f'<span style="color:#B0AFA8; font-size:11px; margin-left:8px;">'
                    f'{ago}</span>' if ago else ""
                )
                col_info, col_btn = st.columns([6, 1])
                with col_info:
                    st.markdown(
                        f'<div style="padding:8px 0;">'
                        f'<span style="font-weight:500; color:#1A1A18;">{brand_nm}</span>'
                        f'<span style="color:#8B8A83; margin:0 6px;">·</span>'
                        f'<span style="color:#57564F;">{retailer}</span>'
                        f'{gap_html}{ago_html}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with col_btn:
                    btn_key = f"recent_form_open_{brand_nm}_{row.get('retailer','')}"
                    if st.button("Open →", key=btn_key, use_container_width=True):
                        st.session_state["admin_brand_pick"] = brand_nm
                        st.rerun()
                st.markdown(
                    "<div style='height:1px; background:#F3F3F0; margin:0;'></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<p style="font-size:13px; color:#8B8A83; margin:4px 0 0;">'
                "No forms filled yet — pick a brand below to fill one.</p>",
                unsafe_allow_html=True,
            )

        _divider()
        _section_heading("Needs your review")
        _render_admin_pending_review(messages, brand_name_map)

    # ── Action interface ───────────────────────────────────────────────────────
    if client:
        if agent_key == "retailer_pitcher":
            _render_pitcher_action(client)
        else:
            _render_admin_action(client)

    # ── Activity timeline ──────────────────────────────────────────────────────
    _divider()
    _render_activity_timeline(messages, brand_name_map)

    # ── Coming soon ────────────────────────────────────────────────────────────
    _render_coming_soon(agent_key)
