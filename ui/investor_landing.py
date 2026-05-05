"""Investor-facing landing page shown before the broker-facing two-card workspace.

Renders a single-page editorial pitch (sticky nav, two-column hero with
queue mockup, Monday morning timeline, agents w/ live + coming-soon
status indicators). The sticky nav CTA flips
st.session_state.investor_entered via ?goto=app, after which the workspace
router drops the user into the existing two-card workspace selector.

CSS is scoped under .bf-investor / .bf-investor-nav / .bf-queue-* /
.bf-monday-* / .bf-hero-*. The page has no st.button widgets — every CTA
is a raw HTML <a> link that the workspace router catches via query params,
so styling is fully under our control.

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
    """Render HTML through st.markdown with unsafe_allow_html, single-lined.

    Collapses all whitespace runs to single spaces so the result is a single
    line — the only reliable way to stop Streamlit's Markdown parser from
    turning indented HTML into a code block. Safe because no HTML on this
    page uses <pre> or whitespace-sensitive tags.
    """
    st.markdown(" ".join(html.split()), unsafe_allow_html=True)


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* Hide Streamlit's default menu and footer for an editorial feel */
#MainMenu, footer {visibility: hidden;}

/* Suppress Streamlit's auto-anchor link icon on headings (we use <div>) */
.bf-investor h1 a, .bf-investor h2 a,
.bf-investor h3 a, .bf-investor h4 a {
    display: none !important;
}

/* Cream page background */
[data-testid="stAppViewContainer"], .stApp {
    background: #FAFAF7 !important;
}

:root {
    --bf-fg: #0A0A0A;
    --bf-muted: #6B6B6B;
    --bf-faint: #A8A8A8;
    --bf-border: #E5E5E5;
    --bf-border-soft: #EFEFEF;
    --bf-bg: #FAFAF7;
    --bf-card: #FFFFFF;
    --bf-action: #E8A33D;
    --bf-live: #4A8A5C;
}

/* ── Sticky nav ────────────────────────────────────────────────────── */
.bf-investor-nav {
    position: sticky;
    top: 0;
    z-index: 100;
    background: #FAFAF7;
    border-bottom: 1px solid var(--bf-border-soft);
    margin: -1rem -2rem 0;
}
.bf-investor-nav-inner {
    max-width: 1080px;
    margin: 0 auto;
    padding: 1rem 2rem;
    display: flex;
    align-items: center;
    justify-content: flex-end;
}
.bf-investor-nav-cta,
.bf-investor-nav-cta:link,
.bf-investor-nav-cta:visited,
.bf-investor-nav-cta:active {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    color: #FFFFFF !important;
    background: var(--bf-fg) !important;
    padding: 0.6rem 1.4rem !important;
    border-radius: 999px !important;
    text-decoration: none !important;
    border: 1px solid var(--bf-fg) !important;
    display: inline-block !important;
    transition: background 0.15s ease, opacity 0.15s ease !important;
}
.bf-investor-nav-cta:hover {
    background: #1F1F1F !important;
    color: #FFFFFF !important;
    text-decoration: none !important;
    opacity: 0.92;
}

/* ── Page wrapper ──────────────────────────────────────────────────── */
.bf-investor {
    color: var(--bf-fg);
    font-family: 'Inter', sans-serif;
    line-height: 1.6;
    max-width: 1280px;
    margin: 0 auto;
    padding: 0 1.25rem 4rem;
}

/* ── Hero — two-column with queue mockup ───────────────────────────── */
.bf-hero-grid {
    display: grid;
    grid-template-columns: minmax(420px, 40fr) minmax(560px, 55fr);
    grid-template-areas: "text mockup";
    column-gap: 5%;
    align-items: center;
    padding: 4rem 0 3rem;
}
.bf-hero-text { grid-area: text; }
.bf-hero-mockup { grid-area: mockup; }
.bf-hero-eyebrow {
    font-family: 'Inter', sans-serif;
    text-transform: uppercase;
    font-size: 0.7rem;
    letter-spacing: 0.18em;
    color: var(--bf-faint);
    margin: 0 0 1rem 0;
}
.bf-hero-h1 {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 3rem;
    font-weight: 500;
    line-height: 1.05;
    letter-spacing: -0.02em;
    color: var(--bf-fg);
    margin: 0 0 1.25rem 0;
    /* Constrain so the headline always wraps before "of finished work."
       — keeping the hand-drawn squiggle anchored under that phrase. */
    max-width: 24ch;
}
.bf-squiggle-wrap {
    position: relative;
    display: inline-block;
    white-space: nowrap;
}
.bf-squiggle {
    position: absolute;
    left: 0;
    right: 0;
    bottom: -0.35em;
    width: 100%;
    height: 0.45em;
    color: var(--bf-fg);
    pointer-events: none;
}
.bf-hero-body {
    font-size: 1rem;
    color: var(--bf-muted);
    line-height: 1.65;
    margin: 0 0 1.75rem 0;
}
.bf-hero-ctas {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
    margin-bottom: 0.85rem;
}
.bf-cta-primary,
.bf-cta-primary:link,
.bf-cta-primary:visited,
.bf-cta-primary:active {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    font-weight: 500 !important;
    color: #FFFFFF !important;
    background: var(--bf-fg) !important;
    padding: 0.7rem 1.5rem !important;
    border-radius: 999px !important;
    text-decoration: none !important;
    border: 1px solid var(--bf-fg) !important;
    display: inline-block !important;
    transition: opacity 0.15s ease !important;
}
.bf-cta-primary:hover { opacity: 0.88; color: #FFFFFF !important; text-decoration: none !important; }
.bf-cta-secondary,
.bf-cta-secondary:link,
.bf-cta-secondary:visited,
.bf-cta-secondary:active {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    font-weight: 500 !important;
    color: var(--bf-fg) !important;
    background: transparent !important;
    padding: 0.7rem 1.5rem !important;
    border-radius: 999px !important;
    text-decoration: none !important;
    border: 1px solid var(--bf-fg) !important;
    display: inline-block !important;
    transition: background 0.15s ease !important;
}
.bf-cta-secondary:hover { background: rgba(10,10,10,0.04) !important; color: var(--bf-fg) !important; text-decoration: none !important; }
.bf-hero-caption {
    font-family: 'Playfair Display', Georgia, serif;
    font-style: italic;
    font-size: 0.85rem;
    color: var(--bf-faint);
    margin: 0.35rem 0 0 0;
}

/* ── Queue mockup (right side of hero) ─────────────────────────────── */
.bf-queue-mockup {
    background: #FFFFFF;
    border: 1px solid var(--bf-border);
    border-radius: 4px;
    padding: 1.5rem 1.5rem 0.75rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    overflow: hidden;
}
.bf-queue-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    flex-wrap: wrap;
    padding-bottom: 0.95rem;
    border-bottom: 1px solid var(--bf-border-soft);
}
.bf-queue-date {
    font-family: 'Playfair Display', Georgia, serif;
    font-style: italic;
    font-size: 0.95rem;
    color: var(--bf-fg);
}
.bf-queue-filters { display: flex; gap: 0.4rem; flex-wrap: wrap; }
.bf-queue-filter {
    font-family: 'Inter', sans-serif;
    font-size: 0.62rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--bf-muted);
    background: transparent;
    border: 1px solid var(--bf-border);
    padding: 0.25rem 0.55rem;
    border-radius: 999px;
}
.bf-queue-filter--active {
    color: var(--bf-fg);
    border-color: var(--bf-fg);
    font-weight: 600;
}
.bf-queue-card {
    padding: 0.95rem 0;
    border-bottom: 1px solid var(--bf-border-soft);
}
.bf-queue-card:last-child { border-bottom: none; }
.bf-queue-card-top {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.85rem;
    margin-bottom: 0.5rem;
}
.bf-queue-card-meta {
    display: flex;
    align-items: baseline;
    gap: 0.55rem;
    flex-wrap: wrap;
    flex: 1;
    min-width: 0;
}
.bf-queue-card-tag {
    font-family: 'Inter', sans-serif;
    font-size: 0.62rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--bf-fg);
    background: rgba(10,10,10,0.06);
    padding: 0.18rem 0.45rem;
    border-radius: 3px;
}
.bf-queue-card-context {
    font-size: 0.78rem;
    color: var(--bf-faint);
}
.bf-queue-card-actions {
    display: flex;
    flex-direction: row;
    gap: 0.35rem;
    flex-shrink: 0;
    align-items: flex-start;
}
.bf-queue-card-actions--stack {
    flex-direction: column;
    gap: 0.3rem;
}
.bf-queue-action {
    font-family: 'Inter', sans-serif;
    font-size: 0.68rem;
    font-weight: 600;
    color: var(--bf-fg);
    background: var(--bf-action);
    border: none;
    padding: 0.3rem 0.6rem;
    border-radius: 999px;
    cursor: default;
    white-space: nowrap;
}
.bf-queue-action--ghost {
    background: transparent;
    color: var(--bf-muted);
    padding: 0.3rem 0.5rem;
}
.bf-queue-card-body {
    font-size: 0.82rem;
    color: var(--bf-fg);
    line-height: 1.55;
}
.bf-queue-card-body em {
    font-family: 'Playfair Display', Georgia, serif;
    font-style: italic;
    color: var(--bf-fg);
}

/* ── Section frame ─────────────────────────────────────────────────── */
.bf-investor-section {
    border-top: 1px solid var(--bf-border-soft);
    margin-top: 4rem;
    padding-top: 2.5rem;
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
    max-width: 760px;
    margin: 0 0 0.75rem 0;
}
.bf-investor-sub {
    font-size: 0.95rem;
    color: var(--bf-muted);
    max-width: 720px;
    margin: 0 0 2.25rem 0;
    line-height: 1.65;
}

/* ── Monday morning timeline ───────────────────────────────────────── */
.bf-monday-headline {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.6rem;
    font-weight: 500;
    line-height: 1.3;
    color: var(--bf-fg);
    margin: 0 0 2.5rem 0;
    letter-spacing: -0.01em;
}
.bf-monday-headline-bold { color: var(--bf-fg); font-weight: 600; }
.bf-monday-headline-muted { color: var(--bf-faint); font-weight: 400; }
.bf-monday-row {
    display: grid;
    grid-template-columns: 110px 1fr;
    gap: 1.5rem;
    align-items: baseline;
    padding: 0.9rem 0;
    border-bottom: 1px solid var(--bf-border-soft);
}
.bf-monday-row:last-of-type { border-bottom: none; }
.bf-monday-time {
    font-family: 'JetBrains Mono', 'SF Mono', ui-monospace, monospace;
    font-size: 0.85rem;
    color: var(--bf-muted);
    letter-spacing: 0.02em;
}
.bf-monday-desc {
    font-size: 0.95rem;
    color: var(--bf-fg);
    line-height: 1.55;
}
.bf-monday-callout {
    font-family: 'Playfair Display', Georgia, serif;
    font-style: italic;
    font-size: 1.4rem;
    color: var(--bf-fg);
    margin: 2.5rem 0 0 0;
    line-height: 1.35;
}

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

/* ── Agents — orchestration diagram + grid ─────────────────────────── */
.bf-investor-orch {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0;
    margin: 0.75rem 0 1.5rem;
    padding: 0 0.5rem;
}
.bf-investor-orch-node {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 0 0 auto;
    min-width: 60px;
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
    position: relative;
}
.bf-investor-agent--soon { opacity: 0.7; }
.bf-investor-agent-status {
    position: absolute;
    top: 0.85rem;
    right: 0.95rem;
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-family: 'Inter', sans-serif;
    font-size: 0.62rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--bf-faint);
}
.bf-investor-agent-status-dot {
    width: 6px;
    height: 6px;
    border-radius: 99px;
    background: var(--bf-faint);
    border: 1px solid var(--bf-faint);
}
.bf-investor-agent-status--live .bf-investor-agent-status-dot {
    background: var(--bf-live);
    border-color: var(--bf-live);
}
.bf-investor-agent-title {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--bf-fg);
    margin: 0 0 0.5rem 0;
    padding-right: 5rem;
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

/* ── Stack hero columns on tablet + mobile (<1024px) ───────────────── */
@media (max-width: 1023px) {
    .bf-hero-grid {
        grid-template-columns: 1fr;
        grid-template-areas: "text" "mockup";
        row-gap: 2.5rem;
        padding: 3rem 0 2rem;
    }
    .bf-hero-mockup { min-width: 100%; }
}

@media (max-width: 720px) {
    .bf-investor-nav-inner { padding: 1rem 1.25rem; }
    .bf-hero-grid { padding: 2.5rem 0 1rem; row-gap: 2rem; }
    .bf-hero-h1 { font-size: 2.25rem; max-width: none; }
    .bf-monday-headline { font-size: 1.3rem; }
    .bf-monday-row { grid-template-columns: 80px 1fr; gap: 0.75rem; }
    .bf-investor-h2 { font-size: 1.5rem; }
    .bf-investor-agents { grid-template-columns: 1fr; }
    .bf-investor-orch { display: none; }
    .bf-queue-card-top { flex-direction: column; align-items: flex-start; }
    .bf-queue-card-actions { flex-direction: row; }
    .bf-queue-card-actions--stack { flex-direction: row; }
}
</style>
"""


