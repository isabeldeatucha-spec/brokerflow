"""Investor-facing landing page shown before the broker-facing two-card workspace.

Renders a single-page editorial pitch (sticky nav, hero, problem, product,
agents w/ orchestration diagram, CTA). Both CTA buttons flip
st.session_state.investor_entered so subsequent visits drop straight into the
existing two-card workspace selector.

CSS is scoped under .bf-investor and .bf-investor-nav. Both CTA buttons are
real st.buttons styled as dark pills via [data-testid="stButton"]; the
in-nav Docs link is a plain <a href="?page=docs"> that matches the existing
docs router in brokerflow_app.py.

All HTML strings are passed through a _md() helper that collapses every
whitespace run to a single space (single-line output) before going to
st.markdown — Streamlit's Markdown parser otherwise turns 4-space-indented
lines after a blank line into code blocks regardless of surrounding HTML.
Headings use <div> instead of <h1>/<h2> so Streamlit doesn't auto-attach
its anchor-link icon.
"""
from __future__ import annotations

import streamlit as st


def _md(html: str) -> None:
    """Render HTML through st.markdown with unsafe_allow_html.

    Collapses all whitespace runs to single spaces so the result is a single
    line. This is the only reliable way to stop Streamlit's Markdown parser
    from turning indented HTML into a code block: any blank line followed by
    a 4-space-indented line becomes a fenced code block, regardless of the
    surrounding HTML. textwrap.dedent alone doesn't fix it because nested
    inner indentation survives. None of the HTML on this page uses <pre>
    or whitespace-sensitive tags, so single-line collapse is safe.
    """
    st.markdown(" ".join(html.split()), unsafe_allow_html=True)


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400&family=Inter:wght@400;500;600&display=swap');

/* Hide Streamlit's default menu and footer for an editorial feel */
#MainMenu, footer {visibility: hidden;}

/* Suppress the auto-anchor link icon Streamlit attaches to headings.
   Belt-and-suspenders: we also use <div> instead of <h1>/<h2> below. */
.bf-investor h1 a, .bf-investor h2 a,
.bf-investor h3 a, .bf-investor h4 a {
    display: none !important;
}

/* Cream page background; cards stay pure white for lift without shadows. */
[data-testid="stAppViewContainer"], .stApp {
    background: #FAFAF7 !important;
}

/* ── Color tokens ──────────────────────────────────────────────────── */
:root {
    --bf-fg: #0A0A0A;
    --bf-muted: #6B6B6B;
    --bf-faint: #A8A8A8;
    --bf-border: #E5E5E5;
    --bf-border-soft: #EFEFEF;
    --bf-bg: #FAFAF7;
    --bf-card: #FFFFFF;
}

