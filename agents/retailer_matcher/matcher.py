"""
Retailer Matcher — recommends which buyers to pitch for a given brand.

Hybrid logic:
  - Rule-based fast path for obvious cases (all 3 for established brands,
    category-gated for broker_ready).
  - LLM reasoning for ambiguous cases (broker_ready in unusual categories).

Returns a ranked list of (retailer, fit_score, reasoning).

Does NOT call the pitcher. Just decides who to pitch.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

import agents.llm_shim  # noqa: F401
import anthropic


Retailer = Literal["whole_foods", "sprouts", "erewhon"]


@dataclass
class RetailerRecommendation:
    retailer: Retailer
    fit_score: int         # 0-100
    reasoning: str         # 1 sentence, <= 120 chars
    tier: Literal["strong", "possible", "skip"]


# ── Category affinity priors ─────────────────────────────────────────────────
# Built from broker interview domain knowledge. Not LLM-generated.
_CATEGORY_FIT: dict[str, dict[str, int]] = {
    "beverage_rtd":           {"whole_foods": 75, "sprouts": 65, "erewhon": 70},
    "snack_bar":              {"whole_foods": 80, "sprouts": 75, "erewhon": 60},
    "condiment_sauce":        {"whole_foods": 75, "sprouts": 70, "erewhon": 65},
    "frozen_food":            {"whole_foods": 70, "sprouts": 65, "erewhon": 50},
    "supplement_functional":  {"whole_foods": 70, "sprouts": 85, "erewhon": 80},
    "olive_oil_cooking_oil":  {"whole_foods": 85, "sprouts": 70, "erewhon": 75},
    "dairy_alternative":      {"whole_foods": 80, "sprouts": 75, "erewhon": 70},
    "meat_snack_protein":     {"whole_foods": 70, "sprouts": 65, "erewhon": 55},
    "unknown":                {"whole_foods": 60, "sprouts": 55, "erewhon": 50},
}

_VERDICT_MULTIPLIER = {
    "established":  1.10,
    "broker_ready": 1.00,
    "too_early":    0.70,
}


def _rule_based_recommendation(
    category: str,
    verdict: str,
) -> list[RetailerRecommendation]:
    base = _CATEGORY_FIT.get(category, _CATEGORY_FIT["unknown"])
    mult = _VERDICT_MULTIPLIER.get(verdict, 0.70)

    recs = []
    for retailer in ("whole_foods", "sprouts", "erewhon"):
        raw = base.get(retailer, 50) * mult
        fit = int(min(100, max(0, raw)))
        if fit >= 70:
            tier: Literal["strong", "possible", "skip"] = "strong"
            reason = f"Strong category fit for {retailer.replace('_', ' ')}."
        elif fit >= 50:
            tier = "possible"
            reason = "Worth considering but not a top priority."
        else:
            tier = "skip"
            reason = "Not a natural fit — skip unless broker has relationship."
        recs.append(RetailerRecommendation(
            retailer=retailer,
            fit_score=fit,
            reasoning=reason,
            tier=tier,
        ))
    return sorted(recs, key=lambda r: -r.fit_score)


def _llm_recommendation(
    brand_name: str,
    category: str,
    verdict: str,
    score_total: int,
    broker_brief: str,
) -> list[RetailerRecommendation] | None:
    prompt = f"""You are a CPG broker. Rank these three retailers by fit for pitching this brand:

Brand: {brand_name}
Category: {category}
Overall score: {score_total}/100 ({verdict})
Broker brief: {broker_brief[:400]}

Retailers:
- Whole Foods: premium natural, ~500 stores, highest volume but toughest to enter
- Sprouts: natural/specialty, ~400 stores, easier for emerging brands
- Erewhon: luxury LA market, ~10 stores, taste-making but limited reach

For each retailer, return fit_score (0-100), tier ("strong"|"possible"|"skip"),
and a 1-sentence reasoning (<=120 chars).

Return ONLY a JSON array, no prose:
[
  {{"retailer": "whole_foods", "fit_score": 78, "tier": "strong", "reasoning": "..."}},
  {{"retailer": "sprouts",     "fit_score": 65, "tier": "possible", "reasoning": "..."}},
  {{"retailer": "erewhon",     "fit_score": 45, "tier": "skip", "reasoning": "..."}}
]"""
    try:
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        text = ""
        for block in msg.content:
            if hasattr(block, "text"):
                text += block.text
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        if text.startswith("json"):
            text = text[4:].lstrip()
        data = json.loads(text)
        recs = [
            RetailerRecommendation(
                retailer=r["retailer"],
                fit_score=int(r["fit_score"]),
                reasoning=r["reasoning"][:120],
                tier=r["tier"],
            )
            for r in data
        ]
        return sorted(recs, key=lambda r: -r.fit_score)
    except Exception:
        return None


def recommend_retailers(
    brand_name: str,
    category: str,
    verdict: str,
    score_total: int,
    broker_brief: str = "",
    use_llm: bool = True,
) -> list[RetailerRecommendation]:
    """
    Return a ranked list of 3 RetailerRecommendation.

    Strategy:
      - too_early: rule-based only (all skip-tier).
      - known category + clear verdict: rule-based.
      - unknown category or ambiguous: LLM fallback.
    """
    if verdict == "too_early":
        return _rule_based_recommendation(category, verdict)

    if category not in _CATEGORY_FIT or category == "unknown":
        if use_llm:
            llm_recs = _llm_recommendation(
                brand_name, category, verdict, score_total, broker_brief,
            )
            if llm_recs:
                return llm_recs

    return _rule_based_recommendation(category, verdict)