# ── SVG squiggle for the hand-drawn underline on "finished work" ─────────
_SQUIGGLE_SVG = (
    '<svg class="bf-squiggle" viewBox="0 0 200 12" preserveAspectRatio="none">'
    '<path d="M2,7 Q12,1 22,7 T42,7 T62,7 T82,7 T102,7 T122,7 T142,7 T162,7 T182,7 T198,7" '
    'stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>'
    '</svg>'
)


def _render_nav() -> None:
    _md("""
    <header class="bf-investor-nav">
      <div class="bf-investor-nav-inner">
        <a class="bf-investor-nav-cta" href="?goto=app" target="_self">I'm a broker &rarr;</a>
      </div>
    </header>
    """)


def _render_hero() -> None:
    _md(f"""
    <div class="bf-investor">
      <section class="bf-hero-grid">
        <div class="bf-hero-text">
          <div class="bf-hero-eyebrow">An AI workforce for CPG brokers</div>
          <div class="bf-hero-h1">
            Wake up to a queue<br>of
            <span class="bf-squiggle-wrap">finished work{_SQUIGGLE_SVG}</span>.
          </div>
          <p class="bf-hero-body">
            BrokerFlow runs end-to-end brand management for brokers. Agents
            draft the emails, file the disputes, fill the forms, chase the
            shippers. You swipe approve.
          </p>
          <div class="bf-hero-ctas">
            <a class="bf-cta-primary" href="?goto=app" target="_self">I'm a broker &rarr;</a>
            <a class="bf-cta-secondary" href="#bf-monday-morning">See a Monday morning &rarr;</a>
          </div>
          <p class="bf-hero-caption">
            &darr; This is the whole product. One column. One swipe per card.
          </p>
        </div>
        <div class="bf-hero-mockup">
          <div class="bf-queue-mockup">
            <div class="bf-queue-header">
              <div class="bf-queue-date">Today &middot; 20 cards</div>
              <div class="bf-queue-filters">
                <span class="bf-queue-filter">All</span>
                <span class="bf-queue-filter bf-queue-filter--active">Needs you &middot; 6</span>
                <span class="bf-queue-filter">Drafted &middot; 14</span>
              </div>
            </div>

            <div class="bf-queue-card">
              <div class="bf-queue-card-top">
                <div class="bf-queue-card-meta">
                  <span class="bf-queue-card-tag">Pitch</span>
                  <span class="bf-queue-card-context">Costco NW &middot; Brand X</span>
                </div>
                <div class="bf-queue-card-actions bf-queue-card-actions--stack">
                  <button class="bf-queue-action">Approve</button>
                  <button class="bf-queue-action bf-queue-action--ghost">Edit</button>
                  <button class="bf-queue-action bf-queue-action--ghost">Skip</button>
                </div>
              </div>
              <div class="bf-queue-card-body">
                <em>&ldquo;Costco NW just confirmed Brand X for 142 stores.&rdquo;</em>
                Drafted the follow-up to the buyer with launch terms, demo plan,
                and first PO timing. Reorder window opens in 14 days.
              </div>
            </div>

            <div class="bf-queue-card">
              <div class="bf-queue-card-top">
                <div class="bf-queue-card-meta">
                  <span class="bf-queue-card-tag">New brand</span>
                  <span class="bf-queue-card-context">Scout &middot; Faire signal</span>
                </div>
                <div class="bf-queue-card-actions">
                  <button class="bf-queue-action">Review verdict</button>
                </div>
              </div>
              <div class="bf-queue-card-body">
                Found a new olive oil brand trending 4.2&times; on Faire and
                Instacart with clean promo independence. Scored 87/100. Drafted
                intro email and one-pager for your next outbound batch.
              </div>
            </div>

            <div class="bf-queue-card">
              <div class="bf-queue-card-top">
                <div class="bf-queue-card-meta">
                  <span class="bf-queue-card-tag">New item</span>
                  <span class="bf-queue-card-context">Whole Foods &middot; Brand Y</span>
                </div>
                <div class="bf-queue-card-actions">
                  <button class="bf-queue-action">Review fields</button>
                </div>
              </div>
              <div class="bf-queue-card-body">
                <em>&ldquo;Whole Foods accepted 6 new SKUs for Brand Y.&rdquo;</em>
                UNFI new-item forms filled and ready. 4 fields need confirmation.
                1 cert expires in 31 days.
              </div>
            </div>

            <div class="bf-queue-card">
              <div class="bf-queue-card-top">
                <div class="bf-queue-card-meta">
                  <span class="bf-queue-card-tag">Demo</span>
                  <span class="bf-queue-card-context">CDS &middot; Sue</span>
                </div>
                <div class="bf-queue-card-actions">
                  <button class="bf-queue-action">Send</button>
                </div>
              </div>
              <div class="bf-queue-card-body">
                3 demos in TX have CDS confirmation but no billing 5 days past
                expected. Drafted email asking where the invoice is.
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
    """)


