"""
HW8 — rerun ONLY the Retailer Pitcher stage.

After modal_handoff.py already populated Supabase with Brand Scout results,
use this to iterate on the Pitcher (e.g., after a bugfix) without re-running
Scout. Same cross-container concurrency — each brand's Pitcher runs in an
independent Modal container, coordinating only through Supabase.
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
app = modal.App("sedge-hw8-pitch-only", image=image)
secret = modal.Secret.from_name("sedge-env")


@app.function(secrets=[secret], timeout=300, max_containers=60)
def pitch_from_memory(brand_name: str) -> dict:
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
    names = [r["brand_name"] for r in rows]

    out = REPO_ROOT / "hw8" / "runs"
    out.mkdir(exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    path = out / f"pitch_only_{stamp}.jsonl"

    print(f"[HW8] Pitcher fan-out on {len(names)} brands (reads Scout rows from Supabase)")
    t0 = time.time()
    n_handoff_ok = n_artifact_ok = 0
    with path.open("w") as fh:
        for rec in pitch_from_memory.map(names, order_outputs=False):
            fh.write(json.dumps(rec) + "\n")
            if rec.get("handoff_status") == "ok":
                n_handoff_ok += 1
            if rec.get("artifact_status") == "ok":
                n_artifact_ok += 1
            tag = "✓" if rec.get("artifact_status") == "ok" else "✗"
            print(f"  {tag} {rec['brand_name']:<24} "
                  f"handoff={rec.get('handoff_status')} "
                  f"artifact={rec.get('artifact_status')} "
                  f"lat={rec.get('latency_s')}s")

    elapsed = time.time() - t0
    print(f"\n[HW8] Done in {elapsed:.1f}s — "
          f"handoff_ok={n_handoff_ok}/{len(names)}  "
          f"artifact_ok={n_artifact_ok}/{len(names)} → {path}")
