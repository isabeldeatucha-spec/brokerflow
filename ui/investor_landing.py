"""Investor-facing landing page shown before the broker-facing two-card workspace.

Renders a single-page editorial pitch (hero, problem, product, agents, CTA).
The CTA flips st.session_state.investor_entered = True, after which
brokerflow_app.py's workspace router takes over and shows the existing
two-card landing.
"""
from __future__ import annotations

import streamlit as st


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400&family=Inter:wght@400;500;600&display=swap');

/* Hide Streamlit's default menu and footer for an editorial feel */
#MainMenu, footer {visibility: hidden;}

/* ── Scoped container ──────────────────────────────────────────────── */
.bf-investor {
    --bf-fg: #0A0A0A;
    --bf-muted: #6B6B6B;
    --bf-faint: #A8A8A8;
    --bf-border: #E5E5E5;
    --bf-bg: #FAFAF7;

    color: var(--bf-fg);
    font-family: 'Inter', sans-serif;
    line-height: 1.55;
    max-width: 980px;
    margin: 0 auto;
    padding: 1rem 0 4rem;
}

/* ── Hero ──────────────────────────────────────────────────────────── */
.bf-investor-hero {
    text-align: center;
    padding: 5rem 1rem 4rem;
}
.bf-investor-hero-title {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 4.5rem;
    font-weight: 500;
    line-height: 1;
    letter-spacing: -0.02em;
    color: var(--bf-fg);
    margin: 0;
}
.bf-investor-hero-tagline {
    font-family: 'Playfair Display', Georgia, serif;
    font-style: italic;
    font-size: 1.4rem;
    color: var(--bf-muted);
    margin: 1rem 0 0 0;
    font-weight: 400;
}

/* ── Section frame ─────────────────────────────────────────────────── */
.bf-investor-section {
    border-top: 1px solid var(--bf-border);
    margin-top: 5rem;
    padding-top: 3rem;
}
.bf-investor-eyebrow {
    font-family: 'Inter', sans-serif;
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.16em;
    color: var(--bf-faint);
    margin: 0 0 1rem 0;
}
.bf-investor-h2 {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 2.25rem;
    font-weight: 500;
    line-height: 1.18;
    letter-spacing: -0.01em;
    color: var(--bf-fg);
    max-width: 760px;
    margin: 0 0 1rem 0;
}
.bf-investor-sub {
    font-size: 1rem;
    color: var(--bf-muted);
    max-width: 720px;
    margin: 0 0 2.5rem 0;
    line-height: 1.65;
}

/* ── Problem stat row ──────────────────────────────────────────────── */
.bf-investor-stat-row {
    display: grid;
    grid-template-columns: 1fr 1.4fr 1fr;
    gap: 1.5rem;
    align-items: stretch;
    margin-top: 1rem;
}
.bf-investor-stat {
    text-align: center;
    padding: 2rem 1rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.bf-investor-stat-number {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 2.75rem;
    font-weight: 500;
    color: var(--bf-fg);
    line-height: 1;
}
.bf-investor-stat-label {
    font-family: 'Inter', sans-serif;
    text-transform: uppercase;
    font-size: 0.7rem;
    letter-spacing: 0.16em;
    color: var(--bf-faint);
    margin-top: 0.6rem;
}
.bf-investor-stat-card {
    border: 1px solid var(--bf-border);
    background: #FFFFFF;
    border-radius: 4px;
    padding: 2rem 1.5rem;
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 0.5rem;
}
.bf-investor-stat-card-title {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.5rem;
    font-weight: 500;
    color: var(--bf-fg);
}
.bf-investor-stat-card-sub {
    font-family: 'Playfair Display', Georgia, serif;
    font-style: italic;
    font-size: 0.95rem;
    color: var(--bf-muted);
}
.bf-investor-stat-card-body {
    font-size: 0.85rem;
    color: var(--bf-muted);
    line-height: 1.55;
    margin-top: 0.4rem;
}

/* ── Product — two workspace cards ─────────────────────────────────── */
.bf-investor-workspaces {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    margin-top: 1rem;
}
.bf-investor-workspace {
    border: 1px solid var(--bf-border);
    background: #FFFFFF;
    border-radius: 4px;
    padding: 2rem 1.75rem;
}
.bf-investor-workspace-title {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.6rem;
    font-weight: 500;
    color: var(--bf-fg);
    margin: 0 0 0.4rem 0;
}
.bf-investor-workspace-tag {
    font-family: 'Playfair Display', Georgia, serif;
    font-style: italic;
    font-size: 1rem;
    color: var(--bf-muted);
    margin: 0 0 1rem 0;
}
.bf-investor-workspace-body {
    font-size: 0.92rem;
    color: var(--bf-fg);
    line-height: 1.65;
    margin: 0;
}

/* ── Agents — 3x2 grid ─────────────────────────────────────────────── */
.bf-investor-agents {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1.25rem;
    margin-top: 1rem;
}
.bf-investor-agent {
    border: 1px solid var(--bf-border);
    background: #FFFFFF;
    border-radius: 4px;
    padding: 1.5rem 1.4rem;
    display: flex;
    flex-direction: column;
}
.bf-investor-agent-title {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--bf-fg);
    margin: 0 0 0.5rem 0;
}
.bf-investor-agent-desc {
    font-size: 0.88rem;
    color: var(--bf-muted);
    line-height: 1.55;
    margin: 0 0 1rem 0;
    flex: 1;
}
.bf-investor-agent-tag {
    font-family: 'Playfair Display', Georgia, serif;
    font-style: italic;
    font-size: 0.82rem;
    color: var(--bf-faint);
    border-top: 1px solid var(--bf-border);
    padding-top: 0.75rem;
    margin: 0;
}

