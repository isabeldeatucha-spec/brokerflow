"""
HW8 — Scaled Brand Scout runner on Modal.

Fan-out: one Modal container per brand evaluation. Target 30+ concurrent
containers across Modal's US regions, each executing the full LangGraph
Brand Scout pipeline independently.

Usage
-----
    modal run hw8/modal_runner.py --brands hw8/brands.csv --repeats 1
    modal run hw8/modal_runner.py --brands hw8/brands.csv --repeats 3   # E2 consistency

Results are written to hw8/runs/<timestamp>.jsonl (one row per agent run).
"""
from __future__ import annotations

import csv
import json
import time
import uuid
from datetime import datetime
from pathlib import Path

import modal

REPO_ROOT = Path(__file__).resolve().parent.parent

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements(str(REPO_ROOT / "requirements.txt"))
    .add_local_dir(str(REPO_ROOT), remote_path="/root/sedge", copy=True)
)

app = modal.App("sedge-hw8", image=image)

# Secret holds ANTHROPIC_API_KEY, FIRECRAWL_API_KEY, PARALLEL_API_KEY,
# SUPABASE_URL, SUPABASE_KEY. Create once: `modal secret create sedge-env ...`
secret = modal.Secret.from_name("sedge-env")


@app.function(
    secrets=[secret],
    timeout=600,
    retries=0,           # we want to see failures, not mask them
    max_containers=60,   # cap for safety
)
def evaluate_brand(brand_name: str, website_url: str, trial: int) -> dict:
    """Run one Brand Scout evaluation in an isolated container."""
    import os
    import sys
    import traceback

    sys.path.insert(0, "/root/sedge")
    os.chdir("/root/sedge")

    t0 = time.time()
    record = {
        "brand_name": brand_name,
        "website_url": website_url,
        "trial": trial,
        "thread_id": str(uuid.uuid4()),
        "region": os.environ.get("MODAL_REGION", "unknown"),
        "container_id": os.environ.get("MODAL_TASK_ID", "unknown"),
        "started_at": datetime.utcnow().isoformat(),
        "status": "pending",
    }

    try:
        from main import run  # noqa: WPS433

        final = run(brand_name=brand_name, website_url=website_url)
        score = final.get("score", {}) or {}

        record.update(
            status="ok",
            total_score=score.get("total"),
            verdict=final.get("verdict"),
            category=final.get("category"),
            reflection_count=final.get("reflection_count", 0),
            score_breakdown={
                k: score.get(k)
                for k in (
                    "velocity_proof",
                    "distribution_density",
                    "margin_viability",
                    "brand_story_clarity",
                    "promotional_independence",
                )
            },
        )
    except Exception as exc:  # noqa: BLE001 — we want everything
        record.update(
            status="error",
            error_type=type(exc).__name__,
            error_msg=str(exc)[:500],
            traceback=traceback.format_exc()[-1000:],
        )

    record["latency_s"] = round(time.time() - t0, 2)
    record["ended_at"] = datetime.utcnow().isoformat()
    return record


@app.local_entrypoint()
def main(brands: str = "hw8/brands.csv", repeats: int = 1, limit: int = 0):
    """Fan-out evaluations over the brands file."""
    brands_path = REPO_ROOT / brands if not Path(brands).is_absolute() else Path(brands)
    rows = list(csv.DictReader(brands_path.open()))
    if limit:
        rows = rows[:limit]

    jobs = [
        (row["brand_name"], row["website_url"], trial)
        for trial in range(repeats)
        for row in rows
    ]
    print(f"[HW8] Dispatching {len(jobs)} evaluations "
          f"({len(rows)} brands × {repeats} trials) to Modal.")

    out_dir = REPO_ROOT / "hw8" / "runs"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    out_path = out_dir / f"run_{stamp}.jsonl"

    t0 = time.time()
    n_ok = n_err = 0
    with out_path.open("w") as fh:
        for record in evaluate_brand.starmap(jobs, order_outputs=False):
            fh.write(json.dumps(record) + "\n")
            fh.flush()
            if record["status"] == "ok":
                n_ok += 1
                print(f"  ✓ {record['brand_name']:<24} "
                      f"score={record.get('total_score')} "
                      f"lat={record['latency_s']}s")
            else:
                n_err += 1
                print(f"  ✗ {record['brand_name']:<24} "
                      f"{record.get('error_type')}: {record.get('error_msg')}")

    elapsed = time.time() - t0
    print(f"\n[HW8] Done in {elapsed:.1f}s — {n_ok} ok / {n_err} err → {out_path}")
