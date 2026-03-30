"""
Brand Scout — Broker Approval UI

Run from the sedge/ directory:
    streamlit run ui/app.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import uuid
import streamlit as st
from langgraph.types import Command

from sedge.agents.brand_scout.graph import graph
from sedge.memory import get_config

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Brand Scout · Sedge",
    page_icon="🌾",
    layout="wide",
)

# ── Session state init ────────────────────────────────────────────────────────
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "phase" not in st.session_state:
    st.session_state.phase = "idle"  # idle | running | awaiting_approval | done | rejected | below_threshold
if "interrupt_data" not in st.session_state:
    st.session_state.interrupt_data = None


def reset():
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.phase = "idle"
    st.session_state.interrupt_data = None


def run_graph_to_interrupt(brand_name: str, website_url: str):
    """Stream the graph until it hits the human_approval interrupt."""
    config = get_config(st.session_state.thread_id)
    initial_state = {
        "brand_name": brand_name,
        "website_url": website_url,
        "sources_checked": [],
        "signals_found": {},
        "score": {},
        "verdict": "",
        "founder_name": "",
        "founder_email": "",
        "email_draft": "",
        "approved": None,
        "rejection_reason": None,
    }

    interrupt_data = None
    for chunk in graph.stream(initial_state, config=config, stream_mode="updates"):
        for node in chunk:
            st.write(f"  ✓ `{node}` completed")

        state_snapshot = graph.get_state(config)
        if state_snapshot.next and state_snapshot.next[0] == "human_approval":
            if state_snapshot.tasks:
                for task in state_snapshot.tasks:
                    if hasattr(task, "interrupts") and task.interrupts:
                        interrupt_data = task.interrupts[0].value
            break

    return interrupt_data


def resume_graph(approved: bool, rejection_reason: str = ""):
    config = get_config(st.session_state.thread_id)
    return graph.invoke(
        Command(resume={"approved": approved, "rejection_reason": rejection_reason}),
        config=config,
    )


# ── Header ────────────────────────────────────────────────────────────────────
col_logo, col_title = st.columns([1, 8])
with col_logo:
    st.markdown("## 🌾")
with col_title:
    st.markdown("## Brand Scout")
    st.caption("Powered by Sedge · Broker review queue")

st.divider()

# ── Phase: idle ───────────────────────────────────────────────────────────────
if st.session_state.phase == "idle":
    st.subheader("Run Discovery")

    mode = st.radio(
        "Mode",
        ["Auto-discover (scrape retailer new arrivals)", "Manual — enter a brand"],
        horizontal=True,
    )

    if mode.startswith("Manual"):
        brand_name = st.text_input("Brand name", placeholder="e.g. Oat & Honor")
        website_url = st.text_input("Website URL", placeholder="https://oatandhonor.com")
    else:
        brand_name = ""
        website_url = ""

    if st.button("▶  Run Brand Scout", type="primary"):
        st.session_state["_brand_name"] = brand_name
        st.session_state["_website_url"] = website_url
        st.session_state.phase = "running"
        st.rerun()

# ── Phase: running ────────────────────────────────────────────────────────────
elif st.session_state.phase == "running":
    st.subheader("Running…")

    b_name = st.session_state.get("_brand_name", "")
    b_url = st.session_state.get("_website_url", "")

    with st.spinner("Researching brand and scoring…"):
        interrupt_data = run_graph_to_interrupt(b_name, b_url)

    if interrupt_data:
        st.session_state.interrupt_data = interrupt_data
        st.session_state.phase = "awaiting_approval"
    else:
        st.session_state.phase = "below_threshold"
    st.rerun()

# ── Phase: awaiting_approval ──────────────────────────────────────────────────
elif st.session_state.phase == "awaiting_approval":
    data = st.session_state.interrupt_data
    score = data["score"]
    signals = data.get("signals_found", {})

    st.subheader(f"Review: {data['brand_name']}")

    total = score.get("total", 0)
    score_color = "#22c55e" if total >= 75 else "#f59e0b" if total >= 60 else "#ef4444"

    st.markdown(
        f"""
        <div style="
            background: {score_color}18;
            border-left: 4px solid {score_color};
            padding: 16px 20px;
            border-radius: 6px;
            margin-bottom: 20px;
        ">
            <span style="font-size: 2rem; font-weight: 700; color: {score_color}">{total}</span>
            <span style="font-size: 1rem; color: #6b7280"> / 100 broker-readiness score</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Score Breakdown**")
        dimensions = [
            ("Velocity Proof", "velocity_proof", 25),
            ("Distribution Density", "distribution_density", 20),
            ("Margin Viability", "margin_viability", 20),
            ("Brand Story Clarity", "brand_story_clarity", 20),
            ("Promotional Independence", "promotional_independence", 15),
        ]
        for label, key, max_val in dimensions:
            val = score.get(key, 0)
            pct = val / max_val
            bar_color = "#22c55e" if pct >= 0.75 else "#f59e0b" if pct >= 0.5 else "#ef4444"
            st.markdown(
                f"""
                <div style="margin-bottom:10px">
                    <div style="display:flex;justify-content:space-between;font-size:0.85rem">
                        <span>{label}</span>
                        <span style="font-weight:600">{val}/{max_val}</span>
                    </div>
                    <div style="background:#e5e7eb;border-radius:4px;height:8px;margin-top:4px">
                        <div style="background:{bar_color};width:{pct*100:.0f}%;height:8px;border-radius:4px"></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        rationale = signals.get("score_rationale", {})
        if rationale:
            with st.expander("Score rationale"):
                for label, key, _ in dimensions:
                    if key in rationale:
                        st.markdown(f"**{label}:** {rationale[key]}")

    with col2:
        st.markdown("**Research Signals**")
        amazon = signals.get("amazon", {})
        faire = signals.get("faire", {})
        website = signals.get("website", {})

        if amazon:
            st.markdown(
                f"- Amazon: **{amazon.get('review_count', '?')} reviews** · "
                f"⭐ {amazon.get('average_rating', '?')} · "
                f"BSR #{amazon.get('best_seller_rank', '?')}"
            )
        if faire:
            st.markdown(
                f"- Faire: **{faire.get('retailers_carrying', '?')} retailers** · "
                f"Reorder {faire.get('reorder_rate', '?')} · "
                f"Wholesale ${faire.get('wholesale_price', '?')}"
            )
        if website:
            st.markdown(f"- Listed in: {', '.join(website.get('where_to_buy_listed', []))}")

    st.divider()

    st.markdown(f"**Draft email → {data['founder_name']} ({data['founder_email']})**")
    email_draft = st.text_area(
        "Edit before sending",
        value=data["email_draft"],
        height=300,
        key="email_draft_editor",
        label_visibility="collapsed",
    )

    st.divider()

    col_approve, col_reject = st.columns([1, 1])

    with col_approve:
        if st.button("✅  Approve & Send", type="primary", use_container_width=True):
            st.session_state.interrupt_data["email_draft"] = email_draft
            with st.spinner("Sending email…"):
                resume_graph(approved=True)
            st.session_state.phase = "done"
            st.rerun()

    with col_reject:
        with st.expander("Reject"):
            reason = st.text_input("Reason (optional)", key="rejection_reason")
            if st.button("Reject", use_container_width=True):
                resume_graph(approved=False, rejection_reason=reason)
                st.session_state.phase = "rejected"
                st.rerun()

# ── Phase: done ───────────────────────────────────────────────────────────────
elif st.session_state.phase == "done":
    st.success("Email sent successfully.")
    data = st.session_state.interrupt_data or {}
    st.markdown(f"Outreach sent to **{data.get('founder_name', '')}** at `{data.get('founder_email', '')}`")
    if st.button("Scout another brand"):
        reset()
        st.rerun()

# ── Phase: rejected ───────────────────────────────────────────────────────────
elif st.session_state.phase == "rejected":
    st.warning("Brand rejected — no email sent.")
    if st.button("Scout another brand"):
        reset()
        st.rerun()

# ── Phase: below_threshold ────────────────────────────────────────────────────
elif st.session_state.phase == "below_threshold":
    st.info("Brand scored below threshold — not advancing to outreach.")
    if st.button("Scout another brand"):
        reset()
        st.rerun()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Brand Scout")
    st.caption("Sedge · v0.1 skeleton")
    st.divider()

    if st.session_state.phase == "idle":
        st.markdown("Enter a brand above or run auto-discovery to start.")
    else:
        st.markdown(f"**Thread:** `{st.session_state.thread_id[:8]}…`")
        st.markdown(f"**Status:** {st.session_state.phase}")

    st.divider()
    if st.button("Reset", use_container_width=True):
        reset()
        st.rerun()