/* ── CTA section ───────────────────────────────────────────────────── */
.bf-investor-cta {
    border-top: 1px solid var(--bf-border);
    margin-top: 5rem;
    padding-top: 3.5rem;
    text-align: center;
}
.bf-investor-cta-eyebrow {
    font-family: 'Playfair Display', Georgia, serif;
    font-style: italic;
    font-size: 1.5rem;
    color: var(--bf-muted);
    margin: 0 0 1.5rem 0;
}

/* Style the single Streamlit button on this page as a dark pill.
   Safe to scope globally because brokerflow_app calls st.stop() after
   render_investor_landing(), so no other buttons render. */
[data-testid="stButton"] {
    max-width: 240px;
    margin: 0 auto;
}
[data-testid="stButton"] > button {
    background: #0A0A0A !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 0.85rem 1.5rem !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.95rem !important;
    width: 100%;
    transition: background 0.15s ease;
}
[data-testid="stButton"] > button:hover {
    background: #1F1F1F !important;
    color: #FFFFFF !important;
}

/* ── Mobile collapse ───────────────────────────────────────────────── */
@media (max-width: 720px) {
    .bf-investor-hero-title { font-size: 3rem; }
    .bf-investor-hero-tagline { font-size: 1.1rem; }
    .bf-investor-h2 { font-size: 1.7rem; }
    .bf-investor-stat-row,
    .bf-investor-workspaces,
    .bf-investor-agents {
        grid-template-columns: 1fr;
    }
    .bf-investor-section,
    .bf-investor-cta {
        margin-top: 3.5rem;
        padding-top: 2.5rem;
    }
}
</style>
"""


def render_investor_landing() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    # Open the scoped wrapper. We close it after the CTA button by re-opening
    # st.markdown — this is safe because the body of each section is rendered
    # via its own st.markdown call inside one logical wrapper.
    st.markdown('<div class="bf-investor">', unsafe_allow_html=True)

    # ── Hero ──────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="bf-investor-hero">
            <h1 class="bf-investor-hero-title">BrokerFlow</h1>
            <p class="bf-investor-hero-tagline">the operating system for CPG brokers</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Problem ───────────────────────────────────────────────────────────
    st.markdown(
        """
        <section class="bf-investor-section">
            <p class="bf-investor-eyebrow">The problem</p>
            <h2 class="bf-investor-h2">
                The broker is the center of gravity in CPG, and the most
                under-tooled node in the chain.
            </h2>
            <p class="bf-investor-sub">
                Brokers waste 60%+ of their time on admin instead of selling.
                Every flow runs through them &mdash; new-item forms, buyer
                outreach, PO processing, deductions &mdash; manually, in
                spreadsheets and email.
            </p>
            <div class="bf-investor-stat-row">
                <div class="bf-investor-stat">
                    <div class="bf-investor-stat-number">20k+</div>
                    <div class="bf-investor-stat-label">F&amp;B brands</div>
                </div>
                <div class="bf-investor-stat-card">
                    <div class="bf-investor-stat-card-title">Brokers</div>
                    <div class="bf-investor-stat-card-sub">the workflow layer</div>
                    <div class="bf-investor-stat-card-body">
                        every flow runs through them: manually, in
                        spreadsheets and email.
                    </div>
                </div>
                <div class="bf-investor-stat">
                    <div class="bf-investor-stat-number">60k+</div>
                    <div class="bf-investor-stat-label">retailers &amp; distributors</div>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    # ── Product ───────────────────────────────────────────────────────────
    st.markdown(
        """
        <section class="bf-investor-section">
            <p class="bf-investor-eyebrow">The product</p>
            <h2 class="bf-investor-h2">Two workspaces. One source of truth.</h2>
            <p class="bf-investor-sub">
                Brokers spend their day in two modes: deciding which brands
                to take on, and servicing the ones they already represent.
                BrokerFlow gives each its own workspace, with agents doing
                the work underneath.
            </p>
            <div class="bf-investor-workspaces">
                <div class="bf-investor-workspace">
                    <h3 class="bf-investor-workspace-title">Scout new brands</h3>
                    <p class="bf-investor-workspace-tag">qualify before you take a meeting</p>
                    <p class="bf-investor-workspace-body">
                        Brand Scout pulls signals across Amazon, Instacart,
                        Faire, social, and trade press. Scores the brand on
                        five criteria &mdash; velocity, distribution, margin,
                        story, promo independence &mdash; and returns a
                        verdict before you spend a meeting on it.
                    </p>
                </div>
                <div class="bf-investor-workspace">
                    <h3 class="bf-investor-workspace-title">Manage your book</h3>
                    <p class="bf-investor-workspace-tag">service the brands you already represent</p>
                    <p class="bf-investor-workspace-body">
                        Drafts buyer-tailored pitches and one-pagers per
                        persona, then auto-fills the new-item paperwork
                        retailers require &mdash; Whole Foods, KeHE, Sprouts
                        &mdash; from a single canonical brand record.
                    </p>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    # ── Agents ────────────────────────────────────────────────────────────
    st.markdown(
        """
        <section class="bf-investor-section">
            <p class="bf-investor-eyebrow">Under the hood</p>
            <h2 class="bf-investor-h2">An orchestrated agent team.</h2>
            <p class="bf-investor-sub">
                Each agent owns one workflow end-to-end. The orchestration
                layer ties them together via a shared blackboard in
                Supabase, so nothing slips across 100+ brands.
            </p>
            <div class="bf-investor-agents">
                <div class="bf-investor-agent">
                    <h4 class="bf-investor-agent-title">Brand Scout</h4>
                    <p class="bf-investor-agent-desc">Research + score 0&ndash;100</p>
                    <p class="bf-investor-agent-tag">ReAct loop</p>
                </div>
                <div class="bf-investor-agent">
                    <h4 class="bf-investor-agent-title">Brand Onboarding</h4>
                    <p class="bf-investor-agent-desc">Docs &rarr; canonical record</p>
                    <p class="bf-investor-agent-tag">6-node linear</p>
                </div>
                <div class="bf-investor-agent">
                    <h4 class="bf-investor-agent-title">Retailer Matcher</h4>
                    <p class="bf-investor-agent-desc">Picks a buyer</p>
                    <p class="bf-investor-agent-tag">Heuristic</p>
                </div>
                <div class="bf-investor-agent">
                    <h4 class="bf-investor-agent-title">Retailer Pitcher</h4>
                    <p class="bf-investor-agent-desc">Drafts email + sell sheet</p>
                    <p class="bf-investor-agent-tag">Parallel + interrupt</p>
                </div>
                <div class="bf-investor-agent">
                    <h4 class="bf-investor-agent-title">New Item Forms</h4>
                    <p class="bf-investor-agent-desc">Fills new-item form</p>
                    <p class="bf-investor-agent-tag">Rules + LLM gaps</p>
                </div>
                <div class="bf-investor-agent">
                    <h4 class="bf-investor-agent-title">+ more soon</h4>
                    <p class="bf-investor-agent-desc">PO Processing, Trade Spend, Accruals&hellip;</p>
                    <p class="bf-investor-agent-tag">12 on the roadmap</p>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    # ── CTA ───────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="bf-investor-cta">
            <p class="bf-investor-cta-eyebrow">Ready to see it?</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("I'm a broker →", key="bf_investor_enter"):
        st.session_state["investor_entered"] = True
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
