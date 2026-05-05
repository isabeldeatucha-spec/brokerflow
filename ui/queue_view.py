"""Queue view — the default landing page after 'I'm a broker'.

Renders the stack of cards inside the shared broker shell. Cards collapse /
expand inline. All actions (Approve & send, Send, Skip) are visual only
for v1 — they update session-state counters that the sidebar reads.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import streamlit as st


def _esc(s: str) -> str:
    """Escape characters Streamlit's markdown parser steals from us:
    $ (LaTeX delimiter)."""
    return s.replace("$", "&#36;")


# ── Seed data ────────────────────────────────────────────────────────────────

@dataclass
class ReasoningBullet:
    text: str
    source: str  # "LEDGER" | "EVENTS" | "INBOX" | ""


@dataclass
class Card:
    id: str
    type: str            # "EMAIL" | "FOLLOW-UP" | "OPPORTUNITY" | "NEW BRAND"
    needs_you: bool
    context: str         # "Costco SE · Marcus"
    elapsed: str         # "2m"
    summary_html: str    # 1-2 sentences with <b>...</b> bolded numbers
    primary_action: str  # button label
    skip_label: str = "Skip"
    brand: str = ""      # filter key (matches sidebar BROKER_BRANDS)

    # Expanded view
    from_email: str = ""
    from_body: str = ""
    drafted_to: str = ""
    drafted_subject: str = ""
    drafted_body: str = ""
    drafted_label: str = "DRAFTED REPLY"  # or "DRAFTED ACTION"
    reasoning: list[ReasoningBullet] = field(default_factory=list)


SEED_CARDS: list[Card] = [
    Card(
        id="card-1",
        type="RETAILER PITCHER",
        needs_you=True,
        context="Costco NW · Marcus",
        elapsed="2m",
        summary_html=(
            "Drafted pitch for <b>Brami</b> to Costco NW. Lupini snacks "
            "indexing <b>3.1×</b> on Faire in PNW + clean promo "
            "independence. Sell sheet attached, proposing <b>142-store "
            "rollout</b> pegged to May reset."
        ),
        primary_action="Approve & send",
        brand="Brami",
        drafted_label="DRAFTED PITCH",
        drafted_to="marcus.alvarez@costco.com",
        drafted_subject="Brami × Costco NW — May reset, 142 stores",
        drafted_body=(
            "Hi Marcus,\n\n"
            "Bringing Brami to you for the May reset. Lupini bean snacks "
            "are indexing 3.1× on Faire across the PNW over the last 90 "
            "days, with no promo dependency in the velocity curve — "
            "rare for the category.\n\n"
            "Proposing the full 142-store NW footprint, sea salt + "
            "garlic SKUs, $1.99 intro for the first 6 weeks. Margin "
            "structure holds at 32% retailer margin even with the "
            "intro pricing.\n\n"
            "Sell sheet + cost build attached. Happy to walk through "
            "anytime this week — the May reset window closes 5/14.\n\n"
            "— Nadia"
        ),
        reasoning=[
            ReasoningBullet(
                "Faire 90-day velocity: 3.1× category baseline in PNW",
                "EVENTS",
            ),
            ReasoningBullet(
                "Promo independence score: 0.91 (clean — velocity holds without TPRs)",
                "EVENTS",
            ),
            ReasoningBullet(
                "Costco NW open SKU slots: 142 stores, 2 SKU max per brand",
                "LEDGER",
            ),
            ReasoningBullet(
                "Marcus's May reset deadline: 5/14 (locked window)",
                "INBOX",
            ),
            ReasoningBullet(
                "Margin model: $1.99 intro → 32% retailer margin (passes Costco threshold)",
                "",
            ),
            ReasoningBullet(
                "Marcus accepted 4 of last 6 pitches Nadia ran with this structure",
                "INBOX",
            ),
        ],
    ),
    Card(
        id="card-2",
        type="BRAND SCOUT",
        needs_you=True,
        context="Faire signal",
        elapsed="4h",
        summary_html=(
            "Found a new <b>sparkling tea brand</b> trending <b>4.2×</b> "
            "on Faire and Instacart with clean promo independence. "
            "Scored <b>87/100 — Broker Ready</b>. Drafted intro email "
            "and one-pager for your next outbound batch."
        ),
        primary_action="Review verdict",
        brand="",
        drafted_label="DRAFTED ACTION",
        drafted_to="founders@steepsparkling.co",
        drafted_subject="Steep Sparkling × Nadia — quick intro",
        drafted_body=(
            "Hey team,\n\n"
            "Came across Steep Sparkling on Faire — your Q1 trajectory "
            "is in the top 5% of beverage SKUs we track, with clean "
            "promo independence and the velocity story holding up "
            "across Faire and Instacart.\n\n"
            "I work with a handful of brands in your category and would "
            "love 15 minutes to see whether broker representation makes "
            "sense for where you're going next quarter.\n\n"
            "— Nadia"
        ),
        reasoning=[
            ReasoningBullet(
                "Velocity proof: 22/25 — top 5% Faire beverage, 4.2× category baseline",
                "EVENTS",
            ),
            ReasoningBullet(
                "Distribution density: 16/20 — Faire + Instacart + 11 indie shops",
                "EVENTS",
            ),
            ReasoningBullet(
                "Margin viability: 14/20 — 38% retailer margin holds at SRP $4.99",
                "",
            ),
            ReasoningBullet(
                "Brand story clarity: 18/20 — single-origin sourcing + functional claim",
                "",
            ),
            ReasoningBullet(
                "Promo independence: 17/15 (capped) — 0.94 score, no TPR dependency",
                "EVENTS",
            ),
            ReasoningBullet(
                "Composite: 87/100 — Broker Ready (45–69 = ready, 70+ = established)",
                "",
            ),
            ReasoningBullet(
                "Broker representation gap: no broker of record in CA / NW yet",
                "EVENTS",
            ),
        ],
    ),
    Card(
        id="card-3",
        type="NEW ITEM FORMS",
        needs_you=False,
        context="Whole Foods · Olipop",
        elapsed="12m",
        summary_html=(
            "Whole Foods accepted <b>6 new SKUs</b> for Olipop. UNFI "
            "new-item forms filled and ready. <b>4 fields need "
            "confirmation</b>. <b>1 cert expires in 31 days</b>."
        ),
        primary_action="Review fields",
        brand="Olipop",
        drafted_label="FORMS DRAFTED",
        drafted_to="UNFI new-item portal — Olipop, 6 SKUs",
        drafted_subject="Olipop · Whole Foods · 6 SKUs · UNFI form package",
        drafted_body=(
            "Form package ready for review:\n\n"
            "  • Olipop Strawberry Vanilla 12oz — auto-filled (38/38 fields)\n"
            "  • Olipop Vintage Cola 12oz — auto-filled (38/38 fields)\n"
            "  • Olipop Cherry Vanilla 12oz — auto-filled (38/38 fields)\n"
            "  • Olipop Orange Cream 12oz — auto-filled (38/38 fields)\n"
            "  • Olipop Banana Cream 12oz — needs confirmation (4 fields)\n"
            "  • Olipop Doctor Goodwin 12oz — auto-filled (38/38 fields)\n\n"
            "Outstanding on Banana Cream:\n"
            "  • Case pack dimensions (carton L×W×H)\n"
            "  • Pallet ti/hi configuration\n"
            "  • Slotting fee acceptance ($1,200/SKU)\n"
            "  • FOB origin confirmation\n\n"
            "⚠ Organic certificate on file expires 6/5 — request renewal "
            "from brand before submitting package."
        ),
        reasoning=[
            ReasoningBullet(
                "Whole Foods accepted 6 SKUs in 4/29 category review meeting",
                "EVENTS",
            ),
            ReasoningBullet(
                "UNFI new-item template v3.2 (current as of 4/15)",
                "LEDGER",
            ),
            ReasoningBullet(
                "Olipop canonical record: 32 of 38 fields complete per SKU",
                "LEDGER",
            ),
            ReasoningBullet(
                "Banana Cream missing 4 fields — newest SKU, packaging not yet finalized",
                "LEDGER",
            ),
            ReasoningBullet(
                "Organic cert on file: USDA #1247-A, expires 2026-06-05 (31 days)",
                "LEDGER",
            ),
            ReasoningBullet(
                "Whole Foods set fee window opens 5/12 — 7 days to package + submit",
                "EVENTS",
            ),
        ],
    ),
    Card(
        id="card-4",
        type="RETAILER PITCHER",
        needs_you=False,
        context="Sprouts · Danielle",
        elapsed="3h",
        summary_html=(
            "Drafted FY27 renewal pitch for <b>Spudsy</b> at same "
            "<b>$126/pallet</b> rate as FY26. Sprouts BA volume up "
            "<b>18% YoY</b> — flagging room to push for higher rate at "
            "next review."
        ),
        primary_action="Approve & send",
        brand="Spudsy",
        drafted_label="DRAFTED PITCH",
        drafted_to="danielle.ortiz@sprouts.com",
        drafted_subject="Spudsy FY27 renewal — Sprouts BA",
        drafted_body=(
            "Hi Danielle,\n\n"
            "Holding the Spudsy pallet rate at $126 for FY27 in the BA "
            "region — same as FY26. Spudsy BA volume is up 18% YoY so "
            "we're comfortable carrying the rate flat into next year.\n\n"
            "Quick note: with the volume trajectory we're seeing, the "
            "next category review (Q3) is probably the right window to "
            "revisit pricing — happy to bring data when we get there.\n\n"
            "Send the agreement and we'll countersign same week.\n\n"
            "— Nadia"
        ),
        reasoning=[
            ReasoningBullet("FY26 BA pallet rate: $126/pallet", "LEDGER"),
            ReasoningBullet(
                "Spudsy BA YoY pallet volume growth: +18% (rolling 12mo)",
                "EVENTS",
            ),
            ReasoningBullet(
                "Comparable region (NW Spudsy) renewed at $134 last quarter",
                "EVENTS",
            ),
            ReasoningBullet(
                "Sprouts Q3 category review window: 7/14–7/28 (next pricing lever)",
                "EVENTS",
            ),
            ReasoningBullet(
                "Danielle's avg renewal-cycle response time: 2 days",
                "INBOX",
            ),
        ],
    ),
    Card(
        id="card-5",
        type="BRAND SCOUT",
        needs_you=False,
        context="Instacart signal",
        elapsed="1h",
        summary_html=(
            "Tracked a new <b>functional snack brand</b> spiking "
            "<b>6×</b> on Instacart over 30 days. Scored "
            "<b>72/100 — Worth a Look</b>. Margins thin but velocity "
            "exceptional. Drafted summary for your review."
        ),
        primary_action="Review verdict",
        brand="",
        drafted_label="DRAFTED SUMMARY",
        drafted_to="Internal — Brand Scout note · Stride Bites",
        drafted_subject="Stride Bites — high velocity, thin margin",
        drafted_body=(
            "New brand surfaced via Instacart 30-day spike monitor:\n\n"
            "Stride Bites — functional protein cookies, hitting 6× "
            "category baseline on Instacart over the last 30 days. "
            "Velocity story is exceptional but margin profile is "
            "tight: 24% retailer margin at SRP $5.49, below the 28% "
            "threshold most of your retailers want.\n\n"
            "Verdict: Worth a Look (72/100). Recommend a 15-min call "
            "with the brand before pitching — if they have flexibility "
            "to land at $5.99 SRP, the margin clears and velocity story "
            "carries the rest.\n\n"
            "Want me to draft an intro email?"
        ),
        reasoning=[
            ReasoningBullet(
                "Velocity proof: 24/25 — 6× Instacart category baseline (30-day)",
                "EVENTS",
            ),
            ReasoningBullet(
                "Distribution density: 11/20 — Instacart + DTC only, no shelf yet",
                "EVENTS",
            ),
            ReasoningBullet(
                "Margin viability: 9/20 — 24% retailer margin (below 28% threshold)",
                "",
            ),
            ReasoningBullet(
                "Brand story clarity: 16/20 — clear functional claim, weak founder narrative",
                "",
            ),
            ReasoningBullet(
                "Promo independence: 12/15 — slight TPR dependency in week-over-week curve",
                "EVENTS",
            ),
            ReasoningBullet(
                "Composite: 72/100 — Worth a Look (margin gap is the swing factor)",
                "",
            ),
        ],
    ),
    Card(
        id="card-6",
        type="NEW ITEM FORMS",
        needs_you=False,
        context="KeHE · Tia Lupita",
        elapsed="6h",
        summary_html=(
            "KeHE new-item form for <b>Tia Lupita salsa</b> drafted. "
            "<b>38 of 42 fields</b> auto-filled from canonical brand "
            "record. Outstanding: case pack dimensions, slotting fee "
            "acceptance, FOB origin, broker code."
        ),
        primary_action="Review fields",
        brand="Tia Lupita",
        drafted_label="FORM DRAFTED",
        drafted_to="KeHE new-item portal — Tia Lupita salsa verde 16oz",
        drafted_subject="Tia Lupita · KeHE · salsa verde 16oz · 38/42 filled",
        drafted_body=(
            "KeHE form draft ready (template v4.1, current):\n\n"
            "Auto-filled from canonical record (38 fields):\n"
            "  • Brand identity, contact, certs, cost build, retail margin\n"
            "  • Nutrition panel, allergen flags, ingredient deck\n"
            "  • UPC/GTIN, SCC, country of origin, gross/net weight\n\n"
            "Outstanding (4 fields — need brand confirmation):\n"
            "  • Case pack dimensions (carton L×W×H, gross weight)\n"
            "  • Slotting fee acceptance ($800/SKU per KeHE schedule)\n"
            "  • FOB origin (port of entry vs. domestic copacker)\n"
            "  • Broker code assignment (Nadia: BR-NA-0241)\n\n"
            "Submit window: KeHE Q2 set fee opens 5/19, closes 5/30."
        ),
        reasoning=[
            ReasoningBullet(
                "KeHE new-item template v4.1 — refreshed 4/22",
                "LEDGER",
            ),
            ReasoningBullet(
                "Tia Lupita canonical record: 38 of 42 KeHE-required fields complete",
                "LEDGER",
            ),
            ReasoningBullet(
                "Missing fields are co-packer dependent — last refresh 11mo ago",
                "LEDGER",
            ),
            ReasoningBullet(
                "KeHE Q2 set fee window: 5/19–5/30 (next submission opportunity)",
                "EVENTS",
            ),
            ReasoningBullet(
                "Slotting fee schedule: $800/SKU (KeHE Q2 rate card)",
                "LEDGER",
            ),
        ],
    ),
]


# ── Filtering ────────────────────────────────────────────────────────────────

def _filter_cards(filter_key: str, brand: Optional[str]) -> list[Card]:
    sent = st.session_state.get("queue_sent_ids", set())
    skipped = st.session_state.get("queue_skipped_ids", set())

    if filter_key == "sent":
        return [c for c in SEED_CARDS if c.id in sent]
    if filter_key == "skipped":
        return [c for c in SEED_CARDS if c.id in skipped]

    cards = [c for c in SEED_CARDS if c.id not in sent and c.id not in skipped]

    if filter_key == "needs_you":
        cards = [c for c in cards if c.needs_you]
    if filter_key == "drafted":
        cards = [c for c in cards if not c.needs_you]
    if brand:
        cards = [c for c in cards if c.brand == brand]
    return cards


def _filter_label(filter_key: str, brand: Optional[str]) -> str:
    if brand:
        return brand
    return {
        "today":     "Today",
        "needs_you": "Needs you",
        "drafted":   "Drafted",
        "sent":      "Sent",
        "skipped":   "Skipped",
    }.get(filter_key, "Today")


# ── Page-scoped CSS ──────────────────────────────────────────────────────────

_QUEUE_CSS = """
<style>
/* ── Ask BrokerFlow bar — full-width pill styled st.text_input ──── */
div[data-testid="stLayoutWrapper"]:has(.bf-ask-marker) {
    border: none !important;
    background: transparent !important;
    padding: 0 !important;
    margin: 0 0 14px !important;
    box-shadow: none !important;
    position: relative;
}
div[data-testid="stLayoutWrapper"]:has(.bf-ask-marker) > div[data-testid="stVerticalBlock"] {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
    gap: 0 !important;
}
div[data-testid="stLayoutWrapper"]:has(.bf-ask-marker) .stTextInput input {
    width: 100% !important;
    background: #FFFFFF !important;
    border: 1px solid #EAEAE4 !important;
    border-radius: 999px !important;
    padding: 14px 70px 14px 22px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    color: #1A1A18 !important;
    box-shadow: none !important;
}
div[data-testid="stLayoutWrapper"]:has(.bf-ask-marker) .stTextInput input::placeholder {
    color: #A8A8A8 !important;
    -webkit-text-fill-color: #A8A8A8 !important;
}
div[data-testid="stLayoutWrapper"]:has(.bf-ask-marker) .stTextInput input:focus {
    border-color: #1A1A18 !important;
    outline: none !important;
}
div[data-testid="stLayoutWrapper"]:has(.bf-ask-marker)::after {
    content: "⌘K";
    position: absolute;
    right: 22px;
    top: 50%;
    transform: translateY(-50%);
    font-family: 'JetBrains Mono', 'SF Mono', monospace;
    font-size: 11px;
    color: #8B8A83;
    background: #F2F2EE;
    padding: 4px 9px;
    border-radius: 6px;
    pointer-events: none;
    z-index: 1;
}

