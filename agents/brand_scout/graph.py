"""
Brand Scout — LangGraph graph definition.

Flow:
  discover_brands
       ↓
  research_brand ←──────────────────┐
       ↓                            │ (if critical gaps, max 2x)
  reflect_and_decide ───────────────┘
       ↓ (no critical gaps or limit reached)
  detect_category_node
       ↓
  score_brand ──[below_threshold]──→ END
       ↓ [above_threshold]
  store_memory
       ↓
  draft_outreach
       ↓
  human_approval ──[rejected]──→ END
       ↓ [approved]
  send_email
       ↓
      END
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt, Command

from state import BrandScoutState, ScoreBreakdown
from memory import memory, get_config, store_brand_evaluation, retrieve_similar_brands, retrieve_brand_history
from agents.brand_scout.prompts import SCORE_THRESHOLDS, SCORING_PROMPT, DRAFT_PROMPT, REFLECTION_PROMPT
from agents.brand_scout.skills.scoring_formula import calculate_score
from agents.brand_scout.tools import (
    scrape_whole_foods_new_arrivals,
    scrape_target_new_arrivals,
    scrape_walmart_new_arrivals,
    scrape_sprouts_new_arrivals,
    scrape_brand_website,
    scrape_amazon_listing,
    scrape_retail_partners,
    scrape_brand_certifications,
    scrape_faire_listing,
    search,
    search_velocity_signals,
    search_press_and_story,
    search_funding_and_team,
    find_founder_contact,
    send_email,
)
from agents.brand_scout.skills.category_benchmarks import detect_category_from_keywords, get_benchmark


# ── Extraction + brief prompts ────────────────────────────────────────────────

EXTRACTION_PROMPT = """
You are a data extraction assistant. Extract structured fields from the research signals below.
Return ONLY valid JSON. Use null for fields not found.
Do NOT guess — only extract what is explicitly stated.

IMPORTANT EXTRACTION RULES:
- For whole_foods_confirmed: check RETAIL PARTNERS section first — if whole_foods=true there, set true. Also set true if "Whole Foods" appears anywhere in signals as a place the brand is sold.
- For target_confirmed: check RETAIL PARTNERS section first — if target=true there, set true. Also check all other signal text.
- For walmart_confirmed: check RETAIL PARTNERS section first — if walmart=true there, set true. Also check all other signal text.
- For sprouts_confirmed: check RETAIL PARTNERS section first — if sprouts=true there, set true.
- For costco_confirmed: check RETAIL PARTNERS section first — if costco=true there, set true.
- For certifications: check CERTIFICATIONS section first — use the list provided there. Supplement with any certs found elsewhere.
- For srp_hero: check CERTIFICATIONS section first for srp value. Then check website/amazon signals. "$18" = 18.0
- For amazon_review_count: look for any number followed by "reviews", "ratings", "global ratings", "customer reviews"
- For amazon_rating: look for any number like "4.7 out of 5" or "4.7 stars"
- For instagram_followers: look for any number followed by "followers" near "instagram" or "IG"
- For funding_amount_usd: look for "$XM raised", "raised $X million", "funding round". Convert to integer (e.g. "$2.37M" = 2370000). Do NOT use valuation as funding.
- For press_trade_mentions: count mentions of NOSH, FoodNavigator, GroceryDive, New Hope Network
- For whole_foods_confirmed, target_confirmed, walmart_confirmed, sprouts_confirmed, costco_confirmed:
  Set true if ANY of these appear in the signals:
  (a) The retailer name is explicitly listed as a place to buy
  (b) Press or Wikipedia describes the brand as having "national distribution", "available nationwide",
      "in major grocery chains", or lists the retailer as a partner
  (c) The brand is described as owned by a major CPG conglomerate (Danone, General Mills, Unilever,
      Nestle, Kraft Heinz, PepsiCo, Coca-Cola) — these brands have national distribution by default
  (d) The brand has 10,000+ Amazon reviews — this level of velocity implies national retail presence
