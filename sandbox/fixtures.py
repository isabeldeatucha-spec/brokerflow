"""Sandbox fixtures — 5 fully-loaded CPG brands for end-to-end demos.

seed_sandbox_brands()   — inserts brands + pre-computed brand_evaluations
clear_sandbox_brands()  — removes all sandbox brands and their evaluations
verify_sandbox_brands() — prints a readiness summary to stdout

Internal consistency guarantees (enforced in data below):
  wholesale_case_cost = case_pack × wholesale_unit_cost  (to the cent)
  cases_per_pallet    = cases_per_layer × layers_per_pallet
  net_weight_grams    ≈ net_weight_oz × 28.35  (rounded)
  GTINs are 14 numeric digits; UPCs are 12 numeric digits
"""
from __future__ import annotations

from datetime import datetime, timezone


# ─────────────────────────────────────────────────────────────────────────────
# SANDBOX_BRANDS  →  brands table
# ─────────────────────────────────────────────────────────────────────────────

SANDBOX_BRANDS: list[dict] = [

    # ══════════════════════════════════════════════════════════════════════════
    # CHOMPS — shelf-stable meat snacks
    # ══════════════════════════════════════════════════════════════════════════
    {
        "brand_name":            "Chomps",
        "website_url":           "https://chomps.com",
        "category":              "snacks",
        "subcategory":           "meat snacks",
        "founded_year":          2012,
        "hq_city":               "Chicago",
        "hq_state":              "IL",
        "founder_name":          "Pete Maldonado",
        "founder_email":         "pete@chomps.com",
        "product_count":         3,
        "flagship_sku":          "Original Beef Stick",
        "best_seller_sku":       "Original Beef Stick",
        "wholesale_price_range": "$1.45–$1.65",
        "retail_price_range":    "$2.49–$2.99",
        "margin_range":          "55–60%",
        "distributor_list":      ["UNFI", "KeHE"],
        "current_retailers":     ["Whole Foods", "Target", "Costco", "Sprouts", "Walmart"],
        "target_retailers":      ["Erewhon", "CVS"],
        "certifications":        [
            "Non-GMO Project Verified", "Paleo Certified",
            "Whole30 Approved", "Gluten-Free Certified",
        ],
        "brand_story": (
            "Chomps makes grass-fed beef and turkey sticks with no sugar, no nitrates, "
            "and a five-ingredient panel. Founded in 2012 by Pete Maldonado and Rashid Ali, "
            "it's the #1 meat snack on Amazon and available in 8,500+ stores across the US."
        ),
        "key_differentiators": [
            "#1 meat snack on Amazon — 45,000+ reviews, 4.7★ average",
            "Five-ingredient panel: grass-fed beef, water, sea salt, organic spices, celery powder",
            "Triple-certified: Non-GMO, Paleo, and Whole30 — covers all natural-channel buyer asks",
        ],
        "unit_velocity_range":  "10–16 units/store/week",
        "slotting_fees_paid":   "$0 at Whole Foods (invited program), $8,000 at Sprouts",
        "completeness_pct":     94.0,
        "status":               "active",
        "is_sandbox":           True,
        "products": [
            {
                # ── Identity ──────────────────────────────────────────────────
                "sku_id":           "CH-OBS-001",
                "sku_name":         "Original Beef Stick",
                "product_name":     "Original Beef Stick",
                "flavor_or_variant":"Original Beef",
                "is_flagship":      True,
                "gtin":             "00850000303010",
                "upc":              "850000303010",
                # ── Physical ──────────────────────────────────────────────────
                "net_weight":       "1.15 oz",
                "net_weight_oz":    1.15,
                "net_weight_grams": 33,             # round(1.15 × 28.35)
                "package_type":     "stick",
                "package_dimensions_in": {"length": 6.0, "width": 1.25, "height": 1.25},
                "shelf_life_days":  365,
                "shelf_life_months":12,
                "storage_temp":     "ambient",
                "requires_refrigeration": False,
                "requires_freezer": False,
                # ── Case / pallet ─────────────────────────────────────────────
                "case_pack":        24,
                "case_dimensions_in": {"length": 14.0, "width": 10.0, "height": 5.0},
                "case_weight_lbs":  4.0,
                "cases_per_layer":  12,
                "layers_per_pallet":10,
                "cases_per_pallet": 120,            # 12 × 10
                "ti_hi":            "12×10",
                # ── Pricing ───────────────────────────────────────────────────
                "wholesale_cost":         1.45,     # legacy field name (Admin Ops reads this)
                "wholesale_unit_cost_usd":1.45,
                "wholesale_case_cost_usd":34.80,    # 24 × 1.45
                "msrp":                  2.49,      # legacy field name (Admin Ops reads this)
                "srp_usd":               2.49,
                "msrp_usd":              2.49,
                "promotional_srp_usd":   1.99,
                "margin_pct":            41.8,      # (2.49 − 1.45) / 2.49
                # ── Free fill / launch terms ──────────────────────────────────
                "free_fill_cases_per_store":1,
                "slotting_fee_per_sku_usd": 0,
                # ── Nutrition (per 1 stick / 33g) ─────────────────────────────
                "serving_size":           "1 stick (33g)",
                "servings_per_container": 1,
                "nutrition": {
                    "calories": 100, "total_fat_g": 7.0, "saturated_fat_g": 3.0,
                    "sodium_mg": 480, "total_carbs_g": 1.0, "sugar_g": 0.0,
                    "added_sugar_g": 0.0, "protein_g": 9.0, "fiber_g": 0.0,
                },
                # ── Compliance ────────────────────────────────────────────────
                "ingredients":     "Grass-Fed Beef, Water, Sea Salt, Organic Spices, Celery Powder.",
                "allergens":        [],
                "contains_gluten":  False,
                "kosher_certified": True,
                "organic_certified":False,
                "country_of_origin":"USA",
                "launch_date":      "2016-03-01",
            },
            {
                "sku_id":           "CH-JBS-002",
                "sku_name":         "Jalapeño Beef Stick",
                "product_name":     "Jalapeño Beef Stick",
                "flavor_or_variant":"Jalapeño Beef",
                "is_flagship":      False,
                "gtin":             "00850000303027",
                "upc":              "850000303027",
                "net_weight":       "1.15 oz",
                "net_weight_oz":    1.15,
                "net_weight_grams": 33,
                "package_type":     "stick",
                "package_dimensions_in": {"length": 6.0, "width": 1.25, "height": 1.25},
                "shelf_life_days":  365,
                "shelf_life_months":12,
                "storage_temp":     "ambient",
                "requires_refrigeration": False,
                "requires_freezer": False,
                "case_pack":        24,
                "case_dimensions_in": {"length": 14.0, "width": 10.0, "height": 5.0},
                "case_weight_lbs":  4.0,
                "cases_per_layer":  12,
                "layers_per_pallet":10,
                "cases_per_pallet": 120,
                "ti_hi":            "12×10",
                "wholesale_cost":         1.45,
                "wholesale_unit_cost_usd":1.45,
                "wholesale_case_cost_usd":34.80,
                "msrp":                  2.49,
                "srp_usd":               2.49,
                "msrp_usd":              2.49,
                "promotional_srp_usd":   1.99,
                "margin_pct":            41.8,
                "free_fill_cases_per_store":1,
                "slotting_fee_per_sku_usd": 0,
                "serving_size":           "1 stick (33g)",
                "servings_per_container": 1,
                "nutrition": {
                    "calories": 100, "total_fat_g": 7.0, "saturated_fat_g": 3.0,
                    "sodium_mg": 500, "total_carbs_g": 1.0, "sugar_g": 0.0,
                    "added_sugar_g": 0.0, "protein_g": 9.0, "fiber_g": 0.0,
                },
                "ingredients":     "Grass-Fed Beef, Water, Jalapeño Powder, Sea Salt, Organic Spices, Celery Powder.",
                "allergens":        [],
                "contains_gluten":  False,
                "kosher_certified": True,
                "organic_certified":False,
                "country_of_origin":"USA",
                "launch_date":      "2017-06-01",
            },
            {
                "sku_id":           "CH-IBS-003",
                "sku_name":         "Italian Style Beef Stick",
                "product_name":     "Italian Style Beef Stick",
                "flavor_or_variant":"Italian Style",
                "is_flagship":      False,
                "gtin":             "00850000303034",
                "upc":              "850000303034",
                "net_weight":       "1.15 oz",
                "net_weight_oz":    1.15,
                "net_weight_grams": 33,
                "package_type":     "stick",
                "package_dimensions_in": {"length": 6.0, "width": 1.25, "height": 1.25},
                "shelf_life_days":  365,
                "shelf_life_months":12,
                "storage_temp":     "ambient",
                "requires_refrigeration": False,
                "requires_freezer": False,
                "case_pack":        24,
                "case_dimensions_in": {"length": 14.0, "width": 10.0, "height": 5.0},
                "case_weight_lbs":  4.0,
                "cases_per_layer":  12,
                "layers_per_pallet":10,
                "cases_per_pallet": 120,
                "ti_hi":            "12×10",
                "wholesale_cost":         1.45,
                "wholesale_unit_cost_usd":1.45,
                "wholesale_case_cost_usd":34.80,
                "msrp":                  2.49,
                "srp_usd":               2.49,
                "msrp_usd":              2.49,
                "promotional_srp_usd":   1.99,
                "margin_pct":            41.8,
                "free_fill_cases_per_store":1,
                "slotting_fee_per_sku_usd": 0,
                "serving_size":           "1 stick (33g)",
                "servings_per_container": 1,
                "nutrition": {
                    "calories": 100, "total_fat_g": 7.0, "saturated_fat_g": 3.0,
                    "sodium_mg": 480, "total_carbs_g": 1.0, "sugar_g": 0.0,
                    "added_sugar_g": 0.0, "protein_g": 9.0, "fiber_g": 0.0,
                },
                "ingredients":     "Grass-Fed Beef, Water, Italian Seasoning, Sea Salt, Organic Spices, Celery Powder, Paprika.",
                "allergens":        [],
                "contains_gluten":  False,
                "kosher_certified": True,
                "organic_certified":False,
                "country_of_origin":"USA",
                "launch_date":      "2018-09-01",
            },
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # FISHWIFE — premium tinned fish
    # ══════════════════════════════════════════════════════════════════════════
    {
        "brand_name":            "Fishwife",
        "website_url":           "https://eatfishwife.com",
        "category":              "seafood",
        "subcategory":           "tinned fish",
        "founded_year":          2020,
        "hq_city":               "Los Angeles",
        "hq_state":              "CA",
        "founder_name":          "Becca Millstein",
        "founder_email":         "becca@eatfishwife.com",
        "product_count":         3,
        "flagship_sku":          "Smoked Atlantic Salmon",
        "best_seller_sku":       "Smoked Atlantic Salmon",
        "wholesale_price_range": "$6.00–$6.50",
        "retail_price_range":    "$11.99–$12.99",
        "margin_range":          "50–55%",
        "distributor_list":      ["UNFI"],
        "current_retailers":     ["Whole Foods", "Erewhon", "Bristol Farms"],
        "target_retailers":      ["Sprouts", "Central Market", "Fresh Market"],
        "certifications":        ["MSC Certified", "Non-GMO Project Verified"],
        "brand_story": (
            "Fishwife is a woman-led tinned fish company that made sustainable seafood "
            "aesthetic, accessible, and delicious. Founded in 2020 by Becca Millstein and "
            "Caroline Goldfarb, the brand has built a cult following across social media and "
            "press, and is carried at Whole Foods, Erewhon, and Bristol Farms."
        ),
        "key_differentiators": [
            "Aesthetic packaging drives impulse purchase and social sharing — viral on TikTok and Instagram",
            "All fish MSC-certified and sustainably sourced; woman-led brand with strong founder POV",
            "Press in NYT, Bon Appétit, Vogue, and Well+Good — consumer pull-through without broker subsidies",
        ],
        "unit_velocity_range":  "5–8 units/store/week",
        "slotting_fees_paid":   "$0 at Whole Foods (invited), $5,000 at Erewhon",
        "completeness_pct":     91.0,
        "status":               "active",
        "is_sandbox":           True,
        "products": [
            {
                "sku_id":           "FW-SAS-001",
                "sku_name":         "Smoked Atlantic Salmon",
                "product_name":     "Smoked Atlantic Salmon",
                "flavor_or_variant":"Smoked Atlantic Salmon",
                "is_flagship":      True,
                "gtin":             "00810081960012",
                "upc":              "810081960012",
                "net_weight":       "3.5 oz",
                "net_weight_oz":    3.5,
                "net_weight_grams": 99,             # round(3.5 × 28.35)
                "package_type":     "tin",
                "package_dimensions_in": {"length": 3.75, "width": 3.0, "height": 1.25},
                "shelf_life_days":  730,
                "shelf_life_months":24,
                "storage_temp":     "ambient",
                "requires_refrigeration": False,
                "requires_freezer": False,
                "case_pack":        12,
                "case_dimensions_in": {"length": 11.5, "width": 9.5, "height": 5.0},
                "case_weight_lbs":  7.5,
                "cases_per_layer":  6,
                "layers_per_pallet":10,
                "cases_per_pallet": 60,             # 6 × 10
                "ti_hi":            "6×10",
                "wholesale_cost":         6.50,
                "wholesale_unit_cost_usd":6.50,
                "wholesale_case_cost_usd":78.00,    # 12 × 6.50
                "msrp":                  12.99,
                "srp_usd":               12.99,
                "msrp_usd":              12.99,
                "promotional_srp_usd":   10.99,
                "margin_pct":            50.0,      # (12.99 − 6.50) / 12.99
                "free_fill_cases_per_store":1,
                "slotting_fee_per_sku_usd": 0,
                "serving_size":           "1/3 tin (33g)",
                "servings_per_container": 3,
                "nutrition": {
                    "calories": 70, "total_fat_g": 3.0, "saturated_fat_g": 0.5,
                    "sodium_mg": 230, "total_carbs_g": 0.0, "sugar_g": 0.0,
                    "added_sugar_g": 0.0, "protein_g": 10.0, "fiber_g": 0.0,
                },
                "ingredients":     "Atlantic Salmon (Salmo salar), Extra Virgin Olive Oil, Sea Salt.",
                "allergens":        ["fish"],
                "contains_gluten":  False,
                "kosher_certified": False,
                "organic_certified":False,
                "country_of_origin":"Scotland",
                "launch_date":      "2020-11-01",
            },
            {
                "sku_id":           "FW-SRT-002",
                "sku_name":         "Smoked Rainbow Trout",
                "product_name":     "Smoked Rainbow Trout",
                "flavor_or_variant":"Smoked Rainbow Trout",
                "is_flagship":      False,
                "gtin":             "00810081960029",
                "upc":              "810081960029",
                "net_weight":       "3.5 oz",
                "net_weight_oz":    3.5,
                "net_weight_grams": 99,
                "package_type":     "tin",
                "package_dimensions_in": {"length": 3.75, "width": 3.0, "height": 1.25},
                "shelf_life_days":  730,
                "shelf_life_months":24,
                "storage_temp":     "ambient",
                "requires_refrigeration": False,
                "requires_freezer": False,
                "case_pack":        12,
                "case_dimensions_in": {"length": 11.5, "width": 9.5, "height": 5.0},
                "case_weight_lbs":  7.5,
                "cases_per_layer":  6,
                "layers_per_pallet":10,
                "cases_per_pallet": 60,
                "ti_hi":            "6×10",
                "wholesale_cost":         6.50,
                "wholesale_unit_cost_usd":6.50,
                "wholesale_case_cost_usd":78.00,
                "msrp":                  12.99,
                "srp_usd":               12.99,
                "msrp_usd":              12.99,
                "promotional_srp_usd":   10.99,
                "margin_pct":            50.0,
                "free_fill_cases_per_store":1,
                "slotting_fee_per_sku_usd": 0,
                "serving_size":           "1/3 tin (33g)",
                "servings_per_container": 3,
                "nutrition": {
                    "calories": 80, "total_fat_g": 4.0, "saturated_fat_g": 1.0,
                    "sodium_mg": 210, "total_carbs_g": 0.0, "sugar_g": 0.0,
                    "added_sugar_g": 0.0, "protein_g": 10.0, "fiber_g": 0.0,
                },
                "ingredients":     "Rainbow Trout (Oncorhynchus mykiss), Extra Virgin Olive Oil, Sea Salt, Black Pepper.",
                "allergens":        ["fish"],
                "contains_gluten":  False,
                "kosher_certified": False,
                "organic_certified":False,
                "country_of_origin":"Idaho, USA",
                "launch_date":      "2021-04-01",
            },
            {
                "sku_id":           "FW-ATJ-003",
                "sku_name":         "Albacore Tuna with Jalapeño",
                "product_name":     "Albacore Tuna with Jalapeño",
                "flavor_or_variant":"Jalapeño",
                "is_flagship":      False,
                "gtin":             "00810081960036",
                "upc":              "810081960036",
                "net_weight":       "3.5 oz",
                "net_weight_oz":    3.5,
                "net_weight_grams": 99,
                "package_type":     "tin",
                "package_dimensions_in": {"length": 3.75, "width": 3.0, "height": 1.25},
                "shelf_life_days":  730,
                "shelf_life_months":24,
                "storage_temp":     "ambient",
                "requires_refrigeration": False,
                "requires_freezer": False,
                "case_pack":        12,
                "case_dimensions_in": {"length": 11.5, "width": 9.5, "height": 5.0},
                "case_weight_lbs":  7.5,
                "cases_per_layer":  6,
                "layers_per_pallet":10,
                "cases_per_pallet": 60,
                "ti_hi":            "6×10",
                "wholesale_cost":         6.00,
                "wholesale_unit_cost_usd":6.00,
                "wholesale_case_cost_usd":72.00,    # 12 × 6.00
                "msrp":                  11.99,
                "srp_usd":               11.99,
                "msrp_usd":              11.99,
                "promotional_srp_usd":   9.99,
                "margin_pct":            50.0,      # (11.99 − 6.00) / 11.99
                "free_fill_cases_per_store":1,
                "slotting_fee_per_sku_usd": 0,
                "serving_size":           "1/3 tin (33g)",
                "servings_per_container": 3,
                "nutrition": {
                    "calories": 60, "total_fat_g": 1.5, "saturated_fat_g": 0.5,
                    "sodium_mg": 260, "total_carbs_g": 0.0, "sugar_g": 0.0,
                    "added_sugar_g": 0.0, "protein_g": 11.0, "fiber_g": 0.0,
                },
                "ingredients":     "Albacore Tuna (Thunnus alalunga), Jalapeño Peppers, Extra Virgin Olive Oil, Sea Salt, Citric Acid.",
                "allergens":        ["fish"],
                "contains_gluten":  False,
                "kosher_certified": False,
                "organic_certified":False,
                "country_of_origin":"Pacific Ocean (pole & line caught)",
                "launch_date":      "2022-01-01",
            },
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # GRAZA — single-origin squeeze-bottle olive oil
    # ══════════════════════════════════════════════════════════════════════════
    {
        "brand_name":            "Graza",
        "website_url":           "https://graza.co",
        "category":              "pantry",
        "subcategory":           "olive oil",
        "founded_year":          2022,
        "hq_city":               "New York",
        "hq_state":              "NY",
        "founder_name":          "Andrew Benin",
        "founder_email":         "andrew@graza.co",
        "product_count":         3,
        "flagship_sku":          "Drizzle — Extra Virgin Olive Oil 500ml",
        "best_seller_sku":       "Drizzle — Extra Virgin Olive Oil 500ml",
        "wholesale_price_range": "$8.50–$9.50",
        "retail_price_range":    "$15.99–$21.00",
        "margin_range":          "55–65%",
        "distributor_list":      ["UNFI", "Whole Foods Direct"],
        "current_retailers":     ["Whole Foods", "Target", "Erewhon", "Fresh Market"],
        "target_retailers":      ["Sprouts", "Wegmans"],
        "certifications":        ["Extra Virgin Certified", "PDO (Picual, Jaén Spain)"],
        "brand_story": (
            "Graza reimagined olive oil with a squeeze-bottle format and a two-oil philosophy: "
            "Sizzle for cooking, Drizzle for finishing. Founded in 2022 by Andrew Benin, the brand "
            "hit $10M in year-one revenue and is distributed at Whole Foods, Target, and Erewhon."
        ),
        "key_differentiators": [
            "Squeeze-bottle format is category-defining — no other EVOO brand has cracked this at scale",
            "Single-origin Spanish Picual and Arbequina — traceable to one cooperative in Jaén",
            "DTC-first with $10M year-one revenue; viral on TikTok and in NYT Food, Food52, Bon Appétit",
        ],
        "unit_velocity_range":  "6–10 units/store/week",
        "slotting_fees_paid":   "$0 at Whole Foods (invited), $0 at Target (test program), $4,000 at Erewhon",
        "completeness_pct":     90.0,
        "status":               "active",
        "is_sandbox":           True,
        "products": [
            {
                "sku_id":           "GZ-DRZ-001",
                "sku_name":         "Drizzle — Extra Virgin Olive Oil 500ml",
                "product_name":     "Drizzle — Extra Virgin Olive Oil",
                "flavor_or_variant":"Finishing (Arbequina)",
                "is_flagship":      True,
                "gtin":             "00850021730023",
                "upc":              "850021730023",
                "net_weight":       "500 ml (16.9 fl oz)",
                "net_weight_oz":    16.9,
                "net_weight_grams": 460,            # 500ml × 0.916 g/mL olive oil density
                "package_type":     "squeeze bottle",
                "package_dimensions_in": {"length": 2.5, "width": 2.5, "height": 9.0},
                "shelf_life_days":  548,
                "shelf_life_months":18,
                "storage_temp":     "ambient",
                "requires_refrigeration": False,
                "requires_freezer": False,
                "case_pack":        6,
                "case_dimensions_in": {"length": 10.0, "width": 8.0, "height": 10.0},
                "case_weight_lbs":  8.0,
                "cases_per_layer":  6,
                "layers_per_pallet":8,
                "cases_per_pallet": 48,             # 6 × 8
                "ti_hi":            "6×8",
                "wholesale_cost":         9.50,
                "wholesale_unit_cost_usd":9.50,
                "wholesale_case_cost_usd":57.00,    # 6 × 9.50
                "msrp":                  21.00,
                "srp_usd":               21.00,
                "msrp_usd":              21.00,
                "promotional_srp_usd":   18.00,
                "margin_pct":            54.8,      # (21.00 − 9.50) / 21.00
                "free_fill_cases_per_store":1,
                "slotting_fee_per_sku_usd": 0,
                "serving_size":           "1 Tbsp (15ml)",
                "servings_per_container": 33,
                "nutrition": {
                    "calories": 120, "total_fat_g": 14.0, "saturated_fat_g": 2.0,
                    "sodium_mg": 0, "total_carbs_g": 0.0, "sugar_g": 0.0,
                    "added_sugar_g": 0.0, "protein_g": 0.0, "fiber_g": 0.0,
                },
                "ingredients":     "100% Extra Virgin Olive Oil (Arbequina variety, Jaén, Spain).",
                "allergens":        [],
                "contains_gluten":  False,
                "kosher_certified": False,
                "organic_certified":False,
                "country_of_origin":"Spain",
                "launch_date":      "2022-01-10",
            },
            {
                "sku_id":           "GZ-SZL-002",
                "sku_name":         "Sizzle — Extra Virgin Olive Oil 750ml",
                "product_name":     "Sizzle — Extra Virgin Olive Oil",
                "flavor_or_variant":"Cooking (Picual)",
                "is_flagship":      False,
                "gtin":             "00850021730016",
                "upc":              "850021730016",
                "net_weight":       "750 ml (25.4 fl oz)",
                "net_weight_oz":    25.4,
                "net_weight_grams": 687,            # 750ml × 0.916
                "package_type":     "squeeze bottle",
                "package_dimensions_in": {"length": 2.75, "width": 2.75, "height": 11.0},
                "shelf_life_days":  548,
                "shelf_life_months":18,
                "storage_temp":     "ambient",
                "requires_refrigeration": False,
                "requires_freezer": False,
                "case_pack":        6,
                "case_dimensions_in": {"length": 10.0, "width": 9.0, "height": 12.0},
                "case_weight_lbs":  11.0,
                "cases_per_layer":  6,
                "layers_per_pallet":8,
                "cases_per_pallet": 48,
                "ti_hi":            "6×8",
                "wholesale_cost":         8.50,
                "wholesale_unit_cost_usd":8.50,
                "wholesale_case_cost_usd":51.00,    # 6 × 8.50
                "msrp":                  15.99,
                "srp_usd":               15.99,
                "msrp_usd":              15.99,
                "promotional_srp_usd":   13.99,
                "margin_pct":            46.8,      # (15.99 − 8.50) / 15.99
                "free_fill_cases_per_store":1,
                "slotting_fee_per_sku_usd": 0,
                "serving_size":           "1 Tbsp (15ml)",
                "servings_per_container": 50,
                "nutrition": {
                    "calories": 120, "total_fat_g": 14.0, "saturated_fat_g": 2.0,
                    "sodium_mg": 0, "total_carbs_g": 0.0, "sugar_g": 0.0,
                    "added_sugar_g": 0.0, "protein_g": 0.0, "fiber_g": 0.0,
                },
                "ingredients":     "100% Extra Virgin Olive Oil (Picual variety, Jaén, Spain).",
                "allergens":        [],
                "contains_gluten":  False,
                "kosher_certified": False,
                "organic_certified":False,
                "country_of_origin":"Spain",
                "launch_date":      "2022-01-10",
            },
            {
                "sku_id":           "GZ-DRZ-003",
                "sku_name":         "Drizzle Refill Tin 500ml",
                "product_name":     "Drizzle Refill Tin",
                "flavor_or_variant":"Finishing (Arbequina) — Refill Tin",
                "is_flagship":      False,
                "gtin":             "00850021730030",
                "upc":              "850021730030",
                "net_weight":       "500 ml (16.9 fl oz)",
                "net_weight_oz":    16.9,
                "net_weight_grams": 460,
                "package_type":     "tin",
                "package_dimensions_in": {"length": 4.0, "width": 4.0, "height": 5.5},
                "shelf_life_days":  548,
                "shelf_life_months":18,
                "storage_temp":     "ambient",
                "requires_refrigeration": False,
                "requires_freezer": False,
                "case_pack":        6,
                "case_dimensions_in": {"length": 12.5, "width": 8.5, "height": 6.0},
                "case_weight_lbs":  8.5,
                "cases_per_layer":  6,
                "layers_per_pallet":8,
                "cases_per_pallet": 48,
                "ti_hi":            "6×8",
                "wholesale_cost":         8.50,
                "wholesale_unit_cost_usd":8.50,
                "wholesale_case_cost_usd":51.00,    # 6 × 8.50
                "msrp":                  17.00,
                "srp_usd":               17.00,
                "msrp_usd":              17.00,
                "promotional_srp_usd":   15.00,
                "margin_pct":            50.0,      # (17.00 − 8.50) / 17.00
                "free_fill_cases_per_store":1,
                "slotting_fee_per_sku_usd": 0,
                "serving_size":           "1 Tbsp (15ml)",
                "servings_per_container": 33,
                "nutrition": {
                    "calories": 120, "total_fat_g": 14.0, "saturated_fat_g": 2.0,
                    "sodium_mg": 0, "total_carbs_g": 0.0, "sugar_g": 0.0,
                    "added_sugar_g": 0.0, "protein_g": 0.0, "fiber_g": 0.0,
                },
                "ingredients":     "100% Extra Virgin Olive Oil (Arbequina variety, Jaén, Spain).",
                "allergens":        [],
                "contains_gluten":  False,
                "kosher_certified": False,
                "organic_certified":False,
                "country_of_origin":"Spain",
                "launch_date":      "2022-09-01",
            },
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # OLIPOP — prebiotic soda
    # ══════════════════════════════════════════════════════════════════════════
    {
        "brand_name":            "Olipop",
        "website_url":           "https://drinkolipop.com",
        "category":              "beverages",
        "subcategory":           "prebiotic soda",
        "founded_year":          2018,
        "hq_city":               "Oakland",
        "hq_state":              "CA",
        "founder_name":          "Ben Goodwin",
        "founder_email":         "ben@drinkolipop.com",
        "product_count":         3,
        "flagship_sku":          "Vintage Cola 12oz",
        "best_seller_sku":       "Vintage Cola 12oz",
        "wholesale_price_range": "$1.80–$1.90",
        "retail_price_range":    "$2.49–$2.99",
        "margin_range":          "45–50%",
        "distributor_list":      ["UNFI", "KeHE", "Keurig Dr Pepper"],
        "current_retailers":     ["Whole Foods", "Target", "Sprouts", "Kroger", "Walmart", "Erewhon"],
        "target_retailers":      ["Costco", "CVS", "Albertsons"],
        "certifications":        ["Non-GMO Project Verified", "Vegan Certified"],
        "brand_story": (
            "Olipop makes prebiotic sodas with 9g of fiber, classic soda flavors, and 2–5g of sugar "
            "per can. Founded in 2018 by Ben Goodwin and David Lester, the brand has crossed $200M in "
            "annual revenue and is the fastest-growing beverage brand in the US, present in 15,000+ doors."
        ),
        "key_differentiators": [
            "9g of fiber vs. 0g in conventional soda — clinically substantiated gut health claim",
            "$200M+ revenue, 15,000+ doors across Whole Foods, Target, Sprouts, Kroger, Walmart, Erewhon",
            "625k+ Instagram followers, celeb-backed (Camila Cabello, Gwyneth Paltrow) — zero paid media dependency",
        ],
        "unit_velocity_range":  "18–28 units/store/week",
        "slotting_fees_paid":   "$0 at Whole Foods (invited), $10,000 at Target (invited program), $0 at Sprouts",
        "completeness_pct":     96.0,
        "status":               "active",
        "is_sandbox":           True,
        "products": [
            {
                "sku_id":           "OL-VCL-001",
                "sku_name":         "Vintage Cola 12oz",
                "product_name":     "Vintage Cola",
                "flavor_or_variant":"Vintage Cola",
                "is_flagship":      True,
                "gtin":             "00857251007016",
                "upc":              "857251007016",
                "net_weight":       "12 fl oz",
                "net_weight_oz":    12.0,
                "net_weight_grams": 355,            # 355ml (standard can)
                "package_type":     "can",
                "package_dimensions_in": {"length": 2.6, "width": 2.6, "height": 4.8},
                "shelf_life_days":  365,
                "shelf_life_months":12,
                "storage_temp":     "ambient",
                "requires_refrigeration": False,
                "requires_freezer": False,
                "case_pack":        12,
                "case_dimensions_in": {"length": 10.0, "width": 8.0, "height": 5.0},
                "case_weight_lbs":  9.5,
                "cases_per_layer":  10,
                "layers_per_pallet":10,
                "cases_per_pallet": 100,            # 10 × 10
                "ti_hi":            "10×10",
                "wholesale_cost":         1.85,
                "wholesale_unit_cost_usd":1.85,
                "wholesale_case_cost_usd":22.20,    # 12 × 1.85
                "msrp":                  2.99,
                "srp_usd":               2.99,
                "msrp_usd":              2.99,
                "promotional_srp_usd":   2.49,
                "margin_pct":            38.1,      # (2.99 − 1.85) / 2.99
                "free_fill_cases_per_store":2,
                "slotting_fee_per_sku_usd": 0,
                "serving_size":           "1 can (355ml)",
                "servings_per_container": 1,
                "nutrition": {
                    "calories": 35, "total_fat_g": 0.0, "saturated_fat_g": 0.0,
                    "sodium_mg": 35, "total_carbs_g": 13.0, "sugar_g": 2.0,
                    "added_sugar_g": 2.0, "protein_g": 0.0, "fiber_g": 9.0,
                },
                "ingredients":     (
                    "Carbonated Water, Cassava Root Fiber, Lemon Juice, Natural Flavors, "
                    "Calendula Flower Extract, Kudzu Root Extract, Nopal Cactus, "
                    "Stevia Leaf Extract."
                ),
                "allergens":        [],
                "contains_gluten":  False,
                "kosher_certified": True,
                "organic_certified":False,
                "country_of_origin":"USA",
                "launch_date":      "2019-03-01",
            },
            {
                "sku_id":           "OL-STV-002",
                "sku_name":         "Strawberry Vanilla 12oz",
                "product_name":     "Strawberry Vanilla",
                "flavor_or_variant":"Strawberry Vanilla",
                "is_flagship":      False,
                "gtin":             "00857251007030",
                "upc":              "857251007030",
                "net_weight":       "12 fl oz",
                "net_weight_oz":    12.0,
                "net_weight_grams": 355,
                "package_type":     "can",
                "package_dimensions_in": {"length": 2.6, "width": 2.6, "height": 4.8},
                "shelf_life_days":  365,
                "shelf_life_months":12,
                "storage_temp":     "ambient",
                "requires_refrigeration": False,
                "requires_freezer": False,
                "case_pack":        12,
                "case_dimensions_in": {"length": 10.0, "width": 8.0, "height": 5.0},
                "case_weight_lbs":  9.5,
                "cases_per_layer":  10,
                "layers_per_pallet":10,
                "cases_per_pallet": 100,
                "ti_hi":            "10×10",
                "wholesale_cost":         1.85,
                "wholesale_unit_cost_usd":1.85,
                "wholesale_case_cost_usd":22.20,
                "msrp":                  2.99,
                "srp_usd":               2.99,
                "msrp_usd":              2.99,
                "promotional_srp_usd":   2.49,
                "margin_pct":            38.1,
                "free_fill_cases_per_store":2,
                "slotting_fee_per_sku_usd": 0,
                "serving_size":           "1 can (355ml)",
                "servings_per_container": 1,
                "nutrition": {
                    "calories": 35, "total_fat_g": 0.0, "saturated_fat_g": 0.0,
                    "sodium_mg": 35, "total_carbs_g": 13.0, "sugar_g": 2.0,
                    "added_sugar_g": 2.0, "protein_g": 0.0, "fiber_g": 9.0,
                },
                "ingredients":     (
                    "Carbonated Water, Cassava Root Fiber, Strawberry Juice, Natural Flavors, "
                    "Vanilla Extract, Kudzu Root Extract, Nopal Cactus, Stevia Leaf Extract."
                ),
                "allergens":        [],
                "contains_gluten":  False,
                "kosher_certified": True,
                "organic_certified":False,
                "country_of_origin":"USA",
                "launch_date":      "2021-02-01",
            },
            {
                "sku_id":           "OL-CRB-003",
                "sku_name":         "Classic Root Beer 12oz",
                "product_name":     "Classic Root Beer",
                "flavor_or_variant":"Classic Root Beer",
                "is_flagship":      False,
                "gtin":             "00857251007047",
                "upc":              "857251007047",
                "net_weight":       "12 fl oz",
                "net_weight_oz":    12.0,
                "net_weight_grams": 355,
                "package_type":     "can",
                "package_dimensions_in": {"length": 2.6, "width": 2.6, "height": 4.8},
                "shelf_life_days":  365,
                "shelf_life_months":12,
                "storage_temp":     "ambient",
                "requires_refrigeration": False,
                "requires_freezer": False,
                "case_pack":        12,
                "case_dimensions_in": {"length": 10.0, "width": 8.0, "height": 5.0},
                "case_weight_lbs":  9.5,
                "cases_per_layer":  10,
                "layers_per_pallet":10,
                "cases_per_pallet": 100,
                "ti_hi":            "10×10",
                "wholesale_cost":         1.85,
                "wholesale_unit_cost_usd":1.85,
                "wholesale_case_cost_usd":22.20,
                "msrp":                  2.99,
                "srp_usd":               2.99,
                "msrp_usd":              2.99,
                "promotional_srp_usd":   2.49,
                "margin_pct":            38.1,
                "free_fill_cases_per_store":2,
                "slotting_fee_per_sku_usd": 0,
                "serving_size":           "1 can (355ml)",
                "servings_per_container": 1,
                "nutrition": {
                    "calories": 35, "total_fat_g": 0.0, "saturated_fat_g": 0.0,
                    "sodium_mg": 45, "total_carbs_g": 11.0, "sugar_g": 2.0,
                    "added_sugar_g": 2.0, "protein_g": 0.0, "fiber_g": 9.0,
                },
                "ingredients":     (
                    "Carbonated Water, Cassava Root Fiber, Natural Flavors (Root Beer), "
                    "Kudzu Root Extract, Nopal Cactus, Marshmallow Root Extract, "
                    "Stevia Leaf Extract."
                ),
                "allergens":        [],
                "contains_gluten":  False,
                "kosher_certified": True,
                "organic_certified":False,
                "country_of_origin":"USA",
                "launch_date":      "2020-09-01",
            },
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # MAGIC SPOON — high-protein, grain-free cereal
    # ══════════════════════════════════════════════════════════════════════════
    {
        "brand_name":            "Magic Spoon",
        "website_url":           "https://magicspoon.com",
        "category":              "breakfast",
        "subcategory":           "cereal",
        "founded_year":          2019,
        "hq_city":               "New York",
        "hq_state":              "NY",
        "founder_name":          "Gabi Lewis",
        "founder_email":         "gabi@magicspoon.com",
        "product_count":         3,
        "flagship_sku":          "Cocoa Single Box 7oz",
        "best_seller_sku":       "Cocoa Single Box 7oz",
        "wholesale_price_range": "$6.25–$6.75",
        "retail_price_range":    "$10.99–$12.99",
        "margin_range":          "50–55%",
        "distributor_list":      ["UNFI", "KeHE"],
        "current_retailers":     ["Target", "Whole Foods", "Walmart"],
        "target_retailers":      ["Sprouts", "Erewhon", "Costco"],
        "certifications":        ["Keto Certified", "Gluten-Free Certified", "Grain-Free Certified"],
        "brand_story": (
            "Magic Spoon reinvented childhood cereal favorites as high-protein, zero-sugar, "
            "grain-free boxes for adults. Founded in 2019 by Gabi Lewis and Greg Sewitz, the brand "
            "raised $100M+ and expanded from DTC into Target, Whole Foods, and Walmart."
        ),
        "key_differentiators": [
            "13–14g protein vs. 2–3g in conventional cereal — the most credible macro-claim in breakfast",
            "$100M+ raised; backed by institutional investors including a General Mills affiliate",
            "DTC Subscribe & Save customer base drives repeat — retail expansion is additive, not the engine",
        ],
        "unit_velocity_range":  "6–10 units/store/week",
        "slotting_fees_paid":   "$12,000 at Whole Foods, $0 at Target (invited innovation program)",
        "completeness_pct":     88.0,
        "status":               "active",
        "is_sandbox":           True,
        "products": [
            {
                "sku_id":           "MS-COC-001",
                "sku_name":         "Cocoa Single Box 7oz",
                "product_name":     "Cocoa Cereal",
                "flavor_or_variant":"Cocoa",
                "is_flagship":      True,
                "gtin":             "00810041570139",
                "upc":              "810041570139",
                "net_weight":       "7 oz",
                "net_weight_oz":    7.0,
                "net_weight_grams": 198,            # round(7.0 × 28.35)
                "package_type":     "box",
                "package_dimensions_in": {"length": 7.5, "width": 2.75, "height": 10.5},
                "shelf_life_days":  365,
                "shelf_life_months":12,
                "storage_temp":     "ambient",
                "requires_refrigeration": False,
                "requires_freezer": False,
                "case_pack":        6,
                "case_dimensions_in": {"length": 16.0, "width": 8.5, "height": 11.0},
                "case_weight_lbs":  7.0,
                "cases_per_layer":  8,
                "layers_per_pallet":6,
                "cases_per_pallet": 48,             # 8 × 6
                "ti_hi":            "8×6",
                "wholesale_cost":         6.50,
                "wholesale_unit_cost_usd":6.50,
                "wholesale_case_cost_usd":39.00,    # 6 × 6.50
                "msrp":                  11.99,
                "srp_usd":               11.99,
                "msrp_usd":              11.99,
                "promotional_srp_usd":   9.99,
                "margin_pct":            45.8,      # (11.99 − 6.50) / 11.99
                "free_fill_cases_per_store":1,
                "slotting_fee_per_sku_usd": 2000,
                "serving_size":           "3/4 cup (28g)",
                "servings_per_container": 7,
                "nutrition": {
                    "calories": 140, "total_fat_g": 7.0, "saturated_fat_g": 1.0,
                    "sodium_mg": 200, "total_carbs_g": 13.0, "sugar_g": 0.0,
                    "added_sugar_g": 0.0, "protein_g": 13.0, "fiber_g": 1.0,
                },
                "ingredients":     (
                    "Whey Protein Blend (Whey Protein Isolate, Whey Protein Concentrate), "
                    "Tapioca Flour, Cocoa Powder, Chicory Root Fiber, High-Oleic Sunflower Oil, "
                    "Natural Flavors, Salt, Monk Fruit Extract."
                ),
                "allergens":        ["milk"],
                "contains_gluten":  False,
                "kosher_certified": False,
                "organic_certified":False,
                "country_of_origin":"USA",
                "launch_date":      "2022-03-01",
            },
            {
                "sku_id":           "MS-FRO-002",
                "sku_name":         "Frosted Single Box 7oz",
                "product_name":     "Frosted Cereal",
                "flavor_or_variant":"Frosted",
                "is_flagship":      False,
                "gtin":             "00810041570122",
                "upc":              "810041570122",
                "net_weight":       "7 oz",
                "net_weight_oz":    7.0,
                "net_weight_grams": 198,
                "package_type":     "box",
                "package_dimensions_in": {"length": 7.5, "width": 2.75, "height": 10.5},
                "shelf_life_days":  365,
                "shelf_life_months":12,
                "storage_temp":     "ambient",
                "requires_refrigeration": False,
                "requires_freezer": False,
                "case_pack":        6,
                "case_dimensions_in": {"length": 16.0, "width": 8.5, "height": 11.0},
                "case_weight_lbs":  7.0,
                "cases_per_layer":  8,
                "layers_per_pallet":6,
                "cases_per_pallet": 48,
                "ti_hi":            "8×6",
                "wholesale_cost":         6.50,
                "wholesale_unit_cost_usd":6.50,
                "wholesale_case_cost_usd":39.00,
                "msrp":                  11.99,
                "srp_usd":               11.99,
                "msrp_usd":              11.99,
                "promotional_srp_usd":   9.99,
                "margin_pct":            45.8,
                "free_fill_cases_per_store":1,
                "slotting_fee_per_sku_usd": 2000,
                "serving_size":           "3/4 cup (28g)",
                "servings_per_container": 7,
                "nutrition": {
                    "calories": 140, "total_fat_g": 7.0, "saturated_fat_g": 1.0,
                    "sodium_mg": 190, "total_carbs_g": 12.0, "sugar_g": 0.0,
                    "added_sugar_g": 0.0, "protein_g": 14.0, "fiber_g": 1.0,
                },
                "ingredients":     (
                    "Whey Protein Blend (Whey Protein Isolate, Whey Protein Concentrate), "
                    "Tapioca Flour, Chicory Root Fiber, High-Oleic Sunflower Oil, "
                    "Natural Flavors, Salt, Monk Fruit Extract."
                ),
                "allergens":        ["milk"],
                "contains_gluten":  False,
                "kosher_certified": False,
                "organic_certified":False,
                "country_of_origin":"USA",
                "launch_date":      "2022-03-01",
            },
            {
                "sku_id":           "MS-PNB-003",
                "sku_name":         "Peanut Butter Single Box 7oz",
                "product_name":     "Peanut Butter Cereal",
                "flavor_or_variant":"Peanut Butter",
                "is_flagship":      False,
                "gtin":             "00810041570146",
                "upc":              "810041570146",
                "net_weight":       "7 oz",
                "net_weight_oz":    7.0,
                "net_weight_grams": 198,
                "package_type":     "box",
                "package_dimensions_in": {"length": 7.5, "width": 2.75, "height": 10.5},
                "shelf_life_days":  365,
                "shelf_life_months":12,
                "storage_temp":     "ambient",
                "requires_refrigeration": False,
                "requires_freezer": False,
                "case_pack":        6,
                "case_dimensions_in": {"length": 16.0, "width": 8.5, "height": 11.0},
                "case_weight_lbs":  7.0,
                "cases_per_layer":  8,
                "layers_per_pallet":6,
                "cases_per_pallet": 48,
                "ti_hi":            "8×6",
                "wholesale_cost":         6.50,
                "wholesale_unit_cost_usd":6.50,
                "wholesale_case_cost_usd":39.00,
                "msrp":                  11.99,
                "srp_usd":               11.99,
                "msrp_usd":              11.99,
                "promotional_srp_usd":   9.99,
                "margin_pct":            45.8,
                "free_fill_cases_per_store":1,
                "slotting_fee_per_sku_usd": 2000,
                "serving_size":           "3/4 cup (28g)",
                "servings_per_container": 7,
                "nutrition": {
                    "calories": 150, "total_fat_g": 9.0, "saturated_fat_g": 1.5,
                    "sodium_mg": 210, "total_carbs_g": 10.0, "sugar_g": 0.0,
                    "added_sugar_g": 0.0, "protein_g": 13.0, "fiber_g": 1.0,
                },
                "ingredients":     (
                    "Whey Protein Blend (Whey Protein Isolate, Whey Protein Concentrate), "
                    "Peanut Flour, Tapioca Flour, Chicory Root Fiber, High-Oleic Sunflower Oil, "
                    "Natural Flavors, Salt, Monk Fruit Extract."
                ),
                "allergens":        ["milk", "peanuts"],
                "contains_gluten":  False,
                "kosher_certified": False,
                "organic_certified":False,
                "country_of_origin":"USA",
                "launch_date":      "2022-06-01",
            },
        ],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# SANDBOX_EVALUATIONS  →  brand_evaluations table
# Pre-computed scoring so Retailer Pitcher and Admin Ops run without re-scoring.
# ─────────────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


SANDBOX_EVALUATIONS: list[dict] = [

    # ── Chomps ─────────────────────────────────────────────────────────────────
    {
        "brand_name":   "Chomps",
        "score":        84,
        "verdict":      "established",
        "category":     "shelf-stable meat snacks",
        "broker_brief": (
            "Chomps is the #1 meat snack on Amazon — 45,000+ reviews, 4.7★, Subscribe & Save active. "
            "Present in 5 national chains (Whole Foods, Target, Costco, Sprouts, Walmart) across 8,500+ doors. "
            "Five-ingredient panel is Non-GMO, Paleo, and Whole30 certified — the trifecta for natural-channel buyers. "
            "Brand gross margin ~58% comfortably absorbs the full broker stack. "
            "Primary consideration for a broker: this brand may already be well-covered at this door count."
        ),
        "key_gaps": [
            "Already in 8,500+ doors — limited whitespace for a new broker to add incremental distribution",
            "In-house sales team likely reduces broker dependency",
        ],
        "score_breakdown": {
            "velocity_proof":          22,
            "distribution_density":    18,
            "margin_viability":        18,
            "brand_story_clarity":     17,
            "promotional_independence": 9,
            "total":                   84,
        },
        "key_signals": {
            "instacart_banners": ["Whole Foods", "Target", "Costco", "Sprouts", "Walmart"],
            "trade_press": ["NOSH", "New Hope Network", "FoodNavigator-USA"],
            "social_signals": {
                "instagram_handle": "@chomps",
                "instagram_followers": 275000,
                "tiktok_handle": "@chomps",
                "tiktok_followers": 45000,
            },
            "funding": {"stage": "Series A", "amount_usd": 14000000},
            "extracted_fields": {
                "amazon_review_count":       45000,
                "amazon_rating":             4.7,
                "amazon_subscribe_save":     True,
                "amazon_bsr_rank":           3,
                "amazon_sku_count":          12,
                "instacart_banner_count":    5,
                "instacart_banners":         ["Whole Foods", "Target", "Costco", "Sprouts", "Walmart"],
                "whole_foods_confirmed":     True,
                "target_confirmed":          True,
                "walmart_confirmed":         True,
                "sprouts_confirmed":         True,
                "costco_confirmed":          True,
                "faire_present":             False,
                "faire_listed":              False,
                "faire_door_count":          0,
                "estimated_door_count":      8500,
                "srp_min":                   2.49,
                "srp_max":                   2.99,
                "srp_hero":                  2.49,
                "category":                  "shelf-stable meat snacks",
                "funding_amount_usd":        14000000,
                "funding_stage":             "Series A",
                "instagram_followers":       275000,
                "tiktok_followers":          45000,
                "press_trade_mentions":      12,
                "press_consumer_mentions":   25,
                "expo_west_confirmed":       True,
                "dtc_channel":               True,
                "subscription_available":    True,
                "promo_frequency_tpr_per_year": 2,
                "bogo_detected":             False,
                "founder_story_clear":       True,
                "certifications":            [
                    "Non-GMO Project Verified", "Paleo Certified",
                    "Whole30 Approved", "Gluten-Free Certified",
                ],
                "hero_product_clear":        True,
                "national_chain_count":      5,
                "publicly_traded":           False,
                "inhouse_sales_team":        True,
                "spins_mentioned":           True,
                "sell_through_press":        True,
            },
        },
        "founder_name":     "Pete Maldonado",
        "founder_email":    "pete@chomps.com",
        "reflection_notes": [],
        "email_draft":      "",
        "email_subject":    "",
    },

    # ── Fishwife ───────────────────────────────────────────────────────────────
    {
        "brand_name":   "Fishwife",
        "score":        72,
        "verdict":      "broker_ready",
        "category":     "shelf-stable seafood",
        "broker_brief": (
            "Fishwife is the brand that made tinned fish cool — 181k Instagram followers, "
            "press in Bon Appétit, NYT Cooking, and Vogue. Currently at Whole Foods, Erewhon, and "
            "Bristol Farms (~140 doors) — enough proof the brand works at premium retail, "
            "with significant whitespace in Sprouts and specialty independents. "
            "Gross margin ~60% absorbs the full broker stack. Best pitch angle: expand into Sprouts "
            "Southwest and Central Market to reach the 40-something female health shopper."
        ),
        "key_gaps": [
            "Low door count limits third-party velocity data — strong DTC but retail proof is nascent",
            "SRP $12.99 positions above typical impulse threshold — requires committed shopper",
        ],
        "score_breakdown": {
            "velocity_proof":          16,
            "distribution_density":    14,
            "margin_viability":        18,
            "brand_story_clarity":     18,
            "promotional_independence": 6,
            "total":                   72,
        },
        "key_signals": {
            "instacart_banners": ["Whole Foods", "Erewhon", "Bristol Farms"],
            "trade_press": ["NOSH", "FoodNavigator-USA", "Bon Appétit", "NYT Cooking"],
            "social_signals": {
                "instagram_handle": "@eatfishwife",
                "instagram_followers": 181000,
                "tiktok_handle": "@eatfishwife",
                "tiktok_followers": 62000,
            },
            "funding": {"stage": "Seed", "amount_usd": 3500000},
            "extracted_fields": {
                "amazon_review_count":       3200,
                "amazon_rating":             4.6,
                "amazon_subscribe_save":     True,
                "amazon_bsr_rank":           12,
                "amazon_sku_count":          8,
                "instacart_banner_count":    3,
                "instacart_banners":         ["Whole Foods", "Erewhon", "Bristol Farms"],
                "whole_foods_confirmed":     True,
                "target_confirmed":          False,
                "walmart_confirmed":         False,
                "sprouts_confirmed":         False,
                "costco_confirmed":          False,
                "faire_present":             True,
                "faire_listed":              True,
                "faire_door_count":          220,
                "estimated_door_count":      140,
                "srp_min":                   11.99,
                "srp_max":                   12.99,
                "srp_hero":                  12.99,
                "category":                  "shelf-stable seafood",
                "funding_amount_usd":        3500000,
                "funding_stage":             "Seed",
                "instagram_followers":       181000,
                "tiktok_followers":          62000,
                "press_trade_mentions":      8,
                "press_consumer_mentions":   22,
                "expo_west_confirmed":       True,
                "dtc_channel":               True,
                "subscription_available":    True,
                "promo_frequency_tpr_per_year": 1,
                "bogo_detected":             False,
                "founder_story_clear":       True,
                "certifications":            ["MSC Certified", "Non-GMO Project Verified"],
                "hero_product_clear":        True,
                "national_chain_count":      1,
                "publicly_traded":           False,
                "inhouse_sales_team":        False,
                "spins_mentioned":           False,
                "sell_through_press":        True,
            },
        },
        "founder_name":     "Becca Millstein",
        "founder_email":    "becca@eatfishwife.com",
        "reflection_notes": [],
        "email_draft":      "",
        "email_subject":    "",
    },

    # ── Graza ──────────────────────────────────────────────────────────────────
    {
        "brand_name":   "Graza",
        "score":        79,
        "verdict":      "broker_ready",
        "category":     "olive_oil",
        "broker_brief": (
            "Graza is the olive oil that went viral — squeeze-bottle format, two-oil philosophy "
            "(Sizzle for cooking, Drizzle for finishing), and $10M in year-one revenue. "
            "Present at Whole Foods, Target, Erewhon, and Fresh Market (~600 doors). "
            "Single-origin Spanish EVOO with a differentiated format no competitor has cracked at retail. "
            "Gross margin ~65%. Strong DTC and Subscribe & Save base validates pull-through. "
            "Pitch angle: expand the Drizzle into Sprouts and Wegmans before a national competitor copies the format."
        ),
        "key_gaps": [
            "Relatively concentrated in national chains — regional specialty and co-op whitespace untapped",
            "Premium SRP ($21 Drizzle) may pressure velocity in value-oriented natural channels",
        ],
        "score_breakdown": {
            "velocity_proof":          19,
            "distribution_density":    15,
            "margin_viability":        18,
            "brand_story_clarity":     20,
            "promotional_independence": 7,
            "total":                   79,
        },
        "key_signals": {
            "instacart_banners": ["Whole Foods", "Target", "Erewhon", "Fresh Market"],
            "trade_press": ["NYT Food", "Food52", "Bon Appétit", "NOSH"],
            "social_signals": {
                "instagram_handle": "@graza",
                "instagram_followers": 102000,
                "tiktok_handle": "@graza.co",
                "tiktok_followers": 88000,
            },
            "funding": {"stage": "Seed", "amount_usd": 6500000},
            "extracted_fields": {
                "amazon_review_count":       8500,
                "amazon_rating":             4.8,
                "amazon_subscribe_save":     True,
                "amazon_bsr_rank":           8,
                "amazon_sku_count":          3,
                "instacart_banner_count":    4,
                "instacart_banners":         ["Whole Foods", "Target", "Erewhon", "Fresh Market"],
                "whole_foods_confirmed":     True,
                "target_confirmed":          True,
                "walmart_confirmed":         False,
                "sprouts_confirmed":         False,
                "costco_confirmed":          False,
                "faire_present":             True,
                "faire_listed":              True,
                "faire_door_count":          180,
                "estimated_door_count":      600,
                "srp_min":                   15.99,
                "srp_max":                   21.00,
                "srp_hero":                  21.00,
                "category":                  "olive_oil",
                "funding_amount_usd":        6500000,
                "funding_stage":             "Seed",
                "instagram_followers":       102000,
                "tiktok_followers":          88000,
                "press_trade_mentions":      6,
                "press_consumer_mentions":   18,
                "expo_west_confirmed":       True,
                "dtc_channel":               True,
                "subscription_available":    True,
                "promo_frequency_tpr_per_year": 1,
                "bogo_detected":             False,
                "founder_story_clear":       True,
                "certifications":            ["Extra Virgin Certified", "PDO (Picual, Jaén Spain)"],
                "hero_product_clear":        True,
                "national_chain_count":      2,
                "publicly_traded":           False,
                "inhouse_sales_team":        True,
                "spins_mentioned":           False,
                "sell_through_press":        True,
            },
        },
        "founder_name":     "Andrew Benin",
        "founder_email":    "andrew@graza.co",
        "reflection_notes": [],
        "email_draft":      "",
        "email_subject":    "",
    },

    # ── Olipop ─────────────────────────────────────────────────────────────────
    {
        "brand_name":   "Olipop",
        "score":        91,
        "verdict":      "established",
        "category":     "prebiotic soda",
        "broker_brief": (
            "Olipop is the benchmark for better-for-you soda — $200M+ revenue, 15,000+ doors, "
            "6 national chains (Whole Foods, Target, Sprouts, Kroger, Walmart, Erewhon). "
            "9g fiber vs. 0g in conventional soda is a legitimate, differentiated health claim "
            "in the largest beverage category in the US. Amazon Subscribe & Save rate indicates "
            "strong repeat; 625k Instagram followers means pull-through without broker subsidies. "
            "The broker play: if you can show whitespace they haven't covered, there's a conversation."
        ),
        "key_gaps": [
            "Already extremely well-distributed — primary value a broker can add is niche regional or foodservice",
            "Margin stack is tight at 38% retailer margin — TPR cycles compress economics further",
        ],
        "score_breakdown": {
            "velocity_proof":          25,
            "distribution_density":    20,
            "margin_viability":        16,
            "brand_story_clarity":     18,
            "promotional_independence":12,
            "total":                   91,
        },
        "key_signals": {
            "instacart_banners": ["Whole Foods", "Target", "Sprouts", "Kroger", "Walmart", "Erewhon"],
            "trade_press": ["NOSH", "FoodNavigator-USA", "New Hope Network", "Forbes"],
            "social_signals": {
                "instagram_handle": "@drinkolipop",
                "instagram_followers": 625000,
                "tiktok_handle": "@drinkolipop",
                "tiktok_followers": 512000,
            },
            "funding": {"stage": "Series B", "amount_usd": 40000000},
            "extracted_fields": {
                "amazon_review_count":       28000,
                "amazon_rating":             4.5,
                "amazon_subscribe_save":     True,
                "amazon_bsr_rank":           1,
                "amazon_sku_count":          15,
                "instacart_banner_count":    6,
                "instacart_banners":         ["Whole Foods", "Target", "Sprouts", "Kroger", "Walmart", "Erewhon"],
                "whole_foods_confirmed":     True,
                "target_confirmed":          True,
                "walmart_confirmed":         True,
                "sprouts_confirmed":         True,
                "costco_confirmed":          False,
                "faire_present":             False,
                "faire_listed":              False,
                "faire_door_count":          0,
                "estimated_door_count":      15000,
                "srp_min":                   2.49,
                "srp_max":                   2.99,
                "srp_hero":                  2.99,
                "category":                  "prebiotic soda",
                "funding_amount_usd":        40000000,
                "funding_stage":             "Series B",
                "instagram_followers":       625000,
                "tiktok_followers":          512000,
                "press_trade_mentions":      30,
                "press_consumer_mentions":   80,
                "expo_west_confirmed":       True,
                "dtc_channel":               True,
                "subscription_available":    True,
                "promo_frequency_tpr_per_year": 4,
                "bogo_detected":             False,
                "founder_story_clear":       True,
                "certifications":            ["Non-GMO Project Verified", "Vegan Certified"],
                "hero_product_clear":        True,
                "national_chain_count":      6,
                "publicly_traded":           False,
                "inhouse_sales_team":        True,
                "spins_mentioned":           True,
                "sell_through_press":        True,
            },
        },
        "founder_name":     "Ben Goodwin",
        "founder_email":    "ben@drinkolipop.com",
        "reflection_notes": [],
        "email_draft":      "",
        "email_subject":    "",
    },

    # ── Magic Spoon ────────────────────────────────────────────────────────────
    {
        "brand_name":   "Magic Spoon",
        "score":        81,
        "verdict":      "established",
        "category":     "cereal",
        "broker_brief": (
            "Magic Spoon turned childhood cereal nostalgia into a high-protein, zero-sugar format. "
            "$100M+ raised (including a General Mills-affiliated investor), in Target, Whole Foods, and Walmart. "
            "13–14g protein vs. 2–3g in conventional cereal is the most credible macro-differentiation in breakfast. "
            "DTC Subscribe & Save is the revenue backbone; retail is additive. "
            "Broker angle: natural channel expansion — Sprouts, Erewhon, and specialty co-ops are untapped."
        ),
        "key_gaps": [
            "High slotting fees ($12,000 at Whole Foods) reduce broker commission economics",
            "In-house sales with investor-connected infrastructure may limit broker upside",
        ],
        "score_breakdown": {
            "velocity_proof":          19,
            "distribution_density":    17,
            "margin_viability":        17,
            "brand_story_clarity":     18,
            "promotional_independence":10,
            "total":                   81,
        },
        "key_signals": {
            "instacart_banners": ["Target", "Whole Foods", "Walmart"],
            "trade_press": ["NOSH", "Forbes", "TechCrunch", "FoodNavigator-USA"],
            "social_signals": {
                "instagram_handle": "@magicspoon",
                "instagram_followers": 205000,
                "tiktok_handle": "@magicspoon",
                "tiktok_followers": 74000,
            },
            "funding": {"stage": "Series B", "amount_usd": 100000000},
            "extracted_fields": {
                "amazon_review_count":       12000,
                "amazon_rating":             4.4,
                "amazon_subscribe_save":     True,
                "amazon_bsr_rank":           5,
                "amazon_sku_count":          10,
                "instacart_banner_count":    3,
                "instacart_banners":         ["Target", "Whole Foods", "Walmart"],
                "whole_foods_confirmed":     True,
                "target_confirmed":          True,
                "walmart_confirmed":         True,
                "sprouts_confirmed":         False,
                "costco_confirmed":          False,
                "faire_present":             False,
                "faire_listed":              False,
                "faire_door_count":          0,
                "estimated_door_count":      4200,
                "srp_min":                   10.99,
                "srp_max":                   12.99,
                "srp_hero":                  11.99,
                "category":                  "cereal",
                "funding_amount_usd":        100000000,
                "funding_stage":             "Series B",
                "instagram_followers":       205000,
                "tiktok_followers":          74000,
                "press_trade_mentions":      10,
                "press_consumer_mentions":   28,
                "expo_west_confirmed":       True,
                "dtc_channel":               True,
                "subscription_available":    True,
                "promo_frequency_tpr_per_year": 2,
                "bogo_detected":             False,
                "founder_story_clear":       True,
                "certifications":            [
                    "Keto Certified", "Gluten-Free Certified", "Grain-Free Certified",
                ],
                "hero_product_clear":        True,
                "national_chain_count":      3,
                "publicly_traded":           False,
                "inhouse_sales_team":        True,
                "spins_mentioned":           True,
                "sell_through_press":        True,
            },
        },
        "founder_name":     "Gabi Lewis",
        "founder_email":    "gabi@magicspoon.com",
        "reflection_notes": [],
        "email_draft":      "",
        "email_subject":    "",
    },
]

_SANDBOX_BRAND_NAMES = [b["brand_name"] for b in SANDBOX_BRANDS]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _seed_brand_evaluations(client, names_seeded: list[str]) -> None:
    """Upsert pre-computed brand_evaluations so downstream agents skip re-scoring."""
    now = _now_iso()
    for ev in SANDBOX_EVALUATIONS:
        if ev["brand_name"] not in names_seeded:
            continue
        row = {**ev, "evaluated_at": now}
        try:
            client.table("brand_evaluations").upsert(
                row, on_conflict="brand_name"
            ).execute()
        except Exception:
            pass  # non-blocking — brand roster still works without evaluation cache


# Per-brand × per-agent activity for the demo roster.
# Each entry: from_agent, to_agent, message_type, payload (with agent_status / action_label /
# pending_review_count), hours_ago (float — how old the message should appear).
_SANDBOX_ACTIVITY: dict[str, list[dict]] = {
    "Chomps": [
        {
            "from_agent": "retailer_pitcher", "to_agent": "admin_ops",
            "message_type": "pitch_sent",
            "payload": {"brand_name": "Chomps", "agent_status": "completed",
                        "action_label": "Sent Whole Foods pitch", "pending_review_count": 0},
            "hours_ago": 2.0,
        },
        {
            "from_agent": "admin_ops", "to_agent": "brand_onboarding",
            "message_type": "review_required",
            "payload": {"brand_name": "Chomps", "agent_status": "awaiting_review",
                        "action_label": "3 deductions to review", "pending_review_count": 3},
            "hours_ago": 1.0,
        },
        {
            "from_agent": "brand_scout", "to_agent": "brand_onboarding",
            "message_type": "idle",
            "payload": {"brand_name": "Chomps", "agent_status": "idle",
                        "action_label": "", "pending_review_count": 0},
            "hours_ago": 48.0,
        },
    ],
    "Fishwife": [
        {
            "from_agent": "retailer_pitcher", "to_agent": "admin_ops",
            "message_type": "pitch_in_progress",
            "payload": {"brand_name": "Fishwife", "agent_status": "in_progress",
                        "action_label": "Drafting Erewhon pitch", "pending_review_count": 0},
            "hours_ago": 0.1,
        },
        {
            "from_agent": "admin_ops", "to_agent": "brand_onboarding",
            "message_type": "form_completed",
            "payload": {"brand_name": "Fishwife", "agent_status": "completed",
                        "action_label": "Filled Whole Foods new-item form", "pending_review_count": 0},
            "hours_ago": 0.23,
        },
        {
            "from_agent": "brand_scout", "to_agent": "brand_onboarding",
            "message_type": "evaluation_complete",
            "payload": {"brand_name": "Fishwife", "agent_status": "completed",
                        "action_label": "Re-scored brand", "pending_review_count": 0},
            "hours_ago": 24.0,
        },
    ],
    "Graza": [
        {
            "from_agent": "retailer_pitcher", "to_agent": "admin_ops",
            "message_type": "pitch_sent",
            "payload": {"brand_name": "Graza", "agent_status": "completed",
                        "action_label": "Sent Sprouts pitch", "pending_review_count": 0},
            "hours_ago": 6.0,
        },
        {
            "from_agent": "admin_ops", "to_agent": "brand_onboarding",
            "message_type": "po_processing",
            "payload": {"brand_name": "Graza", "agent_status": "in_progress",
                        "action_label": "Processing PO from Whole Foods", "pending_review_count": 0},
            "hours_ago": 0.5,
        },
        {
            "from_agent": "brand_scout", "to_agent": "brand_onboarding",
            "message_type": "idle",
            "payload": {"brand_name": "Graza", "agent_status": "idle",
                        "action_label": "", "pending_review_count": 0},
            "hours_ago": 72.0,
        },
    ],
    "Olipop": [
        {
            "from_agent": "retailer_pitcher", "to_agent": "admin_ops",
            "message_type": "pitches_awaiting_review",
            "payload": {"brand_name": "Olipop", "agent_status": "awaiting_review",
                        "action_label": "2 buyer pitches ready", "pending_review_count": 2},
            "hours_ago": 0.75,
        },
        {
            "from_agent": "admin_ops", "to_agent": "brand_onboarding",
            "message_type": "spend_reconciled",
            "payload": {"brand_name": "Olipop", "agent_status": "completed",
                        "action_label": "Reconciled demo spend", "pending_review_count": 0},
            "hours_ago": 3.0,
        },
        {
            "from_agent": "brand_scout", "to_agent": "brand_onboarding",
            "message_type": "idle",
            "payload": {"brand_name": "Olipop", "agent_status": "idle",
                        "action_label": "", "pending_review_count": 0},
            "hours_ago": 72.0,
        },
    ],
    "Magic Spoon": [
        {
            "from_agent": "retailer_pitcher", "to_agent": "admin_ops",
            "message_type": "idle",
            "payload": {"brand_name": "Magic Spoon", "agent_status": "idle",
                        "action_label": "", "pending_review_count": 0},
            "hours_ago": 72.0,
        },
        {
            "from_agent": "admin_ops", "to_agent": "brand_onboarding",
            "message_type": "review_required",
            "payload": {"brand_name": "Magic Spoon", "agent_status": "awaiting_review",
                        "action_label": "1 PO discrepancy flagged", "pending_review_count": 1},
            "hours_ago": 2.0,
        },
        {
            "from_agent": "brand_scout", "to_agent": "brand_onboarding",
            "message_type": "evaluation_complete",
            "payload": {"brand_name": "Magic Spoon", "agent_status": "completed",
                        "action_label": "Updated velocity signals", "pending_review_count": 0},
            "hours_ago": 5.0,
        },
    ],
}


def _seed_coordination_messages(client, brand_id_map: dict) -> None:
    """Seed per-brand × per-agent activity messages. Delete-first for idempotency."""
    from datetime import timedelta
    now = datetime.now(timezone.utc)

    # Delete existing messages for these brands so re-seeding is idempotent
    brand_ids = [v for v in brand_id_map.values() if v]
    if brand_ids:
        try:
            client.table("coordination_messages").delete().in_("brand_id", brand_ids).execute()
        except Exception:
            pass

    messages = []
    for brand_name, activity_list in _SANDBOX_ACTIVITY.items():
        brand_id = brand_id_map.get(brand_name)
        if not brand_id:
            continue
        for entry in activity_list:
            ts = now - timedelta(hours=entry["hours_ago"])
            messages.append({
                "from_agent":   entry["from_agent"],
                "to_agent":     entry["to_agent"],
                "brand_id":     brand_id,
                "message_type": entry["message_type"],
                "payload":      entry["payload"],
                "created_at":   ts.isoformat(),
            })

    if messages:
        try:
            client.table("coordination_messages").insert(messages).execute()
        except Exception:
            pass  # activity feed is cosmetic; never block brand seeding


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def seed_sandbox_brands() -> list[str]:
    """
    Insert sandbox brands + brand_evaluations + coordination messages.
    Skips brands already present. Returns list of newly seeded brand names.
    """
    from memory import _get_client
    client = _get_client()
    seeded: list[str] = []
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

    # Seed evaluations for newly added brands (always upsert so scores stay fresh)
    names_to_eval = seeded or _SANDBOX_BRAND_NAMES
    try:
        _seed_brand_evaluations(client, names_to_eval)
    except Exception:
        pass

    # Always reseed activity messages (delete-first inside, so idempotent)
    try:
        _seed_coordination_messages(client, brand_id_map)
    except Exception:
        pass

    return seeded


def clear_sandbox_brands() -> int:
    """
    Delete all sandbox brands, their evaluations, and their coordination messages.
    Returns the number of brands deleted.
    """
    from memory import _get_client
    client = _get_client()

    # Collect sandbox brand IDs for message cleanup
    sandbox = client.table("brands").select("id").eq("is_sandbox", True).execute()
    sandbox_ids = [r["id"] for r in (sandbox.data or [])]

    if sandbox_ids:
        try:
            client.table("coordination_messages").delete().in_("brand_id", sandbox_ids).execute()
        except Exception:
            pass

    # Delete brand evaluations by name (no is_sandbox column there)
    try:
        client.table("brand_evaluations").delete().in_(
            "brand_name", _SANDBOX_BRAND_NAMES
        ).execute()
    except Exception:
        pass

    # Delete the brands (FK CASCADE removes brand_events automatically)
    result = client.table("brands").delete().eq("is_sandbox", True).execute()
    return len(result.data or [])


def verify_sandbox_brands() -> None:
    """Print a readiness summary for each sandbox brand."""

    def _sku_ready(products: list[dict]) -> dict:
        flagship = next((p for p in products if p.get("is_flagship")), products[0] if products else {})
        required_form = ["upc", "case_pack", "net_weight", "wholesale_cost", "msrp", "shelf_life_days", "storage_temp"]
        required_spec = ["gtin", "nutrition", "allergens", "package_dimensions_in", "case_dimensions_in"]
        form_ok = all(flagship.get(f) is not None for f in required_form)
        spec_ok = all(flagship.get(f) is not None for f in required_spec)
        return {"form": form_ok, "spec": spec_ok}

    def _eval_ready(brand_name: str) -> bool:
        return any(e["brand_name"] == brand_name for e in SANDBOX_EVALUATIONS)

    print("\nSandbox brand readiness:")
    for brand in SANDBOX_BRANDS:
        products = brand.get("products", [])
        sku_check = _sku_ready(products)
        eval_ok = _eval_ready(brand["brand_name"])
        has_contact = bool(brand.get("founder_name") and brand.get("founder_email") and brand.get("brand_story"))
        new_item_ok = sku_check["form"] and has_contact
        sell_sheet_ok = eval_ok
        spec_ok = sku_check["spec"]
        pitch_ok = eval_ok

        def tick(b: bool) -> str:
            return "✓" if b else "✗"

        print(
            f"  {brand['brand_name']:<14} "
            f"({len(products)} SKUs)  "
            f"new_item_form {tick(new_item_ok)}  "
            f"sell_sheet {tick(sell_sheet_ok)}  "
            f"spec_sheet {tick(spec_ok)}  "
            f"pitch_email {tick(pitch_ok)}"
        )
    print()


if __name__ == "__main__":
    verify_sandbox_brands()
