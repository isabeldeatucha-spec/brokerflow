"""
Experiment 4: Prompt Variants — Baseline vs Skeptic vs Optimistic
==================================================================
Test whether the evaluative stance baked into the reflection prompt changes
the final score and verdict. Three agents each use a different prompt variant.

Design
------
  3 prompt variants × 2 brands = 6 agent-runs, all in parallel.

  Agent P_baseline_1  — Baseline prompt,   Chomps
  Agent P_baseline_2  — Baseline prompt,   Fishwife
  Agent P_skeptic_1   — Skeptic prompt,    Chomps
  Agent P_skeptic_2   — Skeptic prompt,    Fishwife
  Agent P_optimist_1  — Optimistic prompt, Chomps
  Agent P_optimist_2  — Optimistic prompt, Fishwife

Prompt variants (see prompt_variants.py):
  Baseline  — current production prompt (neutral, balanced)
  Skeptic   — raises the bar for "sufficient" signals; defaults to dig deeper;
              treats missing data as a red flag
  Optimistic — charitable interpretation; stops digging early; missing data
               is neutral, not negative

Hypothesis
----------
  - Skeptic agents will request more follow-up queries (higher reflection rounds)
    and may produce lower scores by surfacing more gaps.
  - Optimistic agents will stop digging earlier and may score the same brand
    higher by skipping gap-detection.
  - Baseline will land between the two extremes.
  - All three should agree on verdict (the scoring formula is deterministic);
    any verdict divergence reveals prompt-induced scoring noise.

What is logged
--------------
  Per brand:
    - score per variant
    - verdict per variant
    - reflection_rounds per variant
    - follow_up_queries count per variant (how aggressively it dug)
    - reflection notes (qualitative difference in reasoning)

Usage
-----
  python experiments/experiment_4_prompts/run_experiment.py
  python experiments/experiment_4_prompts/run_experiment.py --dry-run
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).parent
_REPO_ROOT = _HERE.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from experiments.experiment_1_memory.memory_strategies import FullHistoryMemory
from experiments.experiment_1_memory.instrumented_runner import run_pipeline
from experiments.experiment_4_prompts.prompt_variants import VARIANTS

RESULTS_DIR = _HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)

TEST_BRANDS = [
    {"brand_name": "Chomps",   "website_url": "https://chomps.com"},
    {"brand_name": "Fishwife", "website_url": "https://eatfishwife.com"},
]

AGENT_DEFINITIONS = [
    {"agent_id": "P_baseline_1",  "variant": "baseline",   "brand_idx": 0},
    {"agent_id": "P_baseline_2",  "variant": "baseline",   "brand_idx": 1},
    {"agent_id": "P_skeptic_1",   "variant": "skeptic",    "brand_idx": 0},
    {"agent_id": "P_skeptic_2",   "variant": "skeptic",    "brand_idx": 1},
    {"agent_id": "P_optimist_1",  "variant": "optimistic", "brand_idx": 0},
    {"agent_id": "P_optimist_2",  "variant": "optimistic", "brand_idx": 1},
]


def _analyze(all_results: list[dict]) -> list[dict]:
    comparisons = []
    for brand in TEST_BRANDS:
        name = brand["brand_name"]
        runs = {r["prompt_variant"]: r for r in all_results if r["brand_name"] == name}
        entry = {"brand": name}
        for variant in ("baseline", "skeptic", "optimistic"):
            r = runs.get(variant, {})
            entry[f"score_{variant}"]           = r.get("score")
            entry[f"verdict_{variant}"]         = r.get("verdict")
            entry[f"reflect_rounds_{variant}"]  = r.get("reflection_rounds")
            entry[f"reflect_tokens_{variant}"]  = r.get("total_reflect_tokens")

        scores = [entry[f"score_{v}"] for v in ("baseline", "skeptic", "optimistic") if entry[f"score_{v}"] is not None]
        verdicts = [entry[f"verdict_{v}"] for v in ("baseline", "skeptic", "optimistic")]
        entry["score_range"]       = (max(scores) - min(scores)) if len(scores) > 1 else 0
        entry["verdict_agreement"] = len(set(v for v in verdicts if v)) == 1
        comparisons.append(entry)
    return comparisons


def _print_report(comparisons: list[dict]):
    sep = "=" * 70
    print(f"\n{sep}")
    print("  EXPERIMENT 4 RESULTS: Prompt Variants (Baseline / Skeptic / Optimistic)")
    print(sep)
    for c in comparisons:
        agree = "AGREE" if c["verdict_agreement"] else "DISAGREE"
        print(f"\n  {c['brand']}  (verdict agreement: {agree})")
        for v in ("baseline", "skeptic", "optimistic"):
            print(
                f"    {v:<12} score={c[f'score_{v}']:>3}  verdict={c[f'verdict_{v}']:<14} "
                f"rounds={c[f'reflect_rounds_{v}']}  tokens={c[f'reflect_tokens_{v}']:,}"
            )
        print(f"    Score range across variants: {c['score_range']} pts")
    print(f"\n{sep}\n")


def main():
    parser = argparse.ArgumentParser(description="Experiment 4: Prompt Variants")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        print("\nExperiment 4 — Prompt Variants Plan")
        for d in AGENT_DEFINITIONS:
            b = TEST_BRANDS[d["brand_idx"]]
            print(f"  Agent {d['agent_id']:<18} variant={d['variant']:<12} brand={b['brand_name']}")
        print("\nHypothesis: Skeptic scores lower; Optimistic scores higher; all same verdict.\n")
        return

    print(f"\nStarting Experiment 4 — {len(AGENT_DEFINITIONS)} agents in parallel")

    all_results: list[dict] = []
    exp_start = time.perf_counter()
    strategy = FullHistoryMemory()

    with ThreadPoolExecutor(max_workers=len(AGENT_DEFINITIONS)) as pool:
        futures = {}
        for defn in AGENT_DEFINITIONS:
            brand = TEST_BRANDS[defn["brand_idx"]]
            prompt = VARIANTS[defn["variant"]]
            futures[pool.submit(
                run_pipeline, brand, strategy, defn["agent_id"],
                reflection_prompt_template=prompt,
            )] = defn

        for future in as_completed(futures):
            defn = futures[future]
            try:
                result = future.result()
                result["prompt_variant"] = defn["variant"]
                all_results.append(result)
            except Exception as exc:
                print(f"Agent {defn['agent_id']} error: {exc}")

    wall_ms = round((time.perf_counter() - exp_start) * 1000, 1)
    comparisons = _analyze(all_results)

    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "experiment": "experiment_4_prompts",
        "hypothesis": "Skeptic scores lower; Optimistic scores higher; all agree on verdict.",
        "run_timestamp": run_ts,
        "total_wall_time_ms": wall_ms,
        "raw_results": all_results,
        "comparisons": comparisons,
    }
    path = RESULTS_DIR / f"run_{run_ts}.json"
    path.write_text(json.dumps(payload, indent=2))
    (RESULTS_DIR / "summary.json").write_text(json.dumps(payload, indent=2))
    print(f"\nResults saved → {path}")
    _print_report(comparisons)


if __name__ == "__main__":
    main()
