"""
Retailer Pitcher — broker-facing demo.

Reads Brand Scout evaluations from shared memory, generates a buyer-specific
outreach email and a 1-page sell sheet ready to screenshot, download, or
forward. Designed for a real independent food & beverage broker workflow.

Run:
    cd "/Users/yi/Documents/Broker agent/sedge"
    set -a && source .env.hw8 && set +a && export SEDGE_LLM_PROVIDER=gemini
    streamlit run hw8/pitcher_demo.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

import streamlit as st  # noqa: E402

from memory import _get_client  # noqa: E402
from agents.retailer_pitcher.skills.buyer_personas import BUYER_PERSONAS  # noqa: E402


st.set_page_config(page_title="Sedge — Retailer Pitcher", page_icon="📬", layout="wide")

st.markdown(
    """
    <div style="padding: 4px 0 18px">
      <div style="font-size: 28px; font-weight: 700; letter-spacing: -0.4px;">
        Sedge · Retailer Pitcher
      </div>
      <div style="font-size: 14px; color: #5c6b5c;">
        Draft a retailer-ready outreach email and 1-page sell sheet for any brand in your book.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── Sidebar: pick brand + buyer ──────────────────────────────────────────────

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
if not brands:
    st.error("No brands in your book yet. Ask Brand Scout to evaluate a few first.")
    st.stop()

with st.sidebar:
    st.subheader("1 · Pick a brand")
    pick = st.selectbox(
        "From your Brand Scout book",
        options=brands,
        format_func=lambda b: f"{b['brand_name']}  ·  {b['score']}/100",
        label_visibility="collapsed",
    )
    st.caption(f"Category: {pick.get('category', '—')}  ·  Verdict: {pick.get('verdict', '—')}")

    st.divider()
    st.subheader("2 · Pick a buyer")
    buyer_labels = {k: v["retailer"] for k, v in BUYER_PERSONAS.items()}
    buyer_key = st.radio(
        "Who are we pitching?",
        options=list(buyer_labels.keys()),
        format_func=lambda k: buyer_labels[k],
        label_visibility="collapsed",
    )
    persona = BUYER_PERSONAS[buyer_key]
    st.caption(f"**{persona['buyer_title']}** · tone: {persona['tone']}")

    st.divider()
    go = st.button("Draft pitch", type="primary", use_container_width=True)


# ── Main ─────────────────────────────────────────────────────────────────────

if not go:
    st.info("Pick a brand and a buyer on the left, then click **Draft pitch**. "
            "You'll get a ready-to-send email and a printable 1-page sell sheet.")
    st.stop()


from agents.retailer_pitcher.graph import run_pitch_once  # noqa: E402

# Force buyer choice via a lightweight override — the graph reads `buyer_key`
# from state if set, otherwise it runs its own heuristic.
import uuid
from langgraph.types import Command
from memory import get_config
from state import RetailerPitcherState
from agents.retailer_pitcher.graph import graph as pitcher_graph


def run_with_buyer(brand_name: str, buyer_key: str) -> dict:
    thread_id = str(uuid.uuid4())
    config = get_config(thread_id)
    initial: RetailerPitcherState = {
        "brand_name": brand_name,
        "buyer_key": buyer_key,
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


with st.spinner(f"Drafting pitch for {pick['brand_name']} → {persona['retailer']}..."):
    final = run_with_buyer(pick["brand_name"], buyer_key)

handoff_status = final.get("handoff_status", "")
artifact_errors = final.get("artifact_errors", [])
if handoff_status != "ok":
    st.error(f"Handoff failed: {handoff_status} — {final.get('handoff_error', 'unknown error')}")
    st.stop()
if artifact_errors:
    st.error(f"Pitch generation errors: {artifact_errors}")
    st.stop()

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
    st.error(f"Pitch ran (status: {final.get('artifact_status')}) but nothing saved to Supabase.")
    st.stop()
row = res.data[0]

email_subject = row.get("email_subject", "")
email_body = row.get("email_body", "")
sell_sheet_html = row.get("sell_sheet_html", "")

st.success(f"Pitch ready for **{pick['brand_name']}** → **{persona['retailer']}**")

slug = f"{pick['brand_name'].lower().replace(' ', '_')}_{buyer_key}"

tab_email, tab_sheet = st.tabs([
    "📧  Outreach email",
    "📄  1-page sell sheet",
])

with tab_email:
    if email_subject:
        st.markdown(f"### Subject: {email_subject}")
    st.text_area(
        "Email body — ready to copy into Gmail / Outlook",
        value=email_body,
        height=420,
        label_visibility="visible",
    )
    col_a, col_b = st.columns([1, 5])
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
        # Render the full letter-size sell sheet. Height generous so the
        # whole page is visible without scrolling inside the iframe.
        st.components.v1.html(sell_sheet_html, height=1100, scrolling=False)
        col_a, col_b = st.columns([1, 5])
        with col_a:
            st.download_button(
                "⬇ Download sell sheet (.html)",
                data=sell_sheet_html,
                file_name=f"{slug}_sellsheet.html",
                mime="text/html",
                use_container_width=True,
            )
        st.caption("Tip: open the downloaded HTML in your browser, then ⌘P → "
                   "Save as PDF for a printable version.")
    else:
        st.info("Sell sheet unavailable. Try again.")