/* ── Sticky nav bar ────────────────────────────────────────────────── */
.bf-investor-nav {
    position: sticky;
    top: 0;
    z-index: 10;
    background: rgba(250, 250, 247, 0.92);
    backdrop-filter: saturate(140%) blur(8px);
    -webkit-backdrop-filter: saturate(140%) blur(8px);
    border-bottom: 1px solid var(--bf-border-soft);
    margin: -1rem -2rem 0;
}
.bf-investor-nav-inner {
    max-width: 980px;
    margin: 0 auto;
    padding: 1.25rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.bf-investor-nav-brand {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.1rem;
    font-weight: 500;
    color: var(--bf-fg);
    letter-spacing: -0.01em;
}
.bf-investor-nav-docs {
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
    font-weight: 500;
    color: #FFFFFF;
    background: var(--bf-fg);
    padding: 0.5rem 1rem;
    border-radius: 999px;
    text-decoration: none;
    transition: background 0.15s ease;
}
.bf-investor-nav-docs:hover {
    background: #1F1F1F;
    color: #FFFFFF;
    text-decoration: none;
}

/* ── Scoped page wrapper ───────────────────────────────────────────── */
.bf-investor {
    color: var(--bf-fg);
    font-family: 'Inter', sans-serif;
    line-height: 1.6;
    max-width: 980px;
    margin: 0 auto;
    padding: 0 0 4rem;
}

/* ── Hero — title + tagline + CTA only ─────────────────────────────── */
.bf-investor-hero {
    text-align: center;
    padding: 5rem 1rem 1rem;
}
.bf-investor-hero-title {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 5rem;
    font-weight: 500;
    line-height: 1;
    letter-spacing: -0.025em;
    color: var(--bf-fg);
    margin: 0;
}
.bf-investor-hero-tagline {
    font-family: 'Playfair Display', Georgia, serif;
    font-style: italic;
    font-size: 1.35rem;
    color: var(--bf-muted);
    margin: 1rem 0 3rem 0;
    font-weight: 400;
}

/* ── Section frame (uniform 4rem top margin, lighter border) ───────── */
.bf-investor-section {
    border-top: 1px solid var(--bf-border-soft);
    margin-top: 4rem;
    padding-top: 2.5rem;
}
.bf-investor-section--cta {
    margin-top: 6rem;
    padding-top: 3rem;
    padding-bottom: 3rem;
}

.bf-investor-eyebrow {
    font-family: 'Inter', sans-serif;
    text-transform: uppercase;
    font-size: 0.7rem;
    letter-spacing: 0.18em;
    color: var(--bf-faint);
    margin: 0 0 0.75rem 0;
}
.bf-investor-h2 {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.75rem;
    font-weight: 500;
    line-height: 1.22;
    letter-spacing: -0.01em;
    color: var(--bf-fg);
    max-width: 720px;
    margin: 0 0 0.75rem 0;
}
.bf-investor-sub {
    font-size: 0.95rem;
    color: var(--bf-muted);
    max-width: 720px;
    margin: 0 0 2.25rem 0;
    line-height: 1.65;
}

/* ── Problem stat row — numbers as anchors ─────────────────────────── */
.bf-investor-stat-row {
    display: grid;
    grid-template-columns: 1fr 1.4fr 1fr;
    gap: 0;
    align-items: center;
    margin-top: 1.25rem;
    position: relative;
}
.bf-investor-stat,
.bf-investor-stat-center {
    text-align: center;
    padding: 1.5rem 0.5rem;
    position: relative;
}
.bf-investor-stat-number {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 5rem;
    font-weight: 400;
    color: var(--bf-fg);
    line-height: 1;
    letter-spacing: -0.02em;
}
.bf-investor-stat-label {
    font-family: 'Inter', sans-serif;
    text-transform: uppercase;
    font-size: 0.7rem;
    letter-spacing: 0.18em;
    color: var(--bf-faint);
    margin-top: 0.85rem;
}
.bf-investor-stat-center-title {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.25rem;
    font-weight: 500;
    color: var(--bf-fg);
}
.bf-investor-stat-center-sub {
    font-family: 'Playfair Display', Georgia, serif;
    font-style: italic;
    font-size: 0.95rem;
    color: var(--bf-muted);
    margin-top: 0.25rem;
}
.bf-investor-stat-center-body {
    font-size: 0.85rem;
    color: var(--bf-muted);
    line-height: 1.6;
    margin-top: 0.5rem;
    max-width: 240px;
    margin-left: auto;
    margin-right: auto;
}
.bf-investor-stat-row::before,
.bf-investor-stat-row::after {
    content: "";
    position: absolute;
    top: 3.7rem;
    height: 1px;
    background: var(--bf-border-soft);
}
.bf-investor-stat-row::before { left: 16%; right: 64%; }
.bf-investor-stat-row::after  { left: 64%; right: 16%; }

/* ── Card primitives ───────────────────────────────────────────────── */
.bf-investor-card {
    background: var(--bf-card);
    border: 1px solid var(--bf-border-soft);
    border-radius: 8px;
    transition: transform 200ms ease, box-shadow 200ms ease;
}
.bf-investor-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}

/* ── Product — two workspace cards with monogram glyphs ────────────── */
.bf-investor-workspaces {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    margin-top: 1rem;
}
.bf-investor-workspace {
    padding: 2rem 1.75rem;
}
.bf-investor-workspace-title {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.4rem;
    font-weight: 500;
    color: var(--bf-fg);
    margin: 0 0 0.4rem 0;
}
.bf-investor-workspace-tag {
    font-family: 'Playfair Display', Georgia, serif;
    font-style: italic;
    font-size: 0.95rem;
    color: var(--bf-muted);
    margin: 0 0 1rem 0;
}
.bf-investor-workspace-body {
    font-size: 0.9rem;
    color: var(--bf-fg);
    line-height: 1.65;
    margin: 0;
}

/* ── Agents — orchestration diagram + grid ─────────────────────────── */
.bf-investor-orch {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0;
    margin: 0.75rem 0 0.75rem;
    padding: 0 0.5rem;
}
.bf-investor-orch-node {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 0 0 auto;
    min-width: 60px;
}
.bf-investor-orch-node {
    z-index: 1;
}
.bf-investor-orch-circle {
    width: 16px;
    height: 16px;
    border: 1.5px solid var(--bf-fg);
    border-radius: 99px;
    background: #FFFFFF;
}
.bf-investor-orch-label {
    font-family: 'Inter', sans-serif;
    font-size: 0.72rem;
    color: var(--bf-muted);
    margin-top: 0.5rem;
    letter-spacing: 0.04em;
}
.bf-investor-orch-line {
    flex: 1 1 auto;
    height: 1px;
    background: #D0D0D0;
    margin-top: 8px;
    z-index: 0;
}

