"""
Experiment 1: Memory Strategy A vs B
=====================================
Two strategies for how the reflect_and_decide node handles accumulated signals.

Group A — FullHistoryMemory:
  Pass the full raw signals dict to Claude verbatim every reflection round.
  This is the existing production behavior.

Group B — SummarizedMemory:
  Before each reflection round, compress the raw signals into a structured
  summary via Claude Haiku, then pass the summary instead.
  Hypothesis: cheaper + faster at the cost of some precision.
"""
import json
import os
import time

import anthropic

SUMMARY_PROMPT = """You are a concise CPG research summarizer. Given raw research signals for a brand,
produce a compact JSON summary that preserves everything needed for a broker-readiness reflection.

Focus on:
- Which retailers carry the brand (Whole Foods, Target, Walmart, Sprouts, etc.)
- Amazon metrics: review count, rating, BSR, Subscribe & Save
- Pricing / SRP for the hero SKU
- Faire presence and door count
- Instacart banner count
- Funding round and stage
- Social following (Instagram, TikTok)
- Trade / consumer press mentions
- Certifications (Organic, Non-GMO, etc.)
- Any failed or missing data sources
- Any contradictions or anomalies you spotted

Brand: {brand_name}
Raw signals (truncated to {char_limit} chars):
{signals_json}

Return ONLY valid JSON with these keys:
{{
  "retail_summary": "...",
  "amazon_summary": "...",
  "velocity_summary": "...",
  "brand_story_summary": "...",
  "pricing_summary": "...",
  "funding_summary": "...",
  "gaps_and_missing": ["..."],
  "contradictions": ["..."],
  "key_facts": ["fact 1", "fact 2", "..."]
}}
Keep total response under 500 tokens. Be specific (numbers, retailer names), not vague."""


class FullHistoryMemory:
    """
    Group A: No compression. Pass the raw signals_found dict unchanged to
    every reflection round — exactly what production does today.
    """
    name = "full_history"

    def compress_signals(
        self,
        signals: dict,
        brand_name: str,
        client: anthropic.Anthropic,
    ) -> tuple[dict, dict]:
        """
        Returns (signals_for_reflection, compression_metrics).
        No LLM call; overhead is zero.
        """
        token_estimate = len(json.dumps(signals)) // 4
        return signals, {
            "compression_tokens_in": 0,
            "compression_tokens_out": 0,
            "compression_latency_ms": 0,
            "signals_char_len": len(json.dumps(signals)),
            "estimated_tokens_passed": token_estimate,
        }


class SummarizedMemory:
    """
    Group B: Before each reflection round, call Claude Haiku to compress the
    accumulated signals into a structured summary. The summary is passed to
    Sonnet instead of the full raw dict.

    Raw signals are kept intact in the state so downstream scoring nodes
    (extract_fields, score_brand) still see complete data.
    """
    name = "summarized"
    CHAR_LIMIT = 8_000  # max chars of raw signals fed to the summarizer

    def compress_signals(
        self,
        signals: dict,
        brand_name: str,
        client: anthropic.Anthropic,
    ) -> tuple[dict, dict]:
        """
        Runs a Haiku summarization call and returns:
          (compressed_signals_dict, compression_metrics)

        compressed_signals_dict is stored under "compressed_summary" so the
        reflection prompt renders it clearly as a summary, not raw data.
        """
        raw_json = json.dumps(signals)
        truncated = raw_json[: self.CHAR_LIMIT]

        prompt = SUMMARY_PROMPT.format(
            brand_name=brand_name,
            char_limit=self.CHAR_LIMIT,
            signals_json=truncated,
        )

        t0 = time.perf_counter()
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        latency_ms = (time.perf_counter() - t0) * 1000

        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").lstrip()
        try:
            summary = json.loads(raw)
        except json.JSONDecodeError:
            summary = {"raw_summary": raw}

        compressed = {
            "compressed_summary": summary,
            "_strategy": "summarized",
            "_original_char_len": len(raw_json),
        }

        metrics = {
            "compression_tokens_in": msg.usage.input_tokens,
            "compression_tokens_out": msg.usage.output_tokens,
            "compression_latency_ms": round(latency_ms, 1),
            "signals_char_len": len(raw_json),
            "estimated_tokens_passed": len(json.dumps(compressed)) // 4,
        }
        return compressed, metrics