- For estimated_door_count: this means TOTAL NUMBER OF INDIVIDUAL STORE LOCATIONS, not the number of retail chains.
  Examples of correct extraction: "available in 500 stores" → 500, "51,000+ locations" → 51000, "distributed in 300 doors" → 300.
  If signals indicate national distribution or conglomerate ownership, set to 50000.
  Examples of WRONG extraction: "sold at 6 retailers" → DO NOT use 6, this is chain count not door count.
  Only return a number if it explicitly refers to individual store/location count OR signals indicate national scale.
- For inhouse_sales_team: set true if signals mention the brand is owned by a conglomerate or has a dedicated sales organization.
- For faire_listed: set true if the brand appears on faire.com or is described as listed/available on Faire wholesale platform

Fields to extract:
{{
  "amazon_review_count": integer or null,
  "amazon_rating": float or null,
  "amazon_subscribe_save": boolean or null,
  "amazon_bsr_rank": integer or null,
  "amazon_sku_count": integer or null,
  "instacart_banner_count": integer or null,
  "instacart_banners": list of strings or null,
  "whole_foods_confirmed": boolean or null,
  "target_confirmed": boolean or null,
  "walmart_confirmed": boolean or null,
  "sprouts_confirmed": boolean or null,
  "costco_confirmed": boolean or null,
  "faire_present": boolean or null,
  "faire_listed": boolean or null,
  "faire_door_count": integer or null,
  "estimated_door_count": integer or null,
  "srp_min": float or null,
  "srp_max": float or null,
  "srp_hero": float or null,
  "category": string or null,
  "funding_amount_usd": integer or null,
  "funding_stage": string or null,
  "instagram_followers": integer or null,
  "tiktok_followers": integer or null,
  "press_trade_mentions": integer or null,
  "press_consumer_mentions": integer or null,
  "expo_west_confirmed": boolean or null,
  "dtc_channel": boolean or null,
  "subscription_available": boolean or null,
  "promo_frequency_tpr_per_year": integer or null,
  "bogo_detected": boolean or null,
  "founder_story_clear": boolean or null,
  "certifications": list of strings or null,
  "hero_product_clear": boolean or null,
  "national_chain_count": integer or null,
  "publicly_traded": boolean or null,
  "inhouse_sales_team": boolean or null,
  "spins_mentioned": boolean or null,
  "sell_through_press": boolean or null
}}

Research signals:
{signals}
"""

CATEGORY_DETECTION_PROMPT = """
You are a CPG category expert. Based on the brand signals below, identify which single category this brand belongs to.

Choose exactly one:
- meat_snack_protein (beef sticks, jerky, meat snacks, protein bars, meat-based snacks)
- snack_bar (granola bars, energy bars, oat bars, trail mix, cereal bars)
- beverage_rtd (drinks, juices, waters, coffee, tea, kombucha, energy drinks, coconut water, smoothies)
- condiment_sauce (hot sauce, dressings, condiments, oils, vinegars, seasonings, spreads, pasta sauce)
- frozen_food (frozen meals, frozen snacks, ice cream, frozen pizza, frozen burritos)
- supplement_functional (vitamins, supplements, protein powder, adaptogens, functional mushrooms, collagen, creatine)
- olive_oil_cooking_oil (olive oil, avocado oil, cooking oils — oil-specific brands only)
- dairy_alternative (yogurt, greek yogurt, kefir, milk, oat milk, almond milk, dairy products, cheese, butter)
- unknown (cannot determine)

Brand: {brand_name}
Signals: {signals_summary}

Return ONLY the category key. Example: dairy_alternative
"""

BRIEF_PROMPT = """
Given these brand scores and research signals, write:
1. A 3-4 sentence broker_brief a broker could read in 20 seconds
2. A list of 2-3 key_gaps — specific things the broker needs to verify before signing
3. An outreach_angle: one sentence describing the hook a broker should use when reaching out

Verdict context:
- established (70+): proven brand, likely already has broker relationships — angle on filling regional gaps or accounts they don't currently reach
- broker_ready (45-69): strong trajectory, ready to scale — angle on accelerating growth into new retail doors
- too_early (<45): not used here

