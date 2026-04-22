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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _table_exists(table_name: str) -> bool:
    try:
        from memory import _get_client
        _get_client().table(table_name).select("*").limit(1).execute()
        return True
    except Exception:
        return False


def _fetch_stats() -> dict:
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


def _progress_row(label: str, icon_type: str, status_text: str) -> str:
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

    # Top-right "How it works" link
    _, _, col_r = st.columns([1, 3, 1])
    with col_r:
        if st.button("How it works →", key="how_works_link"):
            st.session_state.phase = "how_it_works"
            st.rerun()

    # Header
    st.markdown(
        '<div style="text-align:center; padding: 48px 0 24px;">'
        '<h1 class="sedge-h1" style="text-align:center;">Sedge</h1>'
        '<p class="sedge-subtitle" style="text-align:center;">'
        'The operating system for independent food brokers.'
        '</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Live stats sentence
    st.markdown(
        f'<p style="text-align:center; color:#8B8A83; font-size:13px; margin-bottom:32px;">'
        f'<span class="sedge-number">{stats["brands"]}</span> brands · '
        f'<span class="sedge-number">{stats["pitches"]}</span> pitches · '
        f'<span class="sedge-number">{stats["forms"]}</span> forms · '
        f'<span class="sedge-number">{stats["bundles"]}</span> bundles sent'
        f'</p>',
        unsafe_allow_html=True,
    )

    # Mode toggle
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        mode_choice = st.radio(
            "",
            ["Manual — you pick at every step",
             "Autonomous — Sedge decides, you approve at the end"],
            index=0 if st.session_state.get("mode", "manual") == "manual" else 1,
            horizontal=True,
            label_visibility="collapsed",
            key="mode_radio",
        )
        st.session_state.mode = "autonomous" if "Autonomous" in mode_choice else "manual"

    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

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
            st.session_state.triage_brands = filled_brands
            if st.session_state.mode == "autonomous":
                st.session_state.phase = "autonomous_running"
            else:
                st.session_state.phase = "triaging"
            st.rerun()

    st.markdown(
        '<p class="sedge-caption" style="text-align:center; margin-top:12px;">'
        "Takes ~30 seconds. We'll score all your brands so you can decide who's worth pitching."
        '</p>',
        unsafe_allow_html=True,
    )

    # Divider
    st.markdown(
        "<hr style='border:none; border-top:1px solid #EAEAE4; margin:56px 0 40px;'>",
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

    # Coming next section
    st.markdown("<div style='margin: 48px 0 32px;'></div>", unsafe_allow_html=True)
    st.markdown('<p class="sedge-section-title">COMING NEXT</p>', unsafe_allow_html=True)
    st.markdown("""
<div style="display:grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
  <div class="sedge-card" style="opacity: 0.65;">
    <p style="font-size:11px; color:#8B8A83; text-transform:uppercase;
              letter-spacing:0.08em; margin:0 0 8px 0;">Admin &amp; Ops · Q2</p>
    <h4 style="font-family:'Instrument Serif', serif; font-size:18px;
               font-weight:400; margin:0 0 8px 0;">PO Processing</h4>
    <p style="font-size:13px; color:#57564F; margin:0;">
      Parse purchase orders from buyer emails. Log line items to Supabase.
      Flag discrepancies against the new item form.
    </p>
  </div>
  <div class="sedge-card" style="opacity: 0.65;">
    <p style="font-size:11px; color:#8B8A83; text-transform:uppercase;
              letter-spacing:0.08em; margin:0 0 8px 0;">Admin &amp; Ops · Q2</p>
    <h4 style="font-family:'Instrument Serif', serif; font-size:18px;
               font-weight:400; margin:0 0 8px 0;">Deduction Tracking</h4>
    <p style="font-size:13px; color:#57564F; margin:0;">
      Monitor chargebacks and short payments. Auto-document disputes.
      Surface patterns by retailer and by SKU.
    </p>
  </div>
  <div class="sedge-card" style="opacity: 0.65;">
    <p style="font-size:11px; color:#8B8A83; text-transform:uppercase;
              letter-spacing:0.08em; margin:0 0 8px 0;">Portfolio Mgr · Q3</p>
    <h4 style="font-family:'Instrument Serif', serif; font-size:18px;
               font-weight:400; margin:0 0 8px 0;">SLA Tracking</h4>
    <p style="font-size:13px; color:#57564F; margin:0;">
      Track every brand's distribution, reorder velocity, and open actions.
      Flag underperformers. Weekly digest to the broker.
    </p>
  </div>
  <div class="sedge-card" style="opacity: 0.65;">
    <p style="font-size:11px; color:#8B8A83; text-transform:uppercase;
              letter-spacing:0.08em; margin:0 0 8px 0;">Admin &amp; Ops · Q3</p>
    <h4 style="font-family:'Instrument Serif', serif; font-size:18px;
               font-weight:400; margin:0 0 8px 0;">Commission Reconciliation</h4>
    <p style="font-size:13px; color:#57564F; margin:0;">
      Match commissions paid against POs shipped. Catch underpayments.
      Generate dispute packages automatically.
    </p>
  </div>
  <div class="sedge-card" style="opacity: 0.65;">
    <p style="font-size:11px; color:#8B8A83; text-transform:uppercase;
              letter-spacing:0.08em; margin:0 0 8px 0;">Retailer Pitcher · Q3</p>
    <h4 style="font-family:'Instrument Serif', serif; font-size:18px;
               font-weight:400; margin:0 0 8px 0;">More Retailers</h4>
    <p style="font-size:13px; color:#57564F; margin:0;">
      KeHE, UNFI, Kroger, Costco. Each adds its own pitch tone, sell-sheet
      template, and new-item form.
    </p>
  </div>
  <div class="sedge-card" style="opacity: 0.65;">
    <p style="font-size:11px; color:#8B8A83; text-transform:uppercase;
              letter-spacing:0.08em; margin:0 0 8px 0;">Platform · Q4</p>
    <h4 style="font-family:'Instrument Serif', serif; font-size:18px;
               font-weight:400; margin:0 0 8px 0;">Multi-Broker</h4>
    <p style="font-size:13px; color:#57564F; margin:0;">
      Every broker's data compounds. Cross-portfolio intelligence across
      hundreds of brokers and thousands of brands — the data flywheel.
    </p>
  </div>
</div>
""", unsafe_allow_html=True)

    # Demo mode footer
    demo_on = st.session_state.get("demo_mode", False)
    demo_label = "Demo mode: ON" if demo_on else "Demo mode: OFF"
    st.markdown(
        f'<div style="text-align:center; margin-top:64px; font-size:12px; color:#8B8A83;">'
        f'{demo_label}</div>',
        unsafe_allow_html=True,
    )
    col_tl, col_tc, col_tr = st.columns([1, 2, 1])
    with col_tc:
        if st.button("Toggle demo mode", key="demo_toggle_btn", use_container_width=True):
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
        name      = r.get("brand_name", "")
        score     = r.get("score_estimate", 0)
        verdict   = r.get("verdict", "too_early")
        reasoning = r.get("one_line_reasoning", "")
        cached    = r.get("cached", False)
        recs      = r.get("retailer_recommendations", [])

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
            # Retailer recommendation pills
            strong_recs   = [rec for rec in recs if rec.get("tier") == "strong"]
            possible_recs = [rec for rec in recs if rec.get("tier") == "possible"]
            pill_html = []
            for rec in strong_recs:
                pill_html.append(
                    f'<span class="sedge-pill sedge-pill-ready" style="margin-right:4px;">'
                    f'{rec["retailer"].replace("_", " ").title()} · {rec["fit_score"]}'
                    f'</span>'
                )
            for rec in possible_recs:
                pill_html.append(
                    f'<span class="sedge-pill" style="margin-right:4px; opacity:0.6;">'
                    f'{rec["retailer"].replace("_", " ").title()} · {rec["fit_score"]}'
                    f'</span>'
                )
            rec_row = (
                f'<div style="padding: 4px 0 8px 0; font-size:11px;">'
                f'<span style="color:#8B8A83; margin-right:8px;">recommended:</span>'
                f'{"".join(pill_html)}'
                f'</div>'
                if pill_html else ""
            )
            st.markdown(
                f'<div style="padding: 8px 0;">'
                f'<p style="font-size:15px; font-weight:500; margin:0; color:#1A1A18;">'
                f'{name}{cached_tag}</p>'
                f'<p style="font-size:12px; color:#8B8A83; margin:2px 0 0 0;">{reasoning}</p>'
                f'{rec_row}'
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
            # Pass full enriched dicts (with retailer_recommendations) to pitching
            st.session_state.selected_enriched = [
                r for r in st.session_state.triage_results
                if r.get("brand_name") in st.session_state.selected_brands
            ]
            st.session_state.phase = "pitching"
            st.rerun()


# ── Phase: pitching ───────────────────────────────────────────────────────────

def render_pitching() -> None:
    selected_enriched = st.session_state.get("selected_enriched", [])
    n = len(selected_enriched)

    st.markdown(
        f'<div style="text-align:center; padding: 32px 0;">'
        f'<h1 class="sedge-h1" style="text-align:center; font-size:42px;">'
        f'Pitching {n} brand{"s" if n != 1 else ""}'
        f'</h1>'
        f'<p class="sedge-caption">'
        f'Running Brand Scout → recommended retailer pitches → WFM form per brand. '
        f'~60-90 seconds per brand.'
        f'</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    from agents.orchestrator.pipeline import run_selective_pitch_pipeline

    brand_names = [b.get("brand_name", "") for b in selected_enriched]
    brand_progress = {name: st.empty() for name in brand_names}
    all_bundles = []

    for event in run_selective_pitch_pipeline(selected_enriched):
        if event.stage == "selective_complete":
            all_bundles = event.data.get("bundles", [])
            break
        brand_name = (event.data or {}).get("brand_name", "?")
        if brand_name in brand_progress:
            brand_progress[brand_name].markdown(
                _progress_row(brand_name, "spinner", event.message),
                unsafe_allow_html=True,
            )

    for name in brand_names:
        brand_progress[name].markdown(
            _progress_row(name, "check", "done"),
            unsafe_allow_html=True,
        )

    st.session_state.final_bundles = all_bundles
    st.session_state.phase = "approval"
    st.rerun()


# ── Phase: approval ───────────────────────────────────────────────────────────

def _fetch_pitch_detail(brand_name: str, buyer_key: str) -> dict | None:
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
                        # CHANGE 1: render sell sheet
                        if pitch_detail.get("sell_sheet_html"):
                            st.markdown("**Sell sheet:**")
                            st.components.v1.html(
                                pitch_detail["sell_sheet_html"],
                                height=800,
                                scrolling=False,
                            )
                            st.download_button(
                                "Download sell sheet",
                                data=pitch_detail["sell_sheet_html"],
                                file_name=f"{brand_name}_{buyer}_sellsheet.html",
                                mime="text/html",
                                key=f"download_sheet_{approval_key}",
                            )

        # Admin WFM — muted "Bonus" by-product card (CHANGE 4)
        if admin:
            filled = len(admin.get("filled_fields") or {})
            gaps   = len(admin.get("gaps") or [])
            xlsx_path = admin.get("output_xlsx_path", "")
            st.markdown(
                f'<div style="background:#F9F8F5; border:1px solid #F2F2EE;'
                f'border-radius:10px; padding:16px 20px; margin-top:12px;'
                f'display:flex; align-items:center; gap:16px;">'
                f'<div style="flex:1;">'
                f'<p style="font-size:13px; font-weight:500; margin:0; color:#1A1A18;">'
                f'Bonus: WFM new item form ready</p>'
                f'<p style="font-size:12px; color:#8B8A83; margin:2px 0 0 0;">'
                f'{filled} fields autofilled · {gaps} gaps for you to review'
                f'</p>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if xlsx_path and Path(xlsx_path).exists():
                with open(xlsx_path, "rb") as f:
                    st.download_button(
                        f"Download WFM form for {brand_name}",
                        data=f.read(),
                        file_name=f"WFM_NewItem_{brand_name}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"download_wfm_{brand_name}",
                    )

        st.markdown(
            "<hr style='border:none; border-top:1px solid #F2F2EE; margin:24px 0;'>",
            unsafe_allow_html=True,
        )

    approved_count = sum(1 for v in st.session_state.approvals.values() if v)
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        if st.button(
            f"Send {approved_count} approved item{'s' if approved_count != 1 else ''} →",
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
                "selected_brands", "selected_enriched", "final_bundles", "approvals",
            ]:
                st.session_state.pop(k, None)
            st.rerun()


# ── Phase: how_it_works ───────────────────────────────────────────────────────

def render_how_it_works() -> None:
    col_l, _ = st.columns([1, 5])
    with col_l:
        if st.button("← Back to Sedge", key="back_howitworks"):
            st.session_state.phase = "idle"
            st.rerun()

    st.markdown("""
    <div style="padding: 32px 0 48px;">
      <h1 class="sedge-h1" style="font-size: 64px;">How Sedge works</h1>
      <p class="sedge-subtitle">Built from 150+ broker interviews.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<p class="sedge-section-title">THE THREE AGENTS</p>',
                unsafe_allow_html=True)
    st.markdown("""
Sedge coordinates three specialized LLM agents through a shared blackboard:

1. **Brand Scout** — researches any CPG brand across 10+ sources
   (Amazon, Instacart, Firecrawl, retailer sites, social, trade press)
   and scores it 0-100 on a 5-criterion rubric.

2. **Retailer Matcher** — recommends which retailers (Whole Foods, Sprouts,
   Erewhon) are the best fit for a given brand, based on category affinity,
   verdict, and domain rules.

3. **Retailer Pitcher** — drafts buyer-specific outreach emails and
   printable 1-page sell sheets for the recommended retailers.

4. **Admin & Ops** *(by-product)* — autofills the Whole Foods New Item
   Setup Form (57 fields) from Brand Scout data whenever a brand
   qualifies, flagging gaps for broker review.
""")

    st.markdown(
        "<hr style='border:none; border-top:1px solid #EAEAE4; margin:48px 0;'>",
        unsafe_allow_html=True,
    )

    st.markdown('<p class="sedge-section-title">THE SCORING RUBRIC</p>',
                unsafe_allow_html=True)
    st.markdown("""
Every brand gets scored on **5 criteria totaling 100 points.**
The rubric comes from 150+ interviews with independent brokers, CPG
founders, distributors, and retail buyers.
""")

    rubric = [
        ("Velocity Proof", 25,
         "The most important signal. Has this brand proven real consumers "
         "buy it repeatedly without heavy promotional support?",
         "Amazon reviews & rating · Subscribe & Save · Instacart banners · "
         "SPINS/NIQ mentions · trade press sell-through"),
        ("Distribution Density", 20,
         "Is the brand in the right number of doors — enough to prove "
         "viability, not so many that a broker adds no value? Sweet spot: "
         "20–300 doors with regional traction.",
         "Store locators · Whole Foods/Target/Walmart/Sprouts/Costco listings · "
         "Faire door count · Instacart banner count"),
        ("Margin Viability", 20,
         "Can this brand survive the full retail cost stack — distributor "
         "markup 12–28%, broker commission 5%, free fill, slotting fees? "
         "Brands need minimum 50% gross margin.",
         "SRP vs category benchmarks · Faire wholesale pricing · "
         "funding signals (can they absorb slotting?)"),
        ("Brand Story Clarity", 20,
         "Can a broker rep explain this brand to a retail buyer in 30 "
         "seconds? Clear hero product, specific consumer, defined "
         "differentiation vs. incumbents.",
         "Website · Instagram/TikTok following · trade press (NOSH, "
         "FoodNavigator) · Expo West presence · certifications"),
        ("Promotional Independence", 15,
         "Can this brand generate consumer demand without relying entirely "
         "on the broker to fund promos? Healthy brands survive on regular pricing.",
         "DTC channel & subscription model · organic social following · "
         "TPR frequency · Amazon Subscribe & Save · promotional history"),
    ]
    for name, pts, desc, sources in rubric:
        st.markdown(f"""
        <div class="sedge-card" style="margin-bottom: 16px;">
          <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:8px;">
            <h3 style="font-family:'Instrument Serif', serif; font-size:20px;
                       font-weight:400; margin:0;">{name}</h3>
            <span class="sedge-number" style="color:#1A1A18; font-size:14px;
                         background:#E8EDE9; padding:4px 12px; border-radius:99px;">
              {pts} pts
            </span>
          </div>
          <p style="font-size:14px; line-height:1.6; color:#1A1A18; margin:0 0 12px 0;">{desc}</p>
          <p style="font-size:12px; color:#8B8A83; margin:0;"><strong>Sources:</strong> {sources}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)
    st.markdown('<p class="sedge-section-title">VERDICT THRESHOLDS</p>',
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="sedge-card">
          <span class="sedge-pill sedge-pill-ready">Broker Ready · 45–69</span>
          <p style="font-size:14px; margin:12px 0 0 0;">
            Emerging brand in the sweet spot. Enough traction to be credible,
            not yet locked into national distribution.
          </p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="sedge-card">
          <span class="sedge-pill sedge-pill-established">Established · 70+</span>
          <p style="font-size:14px; margin:12px 0 0 0;">
            Proven brand, likely already working with brokers.
            Pitch angle: why you're better than their current broker.
          </p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="sedge-card">
          <span class="sedge-pill sedge-pill-early">Too Early · under 45</span>
          <p style="font-size:14px; margin:12px 0 0 0;">
            Not enough traction yet. Missing velocity proof, distribution,
            or story clarity. Check back in 6 months.
          </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(
        "<hr style='border:none; border-top:1px solid #EAEAE4; margin:48px 0;'>",
        unsafe_allow_html=True,
    )

    st.markdown('<p class="sedge-section-title">ON MISSING DATA</p>',
                unsafe_allow_html=True)
    st.markdown("""
Missing data scores at **50% of max** for each criterion — absence of
information is treated as neutral, not negative. Only active negative
signals (confirmed over-distribution, below-viable pricing, promotional
dependency) reduce scores below the neutral floor.

This matters because early brands often lack trackable signals, not
because they lack promise.
""")
    st.markdown("<div style='margin: 48px 0;'></div>", unsafe_allow_html=True)


# ── Phase: autonomous_running ─────────────────────────────────────────────────

def render_autonomous_running() -> None:
    brands = st.session_state.get("triage_brands", [])

    st.markdown(
        f'<div style="text-align:center; padding: 48px 0;">'
        f'<h1 class="sedge-h1" style="text-align:center; font-size:48px;">'
        f'Sedge is running'
        f'</h1>'
        f'<p class="sedge-subtitle" style="text-align:center;">'
        f'Triage → select → pitch → form. You\'ll review at the end.'
        f'</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Step 1: Triage
    step1_slot = st.empty()
    step1_slot.markdown(
        _progress_row("Triage", "spinner", f"Scoring {len(brands)} brands…"),
        unsafe_allow_html=True,
    )

    from agents.orchestrator.pipeline import run_triage_pipeline
    triage_results = None
    for event in run_triage_pipeline(brands):
        if event.stage == "triage_complete":
            triage_results = event.data.get("results", [])
            break

    qualifying = [r for r in (triage_results or [])
                  if r.get("score_estimate", 0) >= 45]
    step1_slot.markdown(
        _progress_row(
            "Triage", "check",
            f"{len(triage_results or [])} brands scored · "
            f"{len(qualifying)} qualifying (≥ 45)",
        ),
        unsafe_allow_html=True,
    )

    if not qualifying:
        st.markdown(
            '<div class="sedge-card" style="margin-top:32px; text-align:center;">'
            '<p>No brands scored high enough for outreach.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button("← Start over", key="auto_restart"):
            st.session_state.phase = "idle"
            st.rerun()
        return

    # Step 2: Auto-pitch qualifying brands
    step2_slot = st.empty()
    step2_slot.markdown(
        _progress_row("Pitching", "spinner",
                      f"Drafting pitches for {len(qualifying)} brands…"),
        unsafe_allow_html=True,
    )

    from agents.orchestrator.pipeline import run_selective_pitch_pipeline
    all_bundles = []
    for event in run_selective_pitch_pipeline(qualifying):
        if event.stage == "selective_complete":
            all_bundles = event.data.get("bundles", [])
            break

    pitch_count = sum(len(b.get("pitches", [])) for b in all_bundles)
    form_count  = sum(1 for b in all_bundles if b.get("admin_result"))
    step2_slot.markdown(
        _progress_row("Pitching", "check",
                      f"{pitch_count} pitches drafted · {form_count} forms filled"),
        unsafe_allow_html=True,
    )

    st.session_state.final_bundles = all_bundles
    st.session_state.phase = "approval"
    time.sleep(1)
    st.rerun()


# ── Error handler ─────────────────────────────────────────────────────────────

def _error_card(exc: Exception) -> None:
    import traceback
    tb = traceback.format_exc()
    print(tb, file=sys.stderr)
    st.error(f"Something went wrong: **{type(exc).__name__}: {exc}**")
    with st.expander("Debug details", expanded=True):
        st.code(tb, language="python")


# ── Tab: Discover (existing phase-based UX) ───────────────────────────────────

def render_discover_tab() -> None:
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
        elif phase == "how_it_works":
            render_how_it_works()
        elif phase == "autonomous_running":
            render_autonomous_running()
        else:
            render_landing()
    except Exception as _page_exc:
        _error_card(_page_exc)


# ── Tab: Operate ──────────────────────────────────────────────────────────────

def render_operate_tab() -> None:
    from agents.brand_onboarding.watchdog import get_pending_reverifications, scan_and_flag_stale_brands

    try:
        scan_and_flag_stale_brands()
    except Exception:
        pass

    pending = get_pending_reverifications()
    if pending:
        st.warning(
            f"**{len(pending)} brand{'s' if len(pending) != 1 else ''} need re-verification** "
            f"— last verified >30 days ago.",
            icon="⚠️",
        )
        with st.expander(f"View {len(pending)} stale brand{'s' if len(pending) != 1 else ''}"):
            for msg in pending:
                payload = msg.get("payload", {})
                st.markdown(
                    f"- **{payload.get('brand_name', '?')}** — "
                    f"last verified {payload.get('days_stale', '?')} days ago"
                )

    sandbox_on = st.session_state.get("sandbox_mode", False)
    col_title, col_sandbox = st.columns([3, 1])
    with col_title:
        st.markdown(
            '<h2 style="font-family:\'Instrument Serif\', serif; font-size:32px; '
            'font-weight:400; margin:0 0 4px 0;">Brand Roster</h2>',
            unsafe_allow_html=True,
        )
    with col_sandbox:
        sandbox_label = "Clear sandbox" if sandbox_on else "Load sandbox brands"
        if st.button(sandbox_label, key="sandbox_toggle_btn", use_container_width=True):
            if sandbox_on:
                try:
                    from sandbox.fixtures import clear_sandbox_brands
                    clear_sandbox_brands()
                    st.session_state["sandbox_mode"] = False
                except Exception as e:
                    st.error(f"Clear failed: {e}")
            else:
                try:
                    from sandbox.fixtures import seed_sandbox_brands
                    seed_sandbox_brands()
                    st.session_state["sandbox_mode"] = True
                except Exception as e:
                    st.error(f"Seed failed: {e}")
            st.rerun()

    try:
        from memory import _get_client
        client = _get_client()
        result = (
            client.table("brands")
            .select("id, brand_name, category, completeness_pct, status, last_verified_at, is_sandbox, products")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        brands_list = result.data or []
    except Exception:
        brands_list = []

    if not brands_list:
        st.markdown(
            '<div class="sedge-card" style="text-align:center; padding:48px 24px;">'
            '<p style="color:#8B8A83; margin:0;">No brands onboarded yet. '
            'Add one below or load sandbox brands to explore.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        for brand in brands_list:
            name = brand.get("brand_name", "?")
            category = brand.get("category") or "—"
            pct = brand.get("completeness_pct") or 0
            status = brand.get("status") or "active"
            is_sb = brand.get("is_sandbox", False)
            product_count = len(brand.get("products") or [])
            sandbox_tag = (
                '<span style="font-size:10px; background:#E8EDE9; color:#2D5F3F; '
                'padding:2px 6px; border-radius:99px; margin-left:6px;">sandbox</span>'
                if is_sb else ""
            )
            sku_tag = (
                f'<span style="font-size:11px; color:#8B8A83; margin-left:10px;">'
                f'📦 {product_count} SKU{"s" if product_count != 1 else ""}</span>'
                if product_count else ""
            )
            pct_color = "#2D5F3F" if pct >= 70 else ("#B8860B" if pct >= 40 else "#8B2F2F")
            st.markdown(
                f'<div class="sedge-card" style="display:flex; align-items:center; '
                f'gap:16px; padding:12px 20px; margin-bottom:8px;">'
                f'<div style="flex:1;">'
                f'<span style="font-size:15px; font-weight:500; color:#1A1A18;">{name}</span>'
                f'{sandbox_tag}'
                f'<span style="font-size:12px; color:#8B8A83; margin-left:12px;">{category}</span>'
                f'{sku_tag}'
                f'</div>'
                f'<div style="font-size:13px; font-weight:500; color:{pct_color};">'
                f'{pct:.0f}% complete'
                f'</div>'
                f'<div>'
                f'<span class="sedge-pill" style="font-size:11px;">{status}</span>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

    if st.button("+ Onboard new brand", type="primary", key="onboard_new_btn"):
        st.session_state["onboarding_active"] = True
        st.rerun()

    if st.session_state.get("onboarding_active"):
        from ui.onboarding_flow import render_onboarding_flow
        render_onboarding_flow()


# ── Top-level tabs ────────────────────────────────────────────────────────────

tab_operate, tab_discover = st.tabs(["🏢 Operate", "🔎 Discover"])

with tab_operate:
    try:
        render_operate_tab()
    except Exception as _exc:
        _error_card(_exc)

with tab_discover:
    render_discover_tab()
