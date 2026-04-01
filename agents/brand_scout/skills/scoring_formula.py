"""
Deterministic scoring formula for Brand Scout.

Converts extracted structured fields into a 100-point broker-readiness score.
All scoring logic is rule-based — no LLM calls — so results are identical across runs.
"""


def calculate_score(fields: dict) -> dict:
    score = {}

    # VELOCITY PROOF (25pts)
    vp = 0
    reviews = fields.get("amazon_review_count")
    if reviews is None:       vp += 5
    elif reviews >= 1000:     vp += 10
    elif reviews >= 500:      vp += 8
    elif reviews >= 200:      vp += 6
    elif reviews >= 50:       vp += 3
    else:                     vp += 1

    rating = fields.get("amazon_rating")
    if rating is None:        vp += 2
    elif rating >= 4.5:       vp += 5
    elif rating >= 4.2:       vp += 4
    elif rating >= 4.0:       vp += 3
    elif rating >= 3.5:       vp += 1
    else:                     vp += 0

    if fields.get("amazon_subscribe_save") is None:  vp += 2
    elif fields.get("amazon_subscribe_save"):        vp += 4
    else:                                            vp += 0

    banners = fields.get("instacart_banner_count") or 0
    if fields.get("instacart_banner_count") is None: vp += 1
    elif banners >= 3:   vp += 3
    elif banners >= 1:   vp += 2
    else:                vp += 0

    if fields.get("spins_mentioned"):       vp += 3
    elif fields.get("sell_through_press"):  vp += 2
    else:                                   vp += 1

    score["velocity_proof"] = min(vp, 25)

    # DISTRIBUTION DENSITY (20pts)
    dd = 0
    doors = fields.get("estimated_door_count")
    if doors is None:            dd += 4
    elif 50 <= doors <= 300:     dd += 8
    elif 20 <= doors < 50:       dd += 5
    elif 300 < doors <= 800:     dd += 6
    elif doors > 800:            dd += 2
    else:                        dd += 1

    retailer_pts = 0
    if fields.get("whole_foods_confirmed"):  retailer_pts += 3
    if fields.get("sprouts_confirmed"):      retailer_pts += 2
    if fields.get("target_confirmed"):       retailer_pts += 2
    if fields.get("costco_confirmed"):       retailer_pts += 2
    if fields.get("walmart_confirmed"):      retailer_pts += 1
    retailer_pts = min(retailer_pts, 8)
    nationals = sum([
        bool(fields.get("whole_foods_confirmed")),
        bool(fields.get("target_confirmed")),
        bool(fields.get("walmart_confirmed")),
        bool(fields.get("costco_confirmed"))
    ])
    if nationals >= 4:  retailer_pts = max(retailer_pts - 2, 3)
    dd += retailer_pts

    if fields.get("faire_listed") is None:  dd += 2
    elif fields.get("faire_listed"):        dd += 4
    else:                                   dd += 0
    score["distribution_density"] = min(dd, 20)

    # MARGIN VIABILITY (20pts)
    mv = 0
    srp = fields.get("srp_hero") or fields.get("srp_min")
    category = fields.get("category", "unknown")
    benchmarks = {
        "beverage_rtd": (3.50, 6.00),
        "snack_bar": (2.50, 5.00),
        "condiment_sauce": (7.00, 16.00),
        "frozen_food": (6.00, 14.00),
        "supplement_functional": (20.00, 65.00),
        "olive_oil_cooking_oil": (12.00, 35.00),
        "dairy_alternative": (5.00, 12.00),
        "meat_snack_protein": (2.00, 5.00),
        "unknown": (6.00, 20.00),
    }
    low, high = benchmarks.get(category, (6.00, 20.00))
    if srp is None:              mv += 5
    elif srp >= low * 1.2:       mv += 10
    elif srp >= low:             mv += 7
    elif srp >= low * 0.8:       mv += 4
    else:                        mv += 1

    funding = fields.get("funding_amount_usd") or 0
    if fields.get("funding_amount_usd") is None:  mv += 3
    elif funding >= 5_000_000:   mv += 6
    elif funding >= 1_000_000:   mv += 4
    elif funding > 0:            mv += 2
    else:                        mv += 1

    if fields.get("faire_listed") is None:  mv += 2
    elif fields.get("faire_listed"):        mv += 3
    else:                                   mv += 1
    score["margin_viability"] = min(mv, 20)

    # BRAND STORY CLARITY (20pts)
    bs = 0
    if fields.get("hero_product_clear") is None:   bs += 2
    elif fields.get("hero_product_clear"):         bs += 4
    else:                                          bs += 0

    if fields.get("founder_story_clear") is None:  bs += 1
    elif fields.get("founder_story_clear"):        bs += 3
    else:                                          bs += 0

    ig = fields.get("instagram_followers") or 0
    tt = fields.get("tiktok_followers") or 0
    social_max = max(ig, tt)
    if fields.get("instagram_followers") is None and fields.get("tiktok_followers") is None:
        bs += 2
    elif social_max >= 100_000:  bs += 5
    elif social_max >= 50_000:   bs += 4
    elif social_max >= 10_000:   bs += 3
    elif social_max >= 1_000:    bs += 2
    else:                        bs += 1

    trade = fields.get("press_trade_mentions") or 0
    if fields.get("press_trade_mentions") is None:  bs += 2
    elif trade >= 3:   bs += 4
    elif trade >= 1:   bs += 3
    else:              bs += 1

    certs = fields.get("certifications") or []
    if fields.get("certifications") is None:  bs += 1
    elif len(certs) >= 2:  bs += 2
    elif len(certs) >= 1:  bs += 1
    else:                  bs += 0

    if fields.get("expo_west_confirmed") is None:   bs += 1
    elif fields.get("expo_west_confirmed"):         bs += 2
    else:                                           bs += 0
    score["brand_story_clarity"] = min(bs, 20)

    # PROMOTIONAL INDEPENDENCE (15pts)
    pi = 0
    if fields.get("dtc_channel") is None:          pi += 2
    elif fields.get("dtc_channel"):
        if fields.get("subscription_available"):   pi += 4
        else:                                      pi += 3
    else:                                          pi += 0

    if fields.get("instagram_followers") is None and fields.get("tiktok_followers") is None:
        pi += 2
    elif social_max >= 100_000:  pi += 4
    elif social_max >= 50_000:   pi += 3
    elif social_max >= 10_000:   pi += 2
    elif social_max >= 1_000:    pi += 1
    else:                        pi += 0

    tprs = fields.get("promo_frequency_tpr_per_year")
    bogo = fields.get("bogo_detected", False)
    if tprs is None:        pi += 2
    elif tprs <= 2:         pi += 4
    elif tprs <= 4:         pi += 3
    elif tprs <= 6:         pi += 1
    else:                   pi += 0
    if bogo:                pi = max(pi - 2, 0)

    if fields.get("amazon_subscribe_save") is None:  pi += 1
    elif fields.get("amazon_subscribe_save"):        pi += 3
    else:                                            pi += 0
    score["promotional_independence"] = min(pi, 15)

    # TOTAL + VERDICT
    total = sum(score.values())
    nationals_count = sum([
        bool(fields.get("whole_foods_confirmed")),
        bool(fields.get("target_confirmed")),
        bool(fields.get("walmart_confirmed")),
        bool(fields.get("costco_confirmed"))
    ])
    beyond_broker = (
        fields.get("publicly_traded") or
        fields.get("inhouse_sales_team") or
        (fields.get("estimated_door_count") or 0) > 5000 or
        nationals_count >= 4
    )
    if total >= 70 and not beyond_broker:
        verdict = "broker_ready"
    elif total >= 45:
        verdict = "promising"
    else:
        verdict = "too_early"

    return {
        "scores": score,
        "total": total,
        "verdict": verdict,
        "beyond_broker_flag": bool(beyond_broker),
        "extracted_fields": fields,
    }