Brand: {brand_name}
Category: {category}
Verdict: {verdict}
Scores: {scores}
Total: {total}/100
Key signals: {signals_summary}

Return JSON: {{"broker_brief": "...", "key_gaps": ["...", "..."], "outreach_angle": "..."}}
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compact_signals(obj, max_str: int = 600):
    """
    Recursively truncate long strings in the signals dict before sending to Claude.
    Parallel Extract returns full-page markdown — without this, prompts easily
    exceed the 200k token limit.
    """
    if isinstance(obj, dict):
        # Strip discovery list — it's brand selection metadata, not scoring signals.
        # At 400+ entries it dominates the token budget (192k / 202k total chars).
        return {
            k: _compact_signals(v, max_str)
            for k, v in obj.items()
            if k not in ("discovery", "discovery_errors")
        }
    if isinstance(obj, list):
        return [_compact_signals(v, max_str) for v in obj]
    if isinstance(obj, str) and len(obj) > max_str:
        return obj[:max_str] + "…"
    return obj


# ── Nodes ─────────────────────────────────────────────────────────────────────

def discover_brands(state: BrandScoutState) -> dict:
    """If brand name already provided, skip scraping and go straight to research."""
    cli_brand = state.get("brand_name", "")
    cli_url   = state.get("website_url", "")

    # Brand name supplied by user — no need to scrape retailer pages
    if cli_brand:
        return {
            "brand_name": cli_brand,
            "website_url": cli_url,
            "sources_checked": [],
            "signals_found": {},
            "follow_up_queries": [],
            "reflection_count": 0,
            "reflection_notes": [],
            "category": "",
            "benchmark": {},
            "extracted_fields": {},
        }

    # No brand name — discover from retailer new-arrivals
    found: list[dict] = []
    found.extend(scrape_whole_foods_new_arrivals())
    found.extend(scrape_target_new_arrivals())
    found.extend(scrape_walmart_new_arrivals())
    found.extend(scrape_sprouts_new_arrivals())

    valid: list[dict] = []
    seen_names: set[str] = set()
    for b in found:
        if "error" in b or not b.get("brand_name"):
            continue
        key = b["brand_name"].lower()
        if key not in seen_names:
            seen_names.add(key)
            valid.append(b)

    errors = [b for b in found if "error" in b]
    if not valid:
        return {
            "brand_name": "Unknown Brand",
            "website_url": "",
            "sources_checked": ["whole_foods", "target", "sprouts"],
            "signals_found": {"discovery_errors": errors},
            "follow_up_queries": [],
            "reflection_count": 0,
            "reflection_notes": [],
            "category": "",
            "benchmark": {},
            "extracted_fields": {},
        }

    brand = valid[0]
    return {
        "brand_name": brand["brand_name"],
        "website_url": brand.get("website_url", ""),
        "sources_checked": ["whole_foods", "target", "sprouts"],
        "signals_found": {"discovery": valid, "discovery_errors": errors},
        "follow_up_queries": [],
        "reflection_count": 0,
        "reflection_notes": [],
        "category": "",
        "benchmark": {},
        "extracted_fields": {},
    }


