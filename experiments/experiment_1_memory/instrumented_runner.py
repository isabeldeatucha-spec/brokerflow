"""
Instrumented pipeline runner for Experiment 1.

Runs the full Brand Scout evaluation pipeline (research → reflect → score)
with one of two memory strategies injected into the reflect_and_decide step.
All metrics (tokens, latency, verdict) are captured and returned.

Usage:
    from experiments.experiment_1_memory.instrumented_runner import run_pipeline
    from experiments.experiment_1_memory.memory_strategies import FullHistoryMemory

    result = run_pipeline(
        brand={"brand_name": "Chomps", "website_url": "https://chomps.com"},
        memory_strategy=FullHistoryMemory(),
        agent_id="A1",
    )
"""
import json
import os
import sys
import time

# Make the project root importable regardless of cwd
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import anthropic

from agents.brand_scout.graph import (
    research_brand,
    detect_category_node,
    extract_fields,
    score_brand,
    _compact_signals,
)
from agents.brand_scout.prompts import REFLECTION_PROMPT


# ── Instrumented reflect_and_decide ──────────────────────────────────────────

def _reflect_and_decide_instrumented(
    state: dict,
    memory_strategy,
    client: anthropic.Anthropic,
    metrics: dict,
    reflection_prompt_template: str = None,
) -> dict:
    """
    Drop-in replacement for graph.reflect_and_decide that:
    1. Applies the memory strategy (compress or pass through raw signals).
    2. Records token usage and wall-clock latency for every Claude call.
    3. Preserves the original raw signals_found in state (scoring nodes need them).
    """
    reflection_count = state.get("reflection_count", 0)

    # Hard limit: stop after 2 rounds regardless of strategy
    if reflection_count >= 2:
        notes = state.get("reflection_notes", [])
        return {
            "reflection_notes": notes + [
                "Reflection limit reached (2/2) — proceeding to score with available data."
            ],
            "follow_up_queries": [],
        }

    # ── Step 1: apply memory strategy ────────────────────────────────────────
    compress_start = time.perf_counter()
    signals_for_reflection, compress_metrics = memory_strategy.compress_signals(
        signals=state["signals_found"],
        brand_name=state["brand_name"],
        client=client,
    )

    # Accumulate compression overhead
    metrics["compression_tokens_in"]  += compress_metrics["compression_tokens_in"]
    metrics["compression_tokens_out"] += compress_metrics["compression_tokens_out"]
    metrics["compression_latency_ms"] += compress_metrics["compression_latency_ms"]
    metrics["compression_calls"]      += 1 if compress_metrics["compression_tokens_in"] > 0 else 0

    # ── Step 2: build reflection prompt with (possibly compressed) signals ───
    template = reflection_prompt_template if reflection_prompt_template else REFLECTION_PROMPT
    prompt = template.format(
        brand_name=state["brand_name"],
        website_url=state["website_url"],
        reflection_count=reflection_count + 1,
        signals_json=json.dumps(
            _compact_signals(signals_for_reflection), indent=2
        ),
    )

    # ── Step 3: call Claude Sonnet ───────────────────────────────────────────
    llm_start = time.perf_counter()
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    llm_latency_ms = (time.perf_counter() - llm_start) * 1000

    # Accumulate reflection metrics
    metrics["reflect_input_tokens"]  += message.usage.input_tokens
    metrics["reflect_output_tokens"] += message.usage.output_tokens
    metrics["reflect_calls"]         += 1
    metrics["reflect_latency_ms"]    += round(llm_latency_ms, 1)

    # ── Step 4: parse JSON response ──────────────────────────────────────────
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw)

    # Build reflection note
    note = data.get("reasoning", "")
    contradictions = data.get("contradictions_found", [])
    gaps = data.get("critical_gaps", [])
    if contradictions:
        note += f" | Contradictions: {'; '.join(contradictions)}"
    if gaps:
        note += f" | Critical gaps: {'; '.join(gaps)}"

    follow_up = (
        data.get("follow_up_queries", [])
        if data.get("should_dig_deeper")
        else []
    )

    return {
        "reflection_count": reflection_count + 1,
        "reflection_notes": state.get("reflection_notes", []) + [note],
        "follow_up_queries": follow_up,
    }


# ── Full pipeline runner ──────────────────────────────────────────────────────