def _render_monday_morning() -> None:
    _md("""
    <div class="bf-investor">
      <section class="bf-investor-section" id="bf-monday-morning">
        <div class="bf-investor-eyebrow">A Monday morning with BrokerFlow</div>
        <div class="bf-monday-headline">
          <span class="bf-monday-headline-bold">8:00am.</span>
          <span class="bf-monday-headline-muted">
            Overnight: 73 emails, 12 chargebacks, 2 stockouts.
          </span>
        </div>

        <div class="bf-monday-row">
          <div class="bf-monday-time">8:00 am</div>
          <div class="bf-monday-desc">
            Open BrokerFlow. One column of cards, ranked by what needs human judgment.
          </div>
        </div>
        <div class="bf-monday-row">
          <div class="bf-monday-time">8:12 am</div>
          <div class="bf-monday-desc">
            First five cards: approve, approve, edit-and-send, approve, skip.
          </div>
        </div>
        <div class="bf-monday-row">
          <div class="bf-monday-time">8:30 am</div>
          <div class="bf-monday-desc">
            Bulk-approve eight chargeback disputes. File.
          </div>
        </div>
        <div class="bf-monday-row">
          <div class="bf-monday-time">8:45 am</div>
          <div class="bf-monday-desc">
            Twenty pieces of work are out the door.
          </div>
        </div>
        <div class="bf-monday-row">
          <div class="bf-monday-time">9:00 am</div>
          <div class="bf-monday-desc">
            Get on a call with a buyer. Walk a store. Be where you&rsquo;re irreplaceable.
          </div>
        </div>

        <p class="bf-monday-callout">
          Last Monday, this was 6 hours of work.
        </p>
      </section>
    </div>
    """)