/* ── Ask response card ──────────────────────────────────────────── */
.bf-ask-response {
    background: #FFFFFF;
    border: 1px solid #EAEAE4;
    border-radius: 12px;
    padding: 24px 26px 20px;
    margin: 12px 0 28px;
}
.bf-ask-response-head {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
}
.bf-ask-response-brand {
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #1A1A18;
}
.bf-ask-response-spark {
    color: #E8A33D;
    font-size: 13px;
    line-height: 1;
}
.bf-ask-response-body {
    font-family: 'Instrument Serif', Georgia, serif;
    font-size: 17px;
    line-height: 1.65;
    color: #1A1A18;
}
.bf-ask-response-body p { margin: 0 0 14px; font-size: inherit; color: inherit; }
.bf-ask-response-body p:last-child { margin-bottom: 0; }
.bf-ask-response-body ol {
    padding-left: 22px;
    margin: 0 0 16px;
}
.bf-ask-response-body li {
    font-family: 'Instrument Serif', Georgia, serif;
    font-size: 16px;
    color: #1A1A18;
    line-height: 1.6;
    margin-bottom: 12px;
}
.bf-ask-response-body li b,
.bf-ask-response-body p b {
    font-weight: 500;
    color: #1A1A18;
}
.bf-ask-response-body a,
.bf-ask-response-body a:link {
    color: #B07A1C;
    text-decoration: none;
    font-weight: 500;
}
.bf-ask-response-body a:hover { text-decoration: underline; }
.bf-ask-response-foot {
    margin-top: 16px;
    padding-top: 14px;
    border-top: 1px solid #F2F2EE;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #8B8A83;
    letter-spacing: 0.04em;
}
.bf-ask-dismiss,
.bf-ask-dismiss:link {
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    color: #8B8A83;
    text-decoration: none;
    letter-spacing: 0;
}
.bf-ask-dismiss:hover { color: #1A1A18; }

.bf-queue-section-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin: 6px 0 22px;
}
.bf-queue-h {
    font-family: 'Instrument Serif', Georgia, serif;
    font-size: 30px;
    font-weight: 400;
    color: #1A1A18;
    letter-spacing: -0.01em;
    margin: 0;
}
.bf-queue-h-count { color: #B0AFA8; font-weight: 400; }

.bf-queue-pills {
    display: flex;
    gap: 8px;
}
.bf-queue-pill,
.bf-queue-pill:link,
.bf-queue-pill:visited {
    font-family: 'Inter', sans-serif;
    font-size: 11.5px;
    font-weight: 500;
    letter-spacing: 0.04em;
    padding: 6px 12px;
    border-radius: 999px;
    border: 1px solid #EAEAE4;
    color: #57564F;
    background: transparent;
    text-decoration: none;
    text-transform: uppercase;
    transition: all 0.12s ease;
}
.bf-queue-pill:hover { border-color: #1A1A18; color: #1A1A18; }
.bf-queue-pill--active {
    background: #1A1A18 !important;
    color: #FAFAF7 !important;
    border-color: #1A1A18 !important;
}

/* ── Card (uses Streamlit st.container(border=True) wrapper) ──────────
   Streamlit renders bordered containers as
   div[data-testid="stVerticalBlockBorderWrapper"]. We use vertical-block
   adjacency to scope the border styling to the queue. Each card's
   contents include a hidden marker that flips expanded styling. */
div[data-testid="stLayoutWrapper"]:has(.bf-card-marker) {
    background: #FAFAF7 !important;
    border: 1px solid #EAEAE4 !important;
    border-radius: 10px !important;
    padding: 18px 20px !important;
    margin: 0 0 14px !important;
    transition: border-color 0.12s ease !important;
    box-shadow: none !important;
}
div[data-testid="stLayoutWrapper"]:has(.bf-card-marker):hover {
    border-color: #D6D6D2 !important;
}
div[data-testid="stLayoutWrapper"]:has(.bf-card-marker--expanded) {
    border-color: #1A1A18 !important;
    background: #FFFFFF !important;
}
/* Strip Streamlit's inner stVerticalBlock border + padding inside our cards */
div[data-testid="stLayoutWrapper"]:has(.bf-card-marker) > div[data-testid="stVerticalBlock"] {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
}

.bf-card-top {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 10px;
}
.bf-tagrow {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}
.bf-tag {
    font-family: 'Inter', sans-serif;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #1A1A18;
    background: #F2F2EE;
    padding: 3px 8px;
    border-radius: 4px;
}
.bf-tag--needs {
    background: #FBE9E7;
    color: #B23A22;
}
.bf-context {
    font-family: 'Inter', sans-serif;
    font-size: 12.5px;
    color: #8B8A83;
}
.bf-elapsed {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11.5px;
    color: #B0AFA8;
}

.bf-card-summary,
.bf-summary-toggle,
.bf-summary-toggle:link,
.bf-summary-toggle:visited {
    font-family: 'Inter', sans-serif;
    font-size: 14.5px;
    line-height: 1.55;
    color: #1A1A18;
    text-decoration: none;
    display: block;
    margin: 0 0 4px;
}
.bf-summary-toggle b { font-weight: 600; color: #1A1A18; }
.bf-summary-toggle:hover { color: #1A1A18; }

div[data-testid="stLayoutWrapper"]:has(.bf-card-marker--expanded) .bf-card-summary {
    border-left: 3px solid #2D5F8A;
    padding-left: 14px;
    margin: 6px 0 22px;
}

.bf-show-reasoning,
.bf-show-reasoning:link,
.bf-show-reasoning:visited {
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    color: #8B8A83;
    text-decoration: none;
    margin-top: 6px;
    display: inline-block;
}
.bf-show-reasoning:hover {
    color: #1A1A18;
    text-decoration: underline;
}

/* Expanded blocks */
.bf-block-h {
    font-family: 'Inter', sans-serif;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #8B8A83;
    margin: 22px 0 8px;
}
.bf-from {
    background: #F4F4EF;
    border: 1px solid #EAEAE4;
    border-radius: 8px;
    padding: 14px 16px;
    font-family: 'Inter', sans-serif;
    font-size: 13.5px;
    color: #57564F;
    line-height: 1.55;
    white-space: pre-wrap;
}
.bf-draft-wrap {
    border: 1px solid #EAEAE4;
    border-radius: 8px;
    background: #FFFFFF;
    overflow: hidden;
}
.bf-draft-subject {
    font-family: 'Inter', sans-serif;
    font-size: 13.5px;
    font-weight: 600;
    color: #1A1A18;
    background: #FAFAF7;
    border-bottom: 1px solid #EAEAE4;
    padding: 10px 16px;
}
.bf-draft-body {
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    color: #1A1A18;
    line-height: 1.6;
    padding: 16px;
    white-space: pre-wrap;
}

.bf-reasoning {
    list-style: none;
    padding: 0;
    margin: 0;
}
.bf-reasoning li {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    padding: 8px 0;
    border-bottom: 1px solid #F2F2EE;
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    color: #1A1A18;
}
.bf-reasoning li:last-child { border-bottom: none; }
.bf-reasoning .bf-reason-text { line-height: 1.55; }
.bf-reasoning .bf-reason-text u {
    text-decoration: underline;
    text-decoration-color: #D6D6D2;
    text-underline-offset: 2px;
}
.bf-reason-src {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    color: #8B8A83;
    letter-spacing: 0.06em;
    white-space: nowrap;
    flex-shrink: 0;
    margin-top: 2px;
}

/* Queue action buttons — scoped to bordered card containers via :has().
   Streamlit's data-testid is "stButton" with no key suffix, so we use
   button[kind=primary|secondary|tertiary] instead. */
div[data-testid="stLayoutWrapper"]:has(.bf-card-marker) div[data-testid="stButton"] > button {
    font-family: 'Inter', sans-serif !important;
    font-size: 12.5px !important;
    font-weight: 500 !important;
    border-radius: 999px !important;
    padding: 7px 14px !important;
    box-shadow: none !important;
    transition: all 0.12s ease !important;
}

/* Primary (Approve & send / Send / Draft / Review) — mustard pill */
div[data-testid="stLayoutWrapper"]:has(.bf-card-marker) div[data-testid="stButton"] > button[kind="primary"] {
    background: #E8A33D !important;
    background-color: #E8A33D !important;
    color: #1A1A18 !important;
    -webkit-text-fill-color: #1A1A18 !important;
    border: 1px solid #E8A33D !important;
}
div[data-testid="stLayoutWrapper"]:has(.bf-card-marker) div[data-testid="stButton"] > button[kind="primary"] p,
div[data-testid="stLayoutWrapper"]:has(.bf-card-marker) div[data-testid="stButton"] > button[kind="primary"] span {
    color: #1A1A18 !important;
    -webkit-text-fill-color: #1A1A18 !important;
}
div[data-testid="stLayoutWrapper"]:has(.bf-card-marker) div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #D89530 !important;
    background-color: #D89530 !important;
    border-color: #D89530 !important;
}

/* Secondary (Edit) — outlined ghost */
div[data-testid="stLayoutWrapper"]:has(.bf-card-marker) div[data-testid="stButton"] > button[kind="secondary"] {
    background: transparent !important;
    background-color: transparent !important;
    color: #57564F !important;
    -webkit-text-fill-color: #57564F !important;
    border: 1px solid #D6D6D2 !important;
}
div[data-testid="stLayoutWrapper"]:has(.bf-card-marker) div[data-testid="stButton"] > button[kind="secondary"] p,
div[data-testid="stLayoutWrapper"]:has(.bf-card-marker) div[data-testid="stButton"] > button[kind="secondary"] span {
    color: #57564F !important;
    -webkit-text-fill-color: #57564F !important;
}
div[data-testid="stLayoutWrapper"]:has(.bf-card-marker) div[data-testid="stButton"] > button[kind="secondary"]:hover {
    background: #F2F2EE !important;
    background-color: #F2F2EE !important;
    border-color: #1A1A18 !important;
    color: #1A1A18 !important;
    -webkit-text-fill-color: #1A1A18 !important;
}

/* Tertiary (Skip) — text-only muted */
div[data-testid="stLayoutWrapper"]:has(.bf-card-marker) div[data-testid="stButton"] > button[kind="tertiary"] {
    background: transparent !important;
    background-color: transparent !important;
    color: #8B8A83 !important;
    -webkit-text-fill-color: #8B8A83 !important;
    border: 1px solid transparent !important;
}
div[data-testid="stLayoutWrapper"]:has(.bf-card-marker) div[data-testid="stButton"] > button[kind="tertiary"] p,
div[data-testid="stLayoutWrapper"]:has(.bf-card-marker) div[data-testid="stButton"] > button[kind="tertiary"] span {
    color: #8B8A83 !important;
    -webkit-text-fill-color: #8B8A83 !important;
}
div[data-testid="stLayoutWrapper"]:has(.bf-card-marker) div[data-testid="stButton"] > button[kind="tertiary"]:hover {
    color: #1A1A18 !important;
    -webkit-text-fill-color: #1A1A18 !important;
    background: transparent !important;
}

.bf-empty {
    padding: 40px 0;
    text-align: center;
    color: #8B8A83;
    font-family: 'Inter', sans-serif;
    font-size: 13.5px;
}
</style>
"""


# ── Card rendering ───────────────────────────────────────────────────────────

def _render_card_header_html(card: Card, expanded: bool) -> str:
    needs_tag = (
        '<span class="bf-tag bf-tag--needs">NEEDS YOU</span>'
        if card.needs_you else ""
    )
    return (
        '<div class="bf-card-top">'
        '<div class="bf-tagrow">'
        f'<span class="bf-tag">{card.type}</span>'
        f'{needs_tag}'
        f'<span class="bf-context">{card.context}</span>'
        '</div>'
        f'<span class="bf-elapsed">{card.elapsed}</span>'
        '</div>'
    )


def _render_action_buttons(card: Card) -> None:
    """Three Streamlit buttons inside the card. Visual only — increments
    sidebar counters and removes the card from the active list."""
    primary_col, edit_col, skip_col = st.columns([2, 1, 1.4])
    with primary_col:
        if st.button(card.primary_action, key=f"prim_{card.id}",
                     use_container_width=True, type="primary"):
            _handle_send(card)
    with edit_col:
        if st.button("Edit", key=f"edit_{card.id}", use_container_width=True):
            st.session_state["expanded_card"] = card.id
            st.session_state[f"editing_{card.id}"] = True
            st.rerun()
    with skip_col:
        if st.button(card.skip_label, key=f"skip_{card.id}",
                     use_container_width=True, type="tertiary"):
            _handle_skip(card)


def _handle_send(card: Card) -> None:
    sent = st.session_state.setdefault("queue_sent_ids", set())
    sent.add(card.id)
    st.session_state["queue_sent_count"] = len(sent)
    st.session_state["expanded_card"] = None
    st.session_state.pop(f"editing_{card.id}", None)
    st.toast(f"Sent · {card.context}")
    st.rerun()


def _handle_skip(card: Card) -> None:
    skipped = st.session_state.setdefault("queue_skipped_ids", set())
    skipped.add(card.id)
    st.session_state["queue_skipped_count"] = len(skipped)
    st.session_state["expanded_card"] = None
    st.session_state.pop(f"editing_{card.id}", None)
    st.toast(f"Skipped · {card.context}")
    st.rerun()


def _render_collapsed(card: Card) -> None:
    with st.container(border=True):
        st.markdown(
            '<div class="bf-card-marker"></div>'
            + _render_card_header_html(card, expanded=False),
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<a class="bf-summary-toggle" href="?nav=queue&expand={card.id}'
            f'{_preserve_filter_query()}" target="_self">'
            f'{_esc(card.summary_html)}'
            f'</a>'
            f'<a class="bf-show-reasoning" href="?nav=queue&expand={card.id}'
            f'{_preserve_filter_query()}" target="_self">Show reasoning &darr;</a>',
            unsafe_allow_html=True,
        )
        _render_action_buttons(card)


def _render_expanded(card: Card) -> None:
    with st.container(border=True):
        st.markdown(
            '<div class="bf-card-marker bf-card-marker--expanded"></div>'
            + _render_card_header_html(card, expanded=True),
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div class="bf-card-summary">{_esc(card.summary_html)}</div>',
            unsafe_allow_html=True,
        )

        # FROM block (only if email card)
        if card.from_email:
            st.markdown(
                f'<div class="bf-block-h">FROM {card.from_email}</div>'
                f'<div class="bf-from">{_esc(card.from_body)}</div>',
                unsafe_allow_html=True,
            )

        # DRAFTED block header
        st.markdown(
            f'<div class="bf-block-h">{card.drafted_label} '
            f'&middot; TO {card.drafted_to}</div>',
            unsafe_allow_html=True,
        )

        editing = st.session_state.get(f"editing_{card.id}", False)
        if editing:
            st.markdown(
                f'<div style="font-family:\'Inter\', sans-serif; font-size:12.5px;'
                f'color:#8B8A83; margin:0 0 6px;">'
                f'Subject: {card.drafted_subject}</div>',
                unsafe_allow_html=True,
            )
            st.text_area(
                "Edit drafted body",
                value=st.session_state.get(f"draft_body_{card.id}", card.drafted_body),
                key=f"draft_body_{card.id}",
                height=260,
                label_visibility="collapsed",
            )
        else:
            body_html = st.session_state.get(f"draft_body_{card.id}", card.drafted_body)
            st.markdown(
                '<div class="bf-draft-wrap">'
                f'<div class="bf-draft-subject">Subject: {card.drafted_subject}</div>'
                f'<div class="bf-draft-body">{_esc(body_html)}</div>'
                '</div>',
                unsafe_allow_html=True,
            )

        # WHY block — Brand Scout cards say "FLAGGED", others say "DRAFTED"
        why_label = (
            "WHY BROKERFLOW FLAGGED THIS"
            if card.type == "BRAND SCOUT"
            else "WHY BROKERFLOW DRAFTED THIS"
        )
        bullets_html = "".join(
            '<li>'
            f'<span class="bf-reason-text">{_esc(b.text)}</span>'
            + (f'<span class="bf-reason-src">&#8599; {b.source}</span>' if b.source else '')
            + '</li>'
            for b in card.reasoning
        )
        st.markdown(
            f'<div class="bf-block-h">{why_label}</div>'
            f'<ul class="bf-reasoning">{bullets_html}</ul>',
            unsafe_allow_html=True,
        )

        st.markdown('<div style="margin-top:18px;"></div>', unsafe_allow_html=True)
        _render_action_buttons(card)

        st.markdown(
            f'<a class="bf-show-reasoning" href="?nav=queue'
            f'{_preserve_filter_query()}" target="_self" '
            'style="margin-top:10px;">&uarr; Collapse</a>',
            unsafe_allow_html=True,
        )


def _preserve_filter_query() -> str:
    """Append &filter=...&brand=... to URL anchors so card click doesn't lose
    the active filter."""
    out = ""
    f = st.session_state.get("queue_filter")
    b = st.session_state.get("queue_brand")
    if f and f != "today":
        out += f"&filter={f}"
    if b:
        out += f"&brand={b}"
    return out


# ── Public render entry point ────────────────────────────────────────────────

def consume_expand_query() -> bool:
    """No-op shim — broker_shell.consume_nav_query_param() now handles
    both ?nav= and ?expand= in a single pass."""
    return False


def _render_ask_bar() -> None:
    """Full-width Ask BrokerFlow input + canned response card.

    The input is a Streamlit st.text_input restyled into a pill via
    :has(.bf-ask-marker). On submit (Enter), the value is matched
    against keyword rules and a response is stashed in session state."""
    placeholder = (
        "Ask BrokerFlow anything... e.g. How much Olipop accrual is left this year?"
    )

    with st.container():
        st.markdown('<div class="bf-ask-marker"></div>', unsafe_allow_html=True)
        query = st.text_input(
            "Ask BrokerFlow",
            value="",
            placeholder=placeholder,
            key="bf_ask_input",
            label_visibility="collapsed",
        )

    # Process new submissions exactly once
    last_submitted = st.session_state.get("bf_ask_last_submitted", "")
    if query and query != last_submitted:
        st.session_state["bf_ask_last_submitted"] = query
        st.session_state["bf_ask_response"] = _generate_ask_response(query)

    response = st.session_state.get("bf_ask_response")
    if response:
        st.markdown(
            '<div class="bf-ask-response">'
            '<div class="bf-ask-response-head">'
            '<span class="bf-ask-response-spark">&#10022;</span>'
            '<span class="bf-ask-response-brand">BrokerFlow</span>'
            '</div>'
            f'<div class="bf-ask-response-body">{response["body_html"]}</div>'
            '<div class="bf-ask-response-foot">'
            f'<span>Sources: {response["sources"]}</span>'
            f'<a class="bf-ask-dismiss" href="?nav=queue'
            f'{_preserve_filter_query()}&dismiss_ask=1" target="_self">Dismiss &times;</a>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )


_BRAND_SUGGESTION_BODY = (
    "<p>Based on your current book and what's trending across Faire, "
    "Instacart, and Amazon over the last 30 days, here are 3 brands "
    "worth a meeting:</p>"
    "<ol>"
    "<li><b>Poppi</b> — prebiotic soda, 4.8× velocity lift on Instacart, "
    "&#36;34M raised Series B. Margins tight (18%) but distribution "
    "white space in your Costco BA territory. Score: 82/100.</li>"
    "<li><b>Fishwife</b> — tinned fish, indexing 3.2× on Faire in PNW "
    "where you have strong Costco NW relationships. Promo independence "
    "clean. Score: 79/100.</li>"
    "<li><b>Magic Spoon</b> — high-protein cereal, expanding into UNFI "
    "natural channel where you have 4 active brands. Recently dropped "
    "their previous broker. Score: 76/100.</li>"
    "</ol>"
    '<p><a href="#">Want me to draft intro pitches for any of these?</a></p>'
)

_GENERIC_BODY = (
    "<p>I can help you with brand suggestions, accrual balances, pitch "
    "drafts, and more. Try asking <b>&ldquo;What new brands should I "
    "scout?&rdquo;</b> to see what I can do.</p>"
)


def _generate_ask_response(query: str) -> dict:
    q = query.lower()
    triggers = ("new brand", "suggest", "scout", "find")
    if any(t in q for t in triggers):
        return {"body_html": _BRAND_SUGGESTION_BODY, "sources": "3 · 1.2s"}
    return {"body_html": _GENERIC_BODY, "sources": "0 · 0.4s"}


def render_queue_view() -> None:
    st.markdown(_QUEUE_CSS, unsafe_allow_html=True)

    # Dismiss-ask URL action — clears the response without changing other state
    if st.query_params.get("dismiss_ask") == "1":
        st.session_state.pop("bf_ask_response", None)
        st.session_state.pop("bf_ask_last_submitted", None)
        st.query_params.clear()
        st.rerun()

    _render_ask_bar()

    filter_key = st.session_state.get("queue_filter", "today")
    brand = st.session_state.get("queue_brand")
    cards = _filter_cards(filter_key, brand)

    label = _filter_label(filter_key, brand)
    count_word = "card" if len(cards) == 1 else "cards"

    # Section title + filter pills
    pills = []
    for key, lbl, cnt in [
        ("today",     "ALL",                 len(_filter_cards("today", brand))),
        ("needs_you", f"NEEDS YOU · {len(_filter_cards('needs_you', brand))}", None),
        ("drafted",   f"DRAFTED · {len(_filter_cards('drafted', brand))}",     None),
    ]:
        active = (filter_key == key) or (filter_key not in ("today", "needs_you", "drafted") and key == "today")
        cls = "bf-queue-pill bf-queue-pill--active" if active else "bf-queue-pill"
        href = f"?nav=queue&filter={key}" + (f"&brand={brand}" if brand else "")
        pills.append(f'<a class="{cls}" href="{href}" target="_self">{lbl}</a>')
    pills_html = '<div class="bf-queue-pills">' + "".join(pills) + '</div>'

    st.markdown(
        '<div class="bf-queue-section-row">'
        f'<h1 class="bf-queue-h">{label} '
        f'<span class="bf-queue-h-count">&middot; {len(cards)} {count_word}</span></h1>'
        f'{pills_html}'
        '</div>',
        unsafe_allow_html=True,
    )

    if not cards:
        st.markdown(
            '<div class="bf-empty">Nothing here yet — check back soon.</div>',
            unsafe_allow_html=True,
        )
        return

    expanded_id = st.session_state.get("expanded_card")
    for card in cards:
        if card.id == expanded_id:
            _render_expanded(card)
        else:
            _render_collapsed(card)
