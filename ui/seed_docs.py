"""Lazy PDF generation for the queue's six seed cards.

Called once per Streamlit session via ensure_seed_docs(). Skips work if
the PDFs already exist in the local static dir, so we don't regenerate
on every rerun.

The payload dicts here intentionally embed the same numbers shown in the
queue card body — keeps the PDF and the card visually consistent.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from agents._shared import doc_storage


_BROKER = {
    "broker_name":  "Nadia Vega",
    "broker_email": "nadia@vegabrokerage.com",
    "broker_phone": "(415) 555-0114",
}


_SEED_PAYLOADS: dict[tuple[str, str], dict] = {
    # ── Card 1: Brami × Costco NW (sell sheet + cost build) ────────────────
    ("card-1", "sell_sheet"): {
        "brand_name": "Brami",
        "tagline":    "Lupini bean snacks",
        "category":   "Better-for-you snacks",
        "retailer":   "Costco NW",
        "contact":    "Marcus Alvarez",
        "stats": [
            ("3.1×",    "FAIRE VELOCITY · PNW"),
            ("$1.99",   "INTRO PRICE"),
            ("32%",     "RETAILER MARGIN"),
        ],
        "story": (
            "Brami brings the Mediterranean lupini bean — high in plant "
            "protein, low in carbs, and with a pickled snap that doesn't "
            "exist anywhere else on the snack aisle.\n\n"
            "Built by a co-founder who walked the family farm in Apulia "
            "and brought the bean home to Brooklyn. Three years of indie "
            "shop velocity, two years of D2C compounding, now ready for "
            "the club channel.\n\n"
            "Costco NW is the natural next door: buyer mix skews "
            "high-protein, the lupini SKU pencils at $1.99 with a clean "
            "32% retailer margin, and Faire data shows the brand is "
            "already indexing 3.1× over the snack baseline in PNW indie."
        ),
        "channel_performance": [
            ["Faire",     "3.1×",   "Top 5% snacks PNW",  "Promo-clean velocity"],
            ["Instacart", "2.4×",   "12 banners live",    "MoM growth +18%"],
            ["Amazon",    "—",      "Subscriber base",    "Intentional pacing"],
            ["DTC",       "+22%",   "12k subs",           "Q1 trend"],
        ],
        "promo_note": (
            "Promo independence score 0.91 — the velocity curve does "
            "not rely on TPRs. Brami's last 4 events at indie were "
            "deep-discount-free, and the post-event run rate held "
            "92% of the on-promo peak."
        ),
        "skus": [
            {"name": "Sea Salt 5oz",  "case_pack": "12", "dims": "11×8×4 in",
             "upc":  "853748000110", "fob": "$1.05",   "srp":  "$1.99"},
            {"name": "Garlic 5oz",    "case_pack": "12", "dims": "11×8×4 in",
             "upc":  "853748000127", "fob": "$1.05",   "srp":  "$1.99"},
        ],
        "margin_stack": [
            ["Suggested retail (SRP)",      "$1.99"],
            ["Retailer margin (32%)",       "$0.64"],
            ["Wholesale to retailer",       "$1.35"],
            ["Slotting fee (1× SKU)",       "$1,200"],
            ["Promo allowance (3 events)",  "$900"],
            ["Brand contribution / unit",   "$0.43"],
        ],
        "coop_terms": (
            "Standard 3% co-op MDF accrual on net wholesale, plus a "
            "$5,400 demo budget across the May reset window (3 events, "
            "1,800 stores eligible). Net 60 pay terms, free freight FOB "
            "Brooklyn co-packer."
        ),
        **_BROKER,
    },
    ("card-1", "cost_build"): {
        "brand_name": "Brami",
        "retailer":   "Costco NW",
    },

    # ── Card 2: Steep Sparkling (one-pager) ────────────────────────────────
    ("card-2", "one_pager"): {
        "brand_name": "Steep Sparkling",
        "category":   "Sparkling tea (RTD beverage)",
        "score":      87,
        "tier":       "Broker Ready",
        "breakdown": [
            ("Velocity proof",         22, 25),
            ("Distribution density",   16, 20),
            ("Margin viability",       14, 20),
            ("Brand story clarity",    18, 20),
            ("Promo independence",     17, 15),
        ],
        "findings": [
            {"text": "Top 5% Faire beverage Q1 — 4.2× category baseline.",
             "source": "EVENTS"},
            {"text": "Instacart trending score 88/100, no promo dependency.",
             "source": "EVENTS"},
            {"text": "11 indie specialty shops in CA/NW already carry it.",
             "source": "EVENTS"},
            {"text": "Single-origin tea + functional adaptogen claim — "
                     "story holds at the shelf.",
             "source": ""},
            {"text": "Founders dropped previous broker in March; CA / NW "
                     "is open territory.",
             "source": "EVENTS"},
        ],
        "interest": (
            "Steep Sparkling fits the gap left by a churn in your "
            "beverage stack: enough velocity to pitch tier-1 retail, "
            "premium positioning that won't cannibalize Olipop in your "
            "existing set, and clean promo math that doesn't require "
            "you to babysit TPRs. Risk: margin viability is 14/20 — "
            "they'll need to land at SRP $4.99 for the Costco math to "
            "pencil."
        ),
        "next_step": (
            "15-min intro call this week. Lead with PNW + CA distribution "
            "white space. If they flex SRP to $4.99, draft a Costco NW "
            "pitch immediately."
        ),
    },

    # ── Card 3: Olipop × Whole Foods (UNFI new-item form) ──────────────────
    ("card-3", "new_item_form"): {
        "retailer":   "Whole Foods",
        "brand_name": "Olipop",
        "skus": [
            "Strawberry Vanilla 12oz",
            "Vintage Cola 12oz",
            "Cherry Vanilla 12oz",
            "Orange Cream 12oz",
            "Banana Cream 12oz",
            "Doctor Goodwin 12oz",
        ],
        "fields": [
            {"label": "Brand", "value": "Olipop", "status": "OK"},
            {"label": "Category / subcategory",
             "value": "Beverages / Sparkling tonic", "status": "OK"},
            {"label": "Case pack (Banana Cream)", "value": "—",
             "status": "NEEDS CONFIRMATION"},
            {"label": "Pallet ti / hi (Banana Cream)", "value": "—",
             "status": "NEEDS CONFIRMATION"},
            {"label": "FOB origin (Banana Cream)", "value": "—",
             "status": "NEEDS CONFIRMATION"},
            {"label": "Slotting fee acceptance",
             "value": "$1,200/SKU — pending brand confirm",
             "status": "NEEDS CONFIRMATION"},
            {"label": "Cost (FOB, all 6 SKUs)", "value": "$1.42 / unit",
             "status": "OK"},
            {"label": "Suggested retail",        "value": "$2.99",
             "status": "OK"},
            {"label": "Retailer margin",         "value": "47%",
             "status": "OK"},
            {"label": "GTIN / UPC (5 SKUs)", "value": "On file in canonical record",
             "status": "OK"},
        ],
        "outstanding": [
            "Case pack dimensions for Banana Cream "
            "(carton L × W × H, gross weight)",
            "Pallet ti × hi configuration for Banana Cream",
            "Slotting fee acceptance ($1,200/SKU per Whole Foods schedule)",
            "FOB origin confirmation for Banana Cream — co-packer not "
            "yet finalized",
        ],
        "certs": [
            {"name": "USDA Organic", "id": "1247-A",
             "expires": "2026-06-05", "status": "expires in 31 days"},
            {"name": "Non-GMO Project", "id": "NGM-99412",
             "expires": "2027-02-14", "status": "current"},
            {"name": "Kosher (OU)", "id": "OU-K-22408",
             "expires": "2027-09-30", "status": "current"},
        ],
    },

    # ── Card 4: Spudsy × Sprouts (renewal sheet) ───────────────────────────
    ("card-4", "sell_sheet"): {
        "brand_name": "Spudsy",
        "tagline":    "Sweet potato puffs · upcycled",
        "category":   "Better-for-you snacks · gluten-free",
        "retailer":   "Sprouts",
        "contact":    "Danielle Ortiz",
        "stats": [
            ("+18%", "BA VOLUME YoY"),
            ("$126", "PALLET RATE (FY26)"),
            ("$134", "COMPARABLE NW RATE"),
        ],
        "story": (
            "FY27 renewal proposal for Spudsy in the Sprouts BA region. "
            "Volume is up 18% year-over-year on the same SKU mix — a "
            "rate of growth that's outpacing the rest of the puff "
            "category at Sprouts.\n\n"
            "Holding the pallet rate flat at $126 for FY27 to keep the "
            "renewal smooth. Flagging for the next category review (Q3) "
            "that NW has comparable Spudsy volume at $134/pallet — "
            "there's room to revisit BA pricing then.\n\n"
            "No structural changes to the SKU set or merchandising plan. "
            "Continuing the current 4-event TPR cadence; volume curve "
            "shows the brand doesn't need a fifth."
        ),
        "channel_performance": [
            ["Sprouts BA",  "+18% YoY",  "232 stores",        "Renewal target"],
            ["Sprouts NW",  "+12% YoY",  "189 stores",        "Comparable rate $134"],
            ["Whole Foods", "+9% YoY",   "Regional",          "Q4 expansion pending"],
            ["DTC",         "+34%",      "8k subs",           "Compounding"],
        ],
        "promo_note": (
            "Promo independence improving — TPR reliance dropped from "
            "0.71 to 0.62 across FY26. The Q3 review is the right window "
            "to push for higher rate; until then, hold."
        ),
        "skus": [
            {"name": "Cinnamon Churro 4.5oz", "case_pack": "12",
             "dims": "10×8×4 in", "upc": "812345700089", "fob": "$1.95",
             "srp": "$3.99"},
            {"name": "BBQ 4.5oz", "case_pack": "12",
             "dims": "10×8×4 in", "upc": "812345700096", "fob": "$1.95",
             "srp": "$3.99"},
        ],
        "margin_stack": [
            ["SRP",                          "$3.99"],
            ["Retailer margin (35%)",        "$1.40"],
            ["Wholesale to retailer",        "$2.59"],
            ["Pallet rate (FY26 = FY27)",    "$126"],
            ["Brand contribution / unit",    "$0.64"],
        ],
        "coop_terms": (
            "Continuing FY26 terms: 3% co-op MDF, 4 TPR events per year, "
            "demo allowance held at $4,200 across BA. Net 60."
        ),
        **_BROKER,
    },

    # ── Card 5: Stride Bites (one-pager) ───────────────────────────────────
    ("card-5", "one_pager"): {
        "brand_name": "Stride Bites",
        "category":   "Functional protein cookies",
        "score":      72,
        "tier":       "Worth a Look",
        "breakdown": [
            ("Velocity proof",         24, 25),
            ("Distribution density",   11, 20),
            ("Margin viability",        9, 20),
            ("Brand story clarity",    16, 20),
            ("Promo independence",     12, 15),
        ],
        "findings": [
            {"text": "6× Instacart category baseline over the last 30 days.",
             "source": "EVENTS"},
            {"text": "Distribution still DTC + Instacart only — no shelf yet.",
             "source": "EVENTS"},
            {"text": "Retailer margin tight: 24% at SRP $5.49 (under "
                     "the 28% threshold most of your retailers want).",
             "source": ""},
            {"text": "Founder narrative thin; functional claim "
                     "(15g protein, 3g sugar) is the strongest hook.",
             "source": ""},
            {"text": "TPR dependency visible in week-over-week curve "
                     "(promo independence 12/15).",
             "source": "EVENTS"},
        ],
        "interest": (
            "Velocity is exceptional but margin gap is the swing factor. "
            "If Stride can flex SRP to $5.99, retailer margin clears 28% "
            "and the Instacart velocity story carries the rest of the "
            "pitch. Worth a 15-min call before any retail outreach."
        ),
        "next_step": (
            "Intro call to test SRP flex. Park a Costco NW pitch in "
            "drafts for if they say yes."
        ),
    },

    # ── Card 6: Tia Lupita × KeHE (new-item form) ──────────────────────────
    ("card-6", "new_item_form"): {
        "retailer":   "KeHE",
        "brand_name": "Tia Lupita",
        "skus": ["Salsa Verde 16oz"],
        "fields": [
            {"label": "Brand", "value": "Tia Lupita", "status": "OK"},
            {"label": "Category / subcategory",
             "value": "Salsa & dips / Salsa verde", "status": "OK"},
            {"label": "Cost (FOB)", "value": "$2.65 / unit", "status": "OK"},
            {"label": "Suggested retail", "value": "$5.99", "status": "OK"},
            {"label": "Retailer margin",  "value": "55%",   "status": "OK"},
            {"label": "Case pack dimensions (L × W × H)", "value": "—",
             "status": "NEEDS CONFIRMATION"},
            {"label": "Slotting fee acceptance ($800/SKU)", "value": "—",
             "status": "NEEDS CONFIRMATION"},
            {"label": "FOB origin (port vs. domestic copacker)", "value": "—",
             "status": "NEEDS CONFIRMATION"},
            {"label": "Broker code assignment", "value": "—",
             "status": "NEEDS CONFIRMATION"},
            {"label": "Allergen panel",  "value": "Contains: none",
             "status": "OK"},
            {"label": "GTIN / UPC",      "value": "856101003047", "status": "OK"},
            {"label": "Net weight",      "value": "16 oz / 454 g", "status": "OK"},
            {"label": "Country of origin", "value": "USA",        "status": "OK"},
        ],
        "outstanding": [
            "Case pack dimensions (carton L × W × H, gross weight)",
            "Slotting fee acceptance — KeHE Q2 schedule = $800/SKU",
            "FOB origin (port of entry vs. domestic copacker)",
            "Broker code: Nadia = BR-NA-0241 (confirm)",
        ],
        "certs": [
            {"name": "Non-GMO Project", "id": "NGM-77821",
             "expires": "2027-04-12", "status": "current"},
            {"name": "Vegan Action",    "id": "VA-994",
             "expires": "2027-01-08",  "status": "current"},
        ],
    },
}


def ensure_seed_docs() -> None:
    """Generate any seed PDFs that aren't on disk yet. Idempotent.
    Cached in session_state so we only check once per session."""
    if st.session_state.get("_seed_docs_ready"):
        return

    from ui.queue_view import SEED_CARDS
    cards_by_id = {c.id: c for c in SEED_CARDS}

    for (card_id, doc_type), payload in _SEED_PAYLOADS.items():
        card = cards_by_id.get(card_id)
        if not card or not card.agent_origin:
            continue
        agent_for_doc = (
            "retailer_pitcher" if doc_type in ("sell_sheet", "cost_build")
            else "brand_scout"  if doc_type == "one_pager"
            else "new_item_forms"
        )
        try:
            doc_storage.ensure_pdf(card_id, agent_for_doc, doc_type, payload)
        except Exception as exc:  # noqa: BLE001
            print(f"[seed_docs] {card_id}/{doc_type} failed: "
                  f"{type(exc).__name__}: {exc}")

    st.session_state["_seed_docs_ready"] = True
