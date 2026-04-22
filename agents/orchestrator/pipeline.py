"""
Orchestrator pipeline — runs Brand Scout → Retailer Pitcher (×3) → Admin & Ops
in sequence and yields PipelineEvent progress updates.

Usage:
    from agents.orchestrator.pipeline import run_full_pipeline, PipelineEvent
    for event in run_full_pipeline("Chomps", "https://chomps.com"):
        print(event.stage, event.status, event.message)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Iterator

from langgraph.types import Command
from memory import get_config


# ── Stages ────────────────────────────────────────────────────────────────────

STAGE_LABELS: dict[str, str] = {
    "scout":           "Brand Scout",
    "pitcher_wf":      "Retailer Pitcher → Whole Foods",
    "pitcher_sprouts": "Retailer Pitcher → Sprouts",
    "pitcher_erewhon": "Retailer Pitcher → Erewhon",
    "admin_wfm":       "Admin & Ops → WFM New Item Form",
    "complete":        "Pipeline complete",
}

STAGE_ORDER = ["scout", "pitcher_wf", "pitcher_sprouts", "pitcher_erewhon", "admin_wfm"]

_BUYER_FOR_STAGE = {
    "pitcher_wf":      "whole_foods",
    "pitcher_sprouts": "sprouts",
    "pitcher_erewhon": "erewhon",
}

_RETAILER_LABEL = {
    "whole_foods": "Whole Foods",
    "sprouts":     "Sprouts",
    "erewhon":     "Erewhon",
}


# ── Event dataclass ───────────────────────────────────────────────────────────

@dataclass
class PipelineEvent:
    stage: str                     # key from STAGE_ORDER or "complete" / "error"
    status: str                    # "running" | "done" | "error"
    message: str = ""
    data: dict = field(default_factory=dict)
    error: str | None = None


# ── Individual agent runners ──────────────────────────────────────────────────

def _run_scout(brand_name: str, website_url: str, force_refresh: bool) -> dict:
    from agents.brand_scout.graph import graph as scout_graph
    from state import BrandScoutState

    thread_id = str(uuid.uuid4())
    config = get_config(thread_id)
    initial: BrandScoutState = {
        "brand_name":    brand_name,
        "website_url":   website_url,
        "cache_hit":     False,
        "force_refresh": force_refresh,
        "sources_checked":  [],
        "signals_found":    {},
        "follow_up_queries": [],
        "reflection_count": 0,
        "reflection_notes": [],
        "category":   "",
        "benchmark":  {},
        "score": {
            "velocity_proof": 0, "distribution_density": 0,
            "margin_viability": 0, "brand_story_clarity": 0,
            "promotional_independence": 0, "total": 0,
        },
        "verdict":         "",
        "founder_name":    "",
        "founder_email":   "",
        "email_draft":     "",
        "extracted_fields": {},
        "approved":          None,
        "rejection_reason":  None,
    }

    for _ in scout_graph.stream(initial, config=config, stream_mode="updates"):
        snap = scout_graph.get_state(config)
        if snap.next and "human_approval" in snap.next:
            scout_graph.invoke(
                Command(resume={"approved": True, "rejection_reason": ""}),
                config=config,
            )
            break

    return dict(scout_graph.get_state(config).values)


def _run_pitcher(brand_name: str, buyer_key: str) -> dict:
    from agents.retailer_pitcher.graph import graph as pitcher_graph
    from state import RetailerPitcherState

    thread_id = str(uuid.uuid4())
    config = get_config(thread_id)
    initial: RetailerPitcherState = {
        "brand_name":       brand_name,
        "buyer_key":        buyer_key,
        "scout_context":    {},
        "handoff_status":   "",
        "handoff_error":    None,
        "email_subject":    "",
        "email_body":       "",
        "sell_sheet_html":  "",
        "artifact_status":  "",
        "artifact_errors":  [],
        "input_tokens":     0,
        "output_tokens":    0,
        "approved":         None,
        "rejection_reason": None,
    }

    for _ in pitcher_graph.stream(initial, config=config, stream_mode="updates"):
        snap = pitcher_graph.get_state(config)
        if snap.next and "human_approval" in snap.next:
            pitcher_graph.invoke(
                Command(resume={"approved": True, "rejection_reason": ""}),
                config=config,
            )
            break

    return dict(pitcher_graph.get_state(config).values)


def _run_admin_ops(brand_name: str) -> dict:
    from agents.admin_ops.graph import run_admin_ops
    return run_admin_ops(brand_name, retailer="whole_foods")


# ── Main generator ────────────────────────────────────────────────────────────

def run_full_pipeline(
    brand_name: str,
    website_url: str = "",
    force_refresh: bool = False,
) -> Iterator[PipelineEvent]:
    """
    Yield PipelineEvent for each pipeline stage in order:
      scout → pitcher_wf → pitcher_sprouts → pitcher_erewhon → admin_wfm → complete
    """
    brand_name = brand_name.strip().title()

    # ── Brand Scout ───────────────────────────────────────────────────────────
    yield PipelineEvent(stage="scout", status="running",
                        message=f"Researching {brand_name}…")
    try:
        scout_result = _run_scout(brand_name, website_url, force_refresh)
        score_obj = scout_result.get("score", {})
        total = score_obj.get("total", 0) if isinstance(score_obj, dict) else 0
        verdict = scout_result.get("verdict", "—")
        yield PipelineEvent(
            stage="scout", status="done",
            message=f"Brand Scout: {brand_name} · {total}/100 · {verdict}",
            data=scout_result,
        )
    except Exception as exc:
        yield PipelineEvent(stage="scout", status="error",
                            message="Brand Scout failed", error=str(exc))
        yield PipelineEvent(stage="complete", status="error",
                            message="Pipeline stopped after scout error", error=str(exc))
        return

    # ── Retailer Pitches ──────────────────────────────────────────────────────
    pitcher_results: dict[str, dict] = {}

    for stage_key, buyer_key in _BUYER_FOR_STAGE.items():
        rlabel = _RETAILER_LABEL[buyer_key]
        yield PipelineEvent(stage=stage_key, status="running",
                            message=f"Drafting pitch → {rlabel}…")
        try:
            result = _run_pitcher(brand_name, buyer_key)
            art_status = result.get("artifact_status", "unknown")
            errors = result.get("artifact_errors", [])
            yield PipelineEvent(
                stage=stage_key,
                status="done" if art_status in ("ok", "partial") else "error",
                message=f"Pitcher → {rlabel}: {art_status}",
                data=result,
                error=("; ".join(errors) if errors else None),
            )
            pitcher_results[buyer_key] = result
        except Exception as exc:
            yield PipelineEvent(stage=stage_key, status="error",
                                message=f"Pitcher → {rlabel} failed", error=str(exc))
            pitcher_results[buyer_key] = {}

    # ── Admin & Ops ───────────────────────────────────────────────────────────
    yield PipelineEvent(stage="admin_wfm", status="running",
                        message="Filling WFM New Item Setup Form…")
    try:
        admin_result = _run_admin_ops(brand_name)
        ao_status = admin_result.get("output_status", "unknown")
        gaps_count = len(admin_result.get("gaps", []))
        yield PipelineEvent(
            stage="admin_wfm",
            status="done" if ao_status in ("ok", "partial") else "error",
            message=f"WFM form: {ao_status} · {gaps_count} gap(s)",
            data=admin_result,
        )
    except Exception as exc:
        yield PipelineEvent(stage="admin_wfm", status="error",
                            message="WFM form failed", error=str(exc))
        admin_result = {}

    # ── Complete ──────────────────────────────────────────────────────────────
    yield PipelineEvent(
        stage="complete", status="done",
        message="All agents complete — review bundles below",
        data={
            "scout":    scout_result,
            "pitchers": pitcher_results,
            "admin_ops": admin_result,
        },
    )
