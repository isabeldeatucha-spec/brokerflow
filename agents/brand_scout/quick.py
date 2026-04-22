"""
Brand Scout — Quick Triage Mode.

Returns a rough score + verdict in ~5 seconds using one LLM call with web
search. Used for multi-brand triage where the broker wants to compare
several brands before committing to full pitches.

NOT a replacement for full Brand Scout. Full Scout gathers 10+ signal
sources, extracts structured fields, drafts emails. Quick mode returns
only:
    - score_estimate (0-100)
    - verdict ("too_early" | "broker_ready" | "established")
    - one_line_reasoning
    - category (best guess)
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from typing import Literal

import agents.llm_shim  # noqa: F401 — install shim before anthropic import
import anthropic

from memory import _get_client


@dataclass
class QuickTriageResult:
    brand_name: str
    score_estimate: int
    verdict: Literal["too_early", "broker_ready", "established"]
    category: str
    one_line_reasoning: str
    cached: bool = False          # True if we hit brand_evaluations cache
    latency_seconds: float = 0.0
    error: str = ""               # populated only on failure


_TRIAGE_PROMPT = """You are a CPG broker triage analyst. You have 5 seconds to give
a rough score for this brand based on what you know or can quickly find.

Brand: {brand_name}

Score the brand 0-100 on its fitness for an independent broker to pitch to
retailers, using this rubric (condensed from 150+ broker interviews):

  - Velocity Proof (25 pts): does it have Amazon reviews, reorder signals?
  - Distribution Density (20 pts): how many doors / which chains?
  - Margin Viability (20 pts): can it survive distributor+broker markups?
  - Brand Story Clarity (20 pts): clear hero product, specific consumer?
  - Promotional Independence (15 pts): DTC, organic demand, or promo-dependent?

Based on your knowledge of this brand, output a JSON object with EXACTLY these fields:

{{
  "score_estimate": <int 0-100>,
  "verdict": <one of "too_early" | "broker_ready" | "established">,
  "category": <string, e.g. "snack_bar", "beverage_rtd", "condiment_sauce">,
  "one_line_reasoning": <string, max 120 chars, why you gave this score>
}}

Verdict mapping:
  - score < 45:  "too_early"
  - 45 <= score <= 69:  "broker_ready"
  - score >= 70:  "established"

If you have NEVER heard of this brand, return score_estimate=35, verdict="too_early",
category="unknown", one_line_reasoning="Unknown brand — insufficient signal for triage".

Return ONLY the JSON object, no prose, no code fences."""


def _check_cache(brand_name: str) -> QuickTriageResult | None:
    """Return a QuickTriageResult from brand_evaluations cache if available."""
    try:
        client = _get_client()
        result = (
            client.table("brand_evaluations")
            .select("brand_name, score, verdict, category, broker_brief")
            .ilike("brand_name", brand_name.strip())
            .limit(1)
            .execute()
        )
        if result.data:
            row = result.data[0]
            score_val = row.get("score", 0)
            if isinstance(score_val, dict):
                score_val = score_val.get("total", 0)
            return QuickTriageResult(
                brand_name=row["brand_name"],
                score_estimate=int(score_val or 0),
                verdict=row.get("verdict", "too_early"),
                category=row.get("category", "unknown"),
                one_line_reasoning=(row.get("broker_brief", "") or "")[:120],
                cached=True,
            )
    except Exception:
        pass
    return None


def _strip_json_fences(text: str) -> str:
    """Strip ```json ... ``` fences from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    if text.startswith("json"):
        text = text[4:].lstrip()
    return text.strip()


def quick_triage(brand_name: str, use_cache: bool = True) -> QuickTriageResult:
    """
    Return a QuickTriageResult for the given brand in ~5 seconds.
    Uses the brand_evaluations cache if available (returns instantly).
    Otherwise makes one Claude call via the shim.
    """
    t0 = time.monotonic()
    brand_name = (brand_name or "").strip()
    if not brand_name:
        return QuickTriageResult(
            brand_name="", score_estimate=0, verdict="too_early",
            category="unknown", one_line_reasoning="Empty brand name",
            latency_seconds=0.0, error="empty_name",
        )

    # Cache hit
    if use_cache:
        cached = _check_cache(brand_name)
        if cached:
            cached.latency_seconds = time.monotonic() - t0
            return cached

    # Live triage call
    try:
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role": "user", "content": _TRIAGE_PROMPT.format(brand_name=brand_name)}],
        )
        text = ""
        for block in msg.content:
            if hasattr(block, "text"):
                text += block.text
        text = _strip_json_fences(text)
        data = json.loads(text)

        score = int(data.get("score_estimate", 35))
        verdict = data.get("verdict", "too_early")
        if verdict not in ("too_early", "broker_ready", "established"):
            if score >= 70:
                verdict = "established"
            elif score >= 45:
                verdict = "broker_ready"
            else:
                verdict = "too_early"

        return QuickTriageResult(
            brand_name=brand_name,
            score_estimate=score,
            verdict=verdict,
            category=data.get("category", "unknown"),
            one_line_reasoning=data.get("one_line_reasoning", "")[:120],
            cached=False,
            latency_seconds=time.monotonic() - t0,
        )
    except json.JSONDecodeError as e:
        return QuickTriageResult(
            brand_name=brand_name, score_estimate=35, verdict="too_early",
            category="unknown",
            one_line_reasoning="Parse error — using fallback score",
            cached=False,
            latency_seconds=time.monotonic() - t0,
            error=f"json_decode: {e}",
        )
    except Exception as e:
        return QuickTriageResult(
            brand_name=brand_name, score_estimate=35, verdict="too_early",
            category="unknown",
            one_line_reasoning="Triage failed — using fallback",
            cached=False,
            latency_seconds=time.monotonic() - t0,
            error=f"{type(e).__name__}: {e}",
        )


def quick_triage_batch(brand_names: list[str], use_cache: bool = True) -> list[QuickTriageResult]:
    """
    Triage up to N brands. Sequential for safety (avoid provider rate limits
    and keep cost predictable). If latency becomes a problem, switch to
    concurrent.futures.ThreadPoolExecutor with max_workers=3.
    """
    results = []
    for name in brand_names:
        if name.strip():
            results.append(quick_triage(name.strip(), use_cache=use_cache))
    return results
