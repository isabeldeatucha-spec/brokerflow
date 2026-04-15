"""
HW8 — Experiment 4: concurrent Brand Scout → Retailer Pitcher handoffs.

Two Modal functions fan out independently; each brand's Scout container and
Pitcher container run on *different* workers and coordinate only through the
Supabase shared-memory layer. Telemetry separates handoff-layer failures from
artifact-generation failures so the analysis can attribute them cleanly.
"""
from __future__ import annotations

import csv
import json
import time
from datetime import datetime
from pathlib import Path

import modal

REPO_ROOT = Path(__file__).resolve().parent.parent

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements(str(REPO_ROOT / "requirements.txt"))
    .add_local_dir(str(REPO_ROOT), remote_path="/root/sedge", copy=True)
)
app = modal.App("sedge-hw8-handoff", image=image)
secret = modal.Secret.from_name("sedge-env")


@app.function(secrets=[secret], timeout=600, max_containers=60)
def scout_then_handoff(brand_name: str, website_url: str) -> dict:
    """Scout stage on container A — writes result into Supabase."""
    import sys, os
    sys.path.insert(0, "/root/sedge")
    os.chdir("/root/sedge")
    from main import run

    t0 = time.time()
    try:
        final = run(brand_name=brand_name, website_url=website_url)
        return {
            "stage": "scout",
            "brand_name": brand_name,
            "status": "ok",
            "score": (final.get("score") or {}).get("total"),
            "verdict": final.get("verdict"),
            "latency_s": round(time.time() - t0, 2),
            "ts": datetime.utcnow().isoformat(),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "stage": "scout",
            "brand_name": brand_name,
            "status": "error",
            "error_type": type(exc).__name__,
            "error_msg": str(exc)[:300],
            "latency_s": round(time.time() - t0, 2),
        }


@app.function(secrets=[secret], timeout=300, max_containers=60)
def pitch_from_memory(brand_name: str) -> dict:
    """Pitcher stage on container B — reads Scout row, drafts email + sell sheet."""
    import sys, os
    sys.path.insert(0, "/root/sedge")
    os.chdir("/root/sedge")
    from agents.retailer_pitcher.graph import run_pitch_once

    rec = run_pitch_once(brand_name, auto_approve=True)
    rec["stage"] = "pitch"
    rec["ts"] = datetime.utcnow().isoformat()
    return rec


@app.local_entrypoint()
def main(brands: str = "hw8/brands.csv", limit: int = 30):
    brands_path = REPO_ROOT / brands if not Path(brands).is_absolute() else Path(brands)
    rows = list(csv.DictReader(brands_path.open()))[:limit]

    out_dir = REPO_ROOT / "hw8" / "runs"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    path = out_dir / f"handoff_{stamp}.jsonl"

    print(f"[HW8-E4] Scout fan-out on {len(rows)} brands")
    scout_jobs = [(r["brand_name"], r["website_url"]) for r in rows]

    t0 = time.time()
    scout_results: list[dict] = []
    with path.open("w") as fh:
        for rec in scout_then_handoff.starmap(scout_jobs, order_outputs=False):
            scout_results.append(rec)
            fh.write(json.dumps(rec) + "\n")
            tag = "✓" if rec["status"] == "ok" else "✗"
            print(f"  {tag} scout {rec['brand_name']:<24} {rec['status']} "
                  f"lat={rec.get('latency_s')}s")

        n_ok = sum(1 for r in scout_results if r["status"] == "ok")
        print(f"[HW8-E4] Scout done in {time.time()-t0:.1f}s — {n_ok}/{len(scout_results)} ok")

        ok_brands = [r["brand_name"] for r in scout_results if r["status"] == "ok"]
        print(f"[HW8-E4] Dispatching {len(ok_brands)} pitcher jobs (separate containers)")

        n_handoff_ok = n_artifact_ok = 0
        for rec in pitch_from_memory.map(ok_brands, order_outputs=False):
            fh.write(json.dumps(rec) + "\n")
            if rec.get("handoff_status") == "ok":
                n_handoff_ok += 1
            if rec.get("artifact_status") == "ok":
                n_artifact_ok += 1
            tag = "✓" if rec.get("artifact_status") == "ok" else "✗"
            print(f"  {tag} pitch {rec['brand_name']:<24} "
                  f"handoff={rec.get('handoff_status')} "
                  f"artifact={rec.get('artifact_status')} "
                  f"lat={rec.get('latency_s')}s")

        print(f"\n[HW8-E4] Handoff ok: {n_handoff_ok}/{len(ok_brands)}  "
              f"Artifacts ok: {n_artifact_ok}/{len(ok_brands)}")

    print(f"[HW8-E4] Done → {path}")
