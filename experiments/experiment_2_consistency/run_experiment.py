"""
Experiment 2: Score Consistency
================================
Run the same 5 brands through 3 independent agents and measure how much
scores vary across runs. Tests whether the pipeline produces stable,
repeatable evaluations or shows significant non-determinism.

Design
------
  3 identical agents (same strategy: full_history, same prompts)
  5 test brands per agent = 15 total agent-runs

  Each agent evaluates all 5 brands sequentially.
  All 3 agents run in parallel (simultaneous cloud instances).

Hypothesis
----------
  The deterministic scoring formula should keep variance low (< 5 pts).
  LLM-driven steps (reflection, field extraction) may introduce ±5–10 pt
  noise due to non-deterministic web scraping results and LLM sampling.

What is logged
--------------
  Per brand across 3 agents:
    - scores (list of 3 totals)
    - score_mean, score_std, score_range (max - min)
    - verdicts (list of 3)
    - verdict_agreement (all 3 agree?)
    - per-criterion variance

Usage
-----
  python experiments/experiment_2_consistency/run_experiment.py
  python experiments/experiment_2_consistency/run_experiment.py --dry-run
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev

_HERE = Path(__file__).parent
_REPO_ROOT = _HERE.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from experiments.experiment_1_memory.memory_strategies import FullHistoryMemory
from experiments.experiment_1_memory.instrumented_runner import run_pipeline

RESULTS_DIR = _HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)

TEST_BRANDS = [
    {"brand_name": "Chomps",       "website_url": "https://chomps.com"},
    {"brand_name": "Fishwife",     "website_url": "https://eatfishwife.com"},
    {"brand_name": "Olipop",       "website_url": "https://drinkolipop.com"},
    {"brand_name": "Magic Spoon",  "website_url": "https://magicspoon.com"},
    {"brand_name": "Graza",        "website_url": "https://graza.co"},
]

# 3 agents, each runs all 5 brands
AGENT_IDS = ["C1", "C2", "C3"]


def run_agent(agent_id: str) -> list[dict]:
    """One agent evaluates all 5 brands sequentially. Returns list of result dicts."""
    strategy = FullHistoryMemory()
    results = []
    for brand in TEST_BRANDS:
        result = run_pipeline(brand=brand, memory_strategy=strategy, agent_id=f"{agent_id}:{brand['brand_name']}")
        results.append(result)
    return results


def _analyze(all_results: list[dict]) -> dict:
    brand_stats = {}
    for brand in TEST_BRANDS:
        name = brand["brand_name"]
        runs = [r for r in all_results if r["brand_name"] == name]
        scores = [r["score"] for r in runs if r["score"] is not None]
        verdicts = [r["verdict"] for r in runs]
        breakdowns = [r.get("score_breakdown", {}) for r in runs]
        criteria = ["velocity_proof", "distribution_density", "margin_viability",
                    "brand_story_clarity", "promotional_independence"]
        criterion_variance = {}
        for c in criteria:
            vals = [b.get(c) for b in breakdowns if b.get(c) is not None]
            criterion_variance[c] = {
                "values": vals,
                "range": (max(vals) - min(vals)) if len(vals) > 1 else 0,
            }
        brand_stats[name] = {
            "scores":            scores,
            "score_mean":        round(mean(scores), 1) if scores else None,
            "score_std":         round(stdev(scores), 2) if len(scores) > 1 else 0.0,
            "score_range":       (max(scores) - min(scores)) if len(scores) > 1 else 0,
            "verdicts":          verdicts,
            "verdict_agreement": len(set(verdicts)) == 1,
            "criterion_variance": criterion_variance,
        }
    return brand_stats


def _print_report(brand_stats: dict):
    sep = "=" * 70
    print(f"\n{sep}")
    print("  EXPERIMENT 2 RESULTS: Score Consistency (3 agents × 5 brands)")
    print(sep)
    all_ranges = []
    for name, s in brand_stats.items():
        agree = "AGREE" if s["verdict_agreement"] else "DISAGREE"
        print(f"\n  {name}")
        print(f"    Scores   : {s['scores']}  mean={s['score_mean']}  std={s['score_std']}  range={s['score_range']}")
        print(f"    Verdicts : {s['verdicts']}  → {agree}")
        max_c = max(s["criterion_variance"].items(), key=lambda x: x[1]["range"])
        print(f"    Noisiest criterion: {max_c[0]} (range={max_c[1]['range']} pts, values={max_c[1]['values']})")
        if s["score_range"] is not None:
            all_ranges.append(s["score_range"])
    if all_ranges:
        print(f"\n  Avg score range across brands : {round(mean(all_ranges), 1)} pts")
        print(f"  Max score range across brands : {max(all_ranges)} pts")
    print(f"\n{sep}\n")


def main():
    parser = argparse.ArgumentParser(description="Experiment 2: Score Consistency")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        print("\nExperiment 2 — Score Consistency Plan")
        print(f"  {len(AGENT_IDS)} agents × {len(TEST_BRANDS)} brands = {len(AGENT_IDS)*len(TEST_BRANDS)} total runs")
        for b in TEST_BRANDS:
            print(f"  Brand: {b['brand_name']}")
        print("\nHypothesis: Score variance < 5 pts per brand across agents.\n")
        return

    print(f"\nStarting Experiment 2 — {len(AGENT_IDS)} agents in parallel, {len(TEST_BRANDS)} brands each")

    all_results: list[dict] = []
    exp_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=len(AGENT_IDS)) as pool:
        futures = {pool.submit(run_agent, aid): aid for aid in AGENT_IDS}
        for future in as_completed(futures):
            try:
                all_results.extend(future.result())
            except Exception as exc:
                print(f"Agent error: {exc}")

    wall_ms = round((time.perf_counter() - exp_start) * 1000, 1)
    brand_stats = _analyze(all_results)

    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "experiment": "experiment_2_consistency",
        "hypothesis": "Score variance < 5 pts per brand across identical agents.",
        "run_timestamp": run_ts,
        "total_wall_time_ms": wall_ms,
        "raw_results": all_results,
        "brand_stats": brand_stats,
    }
    path = RESULTS_DIR / f"run_{run_ts}.json"
    path.write_text(json.dumps(payload, indent=2))
    (RESULTS_DIR / "summary.json").write_text(json.dumps(payload, indent=2))
    print(f"\nResults saved → {path}")
    _print_report(brand_stats)


if __name__ == "__main__":
    main()
