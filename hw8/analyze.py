"""
HW8 — aggregate and visualize run_*.jsonl files produced by the Modal runners.

Produces:
    hw8/figs/throughput.png        wall-clock vs concurrency
    hw8/figs/latency.png           p50/p95 by experiment
    hw8/figs/failure_modes.png     failure taxonomy
    hw8/figs/consistency.png       score std-dev across repeats
    hw8/figs/handoff.png           scout→pitch success rate
    hw8/SUMMARY_DATA.json          numbers used in SUMMARY.md
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

FIGS = Path(__file__).parent / "figs"
RUNS = Path(__file__).parent / "runs"


def load(paths: list[Path]) -> list[dict]:
    records: list[dict] = []
    for p in paths:
        for line in p.open():
            if line.strip():
                records.append(json.loads(line))
    return records


def summarize_throughput(recs: list[dict]) -> dict:
    ok = [r for r in recs if r.get("status") == "ok"]
    err = [r for r in recs if r.get("status") != "ok"]
    latencies = [r["latency_s"] for r in ok if "latency_s" in r]
    return {
        "total_runs": len(recs),
        "success": len(ok),
        "failure": len(err),
        "success_rate": round(len(ok) / max(1, len(recs)), 3),
        "p50_latency_s": round(statistics.median(latencies), 2) if latencies else None,
        "p95_latency_s": round(sorted(latencies)[int(0.95 * len(latencies))], 2)
                          if len(latencies) >= 20 else None,
        "max_latency_s": max(latencies) if latencies else None,
        "failure_modes": dict(Counter(r.get("error_type", "unknown") for r in err)),
        "regions": dict(Counter(r.get("region", "unknown") for r in ok)),
    }


def plot_latency(recs: list[dict]) -> None:
    ok = [r for r in recs if r.get("status") == "ok" and "latency_s" in r]
    if not ok:
        return
    lat = sorted(r["latency_s"] for r in ok)
    plt.figure(figsize=(6, 4))
    plt.plot(lat, marker=".")
    p50 = lat[len(lat) // 2]
    p95 = lat[int(0.95 * len(lat))] if len(lat) >= 20 else lat[-1]
    plt.axhline(p50, ls="--", c="tab:blue", label=f"p50 = {p50:.1f}s")
    plt.axhline(p95, ls="--", c="tab:red",  label=f"p95 = {p95:.1f}s")
    plt.xlabel("run (sorted by latency)")
    plt.ylabel("latency (s)")
    plt.title(f"Brand Scout per-run latency (n={len(lat)})")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGS / "latency.png", dpi=140)
    plt.close()


def plot_failure_modes(recs: list[dict]) -> None:
    err = [r for r in recs if r.get("status") != "ok"]
    if not err:
        return
    counts = Counter(r.get("error_type", "unknown") for r in err)
    labels, values = zip(*counts.most_common())
    plt.figure(figsize=(6, 4))
    plt.barh(labels, values)
    plt.xlabel("# failed runs")
    plt.title(f"Failure taxonomy at scale (n_fail={len(err)})")
    plt.tight_layout()
    plt.savefig(FIGS / "failure_modes.png", dpi=140)
    plt.close()


def plot_consistency(recs: list[dict]) -> None:
    by_brand: dict[str, list[int]] = defaultdict(list)
    for r in recs:
        if r.get("status") == "ok" and r.get("total_score") is not None:
            by_brand[r["brand_name"]].append(r["total_score"])
    multi = {b: s for b, s in by_brand.items() if len(s) >= 2}
    if not multi:
        return
    brands = sorted(multi, key=lambda b: statistics.pstdev(multi[b]), reverse=True)
    stds = [statistics.pstdev(multi[b]) for b in brands]
    plt.figure(figsize=(7, max(3, 0.25 * len(brands))))
    plt.barh(brands, stds)
    plt.xlabel("score stddev across repeats")
    plt.title("Per-brand score consistency (HW7 had n=3; HW8 ≥2)")
    plt.tight_layout()
    plt.savefig(FIGS / "consistency.png", dpi=140)
    plt.close()


def plot_handoff(recs: list[dict]) -> None:
    scout = [r for r in recs if r.get("stage") == "scout"]
    pitch = [r for r in recs if r.get("stage") == "pitch"]
    if not scout or not pitch:
        return
    scout_ok = sum(1 for r in scout if r["status"] == "ok")
    handoff = Counter(r.get("handoff_status", "unknown") for r in pitch)
    artifact = Counter(r.get("artifact_status", "unknown") for r in pitch)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].bar(list(handoff.keys()), list(handoff.values()), color="tab:blue")
    axes[0].set_title(f"Handoff layer (Scout→Pitcher memory read)\n"
                      f"n_scout_ok={scout_ok}, n_pitch={len(pitch)}")
    axes[0].set_ylabel("count")
    axes[1].bar(list(artifact.keys()), list(artifact.values()), color="tab:orange")
    axes[1].set_title("Artifact layer (email + sell sheet generation)")
    plt.tight_layout()
    plt.savefig(FIGS / "handoff.png", dpi=140)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", nargs="*", default=None,
                        help="specific jsonl files (default: all in hw8/runs/)")
    args = parser.parse_args()

    FIGS.mkdir(exist_ok=True)
    files = [Path(p) for p in args.runs] if args.runs else sorted(RUNS.glob("*.jsonl"))
    if not files:
        print("No run files found. Execute modal_runner.py first.")
        return

    recs = load(files)
    scout_pitch = [r for r in recs if r.get("stage") in {"scout", "pitch"}]
    brand_scout = [r for r in recs if r.get("stage") not in {"pitch"}]

    summary = summarize_throughput(brand_scout)
    print(json.dumps(summary, indent=2))

    plot_latency(brand_scout)
    plot_failure_modes(brand_scout)
    plot_consistency(brand_scout)
    if scout_pitch:
        plot_handoff(scout_pitch)

    (Path(__file__).parent / "SUMMARY_DATA.json").write_text(
        json.dumps(summary, indent=2)
    )
    print(f"\nFigures → {FIGS}")


if __name__ == "__main__":
    main()
