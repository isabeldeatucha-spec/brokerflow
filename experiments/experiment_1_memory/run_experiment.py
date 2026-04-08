"""
Experiment 1: Memory Strategy A vs B — Full History vs Summarized Memory
=========================================================================

Design
------
  Group A (FullHistoryMemory) — 2 agents
    Each reflection round receives the complete raw signals dict verbatim.
    This mirrors the current production behavior.

  Group B (SummarizedMemory) — 2 agents
    Before each reflection round, Claude Haiku compresses the signals into a
    structured JSON summary. Sonnet then reflects on the summary, not the raw data.

Hypothesis
----------
  Group B will use fewer reflection tokens and have lower latency because Sonnet
  receives a much shorter prompt. However, it may lose precision on multi-step
  tasks where specific signal details matter for gap identification.

What is logged
--------------
  Per agent:
    - reflect_input_tokens / reflect_output_tokens: tokens Sonnet consumed
    - compression_tokens_in / out: Haiku overhead for Group B
    - reflect_latency_ms: wall-clock time inside reflect_and_decide
    - total_latency_ms: full pipeline end-to-end
    - reflection_rounds: how many ReAct loops occurred
    - verdict: established / broker_ready / too_early
    - score: 0–100 total
    - score_breakdown: per-criterion scores

  Aggregate comparison:
    - avg tokens (reflect) per group
    - avg compression overhead per group B agent
    - avg latency per group
    - verdict agreement (did strategies agree on the same brand?)
    - score delta between groups

Usage
-----
  # Run all 4 agents (2 per group) in parallel:
  python experiments/experiment_1_memory/run_experiment.py

  # Dry-run (prints plan, no API calls):
  python experiments/experiment_1_memory/run_experiment.py --dry-run

  # Run a single agent:
  python experiments/experiment_1_memory/run_experiment.py --agent A1

Deployment note
---------------
  Each agent is designed to run as an independent process/container.
  To scale to cloud (Railway / Fly.io), export run_single_agent() as the
  entrypoint and pass AGENT_ID + STRATEGY + BRAND env vars:

    AGENT_ID=A1 STRATEGY=full_history BRAND_NAME=Chomps \\
      WEBSITE_URL=https://chomps.com python run_experiment.py --cloud-worker
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path
_HERE = Path(__file__).parent
_REPO_ROOT = _HERE.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from experiments.experiment_1_memory.memory_strategies import (
    FullHistoryMemory,
    SummarizedMemory,
)
from experiments.experiment_1_memory.instrumented_runner import run_pipeline
from experiments.experiment_1_memory.test_brands import TEST_BRANDS

RESULTS_DIR = _HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# ── Agent definitions ─────────────────────────────────────────────────────────
#
#  4 agents total:
#    A1 — full_history,  brand 0 (Chomps)
#    A2 — full_history,  brand 1 (Fishwife)
#    B1 — summarized,    brand 0 (Chomps)
#    B2 — summarized,    brand 1 (Fishwife)

AGENT_DEFINITIONS = [
    {"agent_id": "A1", "strategy": "full_history",  "brand_idx": 0},
    {"agent_id": "A2", "strategy": "full_history",  "brand_idx": 1},
    {"agent_id": "B1", "strategy": "summarized",    "brand_idx": 0},
    {"agent_id": "B2", "strategy": "summarized",    "brand_idx": 1},
]


def _make_strategy(name: str):
    if name == "full_history":
        return FullHistoryMemory()
    if name == "summarized":
        return SummarizedMemory()
    raise ValueError(f"Unknown strategy: {name}")


# ── Single-agent entrypoint (used by cloud workers too) ───────────────────────

def run_single_agent(agent_id: str, strategy_name: str, brand: dict) -> dict:
    """Run one agent and return its metrics dict."""
    strategy = _make_strategy(strategy_name)
    return run_pipeline(brand=brand, memory_strategy=strategy, agent_id=agent_id)


# ── Aggregate analysis ────────────────────────────────────────────────────────

def _group_results(all_results: list[dict]) -> dict:
    """Split results by group and compute per-group averages."""
    groups: dict[str, list[dict]] = {"full_history": [], "summarized": []}
    for r in all_results:
        groups[r["strategy"]].append(r)

    summary = {}
    for strategy, results in groups.items():
        if not results:
            continue
        n = len(results)
        summary[strategy] = {
            "agent_count": n,
            "avg_reflect_tokens": round(
                sum(r["total_reflect_tokens"] for r in results) / n
            ),
            "avg_compression_tokens": round(
                sum(r["total_extra_tokens"] for r in results) / n
            ),
            "avg_reflect_latency_ms": round(
                sum(r["reflect_latency_ms"] for r in results) / n
            ),
            "avg_total_latency_ms": round(
                sum(r["total_latency_ms"] for r in results) / n
            ),
            "avg_reflection_rounds": round(
                sum(r["reflection_rounds"] for r in results) / n, 2
            ),
            "verdicts": [r["verdict"] for r in results],
            "scores": [r["score"] for r in results],
            "avg_score": round(
                sum((r["score"] or 0) for r in results) / n, 1
            ),
            "errors": [r["error"] for r in results if r.get("error")],
        }

    # Cross-group comparisons (if both groups ran the same brands)
    comparisons = []
    for brand in TEST_BRANDS:
        brand_name = brand["brand_name"]
        a = next((r for r in all_results if r["brand_name"] == brand_name and r["strategy"] == "full_history"), None)
        b = next((r for r in all_results if r["brand_name"] == brand_name and r["strategy"] == "summarized"), None)
        if a and b:
            comparisons.append({
                "brand":             brand_name,
                "expected_verdict":  brand.get("expected_verdict"),
                "verdict_A":         a["verdict"],
                "verdict_B":         b["verdict"],
                "verdicts_agree":    a["verdict"] == b["verdict"],
                "score_A":           a["score"],
                "score_B":           b["score"],
                "score_delta":       (b["score"] or 0) - (a["score"] or 0),
                "reflect_tokens_A":  a["total_reflect_tokens"],
                "reflect_tokens_B":  b["total_reflect_tokens"],
                "token_savings_B":   a["total_reflect_tokens"] - b["total_reflect_tokens"],
                "latency_ms_A":      a["total_latency_ms"],
                "latency_ms_B":      b["total_latency_ms"],
                "latency_savings_ms_B": a["total_latency_ms"] - b["total_latency_ms"],
            })

    return {"by_group": summary, "brand_comparisons": comparisons}


def _print_report(analysis: dict):
    """Print a human-readable experiment report to stdout."""
    sep = "=" * 70
    print(f"\n{sep}")
    print("  EXPERIMENT 1 RESULTS: Memory Strategy A vs B")
    print(sep)

    for strategy, stats in analysis["by_group"].items():
        label = "Group A — Full History" if strategy == "full_history" else "Group B — Summarized"
        print(f"\n{label}  ({stats['agent_count']} agents)")
        print(f"  Avg reflect tokens  : {stats['avg_reflect_tokens']:,}")
        print(f"  Avg compression tok : {stats['avg_compression_tokens']:,}  (Haiku overhead)")
        print(f"  Avg reflect latency : {stats['avg_reflect_latency_ms']:,} ms")
        print(f"  Avg total latency   : {stats['avg_total_latency_ms']:,} ms")
        print(f"  Avg reflection rnds : {stats['avg_reflection_rounds']}")
        print(f"  Avg score           : {stats['avg_score']}")
        print(f"  Verdicts            : {stats['verdicts']}")
        if stats["errors"]:
            print(f"  Errors              : {stats['errors']}")

    print(f"\n{'─' * 70}")
    print("  Per-Brand Comparison")
    print(f"{'─' * 70}")
    for c in analysis["brand_comparisons"]:
        agree_str = "AGREE" if c["verdicts_agree"] else "DISAGREE"
        print(f"\n  {c['brand']}  (expected: {c['expected_verdict']})")
        print(f"    Verdict A={c['verdict_A']}, B={c['verdict_B']}  → {agree_str}")
        print(f"    Score   A={c['score_A']},   B={c['score_B']}   (delta={c['score_delta']:+})")
        print(f"    Reflect tokens  A={c['reflect_tokens_A']:,}, B={c['reflect_tokens_B']:,}  (B saves {c['token_savings_B']:,})")
        print(f"    Total latency   A={c['latency_ms_A']:,.0f}ms, B={c['latency_ms_B']:,.0f}ms  (B saves {c['latency_savings_ms_B']:,.0f}ms)")

    print(f"\n{sep}\n")


# ── Cloud-worker mode ─────────────────────────────────────────────────────────

def cloud_worker_main():
    """
    Entrypoint when a single agent is deployed as a cloud container.
    Reads config from env vars, runs the agent, and writes results to stdout as JSON.

    Env vars:
        AGENT_ID        e.g. "B2"
        STRATEGY        "full_history" | "summarized"
        BRAND_NAME      e.g. "Chomps"
        WEBSITE_URL     e.g. "https://chomps.com"
        ANTHROPIC_API_KEY  (required by the pipeline)
    """
    agent_id   = os.environ["AGENT_ID"]
    strategy   = os.environ["STRATEGY"]
    brand_name = os.environ["BRAND_NAME"]
    website    = os.environ["WEBSITE_URL"]

    result = run_single_agent(
        agent_id=agent_id,
        strategy_name=strategy,
        brand={"brand_name": brand_name, "website_url": website},
    )
    print(json.dumps(result, indent=2))


# ── Main orchestrator ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Experiment 1: Memory Strategy A vs B")
    parser.add_argument("--dry-run",      action="store_true", help="Print plan only — no API calls")
    parser.add_argument("--agent",        type=str,            help="Run a single agent by ID (A1, A2, B1, B2)")
    parser.add_argument("--cloud-worker", action="store_true", help="Cloud-worker mode (reads config from env)")
    args = parser.parse_args()

    # Cloud-worker mode: single agent, reads from env
    if args.cloud_worker:
        cloud_worker_main()
        return

    # Dry-run: show the plan
    if args.dry_run:
        print("\nExperiment 1 — Agent Plan")
        print("-" * 50)
        for defn in AGENT_DEFINITIONS:
            brand = TEST_BRANDS[defn["brand_idx"]]
            print(
                f"  Agent {defn['agent_id']}  strategy={defn['strategy']:<14}  brand={brand['brand_name']}"
            )
        print("\nHypothesis: Group B will use fewer reflect tokens and be faster,")
        print("but may miss details that Group A catches verbatim.\n")
        return

    # Filter to a single agent if requested
    agents_to_run = AGENT_DEFINITIONS
    if args.agent:
        agents_to_run = [d for d in AGENT_DEFINITIONS if d["agent_id"] == args.agent]
        if not agents_to_run:
            print(f"Unknown agent ID: {args.agent}. Valid: {[d['agent_id'] for d in AGENT_DEFINITIONS]}")
            sys.exit(1)

    print(f"\nStarting Experiment 1 — {len(agents_to_run)} agent(s) running in parallel")
    print(f"Brands: {[TEST_BRANDS[d['brand_idx']]['brand_name'] for d in agents_to_run]}")
    print(f"Strategies: {[d['strategy'] for d in agents_to_run]}\n")

    # ── Run agents in parallel ─────────────────────────────────────────────────
    all_results: list[dict] = []
    experiment_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=len(agents_to_run)) as pool:
        futures = {
            pool.submit(
                run_single_agent,
                defn["agent_id"],
                defn["strategy"],
                TEST_BRANDS[defn["brand_idx"]],
            ): defn
            for defn in agents_to_run
        }
        for future in as_completed(futures):
            defn = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {
                    "agent_id": defn["agent_id"],
                    "strategy": defn["strategy"],
                    "brand_name": TEST_BRANDS[defn["brand_idx"]]["brand_name"],
                    "error": str(exc),
                    "total_reflect_tokens": 0,
                    "total_extra_tokens": 0,
                    "reflect_latency_ms": 0,
                    "total_latency_ms": 0,
                    "reflection_rounds": 0,
                    "verdict": None,
                    "score": None,
                    "score_breakdown": {},
                    "broker_brief": "",
                    "key_gaps": [],
                }
            all_results.append(result)

    total_wall_ms = (time.perf_counter() - experiment_start) * 1000

    # ── Save raw results ───────────────────────────────────────────────────────
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_path = RESULTS_DIR / f"run_{run_ts}.json"
    payload = {
        "experiment":        "experiment_1_memory",
        "hypothesis":        "Summarized memory (Group B) will be faster and cheaper but may lose precision.",
        "run_timestamp":     run_ts,
        "total_wall_time_ms": round(total_wall_ms, 1),
        "agents":            all_results,
    }
    raw_path.write_text(json.dumps(payload, indent=2))
    print(f"\nRaw results saved → {raw_path}")

    # ── Analysis and report ────────────────────────────────────────────────────
    analysis = _group_results(all_results)
    payload["analysis"] = analysis

    summary_path = RESULTS_DIR / "summary.json"
    summary_path.write_text(json.dumps(payload, indent=2))
    print(f"Summary saved     → {summary_path}")

    _print_report(analysis)


if __name__ == "__main__":
    main()
