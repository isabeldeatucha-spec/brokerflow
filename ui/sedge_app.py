"""
Sedge — multi-brand triage + pitch operating system for independent food brokers.

Run:
    cd /Users/isabelatucha/sedge
    streamlit run ui/sedge_app.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# llm_shim must be imported before any anthropic import
import agents.llm_shim  # noqa: F401, E402

import streamlit as st

from ui.global_css import inject_global_css

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Sedge",
    page_icon="",
    layout="centered",
    initial_sidebar_state="collapsed",
)

inject_global_css()


# ── Stats helpers ─────────────────────────────────────────────────────────────

def _table_exists(table_name: str) -> bool:
    try:
        from memory import _get_client
        _get_client().table(table_name).select("*").limit(1).execute()
        return True
    except Exception:
        return False


def _fetch_stats() -> dict:
    """Count rows across blackboard tables for the stats sentence."""
    try:
        from memory import _get_client
        client = _get_client()
        brands = client.table("brand_evaluations").select("brand_name", count="exact").execute()
        pitches = client.table("retailer_pitches").select("id", count="exact").execute()
        forms = (
            client.table("new_item_forms").select("id", count="exact").execute()
            if _table_exists("new_item_forms") else None
        )
        bundles = (
            client.table("sent_bundles").select("id", count="exact").execute()
            if _table_exists("sent_bundles") else None
        )
        return {
            "brands":  brands.count or 0,
            "pitches": pitches.count or 0,
            "forms":   (forms.count if forms else 0) or 0,
            "bundles": (bundles.count if bundles else 0) or 0,
        }
    except Exception:
        return {"brands": 0, "pitches": 0, "forms": 0, "bundles": 0}


# ── Progress row helper ───────────────────────────────────────────────────────

def _progress_row(label: str, icon_type: str, status_text: str) -> str:
    """Render one progress row — spinner/check/x + label + status."""
    icons = {
        "spinner": (
            '<div class="sedge-spin" style="width:16px; height:16px; '
            'border:2px solid #EAEAE4; border-top-color:#1A1A18; '
            'border-radius:50%; display:inline-block;"></div>'
        ),
        "check": '<span style="color:#2D5F3F; font-size:16px;">&#10003;</span>',
        "x":     '<span style="color:#8B2F2F; font-size:16px;">&#10007;</span>',
    }
    return (
        f'<div style="display:flex; align-items:center; gap:16px; padding:12px 0;'
        f'border-bottom:1px solid #F2F2EE;">'
        f'<div style="width:20px; flex-shrink:0;">{icons.get(icon_type, "○")}</div>'
        f'<div style="flex:1;">'
        f'<div style="font-size:14px; font-weight:500; color:#1A1A18;">{label}</div>'
        f'<div style="font-size:13px; color:#8B8A83; margin-top:2px;">{status_text}</div>'
        f'</div>'
        f'</div>'
    )


# ── Agent card helper ─────────────────────────────────────────────────────────

def _render_agent_card(name: str, description: str, stat: str) -> None:
    st.markdown(
        f'<div class="sedge-card" style="height:100%;">'
        f'<h3 style="font-family:\'Instrument Serif\', serif; font-size:22px;'
        f'font-weight:400; margin:0 0 12px 0;">{name}</h3>'
        f'<p style="font-size:13px; line-height:1.6; color:#57564F;'
        f'margin-bottom:16px;">{description}</p>'
        f'<p class="sedge-caption sedge-number" style="color:#8B8A83;">{stat}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Phase: idle (landing) ─────────────────────────────────────────────────────

def render_landing() -> None:
    stats = _fetch_stats()

    # Header
    st.markdown(
        '<div style="text-align:center; padding: 64px 0 32px;">'
        '<h1 class="sedge-h1" style="text-align:center;">Sedge</h1>'
        '<p class="sedge-subtitle" style="text-align:center;">'
        'The operating system for independent food brokers.'
        '</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Live stats sentence
    st.markdown(
        f'<p style="text-align:center; color:#8B8A83; font-size:13px; margin-bottom:48px;">'
        f'<span class="sedge-number">{stats["brands"]}</span> brands · '
        f'<span class="sedge-number">{stats["pitches"]}</span> pitches · '
        f'<span class="sedge-number">{stats["forms"]}</span> forms · '
        f'<span class="sedge-number">{stats["bundles"]}</span> bundles sent'
        f'</p>',
        unsafe_allow_html=True,
    )

    # Brand input grid
    st.markdown(
        '<p class="sedge-section-title">TRIAGE UP TO 5 BRANDS</p>',
        unsafe_allow_html=True,
    )

    if "brand_inputs" not in st.session_state:
        st.session_state.brand_inputs = ["", "", "", "", ""]

    placeholders = ["Chomps", "Fishwife", "Graza", "Olipop", "Magic Spoon"]
    cols = st.columns(5)
    for i, col in enumerate(cols):
        with col:
            st.session_state.brand_inputs[i] = st.text_input(
                f"Brand {i + 1}",
                value=st.session_state.brand_inputs[i],
                placeholder=placeholders[i],
                key=f"brand_input_{i}",
                label_visibility="collapsed",
            )

    filled_brands = [b for b in st.session_state.brand_inputs if b.strip()]
    st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        label = (
            f"Triage {len(filled_brands)} brand{'s' if len(filled_brands) != 1 else ''} →"
            if filled_brands
            else "Enter brand names above"
        )
        if st.button(
            label,
            disabled=len(filled_brands) == 0,
            use_container_width=True,
            type="primary",
            key="run_triage_btn",
        ):
            st.session_state.phase = "triaging"
            st.session_state.triage_brands = filled_brands
            st.rerun()

    st.markdown(
        '<p class="sedge-caption" style="text-align:center; margin-top:12px;">'
        "Takes ~30 seconds. We'll score all your brands so you can decide who's worth pitching."
        '</p>',
        unsafe_allow_html=True,
    )

    # Divider
    st.markdown(
        "<hr style='border:none; border-top:1px solid #EAEAE4; margin:64px 0;'>",
        unsafe_allow_html=True,
    )

    # How Sedge Works cards
    st.markdown(
        '<p class="sedge-section-title">HOW SEDGE WORKS</p>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        _render_agent_card(
            "Brand Scout",
            "Research any CPG brand across 10+ sources. Score it on 5 criteria "
            "from 150+ broker interviews.",
            f"{stats['brands']} brands evaluated",
        )
    with c2:
        _render_agent_card(
            "Retailer Pitcher",
            "Draft a buyer-specific outreach email and 1-page sell sheet for "
            "Whole Foods, Sprouts, or Erewhon.",
            f"{stats['pitches']} pitches drafted",
        )
    with c3:
        _render_agent_card(
            "Admin & Ops",
            "Autofill the Whole Foods New Item Setup Form from Brand Scout "
            "data. Flag data gaps before your buyer meeting.",
            f"{stats['forms']} forms filled",
        )

    # Demo mode footer toggle
    demo_on = st.session_state.get("demo_mode", False)
    demo_label = "Demo mode: ON" if demo_on else "Demo mode: OFF"
    st.markdown(
        f'<div style="text-align:center; margin-top:64px; font-size:12px; color:#8B8A83;">'
        f'{demo_label}</div>',
        unsafe_allow_html=True,
    )
    col_tl, col_tc, col_tr = st.columns([1, 2, 1])
    with col_tc:
        if st.button(
            "Toggle demo mode",
            key="demo_toggle_btn",
            use_container_width=True,
        ):
            st.session_state["demo_mode"] = not demo_on
            st.rerun()


# ── Phase: triaging ───────────────────────────────────────────────────────────

def render_triaging() -> None:
    brands = st.session_state.get("triage_brands", [])
    st.markdown(
        f'<div style="text-align:center; padding: 64px 0 32px;">'
        f'<h1 class="sedge-h1" style="text-align:center; font-size:42px;">'
        f'Triaging {len(brands)} brand{"s" if len(brands) != 1 else ""}'
        f'</h1>'
        f'<p class="sedge-caption">~5 seconds per brand</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    from agents.orchestrator.pipeline import run_triage_pipeline

    progress_slots = {b: st.empty() for b in brands}
    final_results = None

    for event in run_triage_pipeline(brands):
        if event.stage == "triage_complete":
            final_results = event.data.get("results", [])
            break
        for b in brands:
            if event.stage == f"triage_{b}":
                if event.status == "started":
                    progress_slots[b].markdown(
                        _progress_row(b, "spinner", "triaging…"),
                        unsafe_allow_html=True,
                    )
                elif event.status == "done":
                    data = event.data.get("result", {})
                    progress_slots[b].markdown(
                        _progress_row(
                            b, "check",
                            f"{data.get('score_estimate', 0)}/100 · {data.get('verdict', '')}",
                        ),
                        unsafe_allow_html=True,
                    )
                elif event.status == "failed":
                    progress_slots[b].markdown(
                        _progress_row(b, "x", "failed"),
                        unsafe_allow_html=True,
                    )

    st.session_state.triage_results = final_results or []
    st.session_state.phase = "selecting"
    time.sleep(0.5)
    st.rerun()


# ── Phase: selecting ──────────────────────────────────────────────────────────

def render_selecting() -> None:
    results = st.session_state.get("triage_results", [])
    if not results:
        st.error("No triage results. Start over?")
        if st.button("← Back"):
            st.session_state.phase = "idle"
            st.rerun()
        return

    n = len(results)
    st.markdown(
        f'<div style="padding: 32px 0;">'
        f'<h1 class="sedge-h1" style="font-size: 48px;">'
        f'{n} brand{"s" if n != 1 else ""} evaluated'
        f'</h1>'
        f'<p class="sedge-subtitle">Pick which to pitch.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    sorted_results = sorted(results, key=lambda r: -r.get("score_estimate", 0))

    if "selected_brands" not in st.session_state:
        st.session_state.selected_brands = set()

    for r in sorted_results:
        name     = r.get("brand_name", "")
        score    = r.get("score_estimate", 0)
        verdict  = r.get("verdict", "too_early")
        reasoning = r.get("one_line_reasoning", "")
        cached   = r.get("cached", False)

        verdict_pill_class = {
            "established": "sedge-pill-established",
            "broker_ready": "sedge-pill-ready",
            "too_early":   "sedge-pill-early",
        }.get(verdict, "sedge-pill-early")
        verdict_label = verdict.replace("_", " ").title()

        col_check, col_name, col_score, col_verdict = st.columns([0.5, 2, 1, 2])
        with col_check:
            is_selected = st.checkbox(
                "",
                value=(name in st.session_state.selected_brands),
                key=f"select_{name}",
                label_visibility="collapsed",
            )
            if is_selected:
                st.session_state.selected_brands.add(name)
            else:
                st.session_state.selected_brands.discard(name)
        with col_name:
            cached_tag = (
                '<span style="font-size:11px; color:#8B8A83; margin-left:6px;">cached</span>'
                if cached else ""
            )
            st.markdown(
                f'<div style="padding: 8px 0;">'
                f'<p style="font-size:15px; font-weight:500; margin:0; color:#1A1A18;">'
                f'{name}{cached_tag}</p>'
                f'<p style="font-size:12px; color:#8B8A83; margin:2px 0 0 0;">{reasoning}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_score:
            st.markdown(
                f'<div style="padding: 12px 0;">'
                f'<span class="sedge-number" style="font-size:20px; font-weight:500; color:#1A1A18;">'
                f'{score}<span style="color:#8B8A83; font-size:13px;">/100</span>'
                f'</span></div>',
                unsafe_allow_html=True,
            )
        with col_verdict:
            st.markdown(
                f'<div style="padding: 14px 0;">'
                f'<span class="sedge-pill {verdict_pill_class}">{verdict_label}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    n_selected = len(st.session_state.selected_brands)
    st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)

    col_back, col_main = st.columns([1, 2])
    with col_back:
        if st.button("← Triage other brands", use_container_width=True, key="back_btn"):
            st.session_state.phase = "idle"
            st.session_state.brand_inputs = ["", "", "", "", ""]
            st.session_state.selected_brands = set()
            st.session_state.triage_results = []
            st.rerun()
    with col_main:
        pitch_label = (
            f"Pitch {n_selected} selected brand{'s' if n_selected != 1 else ''} →"
            if n_selected > 0
            else "Select at least one brand"
        )
        if st.button(
            pitch_label,
            disabled=n_selected == 0,
            use_container_width=True,
            type="primary",
            key="pitch_btn",
        ):
            st.session_state.phase = "pitching"
            st.session_state.selected_list = list(st.session_state.selected_brands)
            st.rerun()


# ── Phase: pitching ───────────────────────────────────────────────────────────

def render_pitching() -> None:
    selected = st.session_state.get("selected_list", [])
    n = len(selected)

    st.markdown(
        f'<div style="text-align:center; padding: 32px 0;">'
        f'<h1 class="sedge-h1" style="text-align:center; font-size:42px;">'
        f'Pitching {n} brand{"s" if n != 1 else ""}'
        f'</h1>'
        f'<p class="sedge-caption">'
        f'Running Brand Scout → 3 retailer pitches → WFM form per brand. '
        f'~60-90 seconds per brand.'
        f'</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    from agents.orchestrator.pipeline import run_selective_pitch_pipeline

    brand_progress = {b: st.empty() for b in selected}
    all_bundles = []

    for event in run_selective_pitch_pipeline(selected):
        if event.stage == "selective_complete":
            all_bundles = event.data.get("bundles", [])
            break
        brand_name = (event.data or {}).get("brand_name", "?")
        if brand_name in brand_progress:
            brand_progress[brand_name].markdown(
                _progress_row(brand_name, "spinner", event.message),
                unsafe_allow_html=True,
            )

    # Mark done rows
    for b in selected:
        brand_progress[b].markdown(
            _progress_row(b, "check", "done"),
            unsafe_allow_html=True,
        )

    st.session_state.final_bundles = all_bundles
    st.session_state.phase = "approval"
    st.rerun()


# ── Phase: approval ───────────────────────────────────────────────────────────

def _fetch_pitch_detail(brand_name: str, buyer_key: str) -> dict | None:
    """Read email_subject, email_body, sell_sheet_html from retailer_pitches."""
    try:
        from memory import _get_client
        client = _get_client()
        result = (
            client.table("retailer_pitches")
            .select("*")
            .ilike("brand_name", brand_name)
            .eq("buyer_key", buyer_key)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


def _log_all_approvals(bundles: list[dict]) -> None:
    from memory import store_sent_bundle
    for bundle in bundles:
        brand_name = bundle.get("brand_name", "")
        for pitch in bundle.get("pitches", []):
            buyer = pitch.get("buyer_key", "")
            if st.session_state.approvals.get(f"{brand_name}__{buyer}", False):
                detail = _fetch_pitch_detail(brand_name, buyer) or {}
                store_sent_bundle(
                    brand_name=brand_name,
                    bundle_type="pitch_only",
                    retailer=buyer,
                    email_subject=detail.get("email_subject", ""),
                    email_body=detail.get("email_body", ""),
                    sell_sheet_html=detail.get("sell_sheet_html", ""),
                    form_xlsx_path=None,
                    status="sent",
                )
        admin = bundle.get("admin_result")
        if admin and st.session_state.approvals.get(f"{brand_name}__wfm_form", False):
            store_sent_bundle(
                brand_name=brand_name,
                bundle_type="form_only",
                retailer="whole_foods",
                email_subject="",
                email_body="",
                sell_sheet_html="",
                form_xlsx_path=admin.get("output_xlsx_path", ""),
                status="sent",
            )


def render_approval() -> None:
    bundles = st.session_state.get("final_bundles", [])
    if not bundles:
        st.error("No bundles generated. Something went wrong.")
        if st.button("← Start over"):
            st.session_state.phase = "idle"
            st.rerun()
        return

    n = len(bundles)
    st.markdown(
        f'<div style="padding: 32px 0;">'
        f'<h1 class="sedge-h1" style="font-size: 48px;">'
        f'{n} pitch package{"s" if n != 1 else ""} ready'
        f'</h1>'
        f'<p class="sedge-subtitle">Review and approve to log as sent.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if "approvals" not in st.session_state:
        st.session_state.approvals = {}

    for bundle in bundles:
        brand_name = bundle.get("brand_name", "?")
        scout      = bundle.get("scout_handoff") or {}
        pitches    = bundle.get("pitches") or []
        admin      = bundle.get("admin_result")

        st.markdown(
            f'<div class="sedge-card" style="margin-bottom:16px;">'
            f'<h2 style="font-family:\'Instrument Serif\', serif; font-size:28px;'
            f'font-weight:400; margin:0 0 4px 0;">{brand_name}</h2>'
            f'<p class="sedge-caption">'
            f'{scout.get("score_total", "?")}/100 · {scout.get("verdict", "?")}'
            f'</p>'
            f'<p style="font-size:13px; margin:12px 0 0 0;">'
            f'{(scout.get("broker_brief", "") or "")[:200]}'
            f'</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        for pitch in pitches:
            buyer = pitch.get("buyer_key", "?")
            approval_key = f"{brand_name}__{buyer}"
            col_check, col_content = st.columns([0.5, 9])
            with col_check:
                approved = st.checkbox(
                    "",
                    value=st.session_state.approvals.get(approval_key, True),
                    key=f"approve_{approval_key}",
                    label_visibility="collapsed",
                )
                st.session_state.approvals[approval_key] = approved
            with col_content:
                buyer_label = buyer.replace("_", " ").title()
                with st.expander(f"{brand_name} → {buyer_label}"):
                    pitch_detail = _fetch_pitch_detail(brand_name, buyer)
                    if pitch_detail:
                        st.markdown(f"**Subject:** {pitch_detail.get('email_subject', '')}")
                        st.text_area(
                            "Email body",
                            value=pitch_detail.get("email_body", ""),
                            height=200,
                            key=f"body_{approval_key}",
                            label_visibility="collapsed",
                        )

        if admin:
            admin_key = f"{brand_name}__wfm_form"
            col_check, col_content = st.columns([0.5, 9])
            with col_check:
                st.session_state.approvals[admin_key] = st.checkbox(
                    "",
                    value=st.session_state.approvals.get(admin_key, True),
                    key=f"approve_{admin_key}",
                    label_visibility="collapsed",
                )
            with col_content:
                filled = admin.get("filled_field_count", 0)
                gaps   = admin.get("gap_count", 0)
                with st.expander(
                    f"{brand_name} → WFM New Item Form ({filled} filled, {gaps} gaps)"
                ):
                    st.caption(f"Output: {admin.get('output_xlsx_path', '')}")

        st.markdown(
            "<hr style='border:none; border-top:1px solid #F2F2EE; margin:24px 0;'>",
            unsafe_allow_html=True,
        )

    approved_count = sum(1 for v in st.session_state.approvals.values() if v)
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        send_label = (
            f"Send {approved_count} approved item{'s' if approved_count != 1 else ''} →"
        )
        if st.button(
            send_label,
            disabled=approved_count == 0,
            use_container_width=True,
            type="primary",
            key="send_all_btn",
        ):
            _log_all_approvals(bundles)
            st.session_state.phase = "sent"
            st.rerun()


# ── Phase: sent ───────────────────────────────────────────────────────────────

def render_sent() -> None:
    st.balloons()
    st.markdown(
        '<div style="text-align:center; padding: 96px 0;">'
        '<h1 class="sedge-h1" style="text-align:center; font-size:56px;">Sent.</h1>'
        '<p class="sedge-subtitle" style="text-align:center;">'
        'Your approved bundles are logged.'
        '</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        if st.button(
            "← Triage more brands",
            use_container_width=True,
            type="primary",
            key="restart_btn",
        ):
            for k in [
                "phase", "brand_inputs", "triage_brands", "triage_results",
                "selected_brands", "selected_list", "final_bundles", "approvals",
            ]:
                st.session_state.pop(k, None)
            st.rerun()


# ── Error handler ─────────────────────────────────────────────────────────────

def _error_card(exc: Exception) -> None:
    import traceback
    tb = traceback.format_exc()
    print(tb, file=sys.stderr)
    st.error(f"Something went wrong: **{type(exc).__name__}: {exc}**")
    with st.expander("Debug details", expanded=True):
        st.code(tb, language="python")


# ── Phase router ──────────────────────────────────────────────────────────────

phase = st.session_state.get("phase", "idle")

try:
    if phase == "idle":
        render_landing()
    elif phase == "triaging":
        render_triaging()
    elif phase == "selecting":
        render_selecting()
    elif phase == "pitching":
        render_pitching()
    elif phase == "approval":
        render_approval()
    elif phase == "sent":
        render_sent()
    else:
        render_landing()
except Exception as _page_exc:
    _error_card(_page_exc)
