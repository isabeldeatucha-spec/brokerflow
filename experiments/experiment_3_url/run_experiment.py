"""
Experiment 3: URL vs No URL
============================
Test whether providing a website URL materially changes the score, verdict,
and signal quality vs. running with brand name only (no URL).

Design
------
  2 brands × 2 conditions = 4 agent-runs, all in parallel.

  Agent U1 — Chomps   + URL  (https://chomps.com)
  Agent U2 — Fishwife + URL  (https://eatfishwife.com)
  Agent N1 — Chomps,    no URL  (empty string)
  Agent N2 — Fishwife,  no URL  (empty string)

  Without a URL, the pipeline skips:
    - scrape_brand_website   (homepage, retail page, about)
    - scrape_retail_partners (where-to-buy page)
    - scrape_brand_certifications (certifications + SRP page)
  All three return empty results, so the agent relies entirely on
  search-based signals (Amazon, Faire, press, funding, velocity).

Hypothesis
----------
  Agents without a URL will score lower (fewer confirmed fields) and may
  produce more follow-up queries in reflection. Score delta expected: 5–15 pts.
  Verdict may remain the same if search signals are strong enough.

What is logged
--------------
  Per brand:
    - score with URL vs. without URL
    - score delta
    - verdict agreement
    - which signal sources returned data (non-empty keys)
    - reflection follow-up query count (proxy for data quality)

Usage
-----
  python experiments/experiment_3_url/run_experiment.py
  python experiments/experiment_3_url/run_experiment.py --dry-run
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

RESULTS_DIR = _HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)

TEST_BRANDS = [
    {"brand_name": "Chomps",   "website_url": "https://chomps.com"},
    {"brand_name": "Fishwife", "website_url": "https://eatfishwife.com"},
]

AGENT_DEFINITIONS = [
    {"agent_id": "U1", "brand_idx": 0, "use_url": True},
    {"agent_id": "U2", "brand_idx": 1, "use_url": True},
    {"agent_id": "N1", "brand_idx": 0, "use_url": False},
    {"agent_id": "N2", "brand_idx": 1, "use_url": False},
]


def _analyze(all_results: list[dict]) -> list[dict]:
    comparisons = []
    for brand in TEST_BRANDS:
        name = brand["brand_name"]
        with_url    = next((r for r in all_results if r["brand_name"] == name and r.get("used_url")), None)
        without_url = next((r for r in all_results if r["brand_name"] == name and not r.get("used_url")), None)
        if with_url and without_url:
            comparisons.append({
                "brand":           name,
                "score_with_url":  with_url["score"],
                "score_no_url":    without_url["score"],
                "score_delta":     (with_url["score"] or 0) - (without_url["score"] or 0),
                "verdict_with_url": with_url["verdict"],
                "verdict_no_url":   without_url["verdict"],
                "verdicts_agree":   with_url["verdict"] == without_url["verdict"],
                "reflect_rounds_with_url":  with_url["reflection_rounds"],
                "reflect_rounds_no_url":    without_url["reflection_rounds"],
                "tokens_with_url":   with_url["total_reflect_tokens"],
                "tokens_no_url":     without_url["total_reflect_tokens"],
                "latency_with_url":  with_url["total_latency_ms"],
                "latency_no_url":    without_url["total_latency_ms"],
            })
    return comparisons


def _print_report(comparisons: list[dict]):
    sep = "=" * 70
    print(f"\n{sep}")
    print("  EXPERIMENT 3 RESULTS: URL vs No URL")
    print(sep)
    for c in comparisons:
        agree = "AGREE" if c["verdicts_agree"] else "DISAGREE"
        print(f"\n  {c['brand']}")
        print(f"    Score      : with_url={c['score_with_url']}  no_url={c['score_no_url']}  delta={c['score_delta']:+}")
        print(f"    Verdict    : with_url={c['verdict_with_url']}  no_url={c['verdict_no_url']}  → {agree}")
        print(f"    Reflect rnd: with_url={c['reflect_rounds_with_url']}  no_url={c['reflect_rounds_no_url']}")
        print(f"    Tokens     : with_url={c['tokens_with_url']:,}  no_url={c['tokens_no_url']:,}")
        print(f"    Latency    : with_url={c['latency_with_url']:,.0f}ms  no_url={c['latency_no_url']:,.0f}ms")
    print(f"\n{sep}\n")


def main():
    parser = argparse.ArgumentParser(description="Experiment 3: URL vs No URL")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        print("\nExperiment 3 — URL vs No URL Plan")
        for d in AGENT_DEFINITIONS:
            b = TEST_BRANDS[d["brand_idx"]]
            url_str = b["website_url"] if d["use_url"] else "(no URL)"
            print(f"  Agent {d['agent_id']}  brand={b['brand_name']}  url={url_str}")
        print("\nHypothesis: No-URL agents score 5–15 pts lower, may need more reflection rounds.\n")
        return

    print(f"\nStarting Experiment 3 — {len(AGENT_DEFINITIONS)} agents in parallel")

    all_results: list[dict] = []
    exp_start = time.perf_counter()
    strategy = FullHistoryMemory()

    with ThreadPoolExecutor(max_workers=len(AGENT_DEFINITIONS)) as pool:
        futures = {}
        for defn in AGENT_DEFINITIONS:
            brand = TEST_BRANDS[defn["brand_idx"]]
            run_brand = {
                "brand_name": brand["brand_name"],
                "website_url": brand["website_url"] if defn["use_url"] else "",
            }
            futures[pool.submit(run_pipeline, run_brand, strategy, defn["agent_id"])] = defn

        for future in as_completed(futures):
            defn = futures[future]
            try:
                result = future.result()
                result["used_url"] = defn["use_url"]
                all_results.append(result)
            except Exception as exc:
                print(f"Agent {defn['agent_id']} error: {exc}")

    wall_ms = round((time.perf_counter() - exp_start) * 1000, 1)
    comparisons = _analyze(all_results)

    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "experiment": "experiment_3_url",
        "hypothesis": "No-URL agents score 5–15 pts lower; may need more reflection rounds.",
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