def _agent_card(name: str, desc: str, tag: str, status: str) -> str:
    """Return one agent card. status: 'live' or 'soon'."""
    soon_class = " bf-investor-agent--soon" if status == "soon" else ""
    status_class = (
        "bf-investor-agent-status bf-investor-agent-status--live"
        if status == "live"
        else "bf-investor-agent-status"
    )
    status_label = "Live" if status == "live" else "Coming soon"
    return (
        f'<div class="bf-investor-card bf-investor-agent{soon_class}">'
        f'<div class="{status_class}">'
        f'<span class="bf-investor-agent-status-dot"></span>{status_label}'
        f'</div>'
        f'<div class="bf-investor-agent-title">{name}</div>'
        f'<p class="bf-investor-agent-desc">{desc}</p>'
        f'<p class="bf-investor-agent-tag">{tag}</p>'
        f'</div>'
    )


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

    cards = [
        ("Brand Scout",      "Research + score 0&ndash;100",       "ReAct loop",          "live"),
        ("Retailer Pitcher", "Drafts email + sell sheet",          "Parallel + interrupt", "live"),
        ("New Item Forms",   "Fills new-item form",                "Rules + LLM gaps",     "live"),
        ("Brand Onboarding", "Docs &rarr; canonical record",       "6-node linear",        "soon"),
        ("Retailer Matcher", "Picks a buyer",                      "Heuristic",            "soon"),
        ("+ more soon",      "PO Processing, Trade Spend, Accruals&hellip;",
                             "12 on the roadmap",                                          "soon"),
    ]
    cards_html = "".join(_agent_card(n, d, t, s) for n, d, t, s in cards)

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

        <div class="bf-investor-agents">{cards_html}</div>
      </section>
    </div>
    """)


def _render_bottom_padding() -> None:
    _md('<div class="bf-investor" style="padding-bottom:6rem;"></div>')


def render_investor_landing() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    _render_nav()
    _render_hero()
    _render_monday_morning()
    _render_agents()
    _render_bottom_padding()
