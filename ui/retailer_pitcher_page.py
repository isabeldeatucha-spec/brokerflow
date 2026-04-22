"""
Retailer Pitcher — Streamlit page extracted from hw8/pitcher_demo.py.
Import and call render_retailer_pitcher_page() from sedge_app.py.
"""
from __future__ import annotations

import json
import os
import sys
import uuid

from pathlib import Path

_DEMO_CACHE_DIR = Path(__file__).parent / "demo_cache" / "retailer_pitcher"
_DEMO_BRANDS = {"chomps", "fishwife", "graza"}

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def render_retailer_pitcher_page() -> None:
    import streamlit as st
    from langgraph.types import Command

    from memory import _get_client, get_config
    from agents.retailer_pitcher.skills.buyer_personas import BUYER_PERSONAS
    from state import RetailerPitcherState
    from ui.global_css import inject_global_css

    inject_global_css()

    st.markdown(
        '<div style="margin-bottom:32px;">'
        '<h1 class="sedge-h1">Retailer Pitcher</h1>'
        '<p class="sedge-subtitle">Buyer-ready outreach and a one-pager for any brand in your book.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "Tip: Use the Dashboard's full pipeline to pitch all three retailers "
        "(Whole Foods, Sprouts, Erewhon) and fill the WFM form in one click.",
        icon=None,
    )

    if st.session_state.get("demo_mode"):
        st.markdown(
            '<div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;'
            'padding:6px 14px;margin-bottom:12px;font-size:12px;color:#92400E;font-weight:500;">'
            '🎬 Demo mode · using cached results for Chomps, Fishwife, and Graza</div>',
            unsafe_allow_html=True,
        )

    # ── Brand list ────────────────────────────────────────────────────────────

    @st.cache_data(ttl=60)
    def list_brands() -> list[dict]:
        client = _get_client()
        res = (
            client.table("brand_evaluations")
            .select("brand_name, score, verdict, category, evaluated_at")
            .order("evaluated_at", desc=True)
            .limit(60)
            .execute()
        )
        return res.data or []

    brands = list_brands()

    # In demo mode, inject cached demo brands that aren't in the DB yet
    if st.session_state.get("demo_mode"):
        _existing = {b["brand_name"].lower() for b in brands}
        _demo_entries = [
            {"brand_name": "Fishwife", "score": 76, "verdict": "established", "category": "condiment_sauce", "evaluated_at": "2026-04-22T00:00:00"},
            {"brand_name": "Graza",    "score": 71, "verdict": "established", "category": "olive_oil_cooking_oil", "evaluated_at": "2026-04-22T00:00:00"},
        ]
        for _de in _demo_entries:
            if _de["brand_name"].lower() not in _existing:
                brands.insert(0, _de)

    if not brands:
        st.error("No brands in your book yet. Ask Brand Scout to evaluate a few first.")
        return

    # ── Handoff from Brand Scout ──────────────────────────────────────────────

    _handoff_brand = st.session_state.get("handoff_brand")
    _handoff_idx = 0
    if _handoff_brand:
        for _i, _b in enumerate(brands):
            if _b.get("brand_name", "").lower() == _handoff_brand.lower():
                _handoff_idx = _i
                break

    if _handoff_brand:
        _hs = brands[_handoff_idx] if brands else {}
        _col_b, _col_x = st.columns([14, 1])
        with _col_b:
            st.markdown(
                f'<div style="background:#EBF5FB;border:1px solid #BFDBFE;border-radius:10px;'
                f'padding:10px 16px;margin-bottom:16px;font-size:13px;color:#1B4F72;font-weight:500;">'
                f'👋 Handed off from Brand Scout — <strong>{_handoff_brand}</strong>'
                f' ({_hs.get("score","—")}/100, {_hs.get("verdict","—")})</div>',
                unsafe_allow_html=True,
            )
        with _col_x:
            if st.button("×", key="rp_clear_handoff", use_container_width=True):
                del st.session_state["handoff_brand"]
                st.rerun()

    # ── Controls ──────────────────────────────────────────────────────────────

    buyer_labels = {k: v["retailer"] for k, v in BUYER_PERSONAS.items()}

    _rp_brand_col, _rp_buyer_col = st.columns([1, 1])
    with _rp_brand_col:
        st.markdown(
            '<p style="font-size:12px;font-weight:700;color:#4A4A4A;margin-bottom:4px;">1 · Pick a brand</p>',
            unsafe_allow_html=True,
        )
        pick = st.selectbox(
            "From your Brand Scout book",
            options=brands,
            index=_handoff_idx,
            format_func=lambda b: f"{b['brand_name']}  ·  {b['score']}/100",
            label_visibility="collapsed",
            key="rp_brand_pick",
        )
        st.caption(f"Category: {pick.get('category', '—')}  ·  Verdict: {pick.get('verdict', '—')}")

    with _rp_buyer_col:
        st.markdown(
            '<p style="font-size:12px;font-weight:700;color:#4A4A4A;margin-bottom:4px;">2 · Pick a buyer</p>',
            unsafe_allow_html=True,
        )
        buyer_key = st.radio(
            "Who are we pitching?",
            options=list(buyer_labels.keys()),
            format_func=lambda k: buyer_labels[k],
            label_visibility="collapsed",
            key="rp_buyer_key",
        )

    persona = BUYER_PERSONAS[buyer_key]
    st.caption(f"**{persona['buyer_title']}** · tone: {persona['tone']}")
    go = st.button("Draft pitch", type="primary", use_container_width=True, key="rp_go")
    st.markdown("<hr style='border:none;border-top:1px solid #EBEBEB;margin:12px 0 20px;'>", unsafe_allow_html=True)

    # ── Main ──────────────────────────────────────────────────────────────────

    if not go:
        st.info(
            "Pick a brand and a buyer. We'll draft the email and a one-pager you can send today."
        )
        return

    from agents.retailer_pitcher.graph import graph as pitcher_graph

    def run_with_buyer(brand_name: str, bkey: str) -> dict:
        thread_id = str(uuid.uuid4())
        config = get_config(thread_id)
        initial: RetailerPitcherState = {
            "brand_name": brand_name,
            "buyer_key": bkey,
            "scout_context": {},
            "handoff_status": "",
            "handoff_error": None,
            "email_subject": "",
            "email_body": "",
            "sell_sheet_html": "",
            "artifact_status": "",
            "artifact_errors": [],
            "input_tokens": 0,
            "output_tokens": 0,
            "approved": None,
            "rejection_reason": None,
        }
        for _ in pitcher_graph.stream(initial, config=config, stream_mode="updates"):
            snap = pitcher_graph.get_state(config)
            if snap.next and "human_approval" in snap.next:
                pitcher_graph.invoke(
                    Command(resume={"approved": True, "rejection_reason": ""}),
                    config=config,
                )
                break
        return pitcher_graph.get_state(config).values

    # Demo mode: load from cache file, skip graph
    if st.session_state.get("demo_mode") and pick["brand_name"].lower() in _DEMO_BRANDS:
        _cache_file = _DEMO_CACHE_DIR / f"{pick['brand_name'].lower()}_wfm.json"
        if _cache_file.exists():
            _cached = json.loads(_cache_file.read_text())
            email_subject = _cached.get("email_subject", "")
            email_body = _cached.get("email_body", "")
            sell_sheet_html = _cached.get("sell_sheet_html", "")
            st.success(f"Pitch ready for **{pick['brand_name']}** → **{persona['retailer']}**")
            slug = f"{pick['brand_name'].lower().replace(' ', '_')}_{buyer_key}"
            tab_email, tab_sheet = st.tabs(["📧  Email to buyer", "📄  One-pager"])
            with tab_email:
                if email_subject:
                    st.markdown(f"### Subject: {email_subject}")
                st.text_area(
                    "Email body — ready to copy into Gmail / Outlook",
                    value=email_body,
                    height=420,
                    label_visibility="visible",
                    key="rp_email_area",
                )
                col_a, _ = st.columns([1, 5])
                with col_a:
                    st.download_button(
                        "⬇ Download email",
                        data=f"Subject: {email_subject}\n\n{email_body}",
                        file_name=f"{slug}_email.txt",
                        mime="text/plain",
                        use_container_width=True,
                    )
            with tab_sheet:
                if sell_sheet_html:
                    st.components.v1.html(sell_sheet_html, height=1100, scrolling=False)
                    col_a, _ = st.columns([1, 5])
                    with col_a:
                        st.download_button(
                            "⬇ Download sell sheet (.html)",
                            data=sell_sheet_html,
                            file_name=f"{slug}_sellsheet.html",
                            mime="text/html",
                            use_container_width=True,
                        )
                    st.caption("Tip: open the downloaded HTML in your browser, then ⌘P → Save as PDF.")
            st.markdown("<hr style='border:none;border-top:1px solid #E5E7EB;margin:24px 0 16px;'>", unsafe_allow_html=True)
            if st.button("📋 Autofill the new item form →", key="rp_handoff_ao_demo", use_container_width=False):
                st.session_state["handoff_brand"] = pick["brand_name"]
                st.session_state["forced_page"] = "📋  Admin & Ops"
                st.rerun()
            return

    with st.spinner(f"Drafting pitch for {pick['brand_name']} → {persona['retailer']}..."):
        final = run_with_buyer(pick["brand_name"], buyer_key)

    handoff_status = final.get("handoff_status", "")
    artifact_errors = final.get("artifact_errors", [])
    if handoff_status != "ok":
        st.error(
            f"Handoff failed: {handoff_status} — {final.get('handoff_error', 'unknown error')}"
        )
        return
    if artifact_errors:
        st.error(f"Pitch generation errors: {artifact_errors}")
        return

    client = _get_client()
    res = (
        client.table("retailer_pitches")
        .select("*")
        .ilike("brand_name", pick["brand_name"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not res.data:
        st.error(
            f"Pitch ran (status: {final.get('artifact_status')}) but nothing saved to Supabase."
        )
        return
    row = res.data[0]

    email_subject = row.get("email_subject", "")
    email_body = row.get("email_body", "")
    sell_sheet_html = row.get("sell_sheet_html", "")

    st.success(f"Pitch ready for **{pick['brand_name']}** → **{persona['retailer']}**")

    slug = f"{pick['brand_name'].lower().replace(' ', '_')}_{buyer_key}"

    tab_email, tab_sheet = st.tabs(["📧  Outreach email", "📄  1-page sell sheet"])

    with tab_email:
        if email_subject:
            st.markdown(f"### Subject: {email_subject}")
        st.text_area(
            "Email body — ready to copy into Gmail / Outlook",
            value=email_body,
            height=420,
            label_visibility="visible",
            key="rp_email_area",
        )
        col_a, _ = st.columns([1, 5])
        with col_a:
            st.download_button(
                "⬇ Download email",
                data=f"Subject: {email_subject}\n\n{email_body}",
                file_name=f"{slug}_email.txt",
                mime="text/plain",
                use_container_width=True,
            )

    with tab_sheet:
        if sell_sheet_html:
            st.components.v1.html(sell_sheet_html, height=1100, scrolling=False)
            col_a, _ = st.columns([1, 5])
            with col_a:
                st.download_button(
                    "⬇ Download sell sheet (.html)",
                    data=sell_sheet_html,
                    file_name=f"{slug}_sellsheet.html",
                    mime="text/html",
                    use_container_width=True,
                )
            st.caption(
                "Tip: open the downloaded HTML in your browser, then ⌘P → "
                "Save as PDF for a printable version."
            )
        else:
            st.info("Sell sheet unavailable. Try again.")

    st.markdown("<hr style='border:none;border-top:1px solid #E5E7EB;margin:24px 0 16px;'>", unsafe_allow_html=True)
    if st.button(
        "📋 Autofill the new item form →",
        key="rp_handoff_ao",
        use_container_width=False,
    ):
        st.session_state["handoff_brand"] = pick["brand_name"]
        st.session_state["forced_page"] = "📋  Admin & Ops"
        st.rerun()


if __name__ == "__main__":
    import streamlit as st

    st.set_page_config(
        page_title="Retailer Pitcher · Sedge",
        page_icon="📬",
        layout="wide",
    )
    render_retailer_pitcher_page()