.bf-investor-agents {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1.25rem;
    margin-top: 0.5rem;
}
.bf-investor-agent {
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
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.45rem;
}
.bf-investor-agent-tag::before {
    content: "•";
    color: var(--bf-faint);
    font-size: 1rem;
    line-height: 1;
}

/* ── CTA section ───────────────────────────────────────────────────── */
.bf-investor-cta {
    text-align: center;
}
.bf-investor-cta-eyebrow {
    font-family: 'Playfair Display', Georgia, serif;
    font-style: italic;
    font-size: 1.5rem;
    color: var(--bf-muted);
    margin: 0 0 1.25rem 0;
}
.bf-investor-cta-fineprint {
    font-family: 'Playfair Display', Georgia, serif;
    font-style: italic;
    font-size: 0.85rem;
    color: var(--bf-faint);
    margin: 1rem 0 0 0;
    text-align: center;
}

/* Bigger bottom CTA, scoped via a keyed container wrapper. */
.st-key-bf_investor_cta_wrap [data-testid="stButton"] {
    max-width: 320px;
    margin: 0 auto;
}
.st-key-bf_investor_cta_wrap [data-testid="stButton"] > button {
    padding: 1.1rem 3rem !important;
    font-size: 1.05rem !important;
    font-weight: 500 !important;
}

/* ── st.button styled as dark pill (applies to both CTAs) ──────────── */
[data-testid="stButton"] {
    max-width: 280px;
    margin: 0 auto;
}
[data-testid="stButton"] > button {
    background: var(--bf-fg) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 999px !important;
    padding: 0.95rem 2.25rem !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 1rem !important;
    width: 100%;
    transition: background 0.15s ease;
}
[data-testid="stButton"] > button:hover {
    background: #1F1F1F !important;
    color: #FFFFFF !important;
}

