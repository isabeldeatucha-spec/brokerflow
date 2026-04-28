"""
Admin & Ops page — autofill WFM new item forms from Brand Scout data.
Export: render_admin_ops_page()

Standalone dev:
    cd /Users/isabelatucha/brokerflow
    streamlit run ui/admin_ops_page.py
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import date

import streamlit as st

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from memory import get_config, retrieve_all_evaluations
from agents.admin_ops.skills.wfm_form_schema import WFM_FORM_FIELDS, FIELD_SECTIONS
from ui.global_css import inject_global_css


# ── Constants ─────────────────────────────────────────────────────────────────

_TOTAL_FIELDS = len(WFM_FORM_FIELDS)

_NODE_LABELS: dict[str, str] = {
    "load_brand_context":   "Loading brand data",
    "rule_based_autofill":  "Matching fields from Brand Scout",
    "llm_inference_pass":   "Running inference pass",
    "flag_gaps":            "Flagging gaps",
    "generate_filled_xlsx": "Generating Excel file",
}

_RETAILER_LABELS: dict[str, str] = {
    "whole_foods": "Whole Foods",
}


# ── Small helpers ─────────────────────────────────────────────────────────────

def _verdict_label(score: int) -> str:
    if score >= 70: return "Established"
    if score >= 45: return "Broker Ready"
    return "Too Early"


def _verdict_dot(score: int) -> str:
    return ""


def _verdict_badge_html(score: int) -> str:
    if score >= 70:
        return '<span class="badge-established">Established</span>'
    if score >= 45:
        return '<span class="badge-ready">Broker Ready</span>'
    return '<span class="badge-early">Too Early</span>'


def _conf_badge_html(confidence: str) -> str:
    STYLES: dict[str, tuple[str, str]] = {
        "high":   ("#E8EDE9", "#2D5F3F"),
        "medium": ("#FEF3C7", "#8B6914"),
        "low":    ("#FEE2E2", "#8B2F2F"),
    }
    bg, color = STYLES.get(confidence, ("#F2F2EE", "#57564F"))
    return (
        f'<span style="background:{bg};color:{color};padding:2px 8px;'
        f'border-radius:99px;font-size:11px;font-weight:600;">'
        f'{confidence.title()}</span>'
    )


def _gap_badge_html(required: bool) -> str:
    if required:
        return (
            '<span style="background:#FEE2E2;color:#8B2F2F;padding:2px 8px;'
            'border-radius:99px;font-size:11px;font-weight:600;">Required</span>'
        )
    return (
        '<span style="background:#F2F2EE;color:#57564F;padding:2px 8px;'
        'border-radius:99px;font-size:11px;font-weight:600;">Optional</span>'
    )


def _row_bg(confidence: str) -> str:
    if confidence == "high":   return "#F0FDF4"
    if confidence == "medium": return "#FFFBEB"
    if confidence == "low":    return "#FFF7ED"
    return "#F9FAFB"


def _gap_row_bg(required: bool) -> str:
    return "#FFF1F2" if required else "#F9FAFB"


def _section_table_html(
    section_key: str,
    filled_fields: dict,
    field_confidence: dict,
    field_sources: dict,
    gaps_by_id: dict,
) -> str:
    fields = [f for f in WFM_FORM_FIELDS if f["section"] == section_key]
    rows_html = ""
    for field in fields:
        fid = field["id"]
        value = filled_fields.get(fid)
        confidence = field_confidence.get(fid, "")
        source = field_sources.get(fid, "")

        if value is not None:
            bg = _row_bg(confidence)
            badge = _conf_badge_html(confidence)
            val_str = str(value)
            val_display = (val_str[:72] + "…") if len(val_str) > 72 else val_str
            src_display = (source[:55] + "…") if len(source) > 55 else source
            rows_html += (
                f'<tr style="background:{bg};">'
                f'<td style="padding:8px 12px;font-size:13px;color:#111111;font-weight:500;width:36%;">{field["label"]}</td>'
                f'<td style="padding:8px 12px;font-size:13px;color:#4A4A4A;width:36%;">{val_display}</td>'
                f'<td style="padding:8px 12px;text-align:right;width:28%;">{badge}'
                f'<br><span style="font-size:11px;color:#9CA3AF;">{src_display}</span></td>'
                f'</tr>'
            )
        else:
            required = field["required"]
            bg = _gap_row_bg(required)
            badge = _gap_badge_html(required)
            gap = gaps_by_id.get(fid, {})
            action = gap.get("suggested_action", "")
            action_display = (action[:50] + "…") if len(action) > 50 else action
            label_color = "#991B1B" if required else "#6B7280"
            label_weight = "600" if required else "400"
            rows_html += (
                f'<tr style="background:{bg};">'
                f'<td style="padding:8px 12px;font-size:13px;color:{label_color};font-weight:{label_weight};width:36%;">'
                f'{field["label"]}{"&nbsp;✱" if required else ""}</td>'
                f'<td style="padding:8px 12px;font-size:13px;color:#9CA3AF;font-style:italic;width:36%;">— gap —</td>'
                f'<td style="padding:8px 12px;text-align:right;width:28%;">{badge}'
                f'<br><span style="font-size:11px;color:#9CA3AF;">{action_display}</span></td>'
                f'</tr>'
            )

    return (
        '<table style="width:100%;border-collapse:collapse;">'
        '<thead><tr style="background:#F9FAFB;border-bottom:2px solid #E5E7EB;">'
        '<th style="padding:8px 12px;font-size:11px;color:#6B7280;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;text-align:left;width:36%;">Field</th>'
        '<th style="padding:8px 12px;font-size:11px;color:#6B7280;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;text-align:left;width:36%;">Value</th>'
        '<th style="padding:8px 12px;font-size:11px;color:#6B7280;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;text-align:right;width:28%;">Confidence</th>'
        '</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        '</table>'
    )


# ── Sub-renderers ─────────────────────────────────────────────────────────────

def _render_empty_state() -> None:
    st.markdown("""
    <div style="padding:48px 0 32px;">
        <h1 class="sedge-h1" style="margin-bottom:8px;">Pick a brand to fill its new-item form</h1>
        <p class="sedge-caption" style="max-width:420px;">
            Select a brand from your book above. BrokerFlow will fill a
            Whole Foods new-item form from your book — and flag what's missing before you submit.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Ghost section cards
    st.markdown(
        '<p style="font-size:11px;font-weight:700;color:#9CA3AF;text-transform:uppercase;'
        'letter-spacing:0.1em;margin:8px 0 12px;">Form preview — 10 sections</p>',
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, (section_key, section_label) in enumerate(FIELD_SECTIONS.items()):
        field_count = sum(1 for f in WFM_FORM_FIELDS if f["section"] == section_key)
        bars = "".join(
            f'<div style="height:22px;background:#E5E7EB;border-radius:4px;margin-bottom:5px;'
            f'width:{85 - (j % 3) * 12}%;"></div>'
            for j in range(min(field_count, 4))
        )
        with cols[i % 2]:
            st.markdown(
                f'<div class="sedge-card" style="opacity:0.4;">'
                f'<p style="font-size:11px;font-weight:700;color:#9CA3AF;text-transform:uppercase;'
                f'letter-spacing:0.1em;margin:0 0 12px 0;">{section_label}</p>'
                f'{bars}'
                f'<p style="font-size:11px;color:#D1D5DB;margin:8px 0 0;">{field_count} fields</p>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _render_brand_header(result: dict) -> None:
    brand_name = result.get("brand_name", "Unknown").strip().title()
    scout_ctx = result.get("scout_context", {})
    score = scout_ctx.get("score", 0) or 0
    verdict = scout_ctx.get("verdict", "")
    category = (scout_ctx.get("category") or "").replace("_", " ").title()
    retailer_label = _RETAILER_LABELS.get(result.get("retailer", "whole_foods"), "Whole Foods")

    # Best-effort Clearbit domain guess
    slug = brand_name.lower().replace(" ", "").replace("'", "").replace(".", "")
    logo_html = (
        f'<img src="https://logo.clearbit.com/{slug}.com" '
        f'style="width:44px;height:44px;border-radius:10px;object-fit:contain;'
        f'background:#F3F4F6;margin-right:12px;" '
        f'onerror="this.style.display=\'none\'">'
    )
    badge_html = _verdict_badge_html(score)
    category_html = f'<span class="category-pill">{category}</span>' if category else ""

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(
            f'<div style="display:flex;align-items:center;margin-bottom:4px;">'
            f'{logo_html}'
            f'<div>'
            f'<h1 style="margin:0 0 6px 0;font-size:30px;">{brand_name}</h1>'
            f'{category_html}'
            f'</div></div>'
            f'<p style="color:#9CA3AF;font-size:13px;margin:8px 0 0;">→ {retailer_label} new item form</p>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div style="text-align:center;">'
            f'<div class="sedge-score-display sedge-number">{score}</div>'
            f'<p class="sedge-caption" style="margin-top:4px;">Brand Scout score</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f'<div style="padding-top:14px;">{badge_html}</div>',
            unsafe_allow_html=True,
        )


def _render_fill_stat(result: dict) -> None:
    filled_count = len(result.get("filled_fields", {}))
    gaps = result.get("gaps", [])
    gaps_count = len(gaps)
    required_gaps = sum(1 for g in gaps if g.get("required"))
    optional_gaps = gaps_count - required_gaps
    pct = filled_count / _TOTAL_FIELDS if _TOTAL_FIELDS else 0
    stat_color = "#10B981" if pct >= 0.70 else "#F59E0B" if pct >= 0.40 else "#EF4444"

    # Summary stat bar
    fill_pct_display = int(pct * 100)
    progress_color = stat_color
    st.markdown(
        f'<div class="sedge-card" style="padding:20px 24px;">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">'
        f'<p style="font-size:15px;font-weight:600;color:#111111;margin:0;">'
        f'<span style="color:{stat_color};font-size:24px;font-weight:700;">{filled_count}</span>'
        f' of {_TOTAL_FIELDS} fields autofilled &nbsp;·&nbsp; '
        f'<span style="color:#EF4444;">{gaps_count} gaps flagged</span>'
        f'</p>'
        f'<span style="font-size:13px;color:{stat_color};font-weight:600;">{fill_pct_display}% complete</span>'
        f'</div>'
        f'<div style="background:#F3F4F6;border-radius:99px;height:6px;width:100%;">'
        f'<div style="height:6px;width:{fill_pct_display}%;background:{progress_color};border-radius:99px;"></div>'
        f'</div>'
        f'<div style="display:flex;gap:16px;margin-top:12px;">'
        f'<span style="font-size:12px;color:#8B2F2F;font-weight:600;">✱ {required_gaps} required gaps</span>'
        f'<span class="sedge-caption">{optional_gaps} optional gaps</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_form_preview_tab(result: dict) -> None:
    filled_fields = result.get("filled_fields", {})
    field_confidence = result.get("field_confidence", {})
    field_sources = result.get("field_sources", {})
    gaps_by_id = {g["field_id"]: g for g in result.get("gaps", [])}

    for section_key, section_label in FIELD_SECTIONS.items():
        section_fields = [f for f in WFM_FORM_FIELDS if f["section"] == section_key]
        filled_in_section = sum(1 for f in section_fields if f["id"] in filled_fields)

        table_html = _section_table_html(
            section_key, filled_fields, field_confidence, field_sources, gaps_by_id
        )
        st.markdown(
            f'<div class="sedge-card">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">'
            f'<p style="font-size:11px;font-weight:700;color:#9CA3AF;text-transform:uppercase;'
            f'letter-spacing:0.1em;margin:0;">{section_label}</p>'
            f'<span style="font-size:12px;color:#9CA3AF;">'
            f'{filled_in_section} / {len(section_fields)} filled</span>'
            f'</div>'
            f'{table_html}'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_gaps_tab(result: dict) -> None:
    gaps = result.get("gaps", [])
    required = [g for g in gaps if g.get("required")]
    optional = [g for g in gaps if not g.get("required")]

    if not gaps:
        st.markdown(
            '<div class="sedge-card" style="text-align:center;padding:40px;">'
            '<p class="sedge-section-title" style="margin-bottom:8px;">Complete</p>'
            '<h1 class="sedge-h1">All fields filled</h1>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    if required:
        st.markdown(
            f'<p class="sedge-section-title" style="color:#8B2F2F;margin:0 0 12px;">Required gaps · {len(required)}</p>',
            unsafe_allow_html=True,
        )
        for gap in required:
            section_label = FIELD_SECTIONS.get(gap.get("section", ""), gap.get("section", ""))
            col_info, col_input = st.columns([3, 2])
            with col_info:
                st.markdown(
                    f'<div style="background:#FFF1F2;border-left:3px solid #EF4444;'
                    f'padding:12px 14px;border-radius:0 8px 8px 0;margin-bottom:4px;">'
                    f'<p style="font-size:14px;font-weight:600;color:#111111;margin:0 0 4px;">'
                    f'{gap["label"]} <span style="color:#EF4444;">✱</span></p>'
                    f'<p style="font-size:12px;color:#6B7280;margin:0 0 2px;">'
                    f'Section: {section_label}</p>'
                    f'<p class="sedge-caption" style="margin:0;">'
                    f'{gap.get("suggested_action","")}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_input:
                st.text_input(
                    gap["label"],
                    placeholder=gap.get("suggested_action", "")[:60],
                    key=f"ao_gap_{gap['field_id']}",
                    label_visibility="collapsed",
                )

    if required and optional:
        st.markdown(
            '<hr style="border:none;border-top:1px solid #EAEAE4;margin:20px 0 16px;">',
            unsafe_allow_html=True,
        )

    if optional:
        st.markdown(
            f'<p class="sedge-section-title" style="margin:0 0 12px;">Optional gaps · {len(optional)}</p>',
            unsafe_allow_html=True,
        )
        for gap in optional:
            section_label = FIELD_SECTIONS.get(gap.get("section", ""), gap.get("section", ""))
            col_info, col_input = st.columns([3, 2])
            with col_info:
                st.markdown(
                    f'<div class="gap-item">'
                    f'<p style="font-size:14px;font-weight:500;color:#1A1A18;margin:0 0 2px;">{gap["label"]}</p>'
                    f'<p class="sedge-caption" style="margin:0 0 2px;">Section: {section_label}</p>'
                    f'<p class="sedge-caption" style="margin:0;">{gap.get("suggested_action","")}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_input:
                st.text_input(
                    gap["label"],
                    placeholder=gap.get("suggested_action", "")[:60],
                    key=f"ao_gap_{gap['field_id']}",
                    label_visibility="collapsed",
                )


def _render_footer(result: dict) -> None:
    brand_name = result.get("brand_name", "Brand").strip().title()
    retailer_label = _RETAILER_LABELS.get(result.get("retailer", "whole_foods"), "Whole Foods")
    filled_count = len(result.get("filled_fields", {}))
    gaps = result.get("gaps", [])
    required_gaps = sum(1 for g in gaps if g.get("required"))
    output_path = result.get("output_xlsx_path", "")
    today_str = date.today().strftime("%Y%m%d")
    download_name = f"WFM_NewItem_{brand_name.replace(' ', '')}_{today_str}.xlsx"

    slack_text = (
        f"New item form ready for {brand_name} → {retailer_label}\n"
        f"✅ {filled_count} fields autofilled\n"
        f"⚠️ {len(gaps)} gaps to close ({required_gaps} required)\n"
        f"📎 Download: share the .xlsx file"
    )
    slack_js = slack_text.replace("`", "\\`").replace("\n", "\\n")

    st.markdown("<hr style='border:none;border-top:1px solid #E5E7EB;margin:24px 0 16px;'>", unsafe_allow_html=True)
    col_dl, col_slack, col_regen = st.columns(3)

    with col_dl:
        xlsx_bytes: bytes | None = None
        if output_path and os.path.exists(output_path):
            with open(output_path, "rb") as fh:
                xlsx_bytes = fh.read()
        if xlsx_bytes:
            st.download_button(
                label="Download the filled form",
                data=xlsx_bytes,
                file_name=download_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        else:
            st.button("Download the filled form", disabled=True, use_container_width=True)

    with col_slack:
        st.html(f"""
<script>
function copySlackSummary() {{
  navigator.clipboard.writeText(`{slack_js}`).then(function() {{
    var btn = document.getElementById('ao-slack-btn');
    btn.innerText = '✓ Copied!';
    btn.style.background = '#1B7A4A';
    setTimeout(() => {{
      btn.innerText = 'Copy summary';
      btn.style.background = '#1B4F72';
    }}, 2500);
  }});
}}
</script>
<button id="ao-slack-btn" onclick="copySlackSummary()"
  style="width:100%;background:#1A1A18;color:#FAFAF7;border:none;border-radius:6px;
  padding:10px 16px;font-size:14px;font-weight:500;cursor:pointer;font-family:Inter,sans-serif;">
  Copy summary
</button>
""")

    with col_regen:
        if st.button("Regenerate", key="ao_regen_btn", use_container_width=True):
            st.session_state.ao_phase = "idle"
            st.session_state.ao_result = None
            st.rerun()


# ── Graph runner ──────────────────────────────────────────────────────────────

def _run_graph(brand_name: str, retailer: str) -> dict:
    """Stream the graph with live progress cards. Returns final state values."""
    from agents.admin_ops.graph import graph
    config = get_config(st.session_state.ao_thread_id)

    initial: dict = {
        "brand_name":       brand_name,
        "retailer":         retailer,
        "scout_context":    {},
        "pitcher_context":  {},
        "handoff_status":   "",
        "handoff_error":    None,
        "form_schema":      [],
        "filled_fields":    {},
        "field_confidence": {},
        "field_sources":    {},
        "gaps":             [],
        "output_xlsx_path": "",
        "output_status":    "",
        "artifact_errors":  [],
        "approved":         None,
        "rejection_reason": None,
    }

    progress_slot = st.empty()
    completed: list[str] = []

    for chunk in graph.stream(initial, config=config, stream_mode="updates"):
        for node in chunk:
            label = _NODE_LABELS.get(node, node)
            completed.append(label)
            cards_html = "".join(
                f'<div style="display:flex;align-items:center;gap:12px;padding:10px 0;'
                f'border-bottom:1px solid #F2F2EE;">'
                f'<span style="color:#2D5F3F;font-size:13px;">&#10003;</span>'
                f'<span style="font-size:13px;color:#57564F;">{lbl}</span>'
                f'</div>'
                for lbl in completed
            )
            progress_slot.markdown(cards_html, unsafe_allow_html=True)

    progress_slot.empty()
    return graph.get_state(config).values


# ── Main exported function ────────────────────────────────────────────────────

def render_admin_ops_page() -> None:
    inject_global_css()

    st.info(
        "Tip: Use the Dashboard's full pipeline to run Brand Scout, "
        "all three Retailer Pitches, and this WFM form automatically in one click.",
        icon=None,
    )

    # ── Session state ─────────────────────────────────────────────────────────
    if "ao_phase" not in st.session_state:
        st.session_state.ao_phase = "idle"
    if "ao_result" not in st.session_state:
        st.session_state.ao_result = None
    if "ao_thread_id" not in st.session_state:
        st.session_state.ao_thread_id = str(uuid.uuid4())
    if "ao_brand_pick" not in st.session_state:
        st.session_state.ao_brand_pick = None
    if "ao_retailer" not in st.session_state:
        st.session_state.ao_retailer = "whole_foods"

    # ── Handoff from Brand Scout / Retailer Pitcher ───────────────────────────
    _handoff_brand = st.session_state.get("handoff_brand")

    # ── Controls ─────────────────────────────────────────────────────────────
    brands: list[dict] = []
    try:
        brands = retrieve_all_evaluations() or []
    except Exception as exc:
        st.markdown(
            f'<p style="font-size:11px;color:#EF4444;">Could not load brands: {exc}</p>',
            unsafe_allow_html=True,
        )

    def _brand_label(b: dict) -> str:
        score = b.get("score", 0) or 0
        return f"{b.get('brand_name','?')} · {score}/100 · {_verdict_label(score)}"

    _ao_handoff_idx = 0
    if _handoff_brand and brands:
        for _i, _b in enumerate(brands):
            if _b.get("brand_name", "").lower() == _handoff_brand.lower():
                _ao_handoff_idx = _i
                break

    _ao_brand_col, _ao_retailer_col = st.columns([1, 1])

    with _ao_brand_col:
        st.markdown(
            '<p style="font-size:12px;font-weight:700;color:#4A4A4A;margin-bottom:4px;">1 · Pick a brand</p>',
            unsafe_allow_html=True,
        )
        if brands:
            selected_brand = st.selectbox(
                "Brand",
                options=brands,
                index=_ao_handoff_idx,
                format_func=_brand_label,
                key="ao_brand_select",
                label_visibility="collapsed",
            )
        else:
            st.markdown(
                '<p style="font-size:13px;color:#9CA3AF;">No brands yet. Run Brand Scout first.</p>',
                unsafe_allow_html=True,
            )
            selected_brand = None

    with _ao_retailer_col:
        st.markdown(
            '<p style="font-size:12px;font-weight:700;color:#4A4A4A;margin-bottom:4px;">2 · Pick a retailer</p>',
            unsafe_allow_html=True,
        )
        st.radio(
            "Retailer",
            options=["Whole Foods"],
            key="ao_retailer_radio",
            label_visibility="collapsed",
        )
        st.markdown(
            '<p style="font-size:11px;color:#9CA3AF;margin-top:4px;">KeHE · UNFI · Sprouts — coming soon</p>',
            unsafe_allow_html=True,
        )

    _ao_run_col, _ao_reset_col = st.columns([4, 1])
    with _ao_run_col:
        _ao_run_clicked = st.button(
            "Autofill form",
            key="ao_run_btn",
            use_container_width=True,
            disabled=(selected_brand is None),
        )
    with _ao_reset_col:
        if st.session_state.ao_phase != "idle":
            if st.button("↺", key="ao_reset_btn", use_container_width=True):
                st.session_state.ao_phase = "idle"
                st.session_state.ao_result = None
                st.rerun()

    if _ao_run_clicked:
        st.session_state.ao_phase = "running"
        st.session_state.ao_brand_pick = selected_brand
        st.session_state.ao_thread_id = str(uuid.uuid4())
        st.session_state.ao_result = None
        st.rerun()

    st.markdown("<hr style='border:none;border-top:1px solid #EBEBEB;margin:16px 0 20px;'>", unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="margin-bottom:32px;">'
        '<h1 class="sedge-h1">Admin &amp; Ops</h1>'
        '<p class="sedge-subtitle">Fill the new-item paperwork retailers require, using everything we already know about the brand.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Demo mode banner ──────────────────────────────────────────────────────
    if st.session_state.get("demo_mode"):
        st.markdown(
            '<div style="background:#FAFAF7;border:1px solid #EAEAE4;border-radius:6px;'
            'padding:6px 14px;margin-bottom:12px;font-size:12px;color:#57564F;font-weight:500;">'
            'Demo mode · LLM inference skipped — rule-based autofill only</div>',
            unsafe_allow_html=True,
        )

    # ── Handoff banner ────────────────────────────────────────────────────────
    if _handoff_brand:
        _col_b, _col_x = st.columns([14, 1])
        with _col_b:
            _hs_score = "—"
            _hs_verdict = "—"
            try:
                _all_ev = retrieve_all_evaluations()
                for _ev in (_all_ev or []):
                    if (_ev.get("brand_name") or "").lower() == _handoff_brand.lower():
                        _hs_score = _ev.get("score", "—")
                        _hs_verdict = _ev.get("verdict", "—")
                        break
            except Exception:
                pass
            st.markdown(
                f'<div style="background:#FAFAF7;border:1px solid #EAEAE4;border-radius:6px;'
                f'padding:10px 16px;margin-bottom:16px;font-size:13px;color:#57564F;">'
                f'Handed off from Brand Scout — <strong style="color:#1A1A18;">{_handoff_brand}</strong>'
                f' ({_hs_score}/100, {_hs_verdict})</div>',
                unsafe_allow_html=True,
            )
        with _col_x:
            if st.button("×", key="ao_clear_handoff", use_container_width=True):
                del st.session_state["handoff_brand"]
                st.rerun()

    # ── Phase: idle ───────────────────────────────────────────────────────────
    if st.session_state.ao_phase == "idle":
        _render_empty_state()

    # ── Phase: running ────────────────────────────────────────────────────────
    elif st.session_state.ao_phase == "running":
        brand_pick = st.session_state.ao_brand_pick or {}
        brand_name = brand_pick.get("brand_name", "brand")

        st.markdown(
            f'<div style="padding:32px 0;">'
            f'<h1 class="sedge-h1" style="margin-bottom:8px;">Autofilling form for {brand_name}</h1>'
            f'<p class="sedge-caption">Matching Brand Scout data to WFM form fields.</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        result = _run_graph(brand_name, "whole_foods")
        st.session_state.ao_result = result

        if result.get("handoff_status") in ("miss", "stale"):
            st.session_state.ao_phase = "error"
        else:
            st.session_state.ao_phase = "done"
        st.rerun()

    # ── Phase: error ──────────────────────────────────────────────────────────
    elif st.session_state.ao_phase == "error":
        result = st.session_state.ao_result or {}
        status = result.get("handoff_status", "miss")
        error_msg = result.get("handoff_error", "Unknown error loading brand data.")
        st.markdown(
            f'<div class="sedge-card" style="text-align:center;padding:40px;">'
            f'<p class="sedge-section-title" style="color:#8B2F2F;margin-bottom:8px;">Error</p>'
            f'<h1 class="sedge-h1" style="margin-bottom:8px;">Could not load brand data</h1>'
            f'<p class="sedge-caption" style="color:#8B2F2F;">{error_msg}</p>'
            f'<p class="sedge-caption">Status: {status} — run Brand Scout on this brand first.</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Phase: done ───────────────────────────────────────────────────────────
    elif st.session_state.ao_phase == "done":
        result = st.session_state.ao_result or {}
        errors = result.get("artifact_errors", [])

        _render_brand_header(result)
        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        _render_fill_stat(result)

        # Surface non-fatal errors as a dismissible warning
        llm_errors = [e for e in errors if "llm_inference" in e]
        other_errors = [e for e in errors if "llm_inference" not in e]
        if llm_errors:
            st.markdown(
                '<div style="background:#FAFAF7;border:1px solid #EAEAE4;border-radius:6px;'
                'padding:10px 14px;margin-bottom:12px;font-size:12px;color:#8B6914;">'
                'LLM inference pass was skipped (API key not configured for this environment). '
                'Fields that require inference (family, GM%, line extension) will appear as gaps.'
                '</div>',
                unsafe_allow_html=True,
            )
        for err in other_errors:
            st.warning(err)

        gaps_count = len(result.get("gaps", []))
        tab_preview, tab_gaps = st.tabs([
            "Form Preview",
            f"Gaps to fill ({gaps_count})",
        ])

        with tab_preview:
            _render_form_preview_tab(result)

        with tab_gaps:
            _render_gaps_tab(result)

        _render_footer(result)

        if st.button(
            "Send this to a buyer",
            key="ao_handoff_pitcher",
            use_container_width=False,
        ):
            st.session_state["handoff_brand"] = result.get("brand_name", "")
            st.session_state["forced_page"] = "Retailer Pitcher"
            st.rerun()


# ── Standalone entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    st.set_page_config(
        page_title="Admin & Ops · BrokerFlow",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    render_admin_ops_page()
