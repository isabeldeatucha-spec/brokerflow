"""
Sedge — unified multi-agent entry point.

Run:
    cd /Users/isabelatucha/sedge
    streamlit run ui/sedge_app.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# llm_shim must be imported before any anthropic import
import agents.llm_shim  # noqa: F401, E402

import streamlit as st

from memory import _get_client
from ui.global_css import inject_global_css

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Sedge",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()

# ── Sidebar nav ───────────────────────────────────────────────────────────────

NAV_OPTIONS = [
    "Dashboard",
    "Brand Scout",
    "Retailer Pitcher",
    "Admin & Ops",
    "Portfolio Mgr",
]

# Keep legacy nav keys so handoff_brand / forced_page still work
_NAV_LEGACY_MAP = {
    "🏠  Dashboard":       "Dashboard",
    "🔍  Brand Scout":     "Brand Scout",
    "📬  Retailer Pitcher": "Retailer Pitcher",
    "📋  Admin & Ops":     "Admin & Ops",
    "📊  Portfolio Mgr":   "Portfolio Mgr",
}
_NAV_PAGE_MAP = {v: v for v in NAV_OPTIONS}

if "_nav_idx" not in st.session_state:
    st.session_state["_nav_idx"] = 0

_forced = st.session_state.pop("forced_page", None)
if _forced:
    _resolved = _NAV_LEGACY_MAP.get(_forced, _forced)
    if _resolved in NAV_OPTIONS:
        st.session_state["_nav_idx"] = NAV_OPTIONS.index(_resolved)

with st.sidebar:
    st.markdown(
        '<div style="padding:40px 20px 0;">'
        '<div style="font-family:\'Instrument Serif\',Georgia,serif;font-size:28px;'
        'font-weight:400;color:#1A1A18;letter-spacing:-0.02em;margin-bottom:2px;">Sedge</div>'
        '<div style="font-family:\'Instrument Serif\',Georgia,serif;font-size:14px;'
        'font-style:italic;color:#8B8A83;margin-bottom:40px;">for independent food brokers</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="padding:0 20px;"><p style="font-size:11px;font-weight:600;color:#8B8A83;'
        'text-transform:uppercase;letter-spacing:0.12em;margin-bottom:8px;">Workspace</p></div>',
        unsafe_allow_html=True,
    )
    _nav_selected = st.radio(
        "nav",
        options=NAV_OPTIONS,
        index=st.session_state["_nav_idx"],
        label_visibility="collapsed",
        key="_nav_radio",
    )
    st.session_state["_nav_idx"] = NAV_OPTIONS.index(_nav_selected)

    st.markdown(
        '<div style="padding:0 20px;margin-top:32px;">'
        '<p style="font-size:11px;font-weight:600;color:#8B8A83;text-transform:uppercase;'
        'letter-spacing:0.12em;margin-bottom:8px;">Settings</p></div>',
        unsafe_allow_html=True,
    )
    demo_on = st.toggle(
        "Demo mode",
        value=st.session_state.get("demo_mode", False),
        key="_demo_toggle",
        help="Uses cached results for Chomps, Fishwife, and Graza — no live LLM calls.",
    )
    st.session_state["demo_mode"] = demo_on
    if demo_on:
        st.caption("Cached results active")

# ── Dashboard ─────────────────────────────────────────────────────────────────

_PIPELINE_DEMO_BRANDS = {"chomps", "fishwife", "graza"}
_PIPELINE_DEMO_DIR = Path(__file__).parent / "demo_cache" / "orchestrator"

_STAGE_ORDER  = ["scout", "pitcher_wf", "pitcher_sprouts", "pitcher_erewhon", "admin_wfm"]
_STAGE_LABELS = {
    "scout":           "Brand Scout",
    "pitcher_wf":      "Retailer Pitcher → Whole Foods",
    "pitcher_sprouts": "Retailer Pitcher → Sprouts",
    "pitcher_erewhon": "Retailer Pitcher → Erewhon",
    "admin_wfm":       "Admin & Ops → WFM New Item Form",
}
_RETAILER_LABEL = {"whole_foods": "Whole Foods", "sprouts": "Sprouts", "erewhon": "Erewhon"}


def _stage_row_html(stage: str, event) -> str:
    """Return editorial HTML for one pipeline progress row (no emoji, Lucide SVGs)."""
    from ui.icons import ICON_CIRCLE, ICON_SPINNER, ICON_CHECK_CIRCLE, ICON_X_CIRCLE
    label = _STAGE_LABELS.get(stage, stage)
    if event is None:
        icon_html = f'<span style="color:#EAEAE4;">{ICON_CIRCLE}</span>'
        msg = "waiting"
        msg_color = "#8B8A83"
    elif event["status"] == "running":
        icon_html = f'<span style="color:#0F3530;" class="sedge-spin">{ICON_SPINNER}</span>'
        msg = event.get("message", "running…")
        msg_color = "#0F3530"
    elif event["status"] == "done":
        icon_html = f'<span style="color:#2D5F3F;">{ICON_CHECK_CIRCLE}</span>'
        msg = event.get("message", "done")
        msg_color = "#8B8A83"
    else:
        icon_html = f'<span style="color:#8B2F2F;">{ICON_X_CIRCLE}</span>'
        msg = event.get("error") or event.get("message", "error")
        msg_color = "#8B2F2F"
    return (
        f'<div class="sedge-pipeline-row">'
        f'<div class="sedge-pipeline-icon">{icon_html}</div>'
        f'<div style="flex:1;">'
        f'<div class="sedge-pipeline-label">{label}</div>'
        f'<div class="sedge-pipeline-msg" style="color:{msg_color};">{msg}</div>'
        f'</div>'
        f'</div>'
    )


def _fetch_stats() -> dict:
    """Pull live counts from Supabase."""
    defaults: dict = {
        "brands_evaluated": 0,
        "pitches_drafted":  0,
        "forms_filled":     0,
        "bundles_sent":     0,
        "recent_activity":  [],
    }
    try:
        client = _get_client()
    except Exception as exc:
        print(f"[Dashboard] Supabase client failed: {exc}")
        return defaults

    evaluations: list[dict] = []
    pitches:     list[dict] = []
    forms:       list[dict] = []
    bundles:     list[dict] = []

    try:
        r = client.table("brand_evaluations").select("brand_name, score, verdict, evaluated_at").order("evaluated_at", desc=True).limit(50).execute()
        evaluations = r.data or []
        defaults["brands_evaluated"] = len(evaluations)
    except Exception as exc:
        print(f"[Dashboard] brand_evaluations: {exc}")

    try:
        r = client.table("retailer_pitches").select("brand_name, buyer, created_at").order("created_at", desc=True).limit(50).execute()
        pitches = r.data or []
        defaults["pitches_drafted"] = len(pitches)
    except Exception as exc:
        print(f"[Dashboard] retailer_pitches: {exc}")

    try:
        r = client.table("new_item_forms").select("brand_name, retailer, generated_at").order("generated_at", desc=True).limit(50).execute()
        forms = r.data or []
        defaults["forms_filled"] = len(forms)
    except Exception as exc:
        print(f"[Dashboard] new_item_forms: {exc}")

    try:
        r = client.table("sent_bundles").select("brand_name, retailer, bundle_type, sent_at").order("sent_at", desc=True).limit(20).execute()
        bundles = r.data or []
        defaults["bundles_sent"] = len(bundles)
    except Exception:
        pass  # table may not exist yet — silently skip

    activity: list[dict] = []
    for row in bundles[:5]:
        activity.append({
            "label": f"Bundle sent — {row['brand_name']} → {row.get('retailer','—')} ({row.get('bundle_type','—')})",
            "ts": (row.get("sent_at") or "")[:10],
            "icon": "📤",
        })
    for row in evaluations[:5]:
        activity.append({
            "label": f"Brand Scout evaluated {row['brand_name']} — {row['score']}/100",
            "ts": (row.get("evaluated_at") or "")[:10],
            "icon": "🔍",
        })
    for row in pitches[:5]:
        activity.append({
            "label": f"Retailer Pitcher drafted pitch for {row['brand_name']} → {row.get('buyer') or '—'}",
            "ts": (row.get("created_at") or "")[:10],
            "icon": "📬",
        })
    for row in forms[:5]:
        activity.append({
            "label": f"Admin & Ops filled WFM form for {row['brand_name']} / {row.get('retailer') or '—'}",
            "ts": (row.get("generated_at") or "")[:10],
            "icon": "📋",
        })
    activity.sort(key=lambda x: x["ts"], reverse=True)
    defaults["recent_activity"] = activity[:10]
    return defaults


def _render_approval_screen(results: dict) -> None:
    """Render the 3-bundle approval screen after pipeline completes."""
    import json as _json

    st.markdown(
        '<div style="margin-top:24px;">'
        '<p style="font-size:15px;font-weight:700;color:#111111;margin-bottom:4px;">Review bundles before sending</p>'
        '<p style="font-size:12px;color:#9CA3AF;margin-bottom:16px;">Check the bundles you want to mark as sent, then click the button below.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    BUNDLE_DEFS = [
        {"stage": "pitcher_wf",      "buyer_key": "whole_foods", "label": "Whole Foods",
         "color": "#1B4F72", "bg": "#EBF5FB", "has_form": True},
        {"stage": "pitcher_sprouts", "buyer_key": "sprouts",     "label": "Sprouts",
         "color": "#065F46", "bg": "#D1FAE5", "has_form": False},
        {"stage": "pitcher_erewhon", "buyer_key": "erewhon",     "label": "Erewhon",
         "color": "#92400E", "bg": "#FEF3C7", "has_form": False},
    ]

    scout_data   = (results.get("scout")    or {}).get("data", {})
    admin_data   = (results.get("admin_wfm") or {}).get("data", {})
    brand_name   = scout_data.get("brand_name", "Brand")
    score        = (scout_data.get("score") or {}).get("total", "—")

    cols = st.columns(3)
    approval_checks: dict[str, bool] = {}

    for col, bd in zip(cols, BUNDLE_DEFS):
        stage_evt  = results.get(bd["stage"]) or {}
        stage_data = stage_evt.get("data", {})
        status     = stage_evt.get("status", "error")
        subj       = stage_data.get("email_subject", "—")
        body       = stage_data.get("email_body", "")
        html       = stage_data.get("sell_sheet_html", "")
        ok         = status == "done"

        with col:
            col.markdown(
                f'<div style="background:{bd["bg"]};border-radius:12px;padding:16px;'
                f'margin-bottom:8px;border:1px solid {bd["color"]}22;">'
                f'<div style="font-size:13px;font-weight:700;color:{bd["color"]};margin-bottom:4px;">{bd["label"]}</div>'
                f'<div style="font-size:11px;color:#6B6B6B;margin-bottom:8px;">{brand_name} · {score}/100</div>'
                f'<div style="font-size:11px;color:#4A4A4A;font-style:italic;margin-bottom:8px;">{subj[:60]}{"…" if len(subj)>60 else ""}</div>'
                f'<div style="font-size:11px;color:{"#065F46" if ok else "#991B1B"};font-weight:600;">'
                f'{"✅ Ready" if ok else "⚠ Error — check logs"}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            checked = col.checkbox(
                f"Include {bd['label']} bundle",
                value=ok,
                disabled=not ok,
                key=f"approve_{bd['stage']}",
            )
            approval_checks[bd["stage"]] = checked and ok

            if ok and body:
                with col.expander("Preview pitch ▸", expanded=False):
                    if subj:
                        st.markdown(f"**Subject:** {subj}")
                    st.text_area("Email body", value=body, height=200, key=f"preview_body_{bd['stage']}", label_visibility="collapsed")
                    if html:
                        st.components.v1.html(html, height=400, scrolling=True)

            if bd["has_form"] and ok:
                filled = admin_data.get("filled_fields", {})
                gaps   = admin_data.get("gaps", [])
                with col.expander("Preview WFM form ▸", expanded=False):
                    if filled:
                        st.markdown("**Auto-filled fields:**")
                        for fid, val in list(filled.items())[:8]:
                            st.markdown(f"- **{fid}**: {val}")
                    if gaps:
                        st.markdown(f"**{len(gaps)} gap(s) to fill manually:**")
                        for g in gaps[:3]:
                            st.markdown(f"- _{g['label']}_: {g['suggested_action']}")
            elif not bd["has_form"]:
                col.markdown(
                    '<div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;'
                    'padding:8px 12px;font-size:11px;color:#92400E;margin-top:8px;">'
                    '⚙ New item form → <em>coming soon</em></div>',
                    unsafe_allow_html=True,
                )

    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
    any_checked = any(approval_checks.values())

    send_col, reset_col = st.columns([3, 1])
    with send_col:
        send_clicked = st.button(
            "📤 Send all approved bundles",
            key="dash_send_bundles",
            disabled=not any_checked,
            use_container_width=True,
            type="primary",
        )
    with reset_col:
        if st.button("↺ Start over", key="dash_reset_pipeline", use_container_width=True):
            for k in ["pipe_results", "pipe_complete", "pipe_brand", "pipe_sent"]:
                st.session_state.pop(k, None)
            st.rerun()

    if send_clicked:
        from memory import store_sent_bundle
        for bd in BUNDLE_DEFS:
            if not approval_checks.get(bd["stage"]):
                continue
            stage_data = (results.get(bd["stage"]) or {}).get("data", {})
            # WF bundle also includes form data
            form_path = admin_data.get("output_xlsx_path", "") if bd["has_form"] else ""
            store_sent_bundle(
                brand_name=brand_name,
                bundle_type="pitch+form" if bd["has_form"] else "pitch",
                retailer=bd["label"],
                email_subject=stage_data.get("email_subject", ""),
                email_body=stage_data.get("email_body", ""),
                sell_sheet_html=stage_data.get("sell_sheet_html", ""),
                form_xlsx_path=form_path,
                status="sent",
            )
        st.session_state["pipe_sent"] = True
        st.rerun()


def render_dashboard() -> None:
    import json as _json
    import time as _time

    stats = _fetch_stats()

    # ── Editorial hero ────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="margin-bottom:48px;">'
        f'<h1 class="sedge-h1">Sedge</h1>'
        f'<p class="sedge-subtitle">The operating system for independent food brokers.</p>'
        f'<p class="sedge-caption" style="margin-top:-32px;">'
        f'<span class="sedge-number">{stats["brands_evaluated"]}</span> brands · '
        f'<span class="sedge-number">{stats["pitches_drafted"]}</span> pitches · '
        f'<span class="sedge-number">{stats["forms_filled"]}</span> forms · '
        f'<span class="sedge-number">{stats["bundles_sent"]}</span> bundles sent'
        f'</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Pipeline session state ────────────────────────────────────────────────
    if "pipe_results"  not in st.session_state:
        st.session_state["pipe_results"]  = {}
    if "pipe_complete" not in st.session_state:
        st.session_state["pipe_complete"] = False
    if "pipe_sent"     not in st.session_state:
        st.session_state["pipe_sent"]     = False
    if "pipe_brand"    not in st.session_state:
        st.session_state["pipe_brand"]    = ""

    # ── Pipeline input ────────────────────────────────────────────────────────
    st.markdown(
        '<p class="sedge-section-title">Full pipeline — Brand Scout · 3 Pitches · WFM Form</p>',
        unsafe_allow_html=True,
    )
    _c1, _c2, _c3 = st.columns([3, 3, 1])
    with _c1:
        pipe_brand = st.text_input(
            "Brand name",
            placeholder="Try: Chomps, Fishwife, Graza",
            key="pipe_brand_input",
            label_visibility="collapsed",
        )
    with _c2:
        pipe_url = st.text_input(
            "Website URL (optional)",
            placeholder="https://chomps.com",
            key="pipe_url_input",
            label_visibility="collapsed",
        )
    with _c3:
        pipe_go = st.button("Run", key="pipe_go", use_container_width=True, type="primary")
    st.markdown(
        '<p class="sedge-caption" style="margin-top:8px;">Takes about 90 seconds — or under 15s in demo mode.</p>',
        unsafe_allow_html=True,
    )

    # ── Progress rows ─────────────────────────────────────────────────────────
    pipeline_card = st.empty()
    stage_slots   = {s: st.empty() for s in _STAGE_ORDER}

    def _refresh_rows(results: dict) -> None:
        for s in _STAGE_ORDER:
            with stage_slots[s].container():
                st.markdown(
                    _stage_row_html(s, results.get(s)),
                    unsafe_allow_html=True,
                )

    _refresh_rows(st.session_state["pipe_results"])

    # ── Run pipeline (button click) ───────────────────────────────────────────
    if pipe_go:
        brand = pipe_brand.strip()
        if not brand:
            st.warning("Enter a brand name first.")
        else:
            st.session_state["pipe_results"]  = {}
            st.session_state["pipe_complete"] = False
            st.session_state["pipe_sent"]     = False
            st.session_state["pipe_brand"]    = brand

            _refresh_rows({})

            demo_mode = st.session_state.get("demo_mode", False)
            demo_file = _PIPELINE_DEMO_DIR / f"{brand.lower()}_pipeline.json"

            if demo_mode and brand.lower() in _PIPELINE_DEMO_BRANDS and demo_file.exists():
                # ── Demo mode: serve from cache with fake delays ──────────────
                cached = _json.loads(demo_file.read_text())
                delay_per_stage = [2.5, 2.0, 1.5, 1.5, 2.0]
                for stage, delay in zip(_STAGE_ORDER, delay_per_stage):
                    # Show running
                    running_evt = {"status": "running", "message": f"{_STAGE_LABELS[stage]}…"}
                    st.session_state["pipe_results"][stage] = running_evt
                    with stage_slots[stage].container():
                        st.markdown(_stage_row_html(stage, running_evt), unsafe_allow_html=True)
                    _time.sleep(delay)
                    # Show done
                    stage_data = cached.get("stages", {}).get(stage, {})
                    done_evt   = {"status": stage_data.get("status", "done"),
                                  "message": stage_data.get("message", "done"),
                                  "data": stage_data.get("data", {})}
                    st.session_state["pipe_results"][stage] = done_evt
                    with stage_slots[stage].container():
                        st.markdown(_stage_row_html(stage, done_evt), unsafe_allow_html=True)
            else:
                # ── Live mode: iterate generator ─────────────────────────────
                from agents.orchestrator.pipeline import run_full_pipeline
                for event in run_full_pipeline(brand, pipe_url or ""):
                    evt_dict = {
                        "status":  event.status,
                        "message": event.message,
                        "data":    event.data,
                        "error":   event.error,
                    }
                    if event.stage == "complete":
                        # Store complete event data for verdict-gated UI
                        st.session_state["pipe_results"]["_complete"] = evt_dict
                        break
                    st.session_state["pipe_results"][event.stage] = evt_dict
                    if event.stage in stage_slots:
                        with stage_slots[event.stage].container():
                            st.markdown(_stage_row_html(event.stage, evt_dict), unsafe_allow_html=True)

            st.session_state["pipe_complete"] = True
            st.rerun()

    # ── Sent confirmation ─────────────────────────────────────────────────────
    if st.session_state.get("pipe_sent"):
        brand_label = st.session_state.get("pipe_brand", "brand")
        st.success(f"✅ Bundles for **{brand_label}** saved to your activity feed!")
        if st.button("↺ Run another", key="dash_run_another", use_container_width=False):
            for k in ["pipe_results", "pipe_complete", "pipe_brand", "pipe_sent"]:
                st.session_state.pop(k, None)
            st.rerun()
        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

    # ── Post-pipeline: watchlist or approval screen ───────────────────────────
    elif st.session_state.get("pipe_complete") and not st.session_state.get("pipe_sent"):
        _complete = st.session_state["pipe_results"].get("_complete", {})
        _routing  = (_complete.get("data") or {}).get("routing", {})
        if not _routing.get("run_pitcher", True):
            # Verdict-gated halt — show watchlist card
            _scout_d  = (_complete.get("data") or {}).get("scout", {})
            _handoff  = (_complete.get("data") or {}).get("scout_handoff", {})
            _score    = (_handoff.get("score_total") or
                         (_scout_d.get("score") or {}).get("total", 0))
            _gaps     = _handoff.get("key_gaps") or []
            _reason   = _routing.get("reason", "Brand scored too early for outreach.")
            gaps_html = "".join(f'<div class="gap-item">{g}</div>' for g in _gaps[:3])
            st.markdown(
                f'<div class="sedge-card" style="padding:28px;margin-top:24px;">'
                f'<p class="sedge-section-title" style="margin-bottom:8px;">Added to watchlist</p>'
                f'<h1 class="sedge-h1" style="margin-bottom:8px;">'
                f'{st.session_state.get("pipe_brand","Brand")} — '
                f'<span class="sedge-number">{_score}</span>/100</h1>'
                f'<p class="sedge-caption" style="margin-bottom:16px;">{_reason}</p>'
                f'{gaps_html}'
                f'<p class="sedge-caption" style="margin-top:16px;">'
                f'Check back in 3–6 months as distribution and velocity grow.</p>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("Run another brand", key="dash_watchlist_reset", use_container_width=False):
                for k in ["pipe_results", "pipe_complete", "pipe_brand", "pipe_sent"]:
                    st.session_state.pop(k, None)
                st.rerun()
        else:
            _render_approval_screen(st.session_state["pipe_results"])

    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:64px;'></div>", unsafe_allow_html=True)
    st.markdown('<p class="sedge-section-title">Workspace</p>', unsafe_allow_html=True)

    # ── Agent cards — hairline bordered, no shadow ────────────────────────────
    AGENTS = [
        {
            "title": "Brand Scout",
            "desc": "Research any CPG brand across 10+ sources in under 60 seconds. Scored brief and outreach draft.",
            "stat": f"{stats['brands_evaluated']} brands evaluated",
            "nav": "Brand Scout",
            "btn": "Open",
        },
        {
            "title": "Retailer Pitcher",
            "desc": "Draft a buyer-specific outreach email and 1-page sell sheet for any brand in your book.",
            "stat": f"{stats['pitches_drafted']} pitches drafted",
            "nav": "Retailer Pitcher",
            "btn": "Open",
        },
        {
            "title": "Admin & Ops",
            "desc": "Auto-fill the Whole Foods New Item Setup Form from Brand Scout data. Flag gaps before your buyer meeting.",
            "stat": f"{stats['forms_filled']} forms filled",
            "nav": "Admin & Ops",
            "btn": "Open",
        },
        {
            "title": "Portfolio Manager",
            "desc": "Track your full brand book, set reminder cadences, and surface re-evaluation alerts.",
            "stat": "Coming soon",
            "nav": "Portfolio Mgr",
            "btn": "Coming soon",
            "disabled": True,
        },
    ]

    cols = st.columns(4)
    for col, agent in zip(cols, AGENTS):
        with col:
            col.markdown(
                f'<div class="sedge-card sedge-card-hover" style="padding:20px;min-height:180px;">'
                f'<div style="font-size:13px;font-weight:600;color:#1A1A18;margin-bottom:8px;">{agent["title"]}</div>'
                f'<p class="sedge-caption" style="margin-bottom:16px;">{agent["desc"]}</p>'
                f'<p class="sedge-caption sedge-number" style="margin:0;">{agent["stat"]}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if not agent.get("disabled"):
                if col.button(agent["btn"], key=f"dash_btn_{agent['title']}", use_container_width=True):
                    st.session_state["_nav_idx"] = NAV_OPTIONS.index(agent["nav"])
                    st.rerun()
            else:
                col.markdown(
                    '<div style="background:#F2F2EE;border-radius:6px;padding:10px;text-align:center;'
                    'font-size:13px;font-weight:500;color:#8B8A83;">Coming soon</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("<div style='margin-top:48px;'></div>", unsafe_allow_html=True)

    # ── Recent activity — hairline list, no card wrapper ─────────────────────
    st.markdown(
        '<p class="sedge-section-title">Recent Activity</p>',
        unsafe_allow_html=True,
    )
    activity = stats["recent_activity"]
    if activity:
        rows_html = "".join(
            f'<div class="sedge-activity-row">'
            f'<span style="font-size:14px;color:#8B8A83;width:20px;flex-shrink:0;">{a["icon"]}</span>'
            f'<span style="font-size:13px;color:#57564F;flex:1;">{a["label"]}</span>'
            f'<span class="sedge-number" style="font-size:12px;color:#8B8A83;white-space:nowrap;">{a["ts"]}</span>'
            f'</div>'
            for a in activity
        )
        st.markdown(rows_html, unsafe_allow_html=True)
    else:
        st.markdown(
            '<p class="sedge-caption" style="padding:16px 0;">No activity yet — run the full pipeline above to get started.</p>',
            unsafe_allow_html=True,
        )


# ── Coming soon ───────────────────────────────────────────────────────────────

def render_coming_soon(title: str) -> None:
    st.markdown(
        f'<div style="margin-bottom:48px;">'
        f'<h1 class="sedge-h1">{title}</h1>'
        f'</div>'
        f'<div class="sedge-card" style="text-align:center;padding:64px 40px;">'
        f'<p style="font-size:32px;margin-bottom:16px;">—</p>'
        f'<p class="sedge-body" style="max-width:360px;margin:0 auto;">'
        f'This agent is coming soon. Check back after Phase 1 ships.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Router ────────────────────────────────────────────────────────────────────

def _error_card(exc: Exception) -> None:
    import traceback, sys
    tb = traceback.format_exc()
    print(tb, file=sys.stderr)
    st.error(f"Something went wrong: **{type(exc).__name__}: {exc}**")
    with st.expander("Debug details", expanded=True):
        st.code(tb, language="python")


page = NAV_OPTIONS[st.session_state["_nav_idx"]]

try:
    if page == "Dashboard":
        render_dashboard()

    elif page == "Brand Scout":
        from ui.brand_scout_page import render_brand_scout_page
        render_brand_scout_page()

    elif page == "Retailer Pitcher":
        from ui.retailer_pitcher_page import render_retailer_pitcher_page
        render_retailer_pitcher_page()

    elif page == "Admin & Ops":
        from ui.admin_ops_page import render_admin_ops_page
        render_admin_ops_page()

    elif page == "Portfolio Mgr":
        render_coming_soon("Portfolio Manager")

except Exception as _page_exc:
    _error_card(_page_exc)