/* ── Mobile collapse ───────────────────────────────────────────────── */
@media (max-width: 720px) {
    .bf-investor-nav-inner { padding: 1rem 1.25rem; }
    .bf-investor-hero { padding: 3rem 1rem 1rem; }
    .bf-investor-hero-title { font-size: 3.25rem; }
    .bf-investor-hero-tagline { font-size: 1.05rem; }
    .bf-investor-h2 { font-size: 1.5rem; }
    .bf-investor-stat-row,
    .bf-investor-workspaces,
    .bf-investor-agents {
        grid-template-columns: 1fr;
    }
    .bf-investor-stat-row::before,
    .bf-investor-stat-row::after { display: none; }
    .bf-investor-stat-number { font-size: 3.5rem; }
    .bf-investor-orch { display: none; }
    [data-testid="stButton"] { max-width: 100%; }
}
</style>
"""


def _render_nav() -> None:
    _md("""
    <header class="bf-investor-nav">
      <div class="bf-investor-nav-inner">
        <span class="bf-investor-nav-brand">BrokerFlow</span>
        <a class="bf-investor-nav-docs" href="?page=docs" target="_self">Docs &rarr;</a>
      </div>
    </header>
    """)


def _render_hero() -> None:
    _md("""
    <div class="bf-investor">
      <section class="bf-investor-hero">
        <div class="bf-investor-hero-title">BrokerFlow</div>
        <div class="bf-investor-hero-tagline">the operating system for CPG brokers</div>
      </section>
    </div>
    """)


def _render_problem() -> None:
    _md("""
    <div class="bf-investor">
      <section class="bf-investor-section">
        <div class="bf-investor-eyebrow">The problem</div>
        <div class="bf-investor-h2">
          The broker is the center of gravity in CPG, and the most
          under-tooled node in the chain.
        </div>
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
          <div class="bf-investor-stat-center">
            <div class="bf-investor-stat-center-title">Brokers</div>
            <div class="bf-investor-stat-center-sub">the workflow layer</div>
            <div class="bf-investor-stat-center-body">
              every flow runs through them: manually, in spreadsheets and email.
            </div>
          </div>
          <div class="bf-investor-stat">
            <div class="bf-investor-stat-number">60k+</div>
            <div class="bf-investor-stat-label">retailers &amp; distributors</div>
          </div>
        </div>
      </section>
    </div>
    """)


def _render_product() -> None:
    _md("""
    <div class="bf-investor">
      <section class="bf-investor-section">
        <div class="bf-investor-eyebrow">The product</div>
        <div class="bf-investor-h2">Two workspaces. One source of truth.</div>
        <p class="bf-investor-sub">
          Brokers spend their day in two modes: deciding which brands
          to take on, and servicing the ones they already represent.
          BrokerFlow gives each its own workspace, with agents doing
          the work underneath.
        </p>
        <div class="bf-investor-workspaces">
          <div class="bf-investor-card bf-investor-workspace">
            <div class="bf-investor-workspace-title">Scout new brands</div>
            <div class="bf-investor-workspace-tag">qualify before you take a meeting</div>
            <p class="bf-investor-workspace-body">
              Brand Scout pulls signals across Amazon, Instacart, Faire,
              social, and trade press. Scores the brand on five criteria
              &mdash; velocity, distribution, margin, story, promo
              independence &mdash; and returns a verdict before you
              spend a meeting on it.
            </p>
          </div>
          <div class="bf-investor-card bf-investor-workspace">
            <div class="bf-investor-workspace-title">Manage your book</div>
            <div class="bf-investor-workspace-tag">service the brands you already represent</div>
            <p class="bf-investor-workspace-body">
              Drafts buyer-tailored pitches and one-pagers per persona,
              then auto-fills the new-item paperwork retailers require
              &mdash; Whole Foods, KeHE, Sprouts &mdash; from a single
              canonical brand record.
            </p>
          </div>
        </div>
      </section>
    </div>
    """)


def _render_agents() -> None:
    pipeline_nodes = ["Scout", "Onboard", "Match", "Pitch", "Form"]
    orch_parts: list[str] = []
    for i, label in enumerate(pipeline_nodes):
        orch_parts.append(
            f'<div class="bf-investor-orch-node">'
            f'<div class="bf-investor-orch-circle"></div>'
            f'<div class="bf-investor-orch-label">{label}</div>'
            f'</div>'
        )
        if i < len(pipeline_nodes) - 1:
            orch_parts.append('<div class="bf-investor-orch-line"></div>')
    orch_html = "".join(orch_parts)

    _md(f"""
    <div class="bf-investor">
      <section class="bf-investor-section">
        <div class="bf-investor-eyebrow">Under the hood</div>
        <div class="bf-investor-h2">An orchestrated agent team.</div>
        <p class="bf-investor-sub">
          Each agent owns one workflow end-to-end. The orchestration
          layer ties them together via a shared blackboard in Supabase,
          so nothing slips across 100+ brands.
        </p>

        <div class="bf-investor-orch">{orch_html}</div>

        <div class="bf-investor-agents">
          <div class="bf-investor-card bf-investor-agent">
            <div class="bf-investor-agent-title">Brand Scout</div>
            <p class="bf-investor-agent-desc">Research + score 0&ndash;100</p>
            <p class="bf-investor-agent-tag">ReAct loop</p>
          </div>
          <div class="bf-investor-card bf-investor-agent">
            <div class="bf-investor-agent-title">Brand Onboarding</div>
            <p class="bf-investor-agent-desc">Docs &rarr; canonical record</p>
            <p class="bf-investor-agent-tag">6-node linear</p>
          </div>
          <div class="bf-investor-card bf-investor-agent">
            <div class="bf-investor-agent-title">Retailer Matcher</div>
            <p class="bf-investor-agent-desc">Picks a buyer</p>
            <p class="bf-investor-agent-tag">Heuristic</p>
          </div>
          <div class="bf-investor-card bf-investor-agent">
            <div class="bf-investor-agent-title">Retailer Pitcher</div>
            <p class="bf-investor-agent-desc">Drafts email + sell sheet</p>
            <p class="bf-investor-agent-tag">Parallel + interrupt</p>
          </div>
          <div class="bf-investor-card bf-investor-agent">
            <div class="bf-investor-agent-title">New Item Forms</div>
            <p class="bf-investor-agent-desc">Fills new-item form</p>
            <p class="bf-investor-agent-tag">Rules + LLM gaps</p>
          </div>
          <div class="bf-investor-card bf-investor-agent">
            <div class="bf-investor-agent-title">+ more soon</div>
            <p class="bf-investor-agent-desc">PO Processing, Trade Spend, Accruals&hellip;</p>
            <p class="bf-investor-agent-tag">12 on the roadmap</p>
          </div>
        </div>
      </section>
    </div>
    """)


def _render_cta_open() -> None:
    _md("""
    <div class="bf-investor">
      <section class="bf-investor-section bf-investor-section--cta bf-investor-cta">
        <div class="bf-investor-cta-eyebrow">Ready to see it?</div>
      </section>
    </div>
    """)


def _render_cta_fineprint() -> None:
    _md("""
    <div class="bf-investor">
      <p class="bf-investor-cta-fineprint">
        Takes ~30 seconds to evaluate your first brand
      </p>
    </div>
    """)


def _enter_app() -> None:
    st.session_state["investor_entered"] = True
    st.rerun()


def render_investor_landing() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    _render_nav()
    _render_hero()

    # Hero CTA — real Streamlit button styled by the dark-pill rule above
    if st.button("I'm a broker →", key="bf_investor_enter_hero"):
        _enter_app()

    _render_problem()
    _render_product()
    _render_agents()

    _render_cta_open()

    with st.container(key="bf_investor_cta_wrap"):
        if st.button("I'm a broker →", key="bf_investor_enter_cta"):
            _enter_app()

    _render_cta_fineprint()
