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


# Display labels for agent_origin / Drafted-by attribution.
_AGENT_LABELS = {
    "retailer_pitcher": "Retailer Pitcher",
    "brand_scout":      "Brand Scout",
    "new_item_forms":   "New Item Forms",
}


# Inline phrases we linkify into a clickable doc reference.
# (regex pattern → doc_type to open)
_LINKIFY_PATTERNS: list[tuple[str, str]] = [
    (r"\bsell sheet \+ cost build attached\b",  "sell_sheet"),
    (r"\bsell sheet attached\b",                "sell_sheet"),
    (r"\brenewal sheet attached\b",             "sell_sheet"),
    (r"\bone-pager\b",                          "one_pager"),
    (r"\bUNFI new-item forms? filled\b",        "new_item_form"),
    (r"\bKeHE new-item forms? drafted\b",       "new_item_form"),
    (r"\bnew-item forms? filled and ready\b",   "new_item_form"),
    (r"\bform drafted\b",                       "new_item_form"),
]


def _linkify_doc_refs(text: str, card_id: str, available_doc_types: set[str]) -> str:
    """Wrap inline doc-reference phrases in <a class="bf-doc-link">.
    Only links to doc types the card actually produces."""
    import re
    out = text
    for pattern, doc_type in _LINKIFY_PATTERNS:
        if doc_type not in available_doc_types:
            continue
        href = f"?nav=queue&open_doc={card_id}:{doc_type}"
        out = re.sub(
            pattern,
            (lambda m, h=href: f'<a class="bf-doc-link" href="{h}" target="_self">'
                              f'{m.group(0)}</a>'),
            out,
            count=1,
            flags=re.IGNORECASE,
        )
    return out


def _render_attachments_row(card: "Card") -> None:
    """Render the ATTACHMENTS row above action buttons in expanded view.
    Pulls metadata from doc_storage for everything in card.docs."""
    from agents._shared import doc_storage as _ds
    items_html = []
    for doc_type, label in card.docs:
        info = _ds.get(card.id, doc_type)
        # If the seed PDFs haven't been generated yet (first render), the
        # entry might be missing — show a placeholder rather than crash.
        meta = "PDF · — pages" if not info else (
            f"PDF · {info['pages']} page{'s' if info['pages'] != 1 else ''}"
        )
        href = f"?nav=queue&open_doc={card.id}:{doc_type}"
        items_html.append(
            f'<a class="bf-attach-item" href="{href}" target="_self">'
            f'<span class="bf-attach-icon">&#128196;</span>'
            f'<span class="bf-attach-name">{label}</span>'
            f'<span class="bf-attach-meta">{meta}</span>'
            f'<span class="bf-attach-open">&#8599; Open</span>'
            f'</a>'
        )
    st.markdown(
        '<div class="bf-attach-row">'
        '<div class="bf-attach-h">ATTACHMENTS</div>'
        + "".join(items_html) +
        '</div>',
        unsafe_allow_html=True,
    )


def _render_doc_panel() -> None:
    """Right-side document viewer.

    Renders the document content as a structured native HTML preview
    (NOT a PDF embed). The PDF is the forwardable artifact the broker
    sends to a buyer; the in-app view uses the same data the PDF was
    generated from, rendered in BrokerFlow typography."""
    target = st.session_state.get("doc_open")
    if not target:
        return
    card_id, doc_type = target.split(":", 1)
    from agents._shared import doc_storage as _ds
    from agents._shared import document_data as _dd
    from ui import doc_preview as _dp

    info = _ds.get(card_id, doc_type)
    payload = _dd.get_payload(card_id, doc_type)
    if not payload:
        return

    eyebrow, title, subtitle, body_html = _dp.render_preview_body(
        doc_type, payload,
    )

    # Agent label comes from the card's agent_origin (first one).
    agent_label = "BrokerFlow"
    for c in SEED_CARDS:
        if c.id == card_id and c.agent_origin:
            agent_label = _AGENT_LABELS.get(c.agent_origin[0], "BrokerFlow")
            break

    # If PDFs aren't generated yet (rare race), fall back to # so the
    # actions still render but don't break.
    pdf_url = info["url"] if info else "#"

    close_href = f"?nav=queue{_preserve_filter_query()}&close_doc=1"

    # Inject preview-specific CSS once
    st.markdown(_dp.PREVIEW_CSS, unsafe_allow_html=True)

    # Dim overlay — clicking anywhere on it closes the panel
    st.markdown(
        f'<a href="{close_href}" target="_self" '
        f'style="text-decoration:none;">'
        f'<div class="bf-doc-overlay"></div></a>',
        unsafe_allow_html=True,
    )

    subtitle_html = (
        f'<div class="bf-doc-subtitle">{subtitle}</div>' if subtitle else ""
    )

    with st.container():
        st.markdown(
            '<div class="bf-doc-marker"></div>'
            '<div class="bf-doc-head">'
            '<div class="bf-doc-head-text">'
            f'<div class="bf-doc-eyebrow">{eyebrow}</div>'
            f'<div class="bf-doc-title">{title}</div>'
            f'{subtitle_html}'
            '</div>'
            '<div class="bf-doc-actions">'
            f'<a class="bf-doc-action" href="{pdf_url}" target="_blank">'
            '&#8599; Open as PDF</a>'
            f'<a class="bf-doc-action" href="{pdf_url}" '
            'download target="_blank">&darr; Download</a>'
            f'<a class="bf-doc-action bf-doc-action--close" '
            f'href="{close_href}" target="_self">&times;</a>'
            '</div>'
            '</div>'
            f'<div class="bf-doc-preview-body">{body_html}</div>'
            '<div class="bf-doc-foot">'
            f'<span>Generated by {agent_label} &middot; just now</span>'
            '<a class="bf-doc-foot-regen" href="#">Regenerate</a>'
            '</div>',
            unsafe_allow_html=True,
        )


