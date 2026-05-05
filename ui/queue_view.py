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
        type="EMAIL",
        needs_you=True,
        context="Costco SE · Marcus",
        elapsed="2m",
        summary_html=(
            "He asked if <b>Brami</b> wants the May end cap. Drafted reply "
            "proposing <b>24 stores</b> using your <b>$8,228 unspent SE accrual</b>."
        ),
        primary_action="Approve & send",
        brand="Brami",
        from_email="marcus.alvarez@costco.com",
        from_body=(
            "Hey Nadia — May end cap window opens up next week. Same as "
            "last year if you want it. Let me know by EOW.\n\n— Marcus"
        ),
        drafted_to="marcus.alvarez@costco.com",
        drafted_subject="Re: May SE end cap — yes, locking in 24 stores",
        drafted_body=(
            "Hi Marcus,\n\n"
            "Yes — Brami is in. Lupini bean snacks did 3.1× lift in 26 of "
            "28 SE stores last May, so we'd love another shot at it.\n\n"
            "We have $8,228 left in SE accrual for FY26, which gets us to "
            "24 stores at $343/each. Can we lock in May 12-25, sea salt "
            "SKU again?\n\n"
            "Send the contract whenever and I'll get it back same day.\n\n"
            "— Nadia"
        ),
        reasoning=[
            ReasoningBullet(
                "Brami SE accrual balance: $8,228 unspent (FY26, 47 days remaining)",
                "LEDGER",
            ),
            ReasoningBullet(
                "Same window FY25: sea salt lupini end cap, 3.1× lift, 26/28 stores executed",
                "EVENTS",
            ),
            ReasoningBullet("Avg cost per store FY25: $342", "EVENTS"),
            ReasoningBullet(
                "Proposed: 24 stores × $343 = $8,232 (uses full SE balance)",
                "",
            ),
            ReasoningBullet(
                "Marcus's avg response time: 4 hours (last 6 months)", "INBOX",
            ),
            ReasoningBullet(
                "Nadia's last 3 replies to Marcus averaged 73 words — this draft: 67 words",
                "INBOX",
            ),
        ],
    ),
    Card(
        id="card-2",
        type="FOLLOW-UP",
        needs_you=False,
        context="CDS · Priya",
        elapsed="1h",
        summary_html=(
            "WO confirmations received but no billing <b>5 days past expected</b>. "
            "Drafted nudge with WO numbers."
        ),
        primary_action="Send",
        brand="Brami",
        from_email="priya.menon@cds.costco.com",
        from_body=(
            "Confirmed receipt of WO #44218 and WO #44219 for the Brami "
            "April demo cycle (12 stores, SE region). Will follow up with "
            "billing details shortly.\n\n— Priya"
        ),
        drafted_to="priya.menon@cds.costco.com",
        drafted_subject="Re: April demo — billing follow-up (WO #44218, #44219)",
        drafted_body=(
            "Hi Priya,\n\n"
            "Quick check-in on the April Brami demo billing — WO #44218 "
            "and #44219 were confirmed two weeks ago and we're 5 days past "
            "the typical billing window.\n\n"
            "Anything outstanding on your end? Happy to send the SE region "
            "store list again if it helps reconcile.\n\n"
            "— Nadia"
        ),
        reasoning=[
            ReasoningBullet("WO #44218 confirmed 4/14, WO #44219 confirmed 4/14", "EVENTS"),
            ReasoningBullet("Avg CDS billing turnaround: 14 days (last 6 cycles)", "LEDGER"),
            ReasoningBullet("Days since confirmation: 19 (5 days past expected)", ""),
            ReasoningBullet("Priya's prior response time on billing nudges: 1 day", "INBOX"),
        ],
    ),
    Card(
        id="card-3",
        type="EMAIL",
        needs_you=True,
        context="Costco BA · Danielle",
        elapsed="3h",
        summary_html=(
            "Drafted FY27 renewal at same <b>$126/pallet</b> rate as FY26. "
            "<b>BA volume up 18% YoY</b> — could push for higher."
        ),
        primary_action="Approve & send",
        brand="Olipop",
        from_email="danielle.ortiz@costco.com",
        from_body=(
            "Nadia — time to lock the FY27 Olipop pallet rate for BA. "
            "Send me your number when you can. Want to wrap by next Friday.\n\n"
            "— Danielle"
        ),
        drafted_to="danielle.ortiz@costco.com",
        drafted_subject="Re: FY27 Olipop pallet rate — BA",
        drafted_body=(
            "Hi Danielle,\n\n"
            "Holding at $126/pallet for FY27 — same as FY26. Olipop volume "
            "in BA is up 18% YoY so we're comfortable carrying the rate "
            "into next year.\n\n"
            "Send the agreement and we'll countersign same week.\n\n"
            "— Nadia"
        ),
        reasoning=[
            ReasoningBullet("FY26 BA pallet rate: $126", "LEDGER"),
            ReasoningBullet("BA YoY pallet volume growth: +18%", "EVENTS"),
            ReasoningBullet(
                "Comparable region (NW) renewed at $134 last quarter — opportunity to push",
                "EVENTS",
            ),
            ReasoningBullet("Danielle's renewal cycle window: 2 weeks", "INBOX"),
        ],
    ),
    Card(
        id="card-4",
        type="FOLLOW-UP",
        needs_you=False,
        context="White Label · Theo",
        elapsed="12m",
        summary_html=(
            "<b>PO #013770501039</b> (Olipop, Owatonna → Costco MW) had "
            "requested pickup <b>4/30</b>. <b>No BOL filed.</b>"
        ),
        primary_action="Send",
        brand="Olipop",
        from_email="theo.rasmussen@whitelabel.com",
        from_body=(
            "PO #013770501039 — confirmed dispatch from Owatonna for the "
            "Costco MW DC, requested pickup 4/30. Will share BOL upon "
            "carrier hand-off.\n\n— Theo"
        ),
        drafted_to="theo.rasmussen@whitelabel.com",
        drafted_subject="Re: PO #013770501039 — BOL not yet filed",
        drafted_body=(
            "Hi Theo,\n\n"
            "Following up on PO #013770501039 (Olipop, Owatonna → Costco "
            "MW) — requested pickup was 4/30 but no BOL has come through "
            "on our end.\n\n"
            "Did the carrier pick up as scheduled? Need confirmation by "
            "EOD or we'll need to reschedule with the DC.\n\n"
            "— Nadia"
        ),
        reasoning=[
            ReasoningBullet("PO #013770501039 requested pickup: 4/30", "EVENTS"),
            ReasoningBullet("No BOL filed in shipment table as of today", "LEDGER"),
            ReasoningBullet("Costco MW DC appointment window closes EOD today", "EVENTS"),
        ],
    ),
    Card(
        id="card-5",
        type="OPPORTUNITY",
        needs_you=True,
        context="Spudsy · LA",
        elapsed="2h",
        summary_html=(
            "Drafted thinking note. Room for <b>2 end caps + 80-store demo "
            "run</b> if you want to move now."
        ),
        primary_action="Draft the outreach",
        skip_label="Skip — I'll handle it",
        brand="Spudsy",
        drafted_label="DRAFTED ACTION",
        drafted_to="Internal — Spudsy LA opportunity note",
        drafted_subject="Spudsy LA — open promo capacity, Q2",
        drafted_body=(
            "Spudsy currently has unspent LA promo capacity:\n\n"
            "  • 2 end caps available in the next 6-week window\n"
            "  • 80-store demo run still on the table for Q2\n\n"
            "Recommend pitching the bundle to LA buyer (Maya at Costco LA) "
            "as a single ask. Estimated lift: 2.4× based on Spudsy's "
            "previous LA demo cycle. Total spend would draw down ~$11K "
            "of unspent LA accrual.\n\n"
            "Want me to draft the outreach to Maya?"
        ),
        reasoning=[
            ReasoningBullet(
                "Spudsy unspent LA accrual: $11,400 (FY26, 47 days remaining)",
                "LEDGER",
            ),
            ReasoningBullet("LA region open end-cap slots: 2 (May–June)", "EVENTS"),
            ReasoningBullet("Last LA demo cycle lift: 2.4× across 64 stores", "EVENTS"),
            ReasoningBullet(
                "Maya (LA buyer) avg pitch-to-decision: 6 days", "INBOX",
            ),
        ],
    ),
    Card(
        id="card-6",
        type="NEW BRAND",
        needs_you=False,
        context="Brand Scout · Faire signal",
        elapsed="4h",
        summary_html=(
            "Found a new <b>sparkling tea brand</b> trending <b>4.2×</b> on "
            "Faire and Instacart with clean promo independence. Scored "
            "<b>87/100</b>. Drafted intro email and one-pager."
        ),
        primary_action="Review verdict",
        brand="",
        drafted_label="DRAFTED ACTION",
        drafted_to="founders@steepsparkling.co",
        drafted_subject="Steep Sparkling × Nadia — quick intro",
        drafted_body=(
            "Hey team,\n\n"
            "Came across Steep Sparkling on Faire — your Q1 trajectory is "
            "in the top 5% of beverage SKUs we track. Clean promo "
            "independence and the velocity story holds up across Faire and "
            "Instacart.\n\n"
            "I work with a few brands in your category and would love a "
            "15-min call to see whether broker representation makes sense "
            "for where you're going next quarter.\n\n"
            "— Nadia"
        ),
        reasoning=[
            ReasoningBullet(
                "Faire Q1 velocity rank: top 5% in beverage (4.2× category baseline)",
                "EVENTS",
            ),
            ReasoningBullet(
                "Instacart trending score: 88/100, no promo dependency detected",
                "EVENTS",
            ),
            ReasoningBullet("Brand Scout composite score: 87/100", ""),
            ReasoningBullet(
                "Broker representation gap: no broker of record in CA / NW yet",
                "EVENTS",
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

        # WHY block
        bullets_html = "".join(
            '<li>'
            f'<span class="bf-reason-text">{_esc(b.text)}</span>'
            + (f'<span class="bf-reason-src">&#8599; {b.source}</span>' if b.source else '')
            + '</li>'
            for b in card.reasoning
        )
        st.markdown(
            '<div class="bf-block-h">WHY BROKERFLOW DRAFTED THIS</div>'
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


def render_queue_view() -> None:
    st.markdown(_QUEUE_CSS, unsafe_allow_html=True)

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