def research_brand(state: BrandScoutState) -> dict:
    """Pull signals from all sources in parallel. On follow-up loops, also run specific queries."""
    brand_name  = state["brand_name"]
    website_url = state["website_url"]
    existing_signals = state.get("signals_found", {})

    tasks = {
        "website":          lambda: scrape_brand_website(website_url),
        "amazon":           lambda: scrape_amazon_listing(brand_name),
        "retail_partners":  lambda: scrape_retail_partners(website_url),
        "certifications_scrape": lambda: scrape_brand_certifications(website_url),
        "faire":            lambda: scrape_faire_listing(brand_name),
        "velocity":         lambda: search_velocity_signals(brand_name),
        "press":            lambda: search_press_and_story(brand_name),
        "funding":          lambda: search_funding_and_team(brand_name),
    }
    # Add brand history check on first pass
    if state.get("reflection_count", 0) == 0:
        tasks["brand_history_raw"] = lambda: retrieve_brand_history(brand_name)

    # Add follow-up queries from reflection loop
    follow_up_queries = state.get("follow_up_queries", [])
    for q in follow_up_queries:
        tasks[f"followup::{q}"] = (lambda _q=q: search(_q, max_results=3))

    results: dict = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fn): key for key, fn in tasks.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as e:
                results[key] = {"error": str(e)}

    new_signals = {**existing_signals}
    for key in ("website", "amazon", "retail_partners", "certifications_scrape",
                "faire", "velocity", "press", "funding"):
        if key in results:
            new_signals[key] = results[key]

    if results.get("brand_history_raw"):
        new_signals["brand_history"] = results["brand_history_raw"]

    follow_up_results: dict = {}
    for q in follow_up_queries:
        raw = results.get(f"followup::{q}", [])
        follow_up_results[q] = [
            {"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content", "")[:300]}
            for r in (raw if isinstance(raw, list) else [])
            if "error" not in r
        ]
    if follow_up_results:
        new_signals["follow_up_research"] = follow_up_results

    return {
        "sources_checked": state.get("sources_checked", []) + [
            "website", "amazon", "faire", "spins_instacart", "press", "funding"
        ],
        "signals_found": new_signals,
        "follow_up_queries": [],
    }


def reflect_and_decide(state: BrandScoutState) -> dict:
    """
    ReAct reflection node: review signals collected, identify critical gaps,
    decide whether to loop back for targeted follow-up or proceed to scoring.
    Max 2 reflection loops.
    """
    reflection_count = state.get("reflection_count", 0)

    # Always proceed after 2 loops regardless of gaps
    if reflection_count >= 2:
        notes = state.get("reflection_notes", [])
        return {
            "reflection_notes": notes + ["Reflection limit reached (2/2) — proceeding to score with available data."],
            "follow_up_queries": [],
        }

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    prompt = REFLECTION_PROMPT.format(
        brand_name=state["brand_name"],
        website_url=state["website_url"],
        reflection_count=reflection_count + 1,
        signals_json=json.dumps(_compact_signals(state["signals_found"]), indent=2),
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw)

    notes = state.get("reflection_notes", [])
    reasoning = data.get("reasoning", "")
    contradictions = data.get("contradictions_found", [])
    gaps = data.get("critical_gaps", [])

    note = reasoning
    if contradictions:
        note += f" | Contradictions: {'; '.join(contradictions)}"
    if gaps:
        note += f" | Critical gaps: {'; '.join(gaps)}"

    follow_up = data.get("follow_up_queries", []) if data.get("should_dig_deeper") else []

    return {
        "reflection_count": reflection_count + 1,
        "reflection_notes": notes + [note],
        "follow_up_queries": follow_up,
    }


def detect_category_node(state: BrandScoutState) -> dict:
    """LLM-based category detection with keyword fallback."""
    brand_name = state.get("brand_name", "")
    signals = state.get("signals_found", {})

    signals_text = " ".join([
        str(signals.get("website", {}).get("homepage", ""))[:500],
        str(signals.get("amazon", {}).get("extracted_page", ""))[:300],
        str(signals.get("press", {}).get("trade_press", ""))[:200],
    ])

    valid_categories = [
        "meat_snack_protein", "snack_bar", "beverage_rtd", "condiment_sauce",
        "frozen_food", "supplement_functional", "olive_oil_cooking_oil",
        "dairy_alternative", "unknown"
    ]

    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            messages=[{
                "role": "user",
                "content": CATEGORY_DETECTION_PROMPT.format(
                    brand_name=brand_name,
                    signals_summary=signals_text[:1000],
                )
            }]
        )
        category = response.content[0].text.strip().lower()
        if category not in valid_categories:
            category = detect_category_from_keywords(signals_text + " " + brand_name)
    except Exception as e:
        print(f"[detect_category] LLM failed: {e}, using keyword fallback")
        category = detect_category_from_keywords(signals_text + " " + brand_name)

    benchmark = get_benchmark(category)
    print(f"[detect_category] {brand_name} → {category}")
    return {"category": category, "benchmark": benchmark}