# ── Seed data ────────────────────────────────────────────────────────────────

@dataclass
class ReasoningBullet:
    text: str
    source: str  # "LEDGER" | "EVENTS" | "INBOX" | ""


@dataclass
class Card:
    id: str
    type: str            # Topic tag: "PITCH" | "RENEWAL" | "NEW BRAND" | "NEW ITEM"
    needs_you: bool
    context: str         # "Costco NW · Marcus"
    elapsed: str         # "2m"
    summary_html: str    # 1-2 sentences with <b>...</b> bolded numbers
    primary_action: str  # button label
    skip_label: str = "Skip"
    brand: str = ""      # filter key (matches sidebar BROKER_BRANDS)

    # Agent attribution — list of agent keys that produced this card. Used by
    # the WHY block "Drafted by:" line and by PDF generation. Order matters
    # (e.g. NEW BRAND credits Brand Scout → Retailer Pitcher).
    agent_origin: list[str] = field(default_factory=list)
    # Documents this card produces. Each is a (doc_type, label) tuple matching
    # pdf_generator template keys: "sell_sheet" | "one_pager" | "new_item_form"
    # | "cost_build". Side panel resolves the URL via doc_storage.
    docs: list[tuple[str, str]] = field(default_factory=list)

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
        type="PITCH",
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
        agent_origin=["retailer_pitcher"],
        docs=[("sell_sheet", "Sell sheet"), ("cost_build", "Cost build")],
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
        type="NEW BRAND",
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
        agent_origin=["brand_scout", "retailer_pitcher"],
        docs=[("one_pager", "Brand one-pager")],
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
        type="NEW ITEM",
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
        agent_origin=["new_item_forms"],
        docs=[("new_item_form", "UNFI new-item form")],
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
        type="RENEWAL",
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
        agent_origin=["retailer_pitcher"],
        docs=[("sell_sheet", "Renewal sheet")],
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
        type="NEW BRAND",
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
        agent_origin=["brand_scout", "retailer_pitcher"],
        docs=[("one_pager", "Brand one-pager")],
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
        type="NEW ITEM",
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
        agent_origin=["new_item_forms"],
        docs=[("new_item_form", "KeHE new-item form")],
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

/* ── Drafted-by line (in WHY block) ─────────────────────────────── */
.bf-drafted-by {
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    color: #8B8A83;
    margin: -2px 0 12px;
}
.bf-drafted-by-agent {
    color: #1A1A18;
    font-weight: 500;
}
.bf-drafted-by-time {
    color: #B0AFA8;
}

/* ── Inline attached-doc reference ──────────────────────────────── */
.bf-doc-link,
.bf-doc-link:link,
.bf-doc-link:visited {
    color: #B07A1C;
    text-decoration: underline;
    text-decoration-color: #E8A33D;
    text-underline-offset: 2px;
    font-weight: 500;
    cursor: pointer;
    text-decoration-thickness: 1px;
}
.bf-doc-link:hover {
    color: #8E5E10;
    text-decoration-color: #1A1A18;
}
.bf-doc-link::after {
    content: " ↗";
    font-size: 10px;
    color: #B07A1C;
}

/* ── Attachments row (in expanded card, above action buttons) ──── */
.bf-attach-row {
    border-top: 1px solid #F2F2EE;
    padding: 16px 0 12px;
    margin-top: 18px;
}
.bf-attach-h {
    font-family: 'Inter', sans-serif;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #8B8A83;
    margin-bottom: 10px;
}
.bf-attach-item,
.bf-attach-item:link,
.bf-attach-item:visited {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 8px 0;
    text-decoration: none;
    border-top: 1px solid #F2F2EE;
}
.bf-attach-item:first-of-type { border-top: none; }
.bf-attach-item:hover .bf-attach-name { color: #1A1A18; }
.bf-attach-icon {
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    color: #8B8A83;
    width: 22px;
    text-align: center;
}
.bf-attach-name {
    font-family: 'Inter', sans-serif;
    font-size: 13.5px;
    color: #57564F;
    flex: 1;
}
.bf-attach-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #B0AFA8;
    margin-right: 14px;
}
.bf-attach-open {
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    font-weight: 500;
    color: #B07A1C;
    letter-spacing: 0.02em;
}

/* ── Document side panel (slides in from right) ─────────────────── */
.bf-doc-overlay {
    position: fixed;
    inset: 0;
    background: rgba(10, 10, 10, 0.22);
    z-index: 250;
    animation: bf-fade-in 0.18s ease-out;
}
@keyframes bf-fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
}

