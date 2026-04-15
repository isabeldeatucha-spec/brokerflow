"""Buyer persona library — drives the personalization of email and sell sheet.

Each persona is a compact description a food broker would recognize: what the
buyer cares about, what kills a pitch, and which proof points resonate. These
are reused across the prompts so the email tone and the sell sheet highlights
stay consistent.

Adding a new retailer? Drop another dict below and add it to BUYER_PERSONAS.
"""
from __future__ import annotations

from typing import TypedDict


class BuyerPersona(TypedDict):
    retailer: str
    buyer_title: str
    cares_about: list[str]
    kills_pitch: list[str]
    proof_points: list[str]
    tone: str


BUYER_PERSONAS: dict[str, BuyerPersona] = {
    "whole_foods": {
        "retailer": "Whole Foods Market",
        "buyer_title": "Regional Category Manager",
        "cares_about": [
            "clean-label ingredients (no artificial colors, flavors, preservatives)",
            "clear unique positioning in a defined category",
            "evidence of existing velocity at comparable banners",
            "promotional calendar that does not rely on broker subsidies",
        ],
        "kills_pitch": [
            "ingredient panel with seed oils or artificial sweeteners",
            "vague positioning ('we taste great and are healthy')",
            "no retail proof — only DTC and Amazon",
        ],
        "proof_points": [
            "velocity at Sprouts, Erewhon, or Wegmans",
            "third-party certifications (Non-GMO, Organic, Fair Trade)",
            "press in NOSH, FoodNavigator, New Hope",
        ],
        "tone": "warm, specific, confident — treat the buyer as a peer running a category, not a gatekeeper",
    },
    "sprouts": {
        "retailer": "Sprouts Farmers Market",
        "buyer_title": "Innovation Center Buyer",
        "cares_about": [
            "emerging brands in the sprouts 'Innovation Center' program",
            "margin stack that works with their promotional cadence",
            "brand story that supports in-store demo and storytelling",
            "velocity in their Southwest and California regions",
        ],
        "kills_pitch": [
            "cost structure that cannot support 4-week TPR cycles",
            "no existing regional velocity data",
            "insufficient brand-owned promotional funding",
        ],
        "proof_points": [
            "case pack and cost structure aligned with Sprouts TPR cadence",
            "social proof (>50k engaged Instagram followers)",
            "clear hero SKU with high reorder rate",
        ],
        "tone": "pragmatic, numbers-forward — the Sprouts IC is a data-driven team",
    },
    "erewhon": {
        "retailer": "Erewhon Market",
        "buyer_title": "Category Buyer",
        "cares_about": [
            "brand narrative and founder story that fits Erewhon's aspirational shopper",
            "premium price points and high-quality ingredients",
            "Los Angeles market relevance",
            "exclusivity or co-marketing angles (smoothie collabs, pop-ups)",
        ],
        "kills_pitch": [
            "mass-market positioning or price point below $6 SRP",
            "generic wellness claims without a founder POV",
            "inability to support LA pop-ups or influencer seeding",
        ],
        "proof_points": [
            "celebrity / founder story",
            "press in goop, Well+Good, Vogue",
            "existing LA-based velocity or cultural moments",
        ],
        "tone": "narrative-led, aspirational — the pitch reads like a founder letter with proof",
    },
}


def get_persona(buyer_key: str) -> BuyerPersona:
    if buyer_key not in BUYER_PERSONAS:
        raise KeyError(
            f"Unknown buyer_key {buyer_key!r}. Available: {list(BUYER_PERSONAS)}"
        )
    return BUYER_PERSONAS[buyer_key]


def select_buyer_for_brand(category: str, score: int) -> str:
    """Heuristic buyer selection based on Brand Scout output.

    Not a learned model — deliberately simple rules we can audit in HW8.
    """
    if score >= 80:
        return "whole_foods"
    if category in {"olive_oil", "skincare", "beauty", "chocolate",
                    "na_aperitif", "na_spirit", "coffee"}:
        return "erewhon"
    return "sprouts"
