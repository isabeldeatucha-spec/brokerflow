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
        "unit_velocity_range": "8-14 units/store/week",
        "slotting_fees_paid": "$0 at Whole Foods, $8k at Sprouts",
        "best_seller_sku": "Original Beef Stick",
        "products": [
            {
                "sku_name": "Original Beef Stick",
                "upc": "850000303010",
                "case_pack": 24, "cases_per_pallet": 150,
                "net_weight": "1.15 oz",
                "wholesale_cost": 1.45, "msrp": 2.49, "margin_pct": 41.8,
                "shelf_life_days": 365, "storage_temp": "ambient",
                "launch_date": "2016-03-01",
                "ingredients": "Grass-fed beef, sea salt, celery powder, natural spices.",
                "allergens": [],
                "is_flagship": True,
            },
            {
                "sku_name": "Jalapeño Beef Stick",
                "upc": "850000303027",
                "case_pack": 24, "cases_per_pallet": 150,
                "net_weight": "1.15 oz",
                "wholesale_cost": 1.45, "msrp": 2.49, "margin_pct": 41.8,
                "shelf_life_days": 365, "storage_temp": "ambient",
                "launch_date": "2017-06-01",
                "ingredients": "Grass-fed beef, jalapeño, sea salt, celery powder, spices.",
                "allergens": [],
                "is_flagship": False,
            },
            {
                "sku_name": "Italian Style Beef Stick",
                "upc": "850000303034",
                "case_pack": 24, "cases_per_pallet": 150,
                "net_weight": "1.15 oz",
                "wholesale_cost": 1.45, "msrp": 2.49, "margin_pct": 41.8,
                "shelf_life_days": 365, "storage_temp": "ambient",
                "launch_date": "2018-09-01",
                "ingredients": "Grass-fed beef, Italian herbs, sea salt, celery powder.",
                "allergens": [],
                "is_flagship": False,
            },
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
        "unit_velocity_range": "4-7 units/store/week",
        "slotting_fees_paid": "$0 at Whole Foods, $5k at Erewhon",
        "best_seller_sku": "Smoked Atlantic Salmon",
        "products": [
            {
                "sku_name": "Smoked Atlantic Salmon",
                "upc": "810081960012",
                "case_pack": 12, "cases_per_pallet": 80,
                "net_weight": "3.5 oz",
                "wholesale_cost": 6.50, "msrp": 12.99, "margin_pct": 50.0,
                "shelf_life_days": 730, "storage_temp": "ambient",
                "launch_date": "2020-11-01",
                "ingredients": "Atlantic salmon, olive oil, salt.",
                "allergens": ["fish"],
                "is_flagship": True,
            },
            {
                "sku_name": "Smoked Rainbow Trout",
                "upc": "810081960029",
                "case_pack": 12, "cases_per_pallet": 80,
                "net_weight": "3.5 oz",
                "wholesale_cost": 6.50, "msrp": 12.99, "margin_pct": 50.0,
                "shelf_life_days": 730, "storage_temp": "ambient",
                "launch_date": "2021-04-01",
                "ingredients": "Rainbow trout, olive oil, salt, spices.",
                "allergens": ["fish"],
                "is_flagship": False,
            },
            {
                "sku_name": "Albacore Tuna with Jalapeño",
                "upc": "810081960036",
                "case_pack": 12, "cases_per_pallet": 80,
                "net_weight": "3.5 oz",
                "wholesale_cost": 6.00, "msrp": 11.99, "margin_pct": 50.0,
                "shelf_life_days": 730, "storage_temp": "ambient",
                "launch_date": "2022-01-01",
                "ingredients": "Albacore tuna, jalapeño, olive oil, salt.",
                "allergens": ["fish"],
                "is_flagship": False,
            },
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
        "unit_velocity_range": "5-9 units/store/week",
        "slotting_fees_paid": "$0 at Whole Foods, $0 at Target (test run)",
        "best_seller_sku": "Sizzle Olive Oil",
        "products": [
            {
                "sku_name": "Sizzle Olive Oil",
                "upc": "850021730016",
                "case_pack": 6, "cases_per_pallet": 60,
                "net_weight": "750 ml",
                "wholesale_cost": 8.50, "msrp": 15.99, "margin_pct": 46.8,
                "shelf_life_days": 548, "storage_temp": "ambient",
                "launch_date": "2022-01-10",
                "ingredients": "100% extra virgin olive oil (Picual variety, Spain).",
                "allergens": [],
                "is_flagship": True,
            },
            {
                "sku_name": "Drizzle Olive Oil",
                "upc": "850021730023",
                "case_pack": 6, "cases_per_pallet": 60,
                "net_weight": "500 ml",
                "wholesale_cost": 9.50, "msrp": 19.99, "margin_pct": 52.5,
                "shelf_life_days": 548, "storage_temp": "ambient",
                "launch_date": "2022-01-10",
                "ingredients": "100% extra virgin olive oil (Arbequina variety, Spain).",
                "allergens": [],
                "is_flagship": False,
            },
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
        "unit_velocity_range": "18-28 units/store/week",
        "slotting_fees_paid": "$0 at Whole Foods, $10k at Target",
        "best_seller_sku": "Vintage Cola",
        "products": [
            {
                "sku_name": "Vintage Cola",
                "upc": "857251007016",
                "case_pack": 12, "cases_per_pallet": 100,
                "net_weight": "12 fl oz",
                "wholesale_cost": 1.85, "msrp": 2.99, "margin_pct": 38.1,
                "shelf_life_days": 365, "storage_temp": "ambient",
                "launch_date": "2019-03-01",
                "ingredients": "Carbonated water, tapioca fiber, cassava root syrup, natural flavors, citric acid.",
                "allergens": [],
                "is_flagship": True,
            },
            {
                "sku_name": "Classic Grape",
                "upc": "857251007023",
                "case_pack": 12, "cases_per_pallet": 100,
                "net_weight": "12 fl oz",
                "wholesale_cost": 1.85, "msrp": 2.99, "margin_pct": 38.1,
                "shelf_life_days": 365, "storage_temp": "ambient",
                "launch_date": "2020-06-01",
                "ingredients": "Carbonated water, tapioca fiber, cassava root syrup, natural grape flavor, citric acid.",
                "allergens": [],
                "is_flagship": False,
            },
            {
                "sku_name": "Strawberry Vanilla",
                "upc": "857251007030",
                "case_pack": 12, "cases_per_pallet": 100,
                "net_weight": "12 fl oz",
                "wholesale_cost": 1.85, "msrp": 2.99, "margin_pct": 38.1,
                "shelf_life_days": 365, "storage_temp": "ambient",
                "launch_date": "2021-02-01",
                "ingredients": "Carbonated water, tapioca fiber, cassava root syrup, natural strawberry and vanilla flavors.",
                "allergens": [],
                "is_flagship": False,
            },
            {
                "sku_name": "Orange Squeeze",
                "upc": "857251007047",
                "case_pack": 12, "cases_per_pallet": 100,
                "net_weight": "12 fl oz",
                "wholesale_cost": 1.85, "msrp": 2.99, "margin_pct": 38.1,
                "shelf_life_days": 365, "storage_temp": "ambient",
                "launch_date": "2021-08-01",
                "ingredients": "Carbonated water, tapioca fiber, cassava root syrup, natural orange flavor, citric acid.",
                "allergens": [],
                "is_flagship": False,
            },
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
        "unit_velocity_range": "6-10 units/store/week",
        "slotting_fees_paid": "$12k at Whole Foods, $0 at Target (invited program)",
        "best_seller_sku": "Frosted Single Box",
        "products": [
            {
                "sku_name": "Frosted Single Box",
                "upc": "810041570122",
                "case_pack": 6, "cases_per_pallet": 48,
                "net_weight": "7 oz",
                "wholesale_cost": 6.50, "msrp": 11.99, "margin_pct": 45.8,
                "shelf_life_days": 365, "storage_temp": "ambient",
                "launch_date": "2022-03-01",
                "ingredients": "Whey protein blend, tapioca starch, chicory root fiber, natural flavors, salt.",
                "allergens": ["milk"],
                "is_flagship": True,
            },
            {
                "sku_name": "Cocoa Single Box",
                "upc": "810041570139",
                "case_pack": 6, "cases_per_pallet": 48,
                "net_weight": "7 oz",
                "wholesale_cost": 6.50, "msrp": 11.99, "margin_pct": 45.8,
                "shelf_life_days": 365, "storage_temp": "ambient",
                "launch_date": "2022-03-01",
                "ingredients": "Whey protein blend, cocoa powder, tapioca starch, chicory root fiber, natural flavors, salt.",
                "allergens": ["milk"],
                "is_flagship": False,
            },
            {
                "sku_name": "Peanut Butter Single Box",
                "upc": "810041570146",
                "case_pack": 6, "cases_per_pallet": 48,
                "net_weight": "7 oz",
                "wholesale_cost": 6.50, "msrp": 11.99, "margin_pct": 45.8,
                "shelf_life_days": 365, "storage_temp": "ambient",
                "launch_date": "2022-06-01",
                "ingredients": "Whey protein blend, peanut flour, tapioca starch, chicory root fiber, natural flavors, salt.",
                "allergens": ["milk", "peanuts"],
                "is_flagship": False,
            },
        ],
        "completeness_pct": 72.0,
        "status": "active",
        "is_sandbox": True,
    },
]


def _seed_coordination_messages(client, brand_id_map: dict) -> None:
    """Insert plausible fake coordination messages so the activity feed looks alive."""
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)

    fake_msgs = [
        {
            "from_agent": "freshness_watchdog",
            "to_agent": "brand_onboarding",
            "brand_id": brand_id_map.get("Fishwife"),
            "message_type": "needs_reverification",
            "payload": {"brand_name": "Fishwife", "days_stale": 32},
            "created_at": (now - timedelta(minutes=12)).isoformat(),
        },
        {
            "from_agent": "retailer_pitcher",
            "to_agent": "admin_ops",
            "brand_id": brand_id_map.get("Chomps"),
            "message_type": "pitch_drafted",
            "payload": {"brand_name": "Chomps", "retailer": "Whole Foods"},
            "created_at": (now - timedelta(hours=2)).isoformat(),
        },
        {
            "from_agent": "brand_onboarding",
            "to_agent": "retailer_matcher",
            "brand_id": brand_id_map.get("Graza"),
            "message_type": "new_brand_onboarded",
            "payload": {"brand_name": "Graza", "category": "pantry"},
            "created_at": (now - timedelta(hours=5)).isoformat(),
        },
        {
            "from_agent": "admin_ops",
            "to_agent": "retailer_pitcher",
            "brand_id": brand_id_map.get("Olipop"),
            "message_type": "form_completed",
            "payload": {"brand_name": "Olipop", "form_type": "WFM_new_item"},
            "created_at": (now - timedelta(hours=8)).isoformat(),
        },
        {
            "from_agent": "brand_scout",
            "to_agent": "brand_onboarding",
            "brand_id": brand_id_map.get("Magic Spoon"),
            "message_type": "evaluation_complete",
            "payload": {"brand_name": "Magic Spoon", "verdict": "broker_ready"},
            "created_at": (now - timedelta(days=1)).isoformat(),
        },
    ]
    # Drop any with a missing brand_id (brand seeding may have skipped it)
    fake_msgs = [m for m in fake_msgs if m.get("brand_id")]
    if fake_msgs:
        client.table("coordination_messages").insert(fake_msgs).execute()


def seed_sandbox_brands() -> list[str]:
    """Insert sandbox brands + fake coordination messages. Skips already-present brands."""
    from memory import _get_client
    client = _get_client()
    seeded = []
    brand_id_map: dict[str, str] = {}

    for brand in SANDBOX_BRANDS:
        existing = (
            client.table("brands")
            .select("id")
            .ilike("brand_name", brand["brand_name"])
            .limit(1)
            .execute()
        )
        if not existing.data:
            result = client.table("brands").insert(brand).execute()
            if result.data:
                brand_id_map[brand["brand_name"]] = result.data[0]["id"]
            seeded.append(brand["brand_name"])
        else:
            brand_id_map[brand["brand_name"]] = existing.data[0]["id"]

    if seeded:  # only seed messages when at least one brand was new
        try:
            _seed_coordination_messages(client, brand_id_map)
        except Exception:
            pass  # activity feed is cosmetic; never block brand seeding

    return seeded


def clear_sandbox_brands() -> int:
    """Delete sandbox brands and their coordination messages. Returns brands deleted."""
    from memory import _get_client
    client = _get_client()

    # Collect sandbox brand IDs first
    sandbox = client.table("brands").select("id").eq("is_sandbox", True).execute()
    sandbox_ids = [r["id"] for r in (sandbox.data or [])]

    if sandbox_ids:
        # Delete coordination messages tied to sandbox brands
        client.table("coordination_messages").delete().in_("brand_id", sandbox_ids).execute()

    # Delete the brands (FK CASCADE removes brand_events automatically)
    result = client.table("brands").delete().eq("is_sandbox", True).execute()
    return len(result.data or [])