div[data-testid="stLayoutWrapper"]:has(.bf-doc-marker) {
    position: fixed !important;
    top: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    left: auto !important;
    width: 540px !important;
    height: 100vh !important;
    background: #FAFAF7 !important;
    border-left: 1px solid #EAEAE4 !important;
    border-top: none !important;
    border-bottom: none !important;
    border-right: none !important;
    border-radius: 0 !important;
    box-shadow: -16px 0 40px -8px rgba(10, 10, 10, 0.18) !important;
    padding: 0 !important;
    margin: 0 !important;
    z-index: 260 !important;
    overflow: hidden !important;
    animation: bf-doc-slide 0.22s ease-out;
}
@keyframes bf-doc-slide {
    from { transform: translateX(40px); opacity: 0.4; }
    to   { transform: translateX(0); opacity: 1; }
}
div[data-testid="stLayoutWrapper"]:has(.bf-doc-marker) > div[data-testid="stVerticalBlock"] {
    border: none !important;
    background: transparent !important;
    padding: 0 !important;
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 0 !important;
    overflow: hidden !important;
}
/* All Streamlit wrappers down to our markdown div must also stretch + flex
   so .bf-doc-body's flex:1 has a definite parent height to grow into */
div[data-testid="stLayoutWrapper"]:has(.bf-doc-marker)
  > div[data-testid="stVerticalBlock"]
  > div[data-testid="stElementContainer"] {
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
    flex: 1 1 auto !important;
    min-height: 0 !important;
}
div[data-testid="stLayoutWrapper"]:has(.bf-doc-marker)
  div[data-testid="stMarkdown"],
div[data-testid="stLayoutWrapper"]:has(.bf-doc-marker)
  div[data-testid="stMarkdownContainer"] {
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
    min-height: 0 !important;
}
@media (max-width: 820px) {
    div[data-testid="stLayoutWrapper"]:has(.bf-doc-marker) {
        width: 100vw !important;
    }
}

