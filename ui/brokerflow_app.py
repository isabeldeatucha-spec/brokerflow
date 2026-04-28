"""
BrokerFlow — multi-brand triage + pitch operating system for independent food brokers.

Run:
    cd /Users/isabelatucha/brokerflow
    streamlit run ui/brokerflow_app.py
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

# Start the SCP background runner once per Streamlit process.
# Idempotent — safe to call on every rerun.
try:
    from agents import runner as _scp_runner
    _scp_runner.start()
except Exception:
    pass

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="BrokerFlow",
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
        '<h1 class="sedge-h1" style="text-align:center;">BrokerFlow</h1>'
        '<p class="sedge-subtitle" style="text-align:center;">'
        'The operating system for CPG brokers.'
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
            ["Step through — review each stage",
             "Run it — review at the end"],
            index=0 if st.session_state.get("mode", "manual") == "manual" else 1,
            horizontal=True,
            label_visibility="collapsed",
            key="mode_radio",
        )
        st.session_state.mode = "autonomous" if "Run it" in mode_choice else "manual"

    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

    # Brand input grid
    st.markdown(
        '<p class="sedge-section-title">QUALIFY UP TO 5 BRANDS</p>',
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
            f"Qualify {len(filled_brands)} brand{'s' if len(filled_brands) != 1 else ''} →"
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
        "~30 seconds. We'll tell you which ones are worth a meeting."
        '</p>',
        unsafe_allow_html=True,
    )

    # Divider
    st.markdown(
        "<hr style='border:none; border-top:1px solid #EAEAE4; margin:56px 0 40px;'>",
        unsafe_allow_html=True,
    )

    # How BrokerFlow Works cards
    st.markdown(
        '<p class="sedge-section-title">HOW SEDGE WORKS</p>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        _render_agent_card(
            "Brand Scout",
            "Pulls everything you'd find by hand — distribution, velocity signals, "
            "social presence, margin viability — and tells you whether the brand "
            "is worth your time.",
            f"{stats['brands']} brands evaluated",
        )
    with c2:
        _render_agent_card(
            "Retailer Pitcher",
            "Tailors the brand's story to each buyer — outreach email and "
            "one-page sell sheet, ready to send.",
            f"{stats['pitches']} pitches drafted",
        )
    with c3:
        _render_agent_card(
            "Admin & Ops",
            "Fills the new-item paperwork retailers require — pulls what we know, "
            "flags what's missing before you hit submit.",
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
      Monitor chargebacks and short payments. Auto-draft disputes.
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
      Every broker's data makes the next pitch sharper. Cross-portfolio intelligence across
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
        f'Qualifying {len(brands)} brand{"s" if len(brands) != 1 else ""}'
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
        st.error("No results found. Start over?")
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
        if st.button("← Qualify other brands", use_container_width=True, key="back_btn"):
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
            "← Qualify more brands",
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
        if st.button("← Back to BrokerFlow", key="back_howitworks"):
            st.session_state.phase = "idle"
            st.rerun()

    st.markdown("""
    <div style="padding: 32px 0 48px;">
      <h1 class="sedge-h1" style="font-size: 64px;">How BrokerFlow works</h1>
      <p class="sedge-subtitle">Built from 150+ broker interviews.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<p class="sedge-section-title">THE THREE AGENTS</p>',
                unsafe_allow_html=True)
    st.markdown("""
Three agents share one workspace and pass context to each other automatically:

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
**Five criteria, 100 points.**
Built from what brokers actually told us they look for before signing a brand.
""")

    rubric = [
        ("Velocity Proof", 25,
         "Does the brand turn on shelf without being on promo? This is what kills "
         "brands at the distributor level — not enough turns and you get dropped.",
         "Amazon reviews & rating · Subscribe & Save · Instacart banners · "
         "SPINS/NIQ mentions · trade press sell-through"),
        ("Distribution Density", 20,
         "Enough stores to prove the brand works, not so many that you can't add "
         "value. Sweet spot: 20–300 stores with regional momentum.",
         "Store locators · Whole Foods/Target/Walmart/Sprouts/Costco listings · "
         "Faire door count · Instacart banner count"),
        ("Margin Viability", 20,
         "Can the brand survive the full stack — 12–28% distributor markup, 5% "
         "commission, free fills, slotting, deductions? Rule of thumb: 50% gross "
         "margin minimum, 60% if you want room to breathe.",
         "SRP vs category benchmarks · Faire wholesale pricing · "
         "funding signals (can they absorb slotting?)"),
        ("Brand Story Clarity", 20,
         "Can a rep explain it to a buyer in 30 seconds? Hero SKU, defined "
         "consumer, clear difference vs. what's already on shelf.",
         "Website · Instagram/TikTok following · trade press (NOSH, "
         "FoodNavigator) · Expo West presence · certifications"),
        ("Promotional Independence", 15,
         "Will the brand pull through without leaning on you for promo funding? "
         "The strongest brands don't promote at all.",
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
            Proven brand, probably already has a broker. If you go after them,
            lead with what their current broker isn't doing.
          </p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="sedge-card">
          <span class="sedge-pill sedge-pill-early">Too Early · under 45</span>
          <p style="font-size:14px; margin:12px 0 0 0;">
            Not there yet. Too early on turns, doors, or story. Worth a
            check-in in 6 months — most of these never make it.
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
Missing data scores neutral, not negative. Early brands often don't have
trackable signals yet — that's not the same as failing.
""")
    st.markdown("<div style='margin: 48px 0;'></div>", unsafe_allow_html=True)


# ── Phase: autonomous_running ─────────────────────────────────────────────────

def render_autonomous_running() -> None:
    brands = st.session_state.get("triage_brands", [])

    st.markdown(
        f'<div style="text-align:center; padding: 48px 0;">'
        f'<h1 class="sedge-h1" style="text-align:center; font-size:48px;">'
        f'BrokerFlow is running'
        f'</h1>'
        f'<p class="sedge-subtitle" style="text-align:center;">'
        f'Qualify → select → pitch → form. You\'ll review at the end.'
        f'</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Step 1: Triage
    step1_slot = st.empty()
    step1_slot.markdown(
        _progress_row("Qualify", "spinner", f"Scoring {len(brands)} brands…"),
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
            "Qualify", "check",
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


# ── Landing: two destination cards ───────────────────────────────────────────

def render_landing_cards() -> None:
    from ui.labels import (
        LABEL_EXISTING_BUSINESS, LABEL_EXISTING_BUSINESS_SUB,
        LABEL_BRAND_SCOUT, LABEL_BRAND_SCOUT_SUB,
    )

    _, col_docs = st.columns([5, 1])
    with col_docs:
        if st.button("Docs →", key="open_docs"):
            st.query_params["page"] = "docs"
            st.rerun()

    st.markdown(
        """
        <div style="text-align:center; padding: 2rem 1rem 2.5rem 1rem;">
            <div style="font-family:'Instrument Serif', Georgia, serif;
                        font-size:64px; line-height:1.1; color:#1a1a1a;">BrokerFlow</div>
            <div style="font-family:'Instrument Serif', Georgia, serif;
                        font-style:italic; font-size:22px; color:#6b6b6b;
                        margin-top:0.5rem;">
                the operating system for CPG brokers
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown(
            '<div class="sedge-destination-card">'
            '<div class="dest-title">Manage your existing business</div>'
            '<div class="dest-sub">Service the brands you already represent</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button(
            "Enter →", key="enter_existing_business",
            use_container_width=True, type="primary",
        ):
            st.session_state["workspace"] = "existing_business"
            st.rerun()

    with col2:
        st.markdown(
            '<div class="sedge-destination-card">'
            '<div class="dest-title">Scout new brands</div>'
            '<div class="dest-sub">Qualify new brands before you take a meeting</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button(
            "Enter →", key="enter_brand_scout",
            use_container_width=True,
        ):
            st.session_state["workspace"] = "brand_scout"
            st.rerun()


def render_back_nav() -> None:
    from ui.labels import LABEL_EXISTING_BUSINESS, LABEL_BRAND_SCOUT
    col_back, col_crumb = st.columns([1, 6])
    with col_back:
        if st.button("← BrokerFlow", key="back_to_landing"):
            st.session_state["workspace"] = None
            # Reset sub-navigation so re-entering starts fresh
            st.session_state.pop("open_agent", None)
            st.rerun()
    with col_crumb:
        ws_label = (
            LABEL_EXISTING_BUSINESS
            if st.session_state.get("workspace") == "existing_business"
            else LABEL_BRAND_SCOUT
        )
        st.markdown(
            f"<div style='padding-top:8px; color:#6b6b6b; font-size:14px;'>"
            f"/ {ws_label}</div>",
            unsafe_allow_html=True,
        )
    st.divider()


# ── Brand Scout workspace: idle (scoped, no landing-page bleed-through) ───────

_QUIET_LABEL = (
    "font-family:'Inter', sans-serif; font-size:12px; font-weight:500;"
    "color:#9CA3AF; letter-spacing:0.01em; margin:0 0 10px 0;"
)


def render_brand_scout_idle() -> None:
    # ── Above the fold — title is rendered by the workspace; here: helper copy,
    # input rows, primary CTA, and one tiny disclosure. No stats, no mode toggle,
    # no top-level "How it works" link. ───────────────────────────────────────
    st.markdown(
        '<p style="font-family:\'Inter\', sans-serif; font-size:14px;'
        'color:#57564F; line-height:1.5; margin:0 0 14px 0;">'
        "Enter up to 5 brands. We’ll tell you which ones are worth "
        "a meeting in about 30 seconds.</p>",
        unsafe_allow_html=True,
    )

    if "brand_inputs" not in st.session_state:
        st.session_state.brand_inputs = ["", "", "", "", ""]
    placeholders = ["Chomps", "Fishwife", "Graza", "Olipop", "Magic Spoon"]
    for i in range(5):
        st.session_state.brand_inputs[i] = st.text_input(
            f"Brand {i + 1}",
            value=st.session_state.brand_inputs[i],
            placeholder=placeholders[i],
            key=f"brand_input_{i}",
            label_visibility="collapsed",
        )

    filled_brands = [b for b in st.session_state.brand_inputs if b.strip()]

    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    if st.button(
        "Evaluate brands",
        disabled=len(filled_brands) == 0,
        use_container_width=True,
        type="primary",
        key="run_triage_btn",
    ):
        st.session_state.triage_brands = filled_brands
        st.session_state.phase = (
            "autonomous_running"
            if st.session_state.get("mode", "manual") == "autonomous"
            else "triaging"
        )
        st.rerun()

    # Tiny secondary disclosures — kept low-prominence on purpose.
    with st.expander("What we check"):
        st.markdown(
            "<p style='font-size:13px; line-height:1.6; color:#57564F; margin:0;'>"
            "Brand Scout pulls distribution, velocity signals, social presence, "
            "margin viability, and brand story across 10+ sources. It scores the "
            "brand on five criteria and returns a verdict: worth a meeting, "
            "watch for six months, or pass."
            "</p>",
            unsafe_allow_html=True,
        )

    with st.expander("Options"):
        mode_choice = st.radio(
            "Review mode",
            ["Step through — review each stage",
             "Run it — review at the end"],
            index=0 if st.session_state.get("mode", "manual") == "manual" else 1,
            label_visibility="collapsed",
            key="mode_radio",
        )
        st.session_state.mode = (
            "autonomous" if "Run it" in mode_choice else "manual"
        )

    # ── Below the fold — supporting documentation, visually quieter. ──────────
    st.markdown(
        "<hr style='border:none; border-top:1px solid #F2F2EE;"
        "margin:32px 0 18px;'>",
        unsafe_allow_html=True,
    )

    # Scoring tiers — compact stacked rows, not big cards
    st.markdown(
        f'<p style="{_QUIET_LABEL}">Scoring tiers</p>',
        unsafe_allow_html=True,
    )
    tier_rows = [
        ("Broker Ready", "45–69", "badge-ready",
         "Worth a meeting — enough traction to be credible, not yet locked into national distribution."),
        ("Established",  "70+",   "badge-established",
         "Check who reps them now — proven brand, likely already working with brokers."),
        ("Too Early",    "< 45",  "badge-early",
         "Check back in 6 months — missing velocity, distribution, or story."),
    ]
    rows_html = "".join(
        f'<div style="display:flex; align-items:center; gap:12px;'
        f'padding:10px 0; border-bottom:1px solid #F2F2EE;">'
        f'<span class="{cls}" style="flex-shrink:0;">{lbl}</span>'
        f'<span class="sedge-number" style="font-size:13px; color:#1A1A18;'
        f'min-width:54px;">{rng}</span>'
        f'<span style="font-size:13px; color:#57564F; line-height:1.5;">{desc}</span>'
        f'</div>'
        for lbl, rng, cls, desc in tier_rows
    )
    st.markdown(rows_html, unsafe_allow_html=True)

    # How scoring works — short paragraph
    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    st.markdown(
        f'<p style="{_QUIET_LABEL}">How scoring works</p>'
        f'<p style="font-size:13px; line-height:1.6; color:#57564F; margin:0;">'
        f"Five criteria, 100 points. Built from what brokers actually look for "
        f"before signing a brand. Missing data scores neutral, not negative — "
        f"early brands often don’t have trackable signals yet."
        f'</p>',
        unsafe_allow_html=True,
    )

    # Scoring rubric — disclosure with compact rows
    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
    with st.expander("Scoring rubric"):
        rubric = [
            ("Velocity Proof", 25,
             "Does the brand turn on shelf without being on promo? Not enough turns and the distributor drops it.",
             "Amazon reviews & rating · Subscribe & Save · Instacart banners · SPINS/NIQ · trade press"),
            ("Distribution Density", 20,
             "Enough stores to prove it works, not so many you can’t add value. Sweet spot: 20–300 stores.",
             "Store locators · WFM/Target/Walmart/Sprouts/Costco · Faire · Instacart banners"),
            ("Margin Viability", 20,
             "Can it survive the full stack — distributor markup, commission, free fills, slotting? 50% gross margin minimum.",
             "SRP vs category benchmarks · Faire wholesale · funding signals"),
            ("Brand Story Clarity", 20,
             "Can a rep explain it to a buyer in 30 seconds? Hero SKU, defined consumer, clear difference on shelf.",
             "Website · Instagram/TikTok · trade press · Expo West · certifications"),
            ("Promotional Independence", 15,
             "Will it pull through without leaning on promo funding? The strongest brands don’t promote at all.",
             "DTC & subscription · organic social · TPR frequency · Subscribe & Save"),
        ]
        rubric_rows = "".join(
            f'<div style="padding:12px 0; border-bottom:1px solid #F2F2EE;">'
            f'<div style="display:flex; justify-content:space-between;'
            f'align-items:baseline; margin-bottom:4px;">'
            f'<span style="font-size:14px; color:#1A1A18; font-weight:500;">{name}</span>'
            f'<span class="sedge-number" style="font-size:12px; color:#8B8A83;">{pts} pts</span>'
            f'</div>'
            f'<p style="font-size:13px; line-height:1.55; color:#57564F; margin:0 0 4px 0;">{desc}</p>'
            f'<p style="font-size:12px; color:#9CA3AF; margin:0;">Sources: {sources}</p>'
            f'</div>'
            for name, pts, desc, sources in rubric
        )
        st.markdown(rubric_rows, unsafe_allow_html=True)

    with st.expander("Verdict thresholds"):
        thresholds = [
            ("badge-ready",       "Broker Ready · 45–69",
             "Emerging brand in the sweet spot — credible traction, not yet locked into national distribution."),
            ("badge-established", "Established · 70+",
             "Proven brand, probably already has a broker. Lead with what their current broker isn’t doing."),
            ("badge-early",       "Too Early · under 45",
             "Not there yet on turns, doors, or story. Worth a check-in in six months."),
        ]
        thresh_html = "".join(
            f'<div style="padding:10px 0; border-bottom:1px solid #F2F2EE;">'
            f'<span class="{cls}" style="margin-right:8px;">{lbl}</span>'
            f'<p style="font-size:13px; line-height:1.55; color:#57564F; margin:8px 0 0 0;">{desc}</p>'
            f'</div>'
            for cls, lbl, desc in thresholds
        )
        st.markdown(thresh_html, unsafe_allow_html=True)

    with st.expander("On missing data"):
        st.markdown(
            "<p style='font-size:13px; line-height:1.6; color:#57564F; margin:0;'>"
            "Missing data scores neutral, not negative. Early brands often "
            "don’t have trackable signals yet — that’s not the same "
            "as failing."
            "</p>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin: 24px 0;'></div>", unsafe_allow_html=True)


# ── Brand Scout workspace ─────────────────────────────────────────────────────

def render_brand_scout_workspace() -> None:
    from ui.labels import LABEL_BRAND_SCOUT, LABEL_BRAND_SCOUT_SUB
    st.markdown(
        f"<div style='margin-bottom:14px;'>"
        f"<h1 style='font-family:\"Instrument Serif\", Georgia, serif;"
        f"font-size:32px; font-weight:400; letter-spacing:-0.01em;"
        f"line-height:1.1; color:#1A1A18; margin:0 0 4px 0;'>"
        f"{LABEL_BRAND_SCOUT}</h1>"
        f"<p style='font-family:\"Instrument Serif\", Georgia, serif;"
        f"font-style:italic; font-size:16px; color:#6b6b6b; line-height:1.4;"
        f"margin:0;'>{LABEL_BRAND_SCOUT_SUB}.</p>"
        f"</div>"
        f"<hr style='border:none; border-top:1px solid #EAEAE4;"
        f"margin:0 0 18px 0;'>",
        unsafe_allow_html=True,
    )

    # Phase-based flow — idle uses dedicated Brand Scout idle renderer
    phase = st.session_state.get("phase", "idle")
    try:
        if phase == "idle":
            render_brand_scout_idle()
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
        elif phase == "autonomous_running":
            render_autonomous_running()
        else:
            render_brand_scout_idle()
    except Exception as _exc:
        _error_card(_exc)


# ── Existing business: per-brand activity helpers ─────────────────────────────

_AGENT_KEYS = ["retailer_pitcher", "admin_ops"]
_AGENT_LABELS = {
    "retailer_pitcher": "Retailer Pitcher",
    "admin_ops":        "Admin & Ops",
}
_STATUS_COLORS = {
    "completed":       ("#D1FAE5", "#065F46"),
    "awaiting_review": ("#FEF3C7", "#92400E"),
    "in_progress":     ("#DBEAFE", "#1E40AF"),
    "idle":            ("#F3F4F6", "#6B7280"),
}
_STATUS_LABELS = {
    "completed":       "done",
    "awaiting_review": "review",
    "in_progress":     "running",
    "idle":            "idle",
}


def _ago_str(iso: str) -> str:
    from datetime import datetime, timezone
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


def _load_brand_activity(client, brand_ids: list) -> dict:
    """Return {brand_id: {agent_key: message}} — latest per (brand, agent) pair."""
    if not brand_ids:
        return {}
    try:
        res = (
            client.table("coordination_messages")
            .select("brand_id, from_agent, payload, created_at")
            .in_("brand_id", brand_ids)
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        )
        messages = res.data or []
    except Exception:
        return {}
    seen: set = set()
    result: dict = {}
    for m in messages:
        key = (m["brand_id"], m["from_agent"])
        if key not in seen:
            seen.add(key)
            bid = m["brand_id"]
            result.setdefault(bid, {})[m["from_agent"]] = m
    return result


def _agent_pill_html(agent_key: str, message: dict | None) -> str:
    label = _AGENT_LABELS.get(agent_key, agent_key)
    if not message:
        bg, fg = _STATUS_COLORS["idle"]
        return (
            f'<span style="font-size:11px; background:{bg}; color:{fg}; '
            f'padding:2px 9px; border-radius:99px; margin-right:6px; white-space:nowrap;">'
            f'{label}: idle</span>'
        )
    payload = message.get("payload") or {}
    status = payload.get("agent_status", "idle")
    action = payload.get("action_label", "")
    pending = payload.get("pending_review_count", 0)
    created_at = message.get("created_at", "")

    bg, fg = _STATUS_COLORS.get(status, _STATUS_COLORS["idle"])
    status_lbl = _STATUS_LABELS.get(status, status)
    if status == "awaiting_review" and pending:
        status_lbl = f"review \xd7{pending}"

    pill = (
        f'<span style="font-size:11px; background:{bg}; color:{fg}; '
        f'padding:2px 9px; border-radius:99px; margin-right:6px; white-space:nowrap;">'
        f'{label}: {status_lbl}</span>'
    )
    detail = ""
    if action:
        detail += f'<span style="font-size:11px; color:#8B8A83; margin-right:10px;">{action}</span>'
    if created_at and status in ("completed", "in_progress"):
        ago = _ago_str(created_at)
        if ago:
            detail += f'<span style="font-size:11px; color:#B0AFA8;">{ago}</span>'
    return pill + detail


# ── Existing business: brand roster ──────────────────────────────────────────

def _load_agent_memory(client, brand_ids: list) -> dict:
    """Return {brand_id: {agent_key: memory_payload}} from agent_memory messages."""
    if not client or not brand_ids:
        return {}
    try:
        res = (
            client.table("coordination_messages")
            .select("brand_id, from_agent, payload, created_at")
            .in_("brand_id", brand_ids)
            .eq("message_type", "agent_memory")
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        msgs = res.data or []
    except Exception:
        return {}
    seen: set = set()
    result: dict = {}
    for m in msgs:
        key = (m["brand_id"], m["from_agent"])
        if key not in seen:
            seen.add(key)
            result.setdefault(m["brand_id"], {})[m["from_agent"]] = m.get("payload") or {}
    return result


def _render_agent_panel_content(brand_id: str, agent_key: str, status: str, client) -> None:
    """Render the expanded artifact + agent memory for one agent panel."""
    from datetime import datetime, timezone

    # ── Artifact preview ──────────────────────────────────────────────────────
    if agent_key == "retailer_pitcher":
        try:
            res = (
                client.table("retailer_pitches")
                .select("email_subject, email_body, sell_sheet_html, created_at")
                .ilike("brand_name", st.session_state.get("_expand_brand_name_" + brand_id, "%"))
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            pitch = (res.data or [{}])[0]
        except Exception:
            pitch = {}

        if pitch.get("email_subject"):
            st.markdown(
                f'<p style="font-size:11px; font-weight:600; letter-spacing:0.08em; '
                f'color:#8B8A83; margin-bottom:4px;">LATEST PITCH</p>'
                f'<p style="font-size:13px; font-weight:500; color:#1A1A18; margin-bottom:4px;">'
                f'Subject: {pitch["email_subject"]}</p>',
                unsafe_allow_html=True,
            )
            body_preview = (pitch.get("email_body") or "")[:400]
            st.markdown(
                f'<div style="background:#FAFAF7; border:0.5px solid #EAEAEA; border-radius:8px; '
                f'padding:12px; font-size:13px; color:#444; line-height:1.6; white-space:pre-wrap;">'
                f'{body_preview}{"…" if len(pitch.get("email_body","")) > 400 else ""}</div>',
                unsafe_allow_html=True,
            )
            if status == "awaiting_review":
                col_edit, _ = st.columns([1, 2])
                with col_edit:
                    if st.button("Edit & send →",
                                 key=f"edit_pitch_{brand_id}", use_container_width=True):
                        st.session_state["open_agent"] = "retailer_agent"
                        st.rerun()
        elif status == "in_progress":
            st.markdown(
                '<p style="color:#1E40AF; font-size:13px;">Agent is drafting the pitch…</p>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<p style="color:#8B8A83; font-size:13px;">No pitch drafted yet for this brand.</p>',
                unsafe_allow_html=True,
            )

    elif agent_key == "admin_ops":
        form_data: dict = {}
        try:
            if _table_exists("new_item_forms"):
                res = (
                    client.table("new_item_forms")
                    .select("filled_fields, gaps, output_status, generated_at")
                    .order("generated_at", desc=True)
                    .limit(1)
                    .execute()
                )
                form_data = (res.data or [{}])[0]
        except Exception:
            pass

        if form_data.get("filled_fields"):
            filled = form_data["filled_fields"]
            gaps = form_data.get("gaps") or []
            sample_fields = list(filled.items())[:6]
            st.markdown(
                f'<p style="font-size:11px; font-weight:600; letter-spacing:0.08em; '
                f'color:#8B8A83; margin-bottom:6px;">WFM NEW-ITEM FORM</p>',
                unsafe_allow_html=True,
            )
            rows_html = "".join(
                f'<tr><td style="padding:4px 12px 4px 0; color:#8B8A83; font-size:12px;'
                f'white-space:nowrap;">{fid.replace("_"," ").title()}</td>'
                f'<td style="padding:4px 0; font-size:13px; color:#1A1A18;">{val}</td></tr>'
                for fid, val in sample_fields
            )
            st.markdown(
                f'<table style="width:100%; border-collapse:collapse;">{rows_html}</table>',
                unsafe_allow_html=True,
            )
            if len(filled) > 6:
                st.caption(f"… {len(filled) - 6} more fields filled")
            if gaps:
                st.markdown(
                    f'<p style="font-size:13px; color:#92400E; margin-top:8px;">'
                    f'⚠ {len(gaps)} gap{"s" if len(gaps) != 1 else ""} to fill</p>',
                    unsafe_allow_html=True,
                )
        elif status == "in_progress":
            st.markdown(
                '<p style="color:#1E40AF; font-size:13px;">Processing…</p>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<p style="color:#8B8A83; font-size:13px;">No form filed yet for this brand.</p>',
                unsafe_allow_html=True,
            )
        if status == "awaiting_review":
            col_open, _ = st.columns([1, 2])
            with col_open:
                if st.button("Review items →",
                             key=f"review_admin_{brand_id}", use_container_width=True):
                    st.session_state["open_agent"] = "admin_agent"
                    st.rerun()

    # ── Agent memory / context ────────────────────────────────────────────────
    mem_map = st.session_state.get("_agent_memory_map", {})
    mem = mem_map.get(brand_id, {}).get(agent_key, {})
    if mem:
        st.markdown(
            '<p style="font-size:11px; font-weight:600; letter-spacing:0.08em; '
            'color:#8B8A83; margin-top:12px; margin-bottom:4px;">AGENT CONTEXT</p>',
            unsafe_allow_html=True,
        )
        runs = mem.get("runs_completed", 0)
        flagged = mem.get("items_flagged_for_review", 0)
        st.markdown(
            f'<p style="font-size:12px; color:#8B8A83; margin-bottom:4px;">'
            f'{runs} runs completed · {flagged} flagged for review</p>',
            unsafe_allow_html=True,
        )
        prefs = mem.get("learned_preferences") or []
        for pref in prefs[:2]:
            st.markdown(
                f'<p style="font-size:12px; color:#57564F; margin:2px 0; padding-left:8px; '
                f'border-left:2px solid #EAEAEA;">Learned: {pref}</p>',
                unsafe_allow_html=True,
            )
        questions = mem.get("open_questions") or []
        for q in questions[:1]:
            st.markdown(
                f'<p style="font-size:12px; color:#92400E; margin:2px 0; padding-left:8px; '
                f'border-left:2px solid #FDE68A;">Open: {q}</p>',
                unsafe_allow_html=True,
            )


def render_brand_roster() -> None:
    from datetime import datetime, timezone

    # ── Load data ─────────────────────────────────────────────────────────────
    client = None
    brands_list: list = []
    try:
        from memory import _get_client
        client = _get_client()
        result = (
            client.table("brands")
            .select("id, brand_name, category, completeness_pct, status, onboarded_at, "
                    "is_sandbox, products, current_retailers, product_count")
            .order("onboarded_at", desc=True)
            .limit(50)
            .execute()
        )
        brands_list = result.data or []
    except Exception:
        pass

    sandbox_on = any(b.get("is_sandbox") for b in brands_list)
    brand_ids = [b["id"] for b in brands_list if b.get("id")]
    activity_map = _load_brand_activity(client, brand_ids) if client else {}
    memory_map = _load_agent_memory(client, brand_ids) if client else {}
    st.session_state["_agent_memory_map"] = memory_map

    # ── Empty state ───────────────────────────────────────────────────────────
    if not brands_list:
        if st.session_state.get("onboarding_active"):
            from ui.onboarding_flow import render_onboarding_flow
            render_onboarding_flow()
            return
        st.markdown(
            '<div style="text-align:center; padding:80px 0 48px;">'
            '<p style="font-size:11px; font-weight:600; letter-spacing:0.1em; '
            'color:#8B8A83; margin-bottom:12px;">READY TO RUN</p>'
            '<h2 style=\'font-family:"Instrument Serif", Georgia, serif; font-size:28px; '
            'font-weight:400; color:#1A1A18; margin:0 0 12px 0;\'>'
            'Your agents are ready — add a brand to get started</h2>'
            '<p style="font-size:14px; color:#8B8A83; max-width:480px; margin:0 auto 32px;">'
            "Onboard your first brand and BrokerFlow's agents will start pitching, "
            'processing paperwork, and tracking the book automatically.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        col_cta, _ = st.columns([1, 2])
        with col_cta:
            if st.button("+ Onboard a brand", type="primary", key="onboard_empty_btn",
                         use_container_width=True):
                st.session_state["onboarding_active"] = True
                st.rerun()
        _render_sandbox_footer(sandbox_on=False)
        return

    # If onboarding was triggered from the roster, show the form and return
    if st.session_state.get("onboarding_active"):
        from ui.onboarding_flow import render_onboarding_flow
        render_onboarding_flow()
        return

    # ── Build review items list ────────────────────────────────────────────────
    review_items: list[dict] = []
    for brand in brands_list:
        bid = brand.get("id")
        bname = brand.get("brand_name", "?")
        for ak in _AGENT_KEYS:
            msg = (activity_map.get(bid) or {}).get(ak)
            if not msg:
                continue
            payload = msg.get("payload") or {}
            if payload.get("agent_status") == "awaiting_review":
                review_items.append({
                    "brand_id":     bid,
                    "brand_name":   bname,
                    "agent_key":    ak,
                    "agent_label":  _AGENT_LABELS.get(ak, ak),
                    "action_label": payload.get("action_label", ""),
                    "pending":      payload.get("pending_review_count", 0),
                    "created_at":   msg.get("created_at", ""),
                })

    # ── Section A: Your agents (top) ──────────────────────────────────────────
    st.markdown(
        f'<h2 style=\'font-family:"Instrument Serif", Georgia, serif; '
        f'font-size:26px; font-weight:400; margin:0 0 2px 0;\'>Your agents</h2>'
        f'<p style="font-size:13px; color:#8B8A83; margin-bottom:16px;">'
        f'See what each agent has been doing across your entire book.</p>',
        unsafe_allow_html=True,
    )
    ba_col1, ba_col2 = st.columns(2, gap="medium")

    def _agent_stats(ak: str) -> tuple[int, str, int]:
        total = sum(1 for b in brands_list if (activity_map.get(b.get("id")) or {}).get(ak))
        msgs_with_status = [
            (activity_map.get(b.get("id")) or {}).get(ak) for b in brands_list
        ]
        review_n = sum(
            1 for m in msgs_with_status
            if m and (m.get("payload") or {}).get("agent_status") == "awaiting_review"
        )
        latest = None
        for m in msgs_with_status:
            if m and m.get("created_at"):
                if not latest or m["created_at"] > latest:
                    latest = m["created_at"]
        last_str = _ago_str(latest) if latest else "No activity"
        return total, last_str, review_n

    for ba_col, ak in zip([ba_col1, ba_col2], _AGENT_KEYS):
        with ba_col:
            total, last_str, review_n = _agent_stats(ak)
            review_indicator = (
                f'<span style="font-size:12px; color:#92400E;">'
                f' · {review_n} pending review</span>' if review_n else ""
            )
            with st.container(border=True):
                st.markdown(
                    f'<div style="font-family:\'Instrument Serif\', Georgia, serif; '
                    f'font-size:20px; font-weight:400; color:#1A1A18; margin-bottom:4px;">'
                    f'{_AGENT_LABELS[ak]}</div>'
                    f'<div style="font-size:13px; color:#8B8A83; margin-bottom:8px;">'
                    f'{total} brand{"s" if total != 1 else ""} · last active {last_str}'
                    f'{review_indicator}</div>',
                    unsafe_allow_html=True,
                )
                dest = "book/retailer_pitcher" if ak == "retailer_pitcher" else "book/admin_ops"
                if st.button(f"Open {_AGENT_LABELS[ak]} →",
                             key=f"browse_{ak}", use_container_width=True):
                    st.session_state["workspace"] = dest
                    st.rerun()

    st.markdown("<div style='margin-bottom:32px;'></div>", unsafe_allow_html=True)

    # ── Section B: Needs your review inbox ────────────────────────────────────
    if review_items:
        st.markdown(
            '<h2 style=\'font-family:"Instrument Serif", Georgia, serif; '
            'font-size:26px; font-weight:400; margin:0 0 2px 0;\'>Needs your review</h2>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p style="font-size:13px; color:#8B8A83; margin-bottom:12px;">'
            f'{len(review_items)} item{"s" if len(review_items) != 1 else ""} flagged by your agents '
            f'— everything else is running autonomously</p>',
            unsafe_allow_html=True,
        )
        for item in review_items:
            ago = _ago_str(item["created_at"])
            pending_str = f" ×{item['pending']}" if item["pending"] else ""
            col_badge, col_info, col_btn = st.columns([1, 5, 1])
            with col_badge:
                bg = "#DBEAFE" if item["agent_key"] == "retailer_pitcher" else "#D1FAE5"
                fg = "#1E40AF" if item["agent_key"] == "retailer_pitcher" else "#065F46"
                st.markdown(
                    f'<span style="background:{bg}; color:{fg}; font-size:11px; '
                    f'padding:3px 8px; border-radius:99px; white-space:nowrap;">'
                    f'{item["agent_label"]}</span>',
                    unsafe_allow_html=True,
                )
            with col_info:
                st.markdown(
                    f'<span style="font-weight:500; color:#1A1A18;">{item["brand_name"]}</span>'
                    f'<span style="color:#8B8A83; margin:0 6px;">·</span>'
                    f'<span style="color:#57564F;">{item["action_label"]}{pending_str}</span>'
                    f'<span style="color:#B0AFA8; font-size:11px; margin-left:8px;">'
                    f'flagged {ago}</span>',
                    unsafe_allow_html=True,
                )
            with col_btn:
                if st.button("Review →",
                             key=f"inbox_review_{item['brand_id']}_{item['agent_key']}",
                             use_container_width=True):
                    st.session_state[f"expand_{item['brand_id']}_{item['agent_key']}"] = True
                    st.session_state[f"_expand_brand_name_{item['brand_id']}"] = item["brand_name"]
                    st.rerun()
            st.markdown(
                "<div style='height:1px; background:#F3F3F0; margin:4px 0;'></div>",
                unsafe_allow_html=True,
            )
        st.markdown("<div style='margin-bottom:32px;'></div>", unsafe_allow_html=True)
    else:
        st.markdown(
            '<p style="font-size:13px; color:#8B8A83; margin-bottom:28px;">'
            'Nothing needs your attention. Agents are running.</p>',
            unsafe_allow_html=True,
        )

    # ── Section C: Your brands ────────────────────────────────────────────────
    n = len(brands_list)
    head_col, btn_col = st.columns([5, 1])
    with head_col:
        st.markdown(
            f'<h2 style=\'font-family:"Instrument Serif", Georgia, serif; '
            f'font-size:26px; font-weight:400; margin:0 0 2px 0;\'>Your brands</h2>'
            f'<p style="font-size:13px; color:#8B8A83; margin-bottom:16px;">'
            f'{n} brand{"s" if n != 1 else ""} · agents working continuously</p>',
            unsafe_allow_html=True,
        )
    with btn_col:
        st.markdown("<div style='padding-top:4px;'></div>", unsafe_allow_html=True)
        if st.button("+ Onboard new brand", key="onboard_roster_btn",
                     use_container_width=True, type="primary"):
            st.session_state["onboarding_active"] = True
            st.rerun()

    for brand in brands_list:
        bid = brand.get("id")
        name = brand.get("brand_name", "?")
        category = brand.get("category") or "—"
        product_count = len(brand.get("products") or [])
        door_count = brand.get("product_count", "")
        is_sb = brand.get("is_sandbox", False)
        brand_activity = activity_map.get(bid, {})

        # Store brand name so artifact loader can use it
        st.session_state[f"_expand_brand_name_{bid}"] = name

        has_review = any(
            (brand_activity.get(ak) or {}).get("payload", {}).get("agent_status") == "awaiting_review"
            for ak in _AGENT_KEYS
        )

        sandbox_tag = (
            ' <span style="font-size:10px; background:#E8EDE9; color:#2D5F3F; '
            'padding:2px 6px; border-radius:99px;">sandbox</span>'
            if is_sb else ""
        )
        door_tag = (
            f'<span style="font-size:12px; color:#8B8A83; margin-left:4px;">'
            f'{door_count} SKU{"s" if door_count != 1 else ""}</span>' if door_count else ""
        )

        # Accent bar for cards needing review
        if has_review:
            st.markdown(
                '<div style="height:3px; background:#F59E0B; border-radius:2px 2px 0 0;'
                ' margin-bottom:-1px;"></div>',
                unsafe_allow_html=True,
            )

        with st.container(border=True):
            # Brand identity row
            st.markdown(
                f'<div style="display:flex; align-items:baseline; gap:8px; '
                f'margin-bottom:10px; flex-wrap:wrap;">'
                f'<span style="font-family:\'Instrument Serif\', Georgia, serif; '
                f'font-size:22px; font-weight:400; color:#1A1A18;">{name}</span>'
                f'{sandbox_tag}'
                f'<span style="font-size:12px; color:#8B8A83;">{category}</span>'
                f'{door_tag}'
                f'<span style="font-size:12px; color:#B0AFA8;">'
                f'&middot; {product_count} SKU{"s" if product_count != 1 else ""}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Agent panels side by side
            col1, col2 = st.columns(2, gap="small")
            for col, ak in zip([col1, col2], _AGENT_KEYS):
                with col:
                    msg = brand_activity.get(ak)
                    payload = (msg or {}).get("payload") or {}
                    status = payload.get("agent_status", "idle")
                    action = payload.get("action_label", "")
                    pending = payload.get("pending_review_count", 0)
                    created_at = (msg or {}).get("created_at", "")

                    status_lbl = {
                        "completed":       "done",
                        "awaiting_review": f"review \xd7{pending}" if pending else "review",
                        "in_progress":     "running",
                        "idle":            "idle",
                    }.get(status, status)

                    exp_label = f"**{_AGENT_LABELS[ak]}** · {status_lbl}"
                    if action:
                        exp_label += f" — {action}"
                    if created_at and status in ("completed", "in_progress"):
                        exp_label += f" · {_ago_str(created_at)}"

                    auto_expand = st.session_state.pop(f"expand_{bid}_{ak}", False)

                    with st.expander(exp_label, expanded=auto_expand):
                        _render_agent_panel_content(bid, ak, status, client)

        st.markdown("<div style='margin-bottom:6px;'></div>", unsafe_allow_html=True)

    # ── Section D: Activity feed ──────────────────────────────────────────────
    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)
    _render_book_activity_feed(client, brand_ids)

    # ── Dev / utilities footer ────────────────────────────────────────────────
    _render_sandbox_footer(sandbox_on)


def _render_book_activity_feed(client, brand_ids: list) -> None:
    """Cross-brand activity feed — last 10 non-idle, non-memory events."""
    if not client or not brand_ids:
        return
    try:
        res = (
            client.table("coordination_messages")
            .select("brand_id, from_agent, message_type, payload, created_at")
            .in_("brand_id", brand_ids)
            .neq("message_type", "agent_memory")
            .neq("message_type", "idle")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        events = res.data or []
    except Exception:
        return
    if not events:
        return

    # Fetch brand names
    try:
        br = client.table("brands").select("id, brand_name").in_("id", brand_ids).execute()
        bn_map = {r["id"]: r["brand_name"] for r in (br.data or [])}
    except Exception:
        bn_map = {}

    st.markdown(
        '<h2 style=\'font-family:"Instrument Serif", Georgia, serif; '
        'font-size:24px; font-weight:400; margin-bottom:4px;\'>What the agents have been doing</h2>',
        unsafe_allow_html=True,
    )
    for ev in events:
        payload = ev.get("payload") or {}
        agent = _AGENT_LABELS.get(ev["from_agent"], ev["from_agent"])
        action = payload.get("action_label") or ev["message_type"].replace("_", " ")
        brand = bn_map.get(ev.get("brand_id", ""), "?")
        ago = _ago_str(ev.get("created_at", ""))
        st.markdown(
            f'<div style="padding:7px 0; border-bottom:0.5px solid #F3F3F0; '
            f'font-size:13px; color:#444;">'
            f'<span style="font-weight:500; color:#1A1A18;">{agent}</span> &nbsp;'
            f'<span>{action}</span> &nbsp;'
            f'<span style="color:#8B8A83;">for {brand}</span> &nbsp;'
            f'<span style="color:#B0AFA8; font-size:11px;">{ago}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)


def _render_sandbox_footer(sandbox_on: bool) -> None:
    st.markdown("<div style='margin-top:48px;'></div>", unsafe_allow_html=True)
    with st.expander("Dev utilities", expanded=False):
        col_load, col_clear, col_run, _ = st.columns([1, 1, 1, 2])
        with col_load:
            if st.button("Load sandbox brands", key="sandbox_load_btn", use_container_width=True):
                try:
                    from sandbox.fixtures import seed_sandbox_brands
                    seed_sandbox_brands()
                except Exception as e:
                    st.error(f"Seed failed: {e}")
                st.rerun()
        with col_clear:
            if st.button("Clear sandbox", key="sandbox_clear_btn",
                         use_container_width=True, disabled=not sandbox_on):
                try:
                    from sandbox.fixtures import clear_sandbox_brands
                    clear_sandbox_brands()
                except Exception as e:
                    st.error(f"Clear failed: {e}")
                st.rerun()
        with col_run:
            if st.button("Run agents now", key="run_agents_btn", use_container_width=True,
                         disabled=not sandbox_on):
                try:
                    from sandbox.fixtures import seed_sandbox_brands
                    seed_sandbox_brands()
                    st.toast("Agent cycle complete — activity refreshed.")
                except Exception as e:
                    st.error(f"Run failed: {e}")
                st.rerun()


# ── Existing business: recent activity feed ───────────────────────────────────

def render_recent_activity_feed() -> None:
    from datetime import datetime, timezone
    from ui.labels import AGENT_DISPLAY_NAMES
    try:
        from memory import _get_client
        client = _get_client()
        result = (
            client.table("coordination_messages")
            .select("from_agent, to_agent, message_type, created_at, payload")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        events = result.data or []
    except Exception:
        events = []

    if not events:
        return

    st.markdown(
        "<h3 style='font-family:\"Instrument Serif\", Georgia, serif; "
        "font-size:22px; font-weight:400; margin-top:1.5rem;'>What the agents have been doing</h3>",
        unsafe_allow_html=True,
    )
    for ev in events:
        try:
            ts = datetime.fromisoformat(ev["created_at"].replace("Z", "+00:00"))
            delta = datetime.now(timezone.utc) - ts
            if delta.total_seconds() < 3600:
                ago = f"{int(delta.total_seconds() / 60)} min ago"
            elif delta.total_seconds() < 86400:
                ago = f"{int(delta.total_seconds() / 3600)} hr ago"
            else:
                ago = f"{delta.days}d ago"
        except Exception:
            ago = "?"
        from_label = AGENT_DISPLAY_NAMES.get(ev["from_agent"], ev["from_agent"])
        to_label = AGENT_DISPLAY_NAMES.get(ev["to_agent"], ev["to_agent"])
        brand_name = (ev.get("payload") or {}).get("brand_name", "")
        msg = ev["message_type"].replace("_", " ")
        st.markdown(
            f"<div style='border-bottom:1px solid #EAEAEA; padding:0.5rem 0; "
            f"font-size:13px; color:#444; line-height:1.5;'>"
            f"<span style='color:#888; font-size:11px;'>{ago}</span> &nbsp; "
            f"<strong>{from_label}</strong> → <strong>{to_label}</strong>: "
            f"{msg}{' (' + brand_name + ')' if brand_name else ''}"
            f"</div>",
            unsafe_allow_html=True,
        )


# ── Existing business: agent loop status helper ───────────────────────────────

def _agent_loop_status(internal_agent_name: str) -> dict:
    from datetime import datetime, timezone
    try:
        from memory import _get_client
        client = _get_client()
        result = (
            client.table("coordination_messages")
            .select("created_at")
            .eq("from_agent", internal_agent_name)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            last = datetime.fromisoformat(
                result.data[0]["created_at"].replace("Z", "+00:00")
            )
            delta = datetime.now(timezone.utc) - last
            if delta.total_seconds() < 3600:
                last_str = f"{int(delta.total_seconds() / 60)} min ago"
            elif delta.total_seconds() < 86400:
                last_str = f"{int(delta.total_seconds() / 3600)} hr ago"
            else:
                last_str = f"{delta.days} day(s) ago"
        else:
            last_str = "Never"
    except Exception:
        last_str = "Unknown"
    return {"last_run": last_str, "next_run": "On next session start"}


# ── Existing business: agent picker ──────────────────────────────────────────

def render_agent_picker() -> None:
    from ui.labels import LABEL_RETAILER_AGENT, LABEL_ADMIN_AGENT
    agents = [
        (
            "retailer_agent", LABEL_RETAILER_AGENT,
            "Pitch buyers · promos (Q3) · category reviews (Q3)",
            _agent_loop_status("retailer_pitcher"),
        ),
        (
            "admin_agent", LABEL_ADMIN_AGENT,
            "New-item forms · POs (Q2) · deductions (Q2) · demo spend (Q3)",
            _agent_loop_status("admin_ops"),
        ),
    ]
    col1, col2 = st.columns(2, gap="medium")
    cols = [col1, col2]
    for col, (key, name, capabilities, loop_status) in zip(cols, agents):
        with col:
            with st.container(border=True):
                st.markdown(
                    f"<div style='font-family:\"Instrument Serif\", Georgia, serif; "
                    f"font-size:24px; font-weight:400; color:#1a1a1a;'>{name}</div>",
                    unsafe_allow_html=True,
                )
                st.caption(capabilities)
                if loop_status:
                    st.markdown(
                        f"<div style='margin-top:0.75rem; font-size:12px; color:#888;'>"
                        f"↻ Last run: {loop_status['last_run']}<br>"
                        f"Next: {loop_status['next_run']}</div>",
                        unsafe_allow_html=True,
                    )
                if st.button("Open", key=f"open_{key}", use_container_width=True):
                    st.session_state["open_agent"] = key
                    st.rerun()


# ── Existing business workspace ───────────────────────────────────────────────

def render_existing_business_workspace() -> None:
    # Top-right "Coordination demo" entry point
    _, col_demo = st.columns([5, 2])
    with col_demo:
        if st.button("▶ Coordination protocol demo", key="open_demo_btn",
                     use_container_width=True):
            st.session_state["workspace"] = "demo"
            st.rerun()

    # Watchdog — run once per session in a background thread so it never
    # blocks the first render of this workspace. (Synchronous scan was making
    # the previous page's DOM linger visibly during navigation.)
    if "watchdog_ran" not in st.session_state:
        st.session_state["watchdog_ran"] = True
        try:
            import threading
            from agents.brand_onboarding.watchdog import scan_and_flag_stale_brands
            threading.Thread(
                target=scan_and_flag_stale_brands, daemon=True
            ).start()
        except Exception:
            pass

    # Watchdog banner
    try:
        from agents.brand_onboarding.watchdog import get_pending_reverifications
        pending = get_pending_reverifications()
    except Exception:
        pending = []
    if pending:
        st.info(
            f"⚡ Watchdog flagged {len(pending)} brand(s) for re-verification — "
            "last verified >30 days ago."
        )
        with st.expander("Show flagged brands"):
            for msg in pending:
                payload = msg.get("payload", {})
                st.write(
                    f"**{payload.get('brand_name', '?')}** — "
                    f"{payload.get('days_stale', '?')} days stale"
                )

    # Route: if an agent page is open, render it; otherwise show roster + agents
    open_agent = st.session_state.get("open_agent")
    if open_agent:
        from ui.agent_page import render_agent_page
        try:
            render_agent_page(open_agent)
        except Exception as exc:
            _error_card(exc)
        return

    render_brand_roster()


# ── Documentation page ────────────────────────────────────────────────────────

def render_docs() -> None:
    col_l, _ = st.columns([1, 5])
    with col_l:
        if st.button("← BrokerFlow", key="back_from_docs"):
            st.query_params.clear()
            st.rerun()

    st.markdown("""
    <div style="padding: 32px 0 48px;">
      <div style="font-family:'Instrument Serif', Georgia, serif; font-size:56px;
                  line-height:1.1; color:#1a1a1a;">BrokerFlow</div>
      <div style="font-family:'Instrument Serif', Georgia, serif; font-style:italic;
                  font-size:22px; color:#6b6b6b; margin-top:0.5rem; margin-bottom:1.5rem;">
        the operating system for CPG brokers
      </div>
      <p style="font-size:16px; color:#444; max-width:640px; line-height:1.7;">
        BrokerFlow replaces the manual research, pitching, and paperwork that independent
        food &amp; beverage brokers do by hand with a multi-agent workspace that runs
        continuously across their entire book of business.
      </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        "<hr style='border:none; border-top:1px solid #EAEAE4; margin:0 0 48px;'>",
        unsafe_allow_html=True,
    )

    # ── What it does ──────────────────────────────────────────────────────────
    st.markdown('<p class="sedge-section-title">WHAT IT DOES</p>', unsafe_allow_html=True)

    agents_info = [
        (
            "Brand Scout",
            "New brand qualification",
            "Enter any CPG brand name. BrokerFlow researches it across Amazon, Instacart, "
            "Faire, social media, and trade press, then scores it on five criteria "
            "(0–100) and returns a broker-ready brief.",
        ),
        (
            "Retailer Pitcher",
            "Buyer-tailored outreach",
            "Drafts outreach emails and one-page sell sheets customized to each "
            "buyer's persona — what they care about, what kills a pitch with them, "
            "and which proof points resonate. Supports Whole Foods, Sprouts, and Erewhon.",
        ),
        (
            "Admin & Ops",
            "Form autofill",
            "Autofills the Whole Foods New Item Setup Form (~70 fields across 10 "
            "sections) from everything BrokerFlow knows about the brand. Two-pass fill: "
            "deterministic rules first, LLM inference for ambiguous fields. Exports "
            "a ready-to-submit Excel file and flags required gaps.",
        ),
        (
            "Brand Onboarding",
            "Canonical record extraction",
            "Three-step flow (brand info → agent processing → review) that adds a "
            "brand to the book, extracts a structured record from uploaded materials "
            "(PDF, DOCX, XLSX), and hands off to Retailer Pitcher and Admin & Ops.",
        ),
    ]

    for name, tagline, desc in agents_info:
        st.markdown(f"""
        <div class="sedge-card" style="margin-bottom:16px;">
          <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:8px;">
            <h3 style="font-family:'Instrument Serif', serif; font-size:20px;
                       font-weight:400; margin:0;">{name}</h3>
            <span style="font-size:12px; color:#8B8A83; font-style:italic;">{tagline}</span>
          </div>
          <p style="font-size:14px; line-height:1.6; color:#1A1A18; margin:0;">{desc}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(
        "<hr style='border:none; border-top:1px solid #EAEAE4; margin:48px 0;'>",
        unsafe_allow_html=True,
    )

    # ── Scoring rubric ────────────────────────────────────────────────────────
    st.markdown('<p class="sedge-section-title">BRAND SCOUT SCORING RUBRIC</p>', unsafe_allow_html=True)
    st.markdown(
        "<p style='font-size:14px; color:#444; margin-bottom:24px;'>"
        "Five criteria, 100 points. Built from what brokers told us they actually look for "
        "before signing a brand.</p>",
        unsafe_allow_html=True,
    )

    rubric = [
        ("Velocity Proof", 25,
         "Does the brand turn on shelf without being on promo?",
         "Amazon reviews & rating · Subscribe & Save · Instacart banners · SPINS/NIQ mentions · trade press"),
        ("Distribution Density", 20,
         "Enough stores to prove it works — not so many you can't add value.",
         "Store locators · Whole Foods/Target/Walmart/Sprouts/Costco · Faire door count"),
        ("Margin Viability", 20,
         "Can it survive the full stack: distributor markup, commission, slotting, deductions?",
         "SRP vs. category benchmarks · Faire wholesale pricing · funding signals"),
        ("Brand Story Clarity", 20,
         "Can a rep explain it to a buyer in 30 seconds?",
         "Website · Instagram/TikTok · trade press (NOSH, FoodNavigator) · certifications"),
        ("Promotional Independence", 15,
         "Will the brand pull through without leaning on you for promo funding?",
         "DTC channel · organic social following · TPR frequency · Subscribe & Save"),
    ]
    for name, pts, desc, sources in rubric:
        st.markdown(f"""
        <div class="sedge-card" style="margin-bottom:12px;">
          <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:6px;">
            <strong style="font-size:14px;">{name}</strong>
            <span style="font-size:12px; background:#E8EDE9; padding:2px 10px;
                         border-radius:99px; color:#1A1A18;">{pts} pts</span>
          </div>
          <p style="font-size:13px; color:#1A1A18; margin:0 0 6px;">{desc}</p>
          <p style="font-size:12px; color:#8B8A83; margin:0;"><strong>Sources:</strong> {sources}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin:16px 0 8px;'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    for col, pill_class, label, note in [
        (c1, "sedge-pill-early",       "Too Early · < 45",    "Not there yet on turns, doors, or story."),
        (c2, "sedge-pill-ready",       "Broker Ready · 45–69","Sweet spot — traction without national lock-in."),
        (c3, "sedge-pill-established", "Established · 70+",   "Proven, but probably already has a broker."),
    ]:
        with col:
            st.markdown(f"""
            <div class="sedge-card">
              <span class="sedge-pill {pill_class}">{label}</span>
              <p style="font-size:13px; margin:10px 0 0;">{note}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(
        "<hr style='border:none; border-top:1px solid #EAEAE4; margin:48px 0;'>",
        unsafe_allow_html=True,
    )

    # ── Architecture ──────────────────────────────────────────────────────────
    st.markdown('<p class="sedge-section-title">ARCHITECTURE</p>', unsafe_allow_html=True)
    st.markdown("""
**Agent coordination** — Agents communicate through a shared Supabase blackboard
(`coordination_messages` table). Each agent writes structured messages when it
completes work or needs human review. The book-of-business page reads these messages
to show status across all brands without any agent-to-agent API calls.

**LLM routing** — A shim module patches `anthropic.Anthropic` at import time.
Set `SEDGE_LLM_PROVIDER=gemini` to route all Claude calls through Gemini 2.5 Flash
(~50× cheaper at some quality tradeoff). Default is `claude`.

**State persistence** — Within a single agent run, state is managed by LangGraph's
`MemorySaver` checkpointer (in-process, per thread). Cross-agent data lives in
Supabase and survives restarts.
""")

    st.code("""ui/brokerflow_app.py          ← Streamlit app, workspace router
ui/per_agent_page.py    ← Retailer Pitcher + Admin & Ops pages
ui/onboarding_flow.py   ← Brand onboarding 3-step UI

agents/
  brand_scout/          ← Research + scoring (LangGraph, 10-tool ReAct loop)
  retailer_pitcher/     ← Email + sell sheet generation per buyer persona
  admin_ops/            ← WFM form autofill + gap flagging
  brand_onboarding/     ← Canonical record extraction from uploaded docs
  retailer_matcher/     ← Buyer heuristic (score + category → buyer_key)
  orchestrator/         ← Pipeline wiring all agents together
  llm_shim.py           ← Routes anthropic calls to Gemini or Claude

memory.py               ← Supabase client + persistence helpers
state.py                ← Shared TypedDict state types""", language="text")

    st.markdown(
        "<hr style='border:none; border-top:1px solid #EAEAE4; margin:48px 0;'>",
        unsafe_allow_html=True,
    )

    # ── Setup ─────────────────────────────────────────────────────────────────
    st.markdown('<p class="sedge-section-title">LOCAL SETUP</p>', unsafe_allow_html=True)
    st.code("""git clone https://github.com/isabeldeatucha-spec/sedge.git
cd sedge
pip install -r requirements.txt
cp .env.example .env   # then fill in your keys
streamlit run ui/brokerflow_app.py""", language="bash")

    st.markdown("**Required environment variables:**")
    st.code("""ANTHROPIC_API_KEY=sk-ant-...       # or set SEDGE_LLM_PROVIDER=gemini + GEMINI_API_KEY
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJ...
FIRECRAWL_API_KEY=fc-...            # for Brand Scout web scraping""", language="bash")

    st.markdown(
        "<hr style='border:none; border-top:1px solid #EAEAE4; margin:48px 0;'>",
        unsafe_allow_html=True,
    )

    # ── Limitations ───────────────────────────────────────────────────────────
    st.markdown('<p class="sedge-section-title">LIMITATIONS</p>', unsafe_allow_html=True)
    limitations = [
        ("Brand Scout accuracy", "Scores are estimates from public signals. Not sourced from SPINS, Nielsen, or any paid data provider. Door counts and velocity figures are inferred, not authoritative."),
        ("Retailer coverage", "Three buyer personas supported: Whole Foods, Sprouts, Erewhon. KeHE, UNFI, Kroger, and Costco are on the roadmap."),
        ("Admin & Ops forms", "Only the Whole Foods New Item Setup Form is implemented. The form template is the 2018 version; field layouts change periodically."),
        ("No email sending", "BrokerFlow drafts and exports pitches and forms but does not send email. 'Send to buyer' buttons are UI placeholders."),
        ("No PO ingestion", "PO processing, deduction tracking, demo spend reconciliation, and commission reconciliation are on the roadmap but not yet implemented."),
        ("Checkpointer", "Agent state uses MemorySaver (in-process). If the Streamlit process restarts mid-run, in-flight graph state is lost. Persisted Supabase data is unaffected."),
    ]
    for title, body in limitations:
        st.markdown(f"""
        <div style="margin-bottom:12px; padding:14px 16px; background:#FAFAF8;
                    border-radius:8px; border:1px solid #EAEAE4;">
          <strong style="font-size:14px;">{title}</strong>
          <p style="font-size:13px; color:#555; margin:4px 0 0;">{body}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin: 48px 0;'></div>", unsafe_allow_html=True)


# ── Top-level workspace router ────────────────────────────────────────────────

if "workspace" not in st.session_state:
    st.session_state["workspace"] = None

workspace = st.session_state["workspace"]

try:
    if st.query_params.get("page") == "docs":
        render_docs()
    elif workspace is None:
        render_landing_cards()
    elif workspace == "existing_business":
        render_back_nav()
        render_existing_business_workspace()
    elif workspace == "brand_scout":
        render_back_nav()
        render_brand_scout_workspace()
    elif workspace in ("book/retailer_pitcher", "book/admin_ops"):
        from ui.per_agent_page import render_per_agent_page
        render_per_agent_page(workspace.split("/")[1])
    elif workspace == "demo":
        from ui.demo_view import render_demo_view
        render_demo_view()
    else:
        render_landing_cards()
except Exception as _top_exc:
    _error_card(_top_exc)