def _build_signals_string(state: BrandScoutState) -> str:
    """Flatten all signal dicts into a single rich string for the extraction prompt."""
    signals = state.get("signals_found", {})
    parts = []

    website = signals.get("website", {})
    parts.append(f"WEBSITE: {website.get('homepage', '')} {website.get('retail_page', '')}")

    amazon = signals.get("amazon", {})
    # Firecrawl keys (structured) + Parallel fallback keys (text)
    fc_parts = []
    if amazon.get("review_count") is not None:
        fc_parts.append(f"{amazon['review_count']} customer reviews")
    if amazon.get("rating") is not None:
        fc_parts.append(f"{amazon['rating']} out of 5 stars")
    if amazon.get("price_min") is not None:
        fc_parts.append(f"price from ${amazon['price_min']}")
    if amazon.get("price_max") is not None:
        fc_parts.append(f"to ${amazon['price_max']}")
    if amazon.get("sku_count") is not None:
        fc_parts.append(f"{amazon['sku_count']} distinct SKUs")
    if amazon.get("subscribe_save") is not None:
        fc_parts.append(f"Subscribe & Save: {amazon['subscribe_save']}")
    if amazon.get("bsr_rank") is not None:
        fc_parts.append(f"Best Seller Rank: #{amazon['bsr_rank']}")
    amazon_text = " | ".join(fc_parts) + " " + " ".join(str(v) for v in [
        amazon.get("review_data", ""),
        amazon.get("product_data", ""),
        amazon.get("presence_data", ""),
        amazon.get("fallback_search", ""),
    ] if v not in ("", None))
    parts.append(f"AMAZON: {amazon_text}")

    velocity = signals.get("velocity", {})
    parts.append(f"INSTACART/VELOCITY: {velocity.get('instacart', '')} {velocity.get('instacart_search', '')} {velocity.get('spins_search', '')} {velocity.get('faire_search', '')}")

    press = signals.get("press", {})
    parts.append(f"PRESS/SOCIAL: {press.get('trade_press', '')} {press.get('consumer_press', '')} {press.get('social_signals', '')} {press.get('expo', '')}")

    funding = signals.get("funding", {})
    parts.append(f"FUNDING/TEAM: {funding.get('funding', '')} {funding.get('founder', '')}")

    # Retail partners (dedicated Firecrawl scrape — most reliable)
    retail = signals.get("retail_partners", {})
    if retail.get("data"):
        retail_text = json.dumps(retail["data"])
    else:
        raw_retail = " | ".join(filter(None, [
            retail.get("retailer_search", ""),
            retail.get("product_search", ""),
        ]))
        # Pre-detect retailer presence and inject explicit flags so Haiku doesn't have to infer
        raw_lower = raw_retail.lower()
        detected = []
        if "target" in raw_lower:        detected.append("target=true")
        if "walmart" in raw_lower:       detected.append("walmart=true")
        if "whole foods" in raw_lower:   detected.append("whole_foods=true")
        if "sprouts" in raw_lower:       detected.append("sprouts=true")
        if "costco" in raw_lower:        detected.append("costco=true")
        if "kroger" in raw_lower:        detected.append("kroger=true")
        flags_line = ("DETECTED RETAILERS: " + ", ".join(detected)) if detected else ""
        retail_text = (flags_line + "\n" + raw_retail).strip()
    parts.append(f"RETAIL PARTNERS (dedicated scrape): {retail_text}")

    # Certifications + SRP (dedicated Firecrawl scrape)
    certs = signals.get("certifications_scrape", {})
    parts.append(f"CERTIFICATIONS (dedicated scrape): {json.dumps(certs.get('data', ''))}")

    follow_up = signals.get("follow_up_research", {})
    if follow_up:
        follow_text = " ".join(
            f"{q}: " + " ".join(r.get("snippet", "") for r in results)
            for q, results in follow_up.items()
        )
        parts.append(f"FOLLOW-UP RESEARCH: {follow_text}")

    return "\n\n".join(p for p in parts if p.strip())


