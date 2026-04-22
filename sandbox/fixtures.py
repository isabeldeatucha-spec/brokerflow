"""Sandbox fixtures for demo-day safety.

seed_sandbox_brands()  — inserts 5 well-known CPG brands with is_sandbox=True
clear_sandbox_brands() — deletes only rows where is_sandbox=True

Real broker data is never touched.
"""
from __future__ import annotations

SANDBOX_BRANDS = [
    {
        "brand_name": "Chomps",
        "category": "snacks",
        "subcategory": "meat snacks",
        "hq_state": "IL",
        "product_count": 12,
        "flagship_sku": "Original Beef Stick",
        "wholesale_price_range": "$1.50-$2.00",
        "retail_price_range": "$2.99-$3.49",
        "margin_range": "50-55%",
        "certifications": ["Non-GMO", "Paleo", "Whole30"],
        "current_retailers": ["Whole Foods", "Target", "Costco"],
        "target_retailers": ["Sprouts", "Erewhon"],
        "brand_story": (
            "Chomps makes grass-fed beef sticks with no sugar and clean ingredients. "
            "Founded in 2012, they're the top-selling meat snack on Amazon."
        ),
        "key_differentiators": [
            "Top-ranked on Amazon for meat snacks",
            "No sugar, no nitrates",
            "Whole30 approved",
        ],
        "completeness_pct": 82.0,
        "status": "active",
        "is_sandbox": True,
    },
    {
        "brand_name": "Fishwife",
        "category": "seafood",
        "subcategory": "tinned fish",
        "hq_state": "CA",
        "product_count": 8,
        "flagship_sku": "Smoked Atlantic Salmon",
        "wholesale_price_range": "$6.00-$8.00",
        "retail_price_range": "$11.99-$14.99",
        "margin_range": "48-52%",
        "certifications": ["MSC Certified"],
        "current_retailers": ["Whole Foods", "Erewhon"],
        "target_retailers": ["Sprouts", "Central Market"],
        "brand_story": (
            "Fishwife elevated tinned fish into a pantry staple with bold flavors "
            "and sustainable sourcing. Founded 2020, cult following on social media."
        ),
        "key_differentiators": [
            "Aesthetic packaging drove viral social media growth",
            "All fish sustainably sourced and MSC certified",
            "Premium positioning in an underserved category",
        ],
        "completeness_pct": 78.0,
        "status": "active",
        "is_sandbox": True,
    },
    {
        "brand_name": "Graza",
        "category": "pantry",
        "subcategory": "olive oil",
        "hq_state": "NY",
        "product_count": 3,
        "flagship_sku": "Sizzle Olive Oil",
        "wholesale_price_range": "$8.00-$10.00",
        "retail_price_range": "$14.99-$19.99",
        "margin_range": "52-58%",
        "certifications": ["Extra Virgin"],
        "current_retailers": ["Whole Foods", "Target"],
        "target_retailers": ["Sprouts", "Fresh Market"],
        "brand_story": (
            "Graza reimagined olive oil with squeeze bottles and two-oil philosophy: "
            "Sizzle for cooking, Drizzle for finishing. $10M in year-one revenue."
        ),
        "key_differentiators": [
            "Squeeze bottle format is category-defining",
            "Single-origin Spanish EVOO",
            "DTC-first with explosive social growth",
        ],
        "completeness_pct": 75.0,
        "status": "active",
        "is_sandbox": True,
    },
    {
        "brand_name": "Olipop",
        "category": "beverages",
        "subcategory": "functional soda",
        "hq_state": "CA",
        "product_count": 15,
        "flagship_sku": "Vintage Cola",
        "wholesale_price_range": "$1.80-$2.20",
        "retail_price_range": "$2.99-$3.49",
        "margin_range": "45-50%",
        "certifications": ["Non-GMO", "Vegan"],
        "current_retailers": ["Whole Foods", "Target", "Sprouts", "Walmart"],
        "target_retailers": ["Costco", "Kroger"],
        "brand_story": (
            "Olipop makes prebiotic sodas with 9g of fiber and classic soda flavors. "
            "The fastest-growing beverage brand in the US, now at $200M+ revenue."
        ),
        "key_differentiators": [
            "Gut health positioning in the $100B soda category",
            "9g fiber vs 0 in conventional soda",
            "Celeb-backed with massive social following",
        ],
        "completeness_pct": 88.0,
        "status": "active",
        "is_sandbox": True,
    },
    {
        "brand_name": "Magic Spoon",
        "category": "breakfast",
        "subcategory": "cereal",
        "hq_state": "NY",
        "product_count": 10,
        "flagship_sku": "Frosted Variety Pack",
        "wholesale_price_range": "$6.00-$7.50",
        "retail_price_range": "$10.99-$12.99",
        "margin_range": "50-55%",
        "certifications": ["Keto Certified", "Grain-Free"],
        "current_retailers": ["Whole Foods", "Target"],
        "target_retailers": ["Sprouts", "Erewhon"],
        "brand_story": (
            "Magic Spoon reinvented childhood cereals as high-protein, low-sugar, "
            "keto-friendly. Started DTC, now expanding into retail with $85M raised."
        ),
        "key_differentiators": [
            "13-14g protein vs 2-3g in conventional cereal",
            "0g sugar, grain-free",
            "Nostalgia marketing with adult positioning",
        ],
        "completeness_pct": 72.0,
        "status": "active",
        "is_sandbox": True,
    },
]


def seed_sandbox_brands() -> list[str]:
    """Insert sandbox brands. Skips any already present. Returns list of seeded names."""
    from memory import _get_client
    client = _get_client()
    seeded = []
    for brand in SANDBOX_BRANDS:
        existing = (
            client.table("brands")
            .select("id")
            .ilike("brand_name", brand["brand_name"])
            .limit(1)
            .execute()
        )
        if not existing.data:
            client.table("brands").insert(brand).execute()
            seeded.append(brand["brand_name"])
    return seeded


def clear_sandbox_brands() -> int:
    """Delete all rows where is_sandbox=True. Returns count deleted."""
    from memory import _get_client
    client = _get_client()
    result = (
        client.table("brands")
        .delete()
        .eq("is_sandbox", True)
        .execute()
    )
    return len(result.data or [])