def run_pipeline(
    brand: dict,
    memory_strategy,
    agent_id: str,
    reflection_prompt_template: str = None,
) -> dict:
    """
    Run the complete Brand Scout evaluation pipeline for one brand using
    the given memory strategy. Returns a metrics dict with all measurements.

    Optional reflection_prompt_template overrides the default REFLECTION_PROMPT.
    Use this for Experiment 4 (prompt variant testing).

    Parameters
    ----------
    brand : dict
        Must have "brand_name" and "website_url".
    memory_strategy : FullHistoryMemory | SummarizedMemory
        Strategy object from memory_strategies.py.
    agent_id : str
        Human-readable label, e.g. "A1", "B2".

    Returns
    -------
    dict
        Metrics including tokens, latency, verdict, score, and broker brief.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    metrics = {
        # Identity
        "agent_id":              agent_id,
        "strategy":              memory_strategy.name,
        "brand_name":            brand["brand_name"],

        # Reflection Claude calls
        "reflect_input_tokens":  0,
        "reflect_output_tokens": 0,
        "reflect_calls":         0,
        "reflect_latency_ms":    0,

        # Summarization overhead (Group B only; zero for Group A)
        "compression_tokens_in":  0,
        "compression_tokens_out": 0,
        "compression_calls":      0,
        "compression_latency_ms": 0,

        # Derived totals (filled in at the end)
        "total_reflect_tokens":  0,
        "total_extra_tokens":    0,   # compression overhead for Group B
        "total_latency_ms":      0,
        "reflection_rounds":     0,

        # Outcome
        "verdict":       None,
        "score":         None,
        "score_breakdown": {},
        "broker_brief":  "",
        "key_gaps":      [],
        "error":         None,
    }

    pipeline_start = time.perf_counter()

    try:
        # ── Initial state ──────────────────────────────────────────────────────
        state: dict = {
            "brand_name":       brand["brand_name"],
            "website_url":      brand["website_url"],
            "signals_found":    {},
            "sources_checked":  [],
            "follow_up_queries": [],
            "reflection_count": 0,
            "reflection_notes": [],
            "category":         "",
            "benchmark":        {},
            "extracted_fields": {},
            "score":            None,
            "verdict":          None,
            "founder_name":     "",
            "founder_email":    "",
            "email_draft":      "",
            "approved":         None,
            "rejection_reason": None,
        }

        print(f"[{agent_id}][{memory_strategy.name}] Starting research on '{brand['brand_name']}'")

        # ── Step 1: Initial research ───────────────────────────────────────────
        state.update(research_brand(state))
        print(f"[{agent_id}] Research complete. Signals keys: {list(state['signals_found'].keys())}")

        # ── Step 2: Reflect loop (max 2 rounds) ───────────────────────────────
        while True:
            reflect_result = _reflect_and_decide_instrumented(
                state, memory_strategy, client, metrics,
                reflection_prompt_template=reflection_prompt_template,
            )
            state.update(reflect_result)
            metrics["reflection_rounds"] = state["reflection_count"]

            follow_up = state.get("follow_up_queries", [])
            should_loop = bool(follow_up) and state["reflection_count"] < 2

            if not should_loop:
                break

            print(f"[{agent_id}] Round {state['reflection_count']}: digging deeper on {len(follow_up)} queries")
            state.update(research_brand(state))

        # ── Step 3: Category detection ────────────────────────────────────────
        state.update(detect_category_node(state))
        print(f"[{agent_id}] Category: {state['category']}")

        # ── Step 4: Field extraction ──────────────────────────────────────────
        state.update(extract_fields(state))

        # ── Step 5: Score ─────────────────────────────────────────────────────
        state.update(score_brand(state))

        # ── Collect outcome metrics ───────────────────────────────────────────
        score_detail = state.get("signals_found", {}).get("score_detail", {})
        metrics["verdict"]         = score_detail.get("verdict")
        metrics["score"]           = state.get("score", {}).get("total")
        metrics["score_breakdown"] = {
            k: state["score"].get(k)
            for k in ("velocity_proof", "distribution_density", "margin_viability",
                      "brand_story_clarity", "promotional_independence")
        }
        metrics["broker_brief"] = score_detail.get("broker_brief", "")
        metrics["key_gaps"]     = score_detail.get("key_gaps", [])

    except Exception as exc:
        metrics["error"] = str(exc)
        print(f"[{agent_id}] ERROR: {exc}")

    finally:
        metrics["total_latency_ms"] = round(
            (time.perf_counter() - pipeline_start) * 1000, 1
        )
        metrics["total_reflect_tokens"] = (
            metrics["reflect_input_tokens"] + metrics["reflect_output_tokens"]
        )
        metrics["total_extra_tokens"] = (
            metrics["compression_tokens_in"] + metrics["compression_tokens_out"]
        )

    print(
        f"[{agent_id}] Done. verdict={metrics['verdict']}, score={metrics['score']}, "
        f"reflect_tokens={metrics['total_reflect_tokens']}, "
        f"latency={metrics['total_latency_ms']:.0f}ms"
    )
    return metrics