def extract_fields(state: BrandScoutState) -> dict:
    """
    Stage 1 of deterministic scoring: use Claude Haiku to extract structured fields
    from raw research signals. Runs after detect_category_node so the detected
    category can be injected into the fields before scoring.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    signals_str = _build_signals_string(state)
    prompt = EXTRACTION_PROMPT.format(signals=signals_str[:10000])

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        fields = json.loads(raw)
    except json.JSONDecodeError:
        fields = {}

    # Override extracted category with the deterministic detect_category result
    if state.get("category"):
        fields["category"] = state["category"]

    # Hard-override retailer flags from pre-detected signals — Haiku is unreliable on boolean inference
    # The RETAIL PARTNERS section has "DETECTED RETAILERS: target=true, walmart=true, ..." injected by
    # _build_signals_string. Parse those directly rather than hoping Haiku picks them up.
    retail = state.get("signals_found", {}).get("retail_partners", {})
    raw_retail = " ".join(filter(None, [
        json.dumps(retail.get("data", {})),
        retail.get("retailer_search", ""),
        retail.get("product_search", ""),
    ])).lower()
    if "target" in raw_retail and fields.get("target_confirmed") is None:
        fields["target_confirmed"] = True
    if "walmart" in raw_retail and fields.get("walmart_confirmed") is None:
        fields["walmart_confirmed"] = True
    if "whole foods" in raw_retail and fields.get("whole_foods_confirmed") is None:
        fields["whole_foods_confirmed"] = True
    if "sprouts" in raw_retail and fields.get("sprouts_confirmed") is None:
        fields["sprouts_confirmed"] = True
    if "costco" in raw_retail and fields.get("costco_confirmed") is None:
        fields["costco_confirmed"] = True

    print(f"[extract_fields] Extracted: {json.dumps(fields, indent=2)}")

    return {"extracted_fields": fields}


def score_brand(state: BrandScoutState) -> dict:
    """
    Stage 2 of deterministic scoring:
      1. Run the rule-based calculate_score formula on extracted_fields.
      2. Make a single Claude Sonnet call to generate broker_brief + key_gaps.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # ── Deterministic score ────────────────────────────────────────────────────
    result = calculate_score(state.get("extracted_fields") or {})
    print(f"[score_brand] extracted_fields keys: {list((state.get('extracted_fields') or {}).keys())}")
    print(f"[score_brand] Formula result: {result}")
    print(f"[score_brand] Storing to state: score={result['total']}, scores={result['scores']}")
    scores      = result["scores"]
    total       = result["total"]
    verdict_key = result["verdict"]

    # Map formula verdict → graph routing key
    if verdict_key in ("established", "broker_ready"):
        graph_verdict = "above_threshold"
    else:
        graph_verdict = "below_threshold"

    # ── Single Sonnet call for broker brief + key gaps ─────────────────────────
    category = state.get("category", "unknown")
    signals_summary = json.dumps(_compact_signals(state["signals_found"]), indent=2)[:2000]

    prompt = BRIEF_PROMPT.format(
        brand_name=state["brand_name"],
        category=category,
        verdict=verdict_key,
        scores=json.dumps(scores),
        total=total,
        signals_summary=signals_summary,
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    brief_data = json.loads(raw)

    score: ScoreBreakdown = {
        "velocity_proof":          scores["velocity_proof"],
        "distribution_density":    scores["distribution_density"],
        "margin_viability":        scores["margin_viability"],
        "brand_story_clarity":     scores["brand_story_clarity"],
        "promotional_independence": scores["promotional_independence"],
        "total": total,
    }

    return {
        "score": score,
        "verdict": graph_verdict,
        "extracted_fields": state.get("extracted_fields") or {},
        "signals_found": {
            **state.get("signals_found", {}),
            "score_detail": {
                "velocity_proof":          {"score": scores["velocity_proof"]},
                "distribution_density":    {"score": scores["distribution_density"]},
                "margin_viability":        {"score": scores["margin_viability"]},
                "brand_story_clarity":     {"score": scores["brand_story_clarity"]},
                "promotional_independence": {"score": scores["promotional_independence"]},
                "total":              total,
                "verdict":         verdict_key,
                "broker_brief":    brief_data.get("broker_brief", ""),
                "key_gaps":        brief_data.get("key_gaps", []),
                "outreach_angle":  brief_data.get("outreach_angle", ""),
            },
        },
    }


def store_memory_node(state: BrandScoutState) -> dict:
    """Persist this evaluation to Supabase for future cross-run comparisons and reload."""
    detail = state.get("signals_found", {}).get("score_detail", {})

    key_signals = {
        "instacart_banners": state.get("signals_found", {}).get("velocity", {}).get("instacart", "")[:200],
        "trade_press":       state.get("signals_found", {}).get("press", {}).get("trade_press", "")[:200],
        "social_signals":    state.get("signals_found", {}).get("press", {}).get("social_signals", "")[:200],
        "funding":           state.get("signals_found", {}).get("funding", {}).get("funding", "")[:200],
    }

    store_brand_evaluation(
        brand_name=       state["brand_name"],
        score=            state["score"]["total"],
        verdict=          detail.get("verdict", state.get("verdict", "")),
        category=         state.get("category", "unknown"),
        key_signals=      key_signals,
        key_gaps=         detail.get("key_gaps", []),
        broker_brief=     detail.get("broker_brief", ""),
        score_breakdown=  {
            k: v for k, v in detail.items()
            if k in ("velocity_proof", "distribution_density", "margin_viability",
                     "brand_story_clarity", "promotional_independence")
        },
        reflection_notes= state.get("reflection_notes", []),
        email_draft=      state.get("email_draft", ""),
        founder_name=     state.get("founder_name", ""),
        founder_email=    state.get("founder_email", ""),
    )
    return {}


def _extract_founder_name(raw_content: str, brand_name: str, client: anthropic.Anthropic) -> str:
    """
    Use Claude to extract the first founder/CEO/co-founder name from raw search content.
    Returns the name string, or empty string if none found.
    """
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=32,
        messages=[{
            "role": "user",
            "content": (
                f"From the text below, extract the full name of the person most likely to be "
                f"the founder, co-founder, or CEO of {brand_name}. "
                f"This includes anyone whose LinkedIn profile is linked to the company, "
                f"or who is described as a leader, owner, or key person at the brand. "
                f"Reply with ONLY the person's full name — no explanation, no punctuation. "
                f"If no individual person can be identified at all, reply: UNKNOWN\n\n{raw_content[:1500]}"
            ),
        }],
    )
    name = message.content[0].text.strip()
    return "" if name.upper().startswith("UNKNOWN") else name


