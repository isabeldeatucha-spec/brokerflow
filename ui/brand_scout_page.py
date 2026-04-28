"""
Brand Scout page — extracted from ui/app.py for use in brokerflow_app.
Export: render_brand_scout_page()

Standalone dev (unchanged behaviour):
    streamlit run ui/app.py
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

_DEMO_CACHE_DIR = Path(__file__).parent / "demo_cache" / "brand_scout"
_DEMO_BRANDS = {"chomps", "fishwife", "graza"}

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import streamlit as st
from langgraph.types import Command

from agents.brand_scout.graph import graph
from memory import get_config, retrieve_all_evaluations
from ui.global_css import inject_global_css


# ── (CSS block removed — inject_global_css() is called inside render_brand_scout_page) ──

# CSS removed — inject_global_css() is the single source of truth


# ── Module-level helpers ──────────────────────────────────────────────────────

def reset() -> None:
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.phase = "idle"
    st.session_state.interrupt_data = None
    st.session_state.final_state = None
    st.session_state.selected_criterion = None
    st.session_state.extracted_fields = {}
    st.session_state.incomplete_record = False
    st.session_state.loaded_from_cache = False


def run_graph_to_completion(brand_name: str, website_url: str):
    config = get_config(st.session_state.thread_id)
    initial_state = {
        "brand_name": brand_name,
        "website_url": website_url,
        "cache_hit": False,
        "force_refresh": st.session_state.get("force_refresh", False),
        "sources_checked": [],
        "signals_found": {},
        "follow_up_queries": [],
        "reflection_count": 0,
        "reflection_notes": [],
        "category": "",
        "benchmark": {},
        "extracted_fields": {},
        "score": {},
        "verdict": "",
        "founder_name": "",
        "founder_email": "",
        "email_draft": "",
        "approved": None,
        "rejection_reason": None,
    }

    _NODE_LABELS = {
        "check_cache":          "Checking memory",
        "discover_brands":      "Discovering brands",
        "research_brand":       "Researching signals",
        "reflect_and_decide":   "Checking for gaps",
        "detect_category_node": "Detecting category",
        "extract_fields":       "Extracting structured fields",
        "score_brand":          "Scoring brand",
        "store_memory":         "Saving to memory",
        "draft_outreach":       "Drafting outreach",
    }

    progress_slot = st.empty()
    completed_labels: list[str] = []

    for chunk in graph.stream(initial_state, config=config, stream_mode="updates"):
        for node in chunk:
            label = _NODE_LABELS.get(node, node)
            completed_labels.append(label)
            cards_html = "".join(
                f'<div style="display:flex;align-items:center;gap:12px;padding:10px 0;'
                f'border-bottom:1px solid #F2F2EE;">'
                f'<span style="color:#2D5F3F;font-size:13px;">&#10003;</span>'
                f'<span style="font-size:13px;color:#57564F;">{lbl}</span>'
                f'</div>'
                for lbl in completed_labels
            )
            progress_slot.markdown(cards_html, unsafe_allow_html=True)

    progress_slot.empty()
    state_snapshot = graph.get_state(config)
    final = state_snapshot.values

    interrupt_data = None
    if state_snapshot.next:
        for task in (state_snapshot.tasks or []):
            if hasattr(task, "interrupts") and task.interrupts:
                interrupt_data = task.interrupts[0].value
                break

    return interrupt_data, final


def resume_graph(approved: bool, rejection_reason: str = ""):
    config = get_config(st.session_state.thread_id)
    return graph.invoke(
        Command(resume={"approved": approved, "rejection_reason": rejection_reason}),
        config=config,
    )


def _criterion_breakdown_rows(criterion: str, fields: dict) -> list:
    rows = []

    if criterion == "velocity_proof":
        reviews = fields.get("amazon_review_count")
        if reviews is None: pts = 5
        elif reviews >= 1000: pts = 10
        elif reviews >= 500: pts = 8
        elif reviews >= 200: pts = 6
        elif reviews >= 50: pts = 3
        else: pts = 1
        val = f"{reviews:,}" if reviews is not None else "not found"
        rows.append(("Amazon reviews", val, pts))

        rating = fields.get("amazon_rating")
        if rating is None: pts = 2
        elif rating >= 4.5: pts = 5
        elif rating >= 4.2: pts = 4
        elif rating >= 4.0: pts = 3
        elif rating >= 3.5: pts = 1
        else: pts = 0
        rows.append(("Amazon rating", str(rating) if rating is not None else "not found", pts))

        ss = fields.get("amazon_subscribe_save")
        if ss is None: pts = 2
        elif ss: pts = 4
        else: pts = 0
        rows.append(("Subscribe & Save", "Yes" if ss else ("No" if ss is not None else "not found"), pts))

        banners = fields.get("instacart_banner_count")
        if banners is None: pts = 1
        elif banners >= 3: pts = 3
        elif banners >= 1: pts = 2
        else: pts = 0
        rows.append(("Instacart banners", str(banners) if banners is not None else "not found", pts))

        spins = fields.get("spins_mentioned")
        sell = fields.get("sell_through_press")
        if spins: pts = 3
        elif sell: pts = 2
        else: pts = 1
        press_val = "SPINS mentioned" if spins else ("Sell-through press" if sell else "None found")
        rows.append(("SPINS / press", press_val, pts))

    elif criterion == "distribution_density":
        doors = fields.get("estimated_door_count")
        if doors is None: pts = 4
        elif 50 <= doors <= 300: pts = 8
        elif 20 <= doors < 50: pts = 5
        elif 300 < doors <= 800: pts = 6
        elif doors > 800: pts = 2
        else: pts = 1
        rows.append(("Est. door count", f"{doors:,}" if doors is not None else "not found", pts))

        retailer_pts = 0
        retailer_parts = []
        if fields.get("whole_foods_confirmed"): retailer_pts += 3; retailer_parts.append("Whole Foods")
        if fields.get("sprouts_confirmed"): retailer_pts += 2; retailer_parts.append("Sprouts")
        if fields.get("target_confirmed"): retailer_pts += 2; retailer_parts.append("Target")
        if fields.get("costco_confirmed"): retailer_pts += 2; retailer_parts.append("Costco")
        if fields.get("walmart_confirmed"): retailer_pts += 1; retailer_parts.append("Walmart")
        retailer_pts = min(retailer_pts, 8)
        nationals = sum(bool(fields.get(k)) for k in ["whole_foods_confirmed", "target_confirmed", "walmart_confirmed", "costco_confirmed"])
        if nationals >= 4: retailer_pts = max(retailer_pts - 4, 2)
        rows.append(("Retail chains", ", ".join(retailer_parts) if retailer_parts else "None confirmed", retailer_pts))

        faire_listed = fields.get("faire_listed")
        if faire_listed is None: pts = 2
        elif faire_listed: pts = 4
        else: pts = 0
        rows.append(("Faire listed", "Yes" if faire_listed else ("No" if faire_listed is not None else "not found"), pts))

    elif criterion == "margin_viability":
        srp = fields.get("srp_hero") or fields.get("srp_min")
        category = fields.get("category", "unknown")
        _benchmarks = {
            "beverage_rtd": (3.50, 6.00), "snack_bar": (2.50, 5.00),
            "condiment_sauce": (7.00, 16.00), "frozen_food": (6.00, 14.00),
            "supplement_functional": (20.00, 65.00), "olive_oil_cooking_oil": (12.00, 35.00),
            "dairy_alternative": (5.00, 12.00), "meat_snack_protein": (2.00, 5.00),
            "unknown": (6.00, 20.00),
        }
        low, _ = _benchmarks.get(category, (6.00, 20.00))
        if srp is None: pts = 5
        elif srp >= low * 1.2: pts = 10
        elif srp >= low: pts = 7
        elif srp >= low * 0.8: pts = 4
        else: pts = 1
        rows.append(("SRP", f"${srp:.2f}" if srp is not None else "not found", pts))

        funding = fields.get("funding_amount_usd")
        if funding is None: pts = 3
        elif funding >= 5_000_000: pts = 6
        elif funding >= 1_000_000: pts = 4
        elif funding > 0: pts = 2
        else: pts = 1
        rows.append(("Funding raised", f"${funding:,}" if funding is not None else "not found", pts))

        faire_listed = fields.get("faire_listed")
        if faire_listed is None: pts = 2
        elif faire_listed: pts = 3
        else: pts = 1
        rows.append(("Faire listed", "Yes" if faire_listed else ("No" if faire_listed is not None else "not found"), pts))

    elif criterion == "brand_story_clarity":
        hero = fields.get("hero_product_clear")
        if hero is None: pts = 2
        elif hero: pts = 4
        else: pts = 0
        rows.append(("Hero product clear", "Yes" if hero else ("No" if hero is not None else "not found"), pts))

        founder = fields.get("founder_story_clear")
        if founder is None: pts = 1
        elif founder: pts = 3
        else: pts = 0
        rows.append(("Founder story clear", "Yes" if founder else ("No" if founder is not None else "not found"), pts))

        ig = fields.get("instagram_followers") or 0
        tt = fields.get("tiktok_followers") or 0
        social_max = max(ig, tt)
        if fields.get("instagram_followers") is None and fields.get("tiktok_followers") is None: pts = 2
        elif social_max >= 100_000: pts = 5
        elif social_max >= 50_000: pts = 4
        elif social_max >= 10_000: pts = 3
        elif social_max >= 1_000: pts = 2
        else: pts = 1
        rows.append(("Social following", f"{social_max:,}" if social_max > 0 else "not found", pts))

        trade = fields.get("press_trade_mentions") or 0
        if fields.get("press_trade_mentions") is None: pts = 2
        elif trade >= 3: pts = 4
        elif trade >= 1: pts = 3
        else: pts = 1
        rows.append(("Trade press mentions", str(trade) if fields.get("press_trade_mentions") is not None else "not found", pts))

        certs = fields.get("certifications") or []
        if fields.get("certifications") is None: pts = 1
        elif len(certs) >= 2: pts = 2
        elif len(certs) >= 1: pts = 1
        else: pts = 0
        cert_val = ", ".join(certs) if certs else ("None found" if fields.get("certifications") is not None else "not found")
        rows.append(("Certifications", cert_val, pts))

        expo = fields.get("expo_west_confirmed")
        if expo is None: pts = 1
        elif expo: pts = 2
        else: pts = 0
        rows.append(("ExpoWest", "Confirmed" if expo else ("No" if expo is not None else "not found"), pts))

    elif criterion == "promotional_independence":
        ig = fields.get("instagram_followers") or 0
        tt = fields.get("tiktok_followers") or 0
        social_max = max(ig, tt)

        dtc = fields.get("dtc_channel")
        sub = fields.get("subscription_available")
        if dtc is None: pts = 2
        elif dtc:
            pts = 4 if sub else 3
        else: pts = 0
        dtc_val = ("Yes + subscription" if (dtc and sub) else "Yes" if dtc else ("No" if dtc is not None else "not found"))
        rows.append(("DTC channel", dtc_val, pts))

        if fields.get("instagram_followers") is None and fields.get("tiktok_followers") is None: pts = 2
        elif social_max >= 100_000: pts = 4
        elif social_max >= 50_000: pts = 3
        elif social_max >= 10_000: pts = 2
        elif social_max >= 1_000: pts = 1
        else: pts = 0
        rows.append(("Social following", f"{social_max:,}" if social_max > 0 else "not found", pts))

        tprs = fields.get("promo_frequency_tpr_per_year")
        bogo = fields.get("bogo_detected", False)
        if tprs is None: pts = 2
        elif tprs <= 2: pts = 4
        elif tprs <= 4: pts = 3
        elif tprs <= 6: pts = 1
        else: pts = 0
        if bogo: pts = max(pts - 2, 0)
        tpr_val = (f"{tprs}/yr" if tprs is not None else "not found") + (" (BOGO detected −2pts)" if bogo else "")
        rows.append(("TPR frequency", tpr_val, pts))

        ss = fields.get("amazon_subscribe_save")
        if ss is None: pts = 1
        elif ss: pts = 3
        else: pts = 0
        rows.append(("Subscribe & Save", "Yes" if ss else ("No" if ss is not None else "not found"), pts))

    return rows


def render_results(state: dict, show_outreach: bool = True):
    brand_name   = state.get("brand_name", "Unknown")
    display_name = brand_name.strip().title()
    category     = state.get("category", "unknown").replace("_", " ").title()
    score_obj    = state.get("score", {})
    total        = score_obj.get("total", 0)
    detail       = state.get("signals_found", {}).get("score_detail", {})
    broker_brief     = detail.get("broker_brief", "No brief available.")
    key_gaps         = detail.get("key_gaps", [])
    reflection_notes = state.get("reflection_notes", [])

    brand_url  = state.get("website_url", "")
    domain     = (brand_url.replace("https://", "").replace("http://", "")
                  .replace("www.", "").split("/")[0]) if brand_url else ""
    logo_url   = f"https://logo.clearbit.com/{domain}" if domain else ""

    def pts(key: str) -> int:
        entry = detail.get(key, {})
        return entry.get("score", score_obj.get(key, 0)) if isinstance(entry, dict) else score_obj.get(key, 0)

    velocity     = pts("velocity_proof")
    distribution = pts("distribution_density")
    margin       = pts("margin_viability")
    story        = pts("brand_story_clarity")
    promo        = pts("promotional_independence")

    # ── Brand hero — editorial serif layout ──────────────────────────────────
    badge_class = "badge-established" if total >= 70 else "badge-ready" if total >= 45 else "badge-early"
    badge_label = "Established" if total >= 70 else "Broker Ready" if total >= 45 else "Too Early"
    dot_color   = "#8B6914" if total >= 70 else "#1A3F2A" if total >= 45 else "#6B1F1F"

    st.markdown(
        f'<p class="sedge-caption" style="margin-bottom:4px;">'
        f'{category} · evaluated today</p>'
        f'<h1 class="sedge-brand-h1">{display_name}</h1>'
        f'<div style="display:flex;align-items:center;gap:16px;margin-bottom:32px;">'
        f'<span class="{badge_class}">'
        f'<span style="width:6px;height:6px;border-radius:99px;background:{dot_color};display:inline-block;margin-right:6px;vertical-align:middle;"></span>'
        f'{badge_label}</span>'
        f'<span class="sedge-score-display sedge-number">{total}</span>'
        f'<span class="sedge-caption">/100</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Score breakdown — hairline rows ───────────────────────────────────────
    st.markdown('<p class="sedge-section-title">Score Breakdown</p>', unsafe_allow_html=True)

    criteria_data = [
        ("Velocity Proof",     velocity,     25, "velocity_proof"),
        ("Distribution",       distribution, 20, "distribution_density"),
        ("Margin Viability",   margin,       20, "margin_viability"),
        ("Brand Story",        story,        20, "brand_story_clarity"),
        ("Promo Independence", promo,        15, "promotional_independence"),
    ]

    for cname, cscore, cmax, ckey in criteria_data:
        pct   = cscore / cmax if cmax else 0
        bar_color = "#2D5F3F" if pct >= 0.7 else "#8B6914" if pct >= 0.4 else "#8B2F2F"
        is_sel = st.session_state.get("selected_criterion") == ckey
        row_bg = "#F2F2EE" if is_sel else "transparent"
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:16px;padding:10px 8px;'
            f'border-bottom:1px solid #F2F2EE;border-radius:4px;background:{row_bg};cursor:pointer;">'
            f'<span style="font-size:13px;color:#57564F;width:160px;flex-shrink:0;">{cname}</span>'
            f'<div style="flex:1;">'
            f'<div class="sedge-progress-track">'
            f'<div class="sedge-progress-fill" style="width:{int(pct*100)}%;background:{bar_color};"></div>'
            f'</div></div>'
            f'<span class="sedge-number" style="font-size:13px;color:#1A1A18;min-width:48px;text-align:right;">'
            f'{cscore}/{cmax}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        # Invisible button overlay for click handling
        _bc, _rest = st.columns([4, 1])
        with _bc:
            if st.button(
                f"{'▲ Close' if is_sel else '▾ Details'} — {cname}",
                key=f"card_{ckey}",
                use_container_width=True,
            ):
                if is_sel:
                    st.session_state.selected_criterion = None
                else:
                    st.session_state.selected_criterion = ckey

    with st.expander("How scoring works"):
        st.markdown("""
        <div style="padding:8px 0;">
            <p class="sedge-body" style="margin-bottom:16px;">
                Brand Scout scores brands on five criteria drawn from 150+ interviews with independent
                food brokers, CPG founders, distributors, and retail buyers. Total is out of 100.
            </p>
            <div style="display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap;">
                <span class="badge-established">Established = 70+</span>
                <span class="badge-ready">Broker Ready = 45–69</span>
                <span class="badge-early">Too Early = below 45</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    selected = st.session_state.get("selected_criterion")
    if selected:
        name_map = {
            "velocity_proof":           "Velocity Proof",
            "distribution_density":     "Distribution Density",
            "margin_viability":         "Margin Viability",
            "brand_story_clarity":      "Brand Story Clarity",
            "promotional_independence": "Promotional Independence",
        }
        extracted = state.get("extracted_fields") or st.session_state.get("extracted_fields") or {}
        rows = _criterion_breakdown_rows(selected, extracted) if extracted else []

        if rows:
            rows_html = "".join(
                f'<div style="display:flex; justify-content:space-between; align-items:center; '
                f'padding:8px 0; border-bottom:1px solid #F3F4F6;">'
                f'<span style="font-size:13px; color:#4A4A4A;">{label}</span>'
                f'<span style="font-size:13px; color:#6B6B6B; flex:1; text-align:center; padding:0 12px;">{val}</span>'
                f'<span style="font-size:13px; font-weight:600; color:#1B4F72; min-width:48px; text-align:right;">{pts} pts</span>'
                f'</div>'
                for label, val, pts in rows
            )
        else:
            crit_detail = detail.get(selected, {})
            reasoning = crit_detail.get("reasoning", "No detail available.") if isinstance(crit_detail, dict) else "No detail available."
            sentences = [s.strip() for s in reasoning.replace(". ", ".|").split("|") if s.strip() and len(s.strip()) > 10]
            rows_html = "".join(
                f'<p style="font-size:13px; color:#4A4A4A; margin:4px 0; padding-left:12px; border-left:2px solid #E5E5E5;">• {s}</p>'
                for s in sentences[:4]
            )

        st.markdown(f"""
        <div style="background:#FFFFFF; border:1px solid #E5E5E5; border-radius:12px; padding:20px; margin:8px 0 16px 0; box-shadow:0 2px 8px rgba(0,0,0,0.06);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <p style="font-weight:600; font-size:14px; color:#111111; margin:0;">{name_map.get(selected, selected)}</p>
                <p style="font-size:12px; color:#9CA3AF; margin:0;">Click card again to close</p>
            </div>
            {rows_html}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)

    left, right = st.columns([1.5, 1])

    with left:
        # Broker brief — italic serif editorial lead
        st.markdown(
            f'<p class="sedge-section-title">Broker Brief</p>'
            f'<p class="sedge-broker-brief">{broker_brief}</p>',
            unsafe_allow_html=True,
        )

        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
        st.markdown('<p class="sedge-section-title">Key Gaps</p>', unsafe_allow_html=True)
        if key_gaps:
            gaps_html = "".join(f'<div class="gap-item">{g}</div>' for g in key_gaps)
        else:
            gaps_html = "<p class='sedge-caption'>None identified.</p>"
        st.markdown(gaps_html, unsafe_allow_html=True)

        with st.expander("Agent Reasoning"):
            if reflection_notes:
                for i, note in enumerate(reflection_notes):
                    st.markdown(f"""
                    <div class="reflection-item">
                        <div class="reflection-label">Round {i+1}</div>
                        <p>{note}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown('<p style="color:#9CA3AF;">No reflection loops required.</p>', unsafe_allow_html=True)

    with right:
        if show_outreach and total >= 45:
            founder_name    = state.get("founder_name", "") or "Founder"
            founder_email   = state.get("founder_email", "")
            email_draft     = state.get("email_draft", "")
            outreach_angle  = state.get("signals_found", {}).get("score_detail", {}).get("outreach_angle", "")

            email_subject = f"Partnership Opportunity — {display_name}"
            email_body    = email_draft
            for line in email_draft.splitlines():
                if line.lower().startswith("subject:"):
                    email_subject = line.split(":", 1)[1].strip()
                    email_body = email_draft[email_draft.index(line) + len(line):].lstrip("\n")
                    break

            angle_html = f'<p class="sedge-caption" style="font-style:italic;margin-bottom:12px;">{outreach_angle}</p>' if outreach_angle else ""
            st.markdown(
                f'<p class="sedge-section-title">Draft Outreach</p>'
                f'<div style="border:1px solid #EAEAE4;border-radius:10px;padding:16px 20px;margin-bottom:8px;background:#FFFFFF;">'
                f'{angle_html}'
                f'<div style="display:flex;gap:12px;padding:8px 0;border-bottom:1px solid #F2F2EE;">'
                f'<span class="sedge-caption" style="width:48px;flex-shrink:0;">To</span>'
                f'<span style="font-size:13px;color:#1A1A18;">{founder_name}</span>'
                f'<span class="sedge-caption" style="margin-left:auto;">verify before sending</span>'
                f'</div>'
                f'<div style="display:flex;gap:12px;padding:8px 0;">'
                f'<span class="sedge-caption" style="width:48px;flex-shrink:0;">Subject</span>'
                f'<span class="sedge-number" style="font-size:13px;color:#1A1A18;">{email_subject}</span>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            edited_body = st.text_area(
                "",
                value=email_body,
                height=220,
                key="email_draft_area",
                label_visibility="collapsed",
            )

            copy_js = edited_body.replace("`", "\\`").replace("\n", "\\n")
            st.html(f"""
<script>
function copyDraft() {{
navigator.clipboard.writeText(`{copy_js}`).then(function() {{
document.getElementById('copy-btn').innerText = 'Copied';
document.getElementById('copy-btn').style.background = '#2D5F3F';
setTimeout(() => {{
document.getElementById('copy-btn').innerText = 'Copy to clipboard';
document.getElementById('copy-btn').style.background = '#1A1A18';
}}, 2500);
}});
}}
</script>
<div style="margin-top:8px;">
<button id="copy-btn" onclick="copyDraft()" style="width:100%; background:#1A1A18; color:#FAFAF7; border:none; border-radius:6px; padding:10px 16px; font-size:14px; font-weight:500; cursor:pointer; font-family:Inter,sans-serif; margin-bottom:8px;">Copy to clipboard</button>
</div>
""")

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            hcol1, hcol2 = st.columns(2)
            with hcol1:
                if st.button("Draft pitch to buyer", key="bs_handoff_pitcher", use_container_width=True):
                    st.session_state["handoff_brand"] = brand_name.strip().title()
                    st.session_state["forced_page"] = "Retailer Pitcher"
                    st.rerun()
            with hcol2:
                if st.button("Autofill WFM form", key="bs_handoff_ao", use_container_width=True):
                    st.session_state["handoff_brand"] = brand_name.strip().title()
                    st.session_state["forced_page"] = "Admin & Ops"
                    st.rerun()

            reject = st.button("Pass — not a fit", key="reject_btn", use_container_width=True)
            return {"approve": False, "reject": reject, "edited_draft": edited_body}

        else:
            comparable_brands = ""
            try:
                from memory import retrieve_similar_brands
                cat = state.get("category", "unknown")
                comparable_brands = retrieve_similar_brands(cat, (max(0, total - 15), total + 15)) or "None yet"
            except Exception:
                comparable_brands = "Unavailable"

            memory_previous = state.get("signals_found", {}).get("brand_history", "") or "None"
            st.markdown(f"""
            <div class="watchlist-card">
                <h3 style="color:#1B4F72;margin-top:0;">Added to Watch List</h3>
                <p style="color:#4A6A7A;">This brand scored {total}/100 — below the 45-point threshold.
                Check back in 3–6 months as they build distribution and velocity.</p>
                <hr style="border:none;border-top:1px solid #AED6F1;margin:14px 0;">
                <p style="font-size:11px;color:#7FB3D3;margin:0;">Previously evaluated: {memory_previous} · Comparable brands: {comparable_brands}</p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
            st.button("Set Reminder", key="reminder_btn")

    return {}


# ── Main exported render function ─────────────────────────────────────────────

def render_brand_scout_page() -> None:
    inject_global_css()

    st.info(
        "Tip: Use the Dashboard's full pipeline to run Brand Scout, "
        "Retailer Pitches, and the WFM form all in one click.",
        icon=None,
    )

    # Session state
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    if "phase" not in st.session_state:
        st.session_state.phase = "idle"
    if "interrupt_data" not in st.session_state:
        st.session_state.interrupt_data = None
    if "final_state" not in st.session_state:
        st.session_state.final_state = None
    if "selected_criterion" not in st.session_state:
        st.session_state.selected_criterion = None
    if "extracted_fields" not in st.session_state:
        st.session_state.extracted_fields = {}
    if "incomplete_record" not in st.session_state:
        st.session_state.incomplete_record = False
    if "loaded_from_cache" not in st.session_state:
        st.session_state.loaded_from_cache = False

    # ── Auto-run from Dashboard query bar ─────────────────────────────────────
    if st.session_state.pop("_auto_run", False):
        b = st.session_state.get("_brand_name", "")
        if b and st.session_state.phase == "idle":
            st.session_state.phase = "running"
            st.rerun()

    # ── Demo mode banner ──────────────────────────────────────────────────────
    if st.session_state.get("demo_mode"):
        st.markdown(
            '<div style="background:#FAFAF7;border:1px solid #EAEAE4;border-radius:6px;'
            'padding:6px 14px;margin-bottom:12px;font-size:12px;color:#57564F;font-weight:500;">'
            'Demo mode · using cached results for Chomps, Fishwife, and Graza</div>',
            unsafe_allow_html=True,
        )

    # ── Input form + Recent evaluations ──────────────────────────────────────────
    _fcol, _rcol = st.columns([3, 2])

    with _fcol:
        mode = st.radio(
            "Mode",
            ["Research a brand", "Discover new brands"],
            key="mode_radio",
            horizontal=True,
            label_visibility="collapsed",
        )
        if mode == "Research a brand":
            _hb = st.session_state.get("handoff_brand") or st.session_state.get("_brand_name", "")
            if _hb and "brand_input" not in st.session_state:
                st.session_state["brand_input"] = _hb
            brand_name_input = st.text_input(
                "Brand name",
                placeholder="Brand name (e.g. Chomps, Fishwife, Graza)",
                key="brand_input",
                label_visibility="collapsed",
            )
            brand_url_input = st.text_input(
                "Website URL",
                placeholder="Website URL — speeds up research (optional)",
                key="url_input",
                label_visibility="collapsed",
            )
        else:
            brand_name_input = ""
            brand_url_input = ""
            st.markdown(
                '<div style="background:#EBF5FB;border-radius:8px;padding:10px 12px;'
                'font-size:13px;color:#1B4F72;line-height:1.5;margin-bottom:8px;">'
                'Scans Whole Foods, Sprouts, Target and Walmart for brands just hitting shelves.</div>',
                unsafe_allow_html=True,
            )
        _btn_c, _new_c = st.columns([4, 1])
        with _btn_c:
            _run_clicked = st.button("Run", key="run_btn", use_container_width=True)
        with _new_c:
            _new_search = st.button(
                "↺", key="new_search_btn", use_container_width=True,
                disabled=(st.session_state.phase == "idle"),
            )
        if _run_clicked:
            if mode == "Research a brand" and not brand_name_input.strip():
                st.warning("Enter a brand name first.")
            else:
                st.session_state["_brand_name"] = brand_name_input.strip()
                st.session_state["_website_url"] = brand_url_input.strip()
                st.session_state["force_refresh"] = False
                st.session_state.phase = "running"
                st.rerun()
        if _new_search:
            reset()
            st.rerun()

    with _rcol:
        st.markdown(
            '<p style="font-size:11px;font-weight:700;color:#9CA3AF;text-transform:uppercase;'
            'letter-spacing:0.1em;margin:0 0 8px;">Recent Evaluations</p>',
            unsafe_allow_html=True,
        )
        try:
            recent = retrieve_all_evaluations()
            if recent:
                for item in recent[:6]:
                    score = item.get("score", 0)
                    name  = item.get("brand_name", "Unknown")
                    dot_col = "#8B6914" if score >= 70 else "#2D5F3F" if score >= 45 else "#8B2F2F"
                    dot_html = f'<span style="display:inline-block;width:7px;height:7px;border-radius:99px;background:{dot_col};margin-right:6px;vertical-align:middle;"></span>'
                    if st.button(f"{name}  {score}/100", key=f"recent_{name}", use_container_width=True):
                        detail = item.get("score_breakdown", {})
                        st.session_state.phase = "awaiting_approval" if score >= 45 else "too_early"
                        st.session_state.loaded_from_cache = True
                        st.session_state.incomplete_record = False
                        st.session_state.final_state = {
                            "brand_name":       name,
                            "cache_hit":        False,
                            "score":            {"total": score, **{
                                k: (detail.get(k, {}).get("score", 0) if isinstance(detail.get(k), dict) else 0)
                                for k in ("velocity_proof", "distribution_density", "margin_viability",
                                          "brand_story_clarity", "promotional_independence")
                            }},
                            "verdict":          item.get("verdict", ""),
                            "category":         item.get("category", ""),
                            "reflection_notes": item.get("reflection_notes") or [],
                            "email_draft":      item.get("email_draft", ""),
                            "founder_name":     item.get("founder_name", ""),
                            "founder_email":    item.get("founder_email", ""),
                            "signals_found":    {"score_detail": {
                                **detail,
                                "broker_brief":   item.get("broker_brief", ""),
                                "key_gaps":       item.get("key_gaps") or [],
                                "email_subject":  item.get("email_subject", ""),
                                "outreach_angle": item.get("outreach_angle", ""),
                            }},
                        }
                        st.session_state.interrupt_data   = st.session_state.final_state
                        st.session_state.extracted_fields = item.get("extracted_fields") or {}
                        st.rerun()
            else:
                st.markdown("<p style='font-size:13px;color:#9CA3AF;'>No evaluations yet.</p>", unsafe_allow_html=True)
        except Exception as _e:
            st.markdown(f"<p style='font-size:11px;color:#EF4444;'>Error: {_e}</p>", unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:1px solid #EBEBEB;margin:16px 0 8px;'>", unsafe_allow_html=True)

    # Page title
    st.markdown(
        '<div style="margin-bottom:32px;">'
        '<h1 class="sedge-h1">Brand Scout</h1>'
        '<p class="sedge-subtitle">AI-powered brand evaluation for CPG brokers.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Phase: idle ───────────────────────────────────────────────────────────
    if st.session_state.phase == "idle":
        st.markdown(
            '<p class="sedge-section-title" style="margin-bottom:16px;">Scoring tiers</p>',
            unsafe_allow_html=True,
        )
        tier_cols = st.columns(3)
        for col, (label, score_range, cta, desc, cls) in zip(tier_cols, [
            ("Broker Ready",  "45–69", "Worth a meeting",        "Enough traction to be credible, not yet locked into national distribution.", "badge-ready"),
            ("Established",   "70+",   "Check who reps them now","Proven brand, likely working with brokers. Pitch angle: why you're better.", "badge-established"),
            ("Too Early",     "< 45",  "Check back in 6 months", "Missing velocity proof, distribution, or brand story clarity.",              "badge-early"),
        ]):
            with col:
                col.markdown(
                    f'<div class="sedge-card" style="padding:20px;">'
                    f'<span class="{cls}">{label}</span>'
                    f'<p class="sedge-number" style="font-size:20px;color:#1A1A18;margin:12px 0 4px;font-weight:400;">{score_range}</p>'
                    f'<p class="sedge-caption" style="font-weight:500;color:#57564F;margin-bottom:8px;">{cta}</p>'
                    f'<p class="sedge-caption">{desc}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Phase: running ────────────────────────────────────────────────────────
    elif st.session_state.phase == "running":
        b_name = st.session_state.get("_brand_name", "")
        b_url  = st.session_state.get("_website_url", "")

        # Demo mode shortcut — load from cache file instantly
        if st.session_state.get("demo_mode") and b_name.lower().strip() in _DEMO_BRANDS:
            _cache_file = _DEMO_CACHE_DIR / f"{b_name.lower().strip()}.json"
            _slot = st.empty()
            _slot.markdown(
                f'<div class="sedge-card" style="text-align:center;padding:32px;">'
                f'<p class="sedge-caption" style="margin-bottom:8px;">Loading cached results for {b_name}</p>'
                f'<p class="sedge-caption">Demo mode · skipping live research</p>'
                f'</div>',
                unsafe_allow_html=True,
            )
            import time; time.sleep(0.8)
            _slot.empty()
            final = json.loads(_cache_file.read_text())
            st.session_state.final_state = final
            st.session_state.extracted_fields = final.get("extracted_fields", {})
            st.session_state.interrupt_data = final
            st.session_state.incomplete_record = False
            st.session_state.loaded_from_cache = True
            st.session_state.phase = "awaiting_approval"
            st.rerun()

        st.markdown(
            f'<div style="padding:32px 0;">'
            f'<h1 class="sedge-h1" style="margin-bottom:8px;">Researching {b_name or "brand"}</h1>'
            f'<p class="sedge-caption">This takes about 30–60 seconds.</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        interrupt_data, final = run_graph_to_completion(b_name, b_url)
        st.session_state.final_state = final
        st.session_state.extracted_fields = (final or {}).get("extracted_fields", {})
        st.session_state.incomplete_record = False
        st.session_state.loaded_from_cache = False

        if interrupt_data:
            st.session_state.interrupt_data = interrupt_data
            st.session_state.phase = "awaiting_approval"
        else:
            verdict = (final or {}).get("verdict", "below_threshold")
            st.session_state.phase = "too_early" if verdict == "below_threshold" else "done"

        st.rerun()

    # ── Phase: awaiting_approval ──────────────────────────────────────────────
    elif st.session_state.phase == "awaiting_approval":
        data  = st.session_state.interrupt_data or {}
        final = st.session_state.final_state or {}
        merged = {**final, **data}

        if merged.get("cache_hit"):
            _cb_col, _rf_col = st.columns([5, 1])
            with _cb_col:
                st.markdown(
                    '<div style="background:#FAFAF7;border:1px solid #EAEAE4;border-radius:6px;'
                    'padding:8px 14px;margin-bottom:12px;font-size:12px;color:#57564F;">'
                    'Loaded from memory — research on file (under 7 days old)</div>',
                    unsafe_allow_html=True,
                )
            with _rf_col:
                if st.button("Re-run", key="force_refresh_btn", use_container_width=True):
                    st.session_state["force_refresh"] = True
                    st.session_state.phase = "running"
                    st.rerun()

        actions = render_results(merged, show_outreach=True)

        if actions.get("reject"):
            st.session_state.phase = "rejected"
            st.rerun()

    # ── Phase: too_early ─────────────────────────────────────────────────────
    elif st.session_state.phase in ("too_early", "below_threshold"):
        final = st.session_state.final_state or {}
        render_results(final, show_outreach=False)

    # ── Phase: done ───────────────────────────────────────────────────────────
    elif st.session_state.phase == "done":
        data = st.session_state.interrupt_data or {}
        st.markdown(f"""
        <div class="sedge-card" style="text-align:center;padding:40px;">
            <p class="sedge-section-title" style="margin-bottom:12px;">Sent</p>
            <h1 class="sedge-h1" style="margin-bottom:8px;">Outreach sent</h1>
            <p class="sedge-caption">To <strong style="color:#1A1A18;">{data.get('founder_name','')}</strong>
            at {data.get('founder_email','')}</p>
        </div>
        """, unsafe_allow_html=True)

    # ── Phase: rejected ───────────────────────────────────────────────────────
    elif st.session_state.phase == "rejected":
        st.markdown("""
        <div class="sedge-card" style="text-align:center;padding:40px;">
            <p class="sedge-section-title" style="margin-bottom:12px;">Passed</p>
            <h1 class="sedge-h1" style="margin-bottom:8px;">Marked as not a fit</h1>
            <p class="sedge-caption">No email was sent.</p>
        </div>
        """, unsafe_allow_html=True)


# ── Standalone entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    st.set_page_config(
        page_title="Brand Scout · BrokerFlow",
        page_icon="🌾",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    render_brand_scout_page()