.bf-doc-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 14px;
    padding: 22px 26px 18px;
    border-bottom: 1px solid #EAEAE4;
    background: #FAFAF7;
}
.bf-doc-head-text {
    flex: 1;
    min-width: 0;
}
.bf-doc-eyebrow {
    font-family: 'Inter', sans-serif;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #B0AFA8;
    margin-bottom: 6px;
}
.bf-doc-title {
    font-family: 'Instrument Serif', Georgia, serif;
    font-size: 22px;
    line-height: 1.2;
    color: #1A1A18;
    margin: 0;
}
.bf-doc-subtitle {
    font-family: 'Instrument Serif', Georgia, serif;
    font-style: italic;
    font-size: 13.5px;
    color: #8B8A83;
    margin-top: 4px;
}
.bf-doc-actions {
    display: flex;
    gap: 14px;
    align-items: center;
    flex-shrink: 0;
}
.bf-doc-action,
.bf-doc-action:link,
.bf-doc-action:visited {
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    color: #57564F;
    text-decoration: none;
    padding: 6px 10px;
    border-radius: 6px;
    transition: background 0.12s ease;
    white-space: nowrap;
}
.bf-doc-action:hover { background: #F2F2EE; color: #1A1A18; }
.bf-doc-action--close {
    font-size: 18px;
    line-height: 1;
    padding: 4px 10px;
    color: #8B8A83;
}
/* Legacy iframe body — kept as fallback if a doc_type has no preview
   template yet. Native HTML preview lives in .bf-doc-preview-body. */
.bf-doc-body {
    flex: 1 1 auto;
    overflow: hidden;
    background: #1A1A18;
}
.bf-doc-body iframe {
    width: 100%;
    height: 100%;
    border: 0;
    background: #1A1A18;
}
.bf-doc-foot {
    flex: 0 0 auto;
    border-top: 1px solid #EAEAE4;
    padding: 12px 26px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: 'Inter', sans-serif;
    font-size: 11.5px;
    color: #8B8A83;
}
.bf-doc-foot-regen,
.bf-doc-foot-regen:link {
    color: #8B8A83;
    text-decoration: none;
}
.bf-doc-foot-regen:hover { color: #1A1A18; text-decoration: underline; }

/* ── Slide-up chat panel ────────────────────────────────────────── */
/* Streamlit container holding .bf-chat-marker becomes a fixed bottom panel.
   :has() scopes the absolute styling without leaking onto other pages.
   Width is explicit (calc) so right:0 doesn't get ignored when the
   inner stLayoutWrapper is already 100% wide in normal flow. */
div[data-testid="stLayoutWrapper"]:has(.bf-chat-marker) {
    position: fixed !important;
    left: 240px !important;
    right: 0 !important;
    bottom: 80px !important;          /* leave room for fixed input bar */
    width: calc(100vw - 240px) !important;
    height: calc(70vh - 80px) !important;
    background: #FAFAF7 !important;
    border-top: 1px solid #EAEAE4 !important;
    border-left: none !important;
    border-right: none !important;
    border-bottom: none !important;
    border-radius: 16px 16px 0 0 !important;
    box-shadow: 0 -16px 40px -16px rgba(10, 10, 10, 0.12) !important;
    padding: 0 !important;
    margin: 0 !important;
    z-index: 200 !important;
    overflow: hidden !important;
    animation: bf-chat-slide 0.22s ease-out;
}
div[data-testid="stLayoutWrapper"]:has(.bf-chat-marker) > div[data-testid="stVerticalBlock"] {
    border: none !important;
    background: transparent !important;
    padding: 24px 36px 24px !important;
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 0 !important;
    overflow: hidden !important;
}
@keyframes bf-chat-slide {
    from { transform: translateY(20px); opacity: 0.6; }
    to   { transform: translateY(0); opacity: 1; }
}
@media (max-width: 820px) {
    div[data-testid="stLayoutWrapper"]:has(.bf-chat-marker) {
        left: 0 !important;
        height: 88vh !important;
    }
}

/* Chat panel header */
.bf-chat-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 12px;
    border-bottom: 1px solid #F2F2EE;
}
.bf-chat-head-l {
    display: flex;
    align-items: center;
    gap: 16px;
}
.bf-chat-newchat,
.bf-chat-newchat:link,
.bf-chat-newchat:visited {
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    color: #57564F;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}
.bf-chat-newchat:hover { color: #1A1A18; }
.bf-chat-newchat-plus {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 18px; height: 18px;
    border: 1px solid #D6D6D2;
    border-radius: 50%;
    font-size: 12px;
    line-height: 1;
    color: #57564F;
}
.bf-chat-close,
.bf-chat-close:link,
.bf-chat-close:visited {
    font-family: 'Inter', sans-serif;
    font-size: 18px;
    color: #8B8A83;
    text-decoration: none;
    line-height: 1;
    padding: 4px 8px;
    border-radius: 6px;
    transition: background 0.12s ease;
}
.bf-chat-close:hover { background: #F2F2EE; color: #1A1A18; }
.bf-chat-sub {
    font-family: 'Instrument Serif', Georgia, serif;
    font-style: italic;
    font-size: 14px;
    color: #8B8A83;
    margin: 10px 0 18px;
}

/* Chat messages area — flex-grows to fill remaining space, scrolls */
div[data-testid="stLayoutWrapper"]:has(.bf-chat-marker) .bf-chat-msgs-marker {
    display: none;
}
.bf-chat-msg-user {
    align-self: flex-end;
    max-width: 75%;
    background: #1A1A18;
    color: #FAFAF7;
    border-radius: 18px 18px 4px 18px;
    padding: 10px 16px;
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    line-height: 1.5;
    margin: 6px 0 14px auto;
    width: fit-content;
}
.bf-chat-msg-assistant {
    font-family: 'Instrument Serif', Georgia, serif;
    font-size: 17px;
    line-height: 1.7;
    color: #1A1A18;
    margin: 6px 0 22px;
    max-width: 92%;
}
.bf-chat-msg-assistant p {
    font-family: 'Instrument Serif', Georgia, serif !important;
    font-size: inherit !important;
    color: inherit !important;
    margin: 0 0 12px !important;
}
.bf-chat-msg-assistant p:last-child { margin-bottom: 0; }
.bf-chat-msg-assistant strong,
.bf-chat-msg-assistant b {
    font-family: 'Instrument Serif', Georgia, serif !important;
    font-weight: 600 !important;
    color: #1A1A18 !important;
}
.bf-chat-msg-assistant ul,
.bf-chat-msg-assistant ol {
    margin: 0 0 12px;
    padding-left: 22px;
}
.bf-chat-msg-assistant li {
    font-family: 'Instrument Serif', Georgia, serif !important;
    font-size: 16px !important;
    line-height: 1.65 !important;
    color: #1A1A18 !important;
    margin-bottom: 6px;
}

@keyframes bf-chat-cursor {
    0%, 49%   { opacity: 1; }
    50%, 100% { opacity: 0; }
}
.bf-chat-cursor {
    display: inline-block;
    width: 2px;
    height: 1em;
    background: #1A1A18;
    margin-left: 2px;
    vertical-align: text-bottom;
    animation: bf-chat-cursor 1s step-end infinite;
}

/* The scroll container inside the panel — wraps message stack */
.bf-chat-scroll {
    flex: 1 1 auto;
    overflow-y: auto;
    padding: 4px 0 16px;
    display: flex;
    flex-direction: column;
}
.bf-chat-scroll::-webkit-scrollbar { width: 4px; }
.bf-chat-scroll::-webkit-scrollbar-thumb { background: #EAEAE4; border-radius: 99px; }

/* Footer input bar — fixed to viewport bottom, just above the panel's
   content area. Sits on top of the panel (same z stack) but pinned. */
div[data-testid="stLayoutWrapper"]:has(.bf-chat-input-marker) {
    position: fixed !important;
    left: 240px !important;
    right: 0 !important;
    bottom: 0 !important;
    width: calc(100vw - 240px) !important;
    height: 80px !important;
    background: #FAFAF7 !important;
    border: none !important;
    border-top: 1px solid #EAEAE4 !important;
    padding: 16px 36px !important;
    margin: 0 !important;
    box-shadow: 0 -4px 16px -8px rgba(10, 10, 10, 0.08) !important;
    border-radius: 0 !important;
    z-index: 201 !important;
    display: flex !important;
    align-items: center !important;
}
div[data-testid="stLayoutWrapper"]:has(.bf-chat-input-marker) > div[data-testid="stVerticalBlock"] {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
    gap: 0 !important;
}
div[data-testid="stLayoutWrapper"]:has(.bf-chat-input-marker) .stTextInput input {
    width: 100% !important;
    background: #FFFFFF !important;
    border: 1px solid #EAEAE4 !important;
    border-radius: 999px !important;
    padding: 12px 90px 12px 20px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    color: #1A1A18 !important;
    box-shadow: none !important;
}
div[data-testid="stLayoutWrapper"]:has(.bf-chat-input-marker) .stTextInput input:focus {
    border-color: #1A1A18 !important;
    outline: none !important;
}
div[data-testid="stLayoutWrapper"]:has(.bf-chat-input-marker)::after {
    content: "Send  ↵";
    position: absolute;
    right: 26px;
    top: 50%;
    transform: translateY(-50%);
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    font-weight: 500;
    color: #1A1A18;
    background: #E8A33D;
    padding: 6px 12px;
    border-radius: 999px;
    pointer-events: none;
    z-index: 1;
    letter-spacing: 0.02em;
}

/* st.form chrome inside the chat input — strip border + padding so
   the pill input is the only visible chrome. The form_submit_button
   stays rendered (Enter submits) but is visually hidden — the CSS
   ::after Send pill above is the user-facing affordance. */
div[data-testid="stLayoutWrapper"]:has(.bf-chat-input-marker)
  div[data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
    width: 100% !important;
}
div[data-testid="stLayoutWrapper"]:has(.bf-chat-input-marker)
  div[data-testid="stFormSubmitButton"] {
    position: absolute !important;
    width: 1px !important;
    height: 1px !important;
    overflow: hidden !important;
    clip: rect(0, 0, 0, 0) !important;
    pointer-events: none !important;
    opacity: 0 !important;
}

.bf-queue-section-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 6px 0 16px;
}
.bf-queue-h {
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: #1A1A18;
    letter-spacing: 0;
    margin: 0;
    text-transform: none;
}
.bf-queue-h-count { color: #B0AFA8; font-weight: 400; }

/* ── One-row topbar (breadcrumb left + ask bar right) ──────────── */
.bf-queue-topbar-marker { display: none; }

/* The Streamlit st.columns row that holds breadcrumb + ask bar */
div[data-testid="stHorizontalBlock"]:has(.bf-queue-topbar-marker) {
    align-items: center !important;
    margin-bottom: 4px !important;
    padding-bottom: 18px !important;
    border-bottom: 1px solid #F2F2EE !important;
    gap: 24px !important;
}
/* Breadcrumb cell — vertically centered with the input */
div[data-testid="stHorizontalBlock"]:has(.bf-queue-topbar-marker)
  > div[data-testid="stColumn"]:first-child {
    display: flex;
    align-items: center;
    min-height: 0 !important;
}
/* Ask input cell — pill style, right-aligned, capped width */
div[data-testid="stHorizontalBlock"]:has(.bf-queue-topbar-marker)
  > div[data-testid="stColumn"]:last-child {
    display: flex !important;
    justify-content: flex-end !important;
    position: relative !important;
}
div[data-testid="stHorizontalBlock"]:has(.bf-queue-topbar-marker)
  .stTextInput {
    max-width: 480px;
    width: 100%;
}
div[data-testid="stHorizontalBlock"]:has(.bf-queue-topbar-marker)
  .stTextInput input {
    width: 100% !important;
    background: #FFFFFF !important;
    border: 1px solid #EAEAE4 !important;
    border-radius: 999px !important;
    padding: 10px 60px 10px 18px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13.5px !important;
    color: #1A1A18 !important;
    box-shadow: none !important;
}
div[data-testid="stHorizontalBlock"]:has(.bf-queue-topbar-marker)
  .stTextInput input::placeholder {
    color: #A8A8A8 !important;
    -webkit-text-fill-color: #A8A8A8 !important;
}
div[data-testid="stHorizontalBlock"]:has(.bf-queue-topbar-marker)
  .stTextInput input:focus {
    border-color: #1A1A18 !important;
    outline: none !important;
}
div[data-testid="stHorizontalBlock"]:has(.bf-queue-topbar-marker)
  > div[data-testid="stColumn"]:last-child::after {
    content: "⌘K";
    position: absolute;
    right: 18px;
    top: 22px;
    font-family: 'JetBrains Mono', 'SF Mono', monospace;
    font-size: 10.5px;
    color: #8B8A83;
    background: #F2F2EE;
    padding: 3px 8px;
    border-radius: 5px;
    pointer-events: none;
}

/* st.form wrapper inside the topbar — kill its border + padding so
   the input pill stays the only visible chrome */
div[data-testid="stHorizontalBlock"]:has(.bf-queue-topbar-marker)
  div[data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
    width: 100%;
    max-width: 480px;
    position: relative;
}
/* Hide the form_submit_button — Enter on the input still submits the
   form. The ⌘K hint above is the visual affordance. */
div[data-testid="stHorizontalBlock"]:has(.bf-queue-topbar-marker)
  div[data-testid="stFormSubmitButton"] {
    position: absolute !important;
    width: 1px !important;
    height: 1px !important;
    overflow: hidden !important;
    clip: rect(0, 0, 0, 0) !important;
    pointer-events: none !important;
    opacity: 0 !important;
}

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
/* New header-row layout: tag/context left + inline actions right.
   Streamlit places these inside an stHorizontalBlock; the card marker
   scopes the styling. */
.bf-card-header-l {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    min-height: 30px;
}
.bf-card-time-cell {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    height: 100%;
    min-height: 30px;
}
/* Tighten the column gap inside the card header */
div[data-testid="stLayoutWrapper"]:has(.bf-card-marker)
  div[data-testid="stHorizontalBlock"] {
    gap: 8px !important;
    align-items: center !important;
    margin-bottom: 8px !important;
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

.bf-card-summary {
    font-family: 'Inter', sans-serif;
    font-size: 14.5px;
    line-height: 1.55;
    color: #1A1A18;
    margin: 0 0 4px;
}
.bf-card-summary b { font-weight: 600; color: #1A1A18; }

/* ── Native <details> expand — no Streamlit rerun, instant ─────── */
.bf-card-details {
    margin-top: 0;
}
.bf-card-details > summary.bf-card-summary-row {
    list-style: none;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 0;
}
.bf-card-details > summary.bf-card-summary-row::-webkit-details-marker { display: none; }

.bf-show-reasoning {
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    color: #8B8A83;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin-top: 2px;
}
.bf-card-details:hover .bf-show-reasoning { color: #1A1A18; }
.bf-card-details[open] .bf-show-reasoning { color: #1A1A18; }
.bf-card-details[open] .bf-show-reasoning .bf-chevron {
    transform: rotate(180deg);
    display: inline-block;
}
.bf-card-details:not([open]) .bf-show-reasoning .bf-chevron {
    display: inline-block;
}

/* Active-card visual: blue accent on summary, darker border on the
   parent card container */
div[data-testid="stLayoutWrapper"]:has(.bf-card-details[open]) {
    border-color: #1A1A18 !important;
    background: #FFFFFF !important;
}
.bf-card-details[open] > summary.bf-card-summary-row .bf-card-summary {
    border-left: 3px solid #2D5F8A;
    padding-left: 14px;
    margin: 6px 0 16px;
}

/* Extras wrapper — gets a soft top divider so it visually separates
   from the always-visible summary */
.bf-card-extras {
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px solid #F2F2EE;
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
    font-size: 11.5px !important;
    font-weight: 500 !important;
    border-radius: 999px !important;
    padding: 4px 12px !important;
    min-height: 28px !important;
    line-height: 1.2 !important;
    box-shadow: none !important;
    transition: all 0.12s ease !important;
    white-space: nowrap !important;
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


def _build_extras_html(card: Card) -> str:
    """Build the FROM / DRAFTED / WHY / ATTACHMENTS HTML as a single
    string. Lives inside the <details> body so expansion is pure CSS."""
    avail_doc_types = {dt for dt, _ in card.docs}

    parts: list[str] = []

    # FROM block (only if email card)
    if card.from_email:
        parts.append(
            f'<div class="bf-block-h">FROM {card.from_email}</div>'
            f'<div class="bf-from">{_esc(card.from_body)}</div>'
        )

    # DRAFTED block
    body_with_links = _linkify_doc_refs(
        _esc(card.drafted_body), card.id, avail_doc_types,
    )
    parts.append(
        f'<div class="bf-block-h">{card.drafted_label} '
        f'&middot; TO {card.drafted_to}</div>'
        '<div class="bf-draft-wrap">'
        f'<div class="bf-draft-subject">Subject: {card.drafted_subject}</div>'
        f'<div class="bf-draft-body">{body_with_links}</div>'
        '</div>'
    )

    # WHY block
    why_label = (
        "WHY BROKERFLOW FLAGGED THIS"
        if card.type == "NEW BRAND"
        else "WHY BROKERFLOW DRAFTED THIS"
    )
    bullets_html = "".join(
        '<li>'
        f'<span class="bf-reason-text">{_esc(b.text)}</span>'
        + (f'<span class="bf-reason-src">&#8599; {b.source}</span>' if b.source else '')
        + '</li>'
        for b in card.reasoning
    )
    drafted_by = " &rarr; ".join(_AGENT_LABELS.get(a, a) for a in card.agent_origin)
    drafted_by_html = (
        f'<div class="bf-drafted-by">'
        f'Drafted by: <span class="bf-drafted-by-agent">{drafted_by}</span> '
        f'<span class="bf-drafted-by-time">&middot; {card.elapsed} ago</span>'
        f'</div>'
    ) if drafted_by else ""
    parts.append(
        f'<div class="bf-block-h">{why_label}</div>'
        f'{drafted_by_html}'
        f'<ul class="bf-reasoning">{bullets_html}</ul>'
    )

    # Attachments row
    if card.docs:
        from agents._shared import doc_storage as _ds
        items_html = []
        for doc_type, label in card.docs:
            info = _ds.get(card.id, doc_type)
            meta = "PDF · — pages" if not info else (
                f"PDF · {info['pages']} page{'s' if info['pages'] != 1 else ''}"
            )
            href = f"?nav=queue&open_doc={card.id}:{doc_type}"
            items_html.append(
                f'<a class="bf-attach-item" href="{href}" target="_self">'
                f'<span class="bf-attach-icon">&#128196;</span>'
                f'<span class="bf-attach-name">{label}</span>'
                f'<span class="bf-attach-meta">{meta}</span>'
                f'<span class="bf-attach-open">&#8599; Open</span>'
                f'</a>'
            )
        parts.append(
            '<div class="bf-attach-row">'
            '<div class="bf-attach-h">ATTACHMENTS</div>'
            + "".join(items_html) +
            '</div>'
        )

    return '<div class="bf-card-extras">' + "".join(parts) + '</div>'


def _render_card_unified(card: Card) -> None:
    """Single render for all cards. Extras live in a <details> so expand
    is a pure CSS state change — no Streamlit rerun, no re-fetch.

    Layout:
        [container border=True]
          [HEADER ROW columns]
            LEFT col: tag + needs + context
            RIGHT col: time | primary | edit | skip   (compact pills)
          [summary + <details> with extras]
    """
    avail_doc_types = {dt for dt, _ in card.docs}
    summary_with_links = _linkify_doc_refs(
        _esc(card.summary_html), card.id, avail_doc_types,
    )

    needs_tag = (
        '<span class="bf-tag bf-tag--needs">NEEDS YOU</span>'
        if card.needs_you else ""
    )
    header_left_html = (
        '<div class="bf-card-header-l">'
        f'<span class="bf-tag">{card.type}</span>'
        f'{needs_tag}'
        f'<span class="bf-context">{card.context}</span>'
        '</div>'
    )
    elapsed_html = f'<span class="bf-elapsed">{card.elapsed}</span>'

    with st.container(border=True):
        st.markdown('<div class="bf-card-marker"></div>',
                    unsafe_allow_html=True)

        # Header row — left content + right (time + 3 inline buttons)
        left_col, right_col = st.columns([1, 1.05])
        with left_col:
            st.markdown(header_left_html, unsafe_allow_html=True)
        with right_col:
            time_col, prim_col, edit_col, skip_col = st.columns(
                [0.45, 1.4, 0.65, 0.6]
            )
            with time_col:
                st.markdown(
                    f'<div class="bf-card-time-cell">{elapsed_html}</div>',
                    unsafe_allow_html=True,
                )
            with prim_col:
                if st.button(card.primary_action, key=f"prim_{card.id}",
                             type="primary", use_container_width=True):
                    _handle_send(card)
            with edit_col:
                if st.button("Edit", key=f"edit_{card.id}",
                             use_container_width=True):
                    st.session_state["expanded_card"] = card.id
                    st.session_state[f"editing_{card.id}"] = True
                    st.rerun()
            with skip_col:
                if st.button(card.skip_label, key=f"skip_{card.id}",
                             type="tertiary", use_container_width=True):
                    _handle_skip(card)

        # Summary + collapsible extras
        st.markdown(
            '<details class="bf-card-details">'
            '<summary class="bf-card-summary-row">'
            f'<div class="bf-card-summary">{summary_with_links}</div>'
            '<span class="bf-show-reasoning">'
            'Show reasoning <span class="bf-chevron">&darr;</span>'
            '</span>'
            '</summary>'
            + _build_extras_html(card)
            + '</details>',
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


def render_queue_topbar(crumb_parts: list[tuple[str, bool]]) -> None:
    """Combined topbar: breadcrumb LEFT, ask bar RIGHT, single row.

    Called by render_shell as the queue's custom_topbar slot. The marker
    div scopes the column-row CSS so it doesn't leak to other pages.

    The ask bar is wrapped in st.form(clear_on_submit=True) so the
    text_input clears automatically after each submit — without the
    form, Streamlit retains widget state across reruns and second
    submissions get garbled."""
    from ui.broker_shell import render_crumb_html

    cols = st.columns([1.6, 1])
    with cols[0]:
        st.markdown(
            '<div class="bf-queue-topbar-marker"></div>'
            + render_crumb_html(crumb_parts),
            unsafe_allow_html=True,
        )
    with cols[1]:
        with st.form("bf_ask_topbar_form", clear_on_submit=True,
                     border=False):
            query = st.text_input(
                "Ask BrokerFlow",
                placeholder="Ask BrokerFlow anything…",
                key="bf_ask_input",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Send", type="primary")
            if submitted and query.strip():
                _open_chat_with_query(query.strip())


# ── Slide-up chat panel ──────────────────────────────────────────────────────

def _render_chat_panel() -> None:
    """Fixed-bottom slide-up chat panel. Renders only when chat_open=True.

    Conversation lives in st.session_state.ask_conversation as a list of
    {"role": "user"|"assistant", "content": str}. Streaming uses an
    st.empty() placeholder updated per token."""
    history: list[dict] = st.session_state.setdefault("ask_conversation", [])
    pending = st.session_state.pop("chat_pending_query", None)

    with st.container():
        st.markdown('<div class="bf-chat-marker"></div>', unsafe_allow_html=True)

        # Header
        st.markdown(
            '<div class="bf-chat-head">'
            '<div class="bf-chat-head-l">'
            f'<a class="bf-chat-newchat" href="?nav=queue'
            f'{_preserve_filter_query()}&chat_clear=1" target="_self">'
            '<span class="bf-chat-newchat-plus">+</span> Ask BrokerFlow'
            '</a>'
            '</div>'
            f'<a class="bf-chat-close" href="?nav=queue'
            f'{_preserve_filter_query()}&chat_close=1" target="_self">&times;</a>'
            '</div>'
            '<div class="bf-chat-sub">I see all your brands, accruals, '
            'POs, demos, and email history.</div>'
            '<div class="bf-chat-scroll">',
            unsafe_allow_html=True,
        )

        # Render frozen conversation history
        for msg in history:
            _render_msg(msg["role"], msg["content"])

        # If a query is pending: render it as a user bubble + start streaming
        if pending:
            history.append({"role": "user", "content": pending})
            _render_msg("user", pending)

            placeholder = st.empty()
            full = ""
            try:
                from agents.ask_brokerflow import stream_ask
                # History EXCLUDES the just-appended pending turn
                prior = history[:-1]
                for tok in stream_ask(pending, prior):
                    full += tok
                    placeholder.markdown(
                        '<div class="bf-chat-msg-assistant">'
                        + _md_to_html(full) +
                        '<span class="bf-chat-cursor"></span></div>',
                        unsafe_allow_html=True,
                    )
            except Exception as exc:  # noqa: BLE001
                print(f"[chat_panel] stream failed: "
                      f"{type(exc).__name__}: {str(exc)[:200]}")
                full = full or (
                    "BrokerFlow is taking longer than usual. "
                    "Try rephrasing or ask again."
                )

            # Freeze final response
            placeholder.markdown(
                '<div class="bf-chat-msg-assistant">'
                + _md_to_html(full) +
                '</div>',
                unsafe_allow_html=True,
            )
            history.append({"role": "assistant", "content": full})

        st.markdown('</div>', unsafe_allow_html=True)  # close bf-chat-scroll

    # Footer input — st.form(clear_on_submit=True) so the input clears
    # on every Send. Without the form, Streamlit retains the previous
    # value and the second message gets dropped or garbled.
    with st.container():
        st.markdown('<div class="bf-chat-input-marker"></div>',
                    unsafe_allow_html=True)
        with st.form("bf_chat_followup_form", clear_on_submit=True,
                     border=False):
            followup = st.text_input(
                "Follow-up",
                placeholder="Ask anything…",
                key="bf_chat_followup",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Send", type="primary")
            if submitted and followup.strip():
                _submit_chat_query(followup.strip())


def _open_chat_with_query(query: str) -> None:
    """Open the chat panel and queue `query` as the first user message."""
    print(f"[chat] open_chat_with_query: {query!r}")
    st.session_state["chat_open"] = True
    st.session_state["chat_pending_query"] = query
    st.rerun()


def _submit_chat_query(query: str) -> None:
    """Submit a follow-up inside an already-open chat panel."""
    history_len = len(st.session_state.get("ask_conversation", []))
    print(f"[chat] submit_chat_query: {query!r} (history len before: {history_len})")
    st.session_state["chat_pending_query"] = query
    st.rerun()


def _render_msg(role: str, content: str) -> None:
    if role == "user":
        st.markdown(
            f'<div class="bf-chat-msg-user">{_esc(content)}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="bf-chat-msg-assistant">{_md_to_html(content)}</div>',
            unsafe_allow_html=True,
        )


def _md_to_html(md: str) -> str:
    """Light markdown → HTML for streaming responses. Handles bold, lists,
    paragraphs. Stays simple to avoid pulling a heavy markdown dep."""
    if not md:
        return ""
    text = _esc(md)

    # **bold** → <strong>
    import re
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    # _italic_ or *italic* → <em>  (single-char, not greedy)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)

    # Convert bullet lists block-by-block
    out_lines: list[str] = []
    in_ul = False
    for line in text.split("\n"):
        bullet = re.match(r"^\s*[-•]\s+(.*)", line)
        numbered = re.match(r"^\s*\d+[\.\)]\s+(.*)", line)
        if bullet or numbered:
            if not in_ul:
                out_lines.append("<ul>")
                in_ul = True
            item = (bullet or numbered).group(1)
            out_lines.append(f"<li>{item}</li>")
        else:
            if in_ul:
                out_lines.append("</ul>")
                in_ul = False
            out_lines.append(line)
    if in_ul:
        out_lines.append("</ul>")

    # Paragraphs from blank-line separated blocks
    blocks = "\n".join(out_lines).split("\n\n")
    html_blocks = []
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        if b.startswith("<ul>") or b.startswith("<ol>") or b.startswith("<li>"):
            html_blocks.append(b)
        else:
            html_blocks.append("<p>" + b.replace("\n", "<br>") + "</p>")
    return "\n".join(html_blocks)


def render_queue_view() -> None:
    st.markdown(_QUEUE_CSS, unsafe_allow_html=True)

    # Lazy-generate the seed PDFs once per session. Skipped if already on
    # disk (idempotent). Doesn't block render — runs synchronously but
    # is fast (~50ms total for the 6 seed cards) and only happens once.
    try:
        from ui.seed_docs import ensure_seed_docs
        ensure_seed_docs()
    except Exception as exc:  # noqa: BLE001
        print(f"[queue_view] seed PDF generation failed: "
              f"{type(exc).__name__}: {exc}")

    # All ?nav=, ?open_doc=, ?close_doc=, ?chat_*= query params are
    # handled by broker_shell.consume_nav_query_param() in one pass
    # before render_queue_view() runs.

    filter_key = st.session_state.get("queue_filter", "today")
    brand = st.session_state.get("queue_brand")
    cards = _filter_cards(filter_key, brand)

    label = _filter_label(filter_key, brand)
    count_word = "card" if len(cards) == 1 else "cards"

    # Section subheader (small, matches filter pills weight) + pills
    pills = []
    for key, lbl, _ in [
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
        f'<div class="bf-queue-h">{label} '
        f'<span class="bf-queue-h-count">&middot; {len(cards)} {count_word}</span></div>'
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

    # Single render path — extras live inside <details> so expand is
    # pure CSS (no Streamlit rerun, instant). See _render_card_unified.
    for card in cards:
        _render_card_unified(card)

    # Chat panel renders so it overlays the queue
    if st.session_state.get("chat_open"):
        _render_chat_panel()

    # Doc side panel renders LAST (highest z) so it overlays everything,
    # including the chat panel
    if st.session_state.get("doc_open"):
        _render_doc_panel()