def draft_outreach(state: BrandScoutState) -> dict:
    """Find founder contact and draft a personalized outreach email using Claude."""
    contact = find_founder_contact(state["brand_name"], state["website_url"])
    founder_email = contact["founder_email"]

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # Parse founder name from raw search content using Claude — more reliable than regex
    raw = contact.get("raw_content", "")
    extracted = _extract_founder_name(raw, state["brand_name"], client) if raw else ""
    cleaned = extracted.strip()
    is_corporate = not cleaned or cleaned.lower() in ("hi there", "unknown", "none", "")
    founder_name = cleaned if not is_corporate else ""
    recipient_context = (
        "This is a corporate brand — no individual founder identified. "
        "Address the email generically (e.g. 'Hi,') and direct it to the brand team or category manager, not a named individual."
        if is_corporate else
        f"Address to {cleaned}, the founder. Use their first name."
    )
    score = state["score"]

    score_detail = state.get("signals_found", {}).get("score_detail", {})
    verdict      = score_detail.get("verdict", "broker_ready")
    outreach_angle = score_detail.get("outreach_angle", "")

    prompt = DRAFT_PROMPT.format(
        brand_name=state["brand_name"],
        founder_name=founder_name if founder_name else "(corporate brand — no founder identified)",
        recipient_context=recipient_context,
        verdict=verdict,
        outreach_angle=outreach_angle,
        total=score["total"],
        velocity_proof=score["velocity_proof"],
        distribution_density=score["distribution_density"],
        margin_viability=score["margin_viability"],
        brand_story_clarity=score["brand_story_clarity"],
        promotional_independence=score["promotional_independence"],
        signals_json=json.dumps(_compact_signals(state["signals_found"]), indent=2),
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    display_name = founder_name or state["brand_name"] + " Team"
    return {
        "founder_name": display_name,
        "founder_email": founder_email,
        "email_draft": message.content[0].text.strip(),
    }


def human_approval(state: BrandScoutState) -> dict:
    """Pause the graph for broker review."""
    decision = interrupt(
        {
            "brand_name": state["brand_name"],
            "score": state["score"],
            "signals_found": state["signals_found"],
            "founder_name": state["founder_name"],
            "founder_email": state["founder_email"],
            "email_draft": state["email_draft"],
        }
    )
    return {
        "approved": decision.get("approved", False),
        "rejection_reason": decision.get("rejection_reason", ""),
    }


def send_email_node(state: BrandScoutState) -> dict:
    """Send the approved outreach email."""
    lines = state["email_draft"].strip().splitlines()
    subject = "Introduction from your broker"
    body_start = 0

    for i, line in enumerate(lines):
        if line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
            body_start = i + 1
            break

    while body_start < len(lines) and not lines[body_start].strip():
        body_start += 1

    body = "\n".join(lines[body_start:])
    result = send_email(to=state["founder_email"], subject=subject, body=body)
    return {"signals_found": {**state["signals_found"], "email_send_result": result}}


# ── Routing ───────────────────────────────────────────────────────────────────

def _route_after_reflect(state: BrandScoutState) -> str:
    """Loop back to research if the agent identified critical gaps; otherwise score."""
    queries = state.get("follow_up_queries", [])
    if queries:
        return "research_brand"
    return "detect_category_node"


def _route_after_score(state: BrandScoutState) -> str:
    return state["verdict"]


def _route_after_approval(state: BrandScoutState) -> str:
    return "send_email" if state.get("approved") else "rejected"


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_graph():
    builder = StateGraph(BrandScoutState)

    builder.add_node("discover_brands", discover_brands)
    builder.add_node("research_brand", research_brand)
    builder.add_node("reflect_and_decide", reflect_and_decide)
    builder.add_node("detect_category_node", detect_category_node)
    builder.add_node("extract_fields", extract_fields)
    builder.add_node("score_brand", score_brand)
    builder.add_node("store_memory", store_memory_node)
    builder.add_node("draft_outreach", draft_outreach)
    builder.add_node("human_approval", human_approval)
    builder.add_node("send_email", send_email_node)

    builder.set_entry_point("discover_brands")
    builder.add_edge("discover_brands", "research_brand")
    builder.add_edge("research_brand", "reflect_and_decide")

    builder.add_conditional_edges(
        "reflect_and_decide",
        _route_after_reflect,
        {"research_brand": "research_brand", "detect_category_node": "detect_category_node"},
    )

    builder.add_edge("detect_category_node", "extract_fields")
    builder.add_edge("extract_fields", "score_brand")

    builder.add_conditional_edges(
        "score_brand",
        _route_after_score,
        {"above_threshold": "draft_outreach", "below_threshold": "store_memory"},
    )

    builder.add_edge("draft_outreach", "store_memory")

    builder.add_conditional_edges(
        "store_memory",
        _route_after_score,
        {"above_threshold": "human_approval", "below_threshold": END},
    )

    builder.add_conditional_edges(
        "human_approval",
        _route_after_approval,
        {"send_email": "send_email", "rejected": END},
    )

    builder.add_edge("send_email", END)

    return builder.compile(checkpointer=memory)


graph = build_graph()
