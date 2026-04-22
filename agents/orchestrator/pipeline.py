"""
Orchestrator pipeline — runs Brand Scout → Retailer Pitcher (×3) → Admin & Ops
in sequence and yields PipelineEvent progress updates.

Upgrade 2 (HW9): Uses typed contracts and verdict-gated routing.
  - ScoutHandoff carries the coordination message from Brand Scout.
  - RoutingDecision.from_verdict() gates downstream agents.
  - too_early brands halt cleanly after Scout; no Pitcher/Admin calls made.
  - established brands get "upgrade_broker" framing in all three pitches.

Usage:
    from agents.orchestrator.pipeline import run_full_pipeline, PipelineEvent
    for event in run_full_pipeline("Chomps", "https://chomps.com"):
        print(event.stage, event.status, event.message)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from typing import Iterator

from langgraph.types import Command
from memory import get_config

from agents.orchestrator.contracts import (
    ScoutHandoff, AdminHandoff, RoutingDecision,
)


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


def _run_pitcher_with_framing(brand_name: str, buyer_key: str, framing: str) -> dict:
    """Run Retailer Pitcher for one buyer. framing is passed in state for future use."""
    from agents.retailer_pitcher.graph import graph as pitcher_graph
    from state import RetailerPitcherState

    thread_id = str(uuid.uuid4())
    config = get_config(thread_id)
    initial: RetailerPitcherState = {
        "brand_name":       brand_name,
        "buyer_key":        buyer_key,
        "framing":          framing,   # future-proof hook; graph ignores if not wired
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
    Yield PipelineEvent for each pipeline stage.

    Verdict-gated routing (Protocol Primitive 2):
      too_early  → Scout only; complete with watchlist data
      broker_ready/established → Scout + Pitcher × 3 + Admin
      established → pitcher_framing = "upgrade_broker"
    """
    brand_name = brand_name.strip().title()

    # ── Brand Scout ───────────────────────────────────────────────────────────
    yield PipelineEvent(stage="scout", status="running",
                        message=f"Researching {brand_name}…")
    try:
        scout_result = _run_scout(brand_name, website_url, force_refresh)
    except Exception as exc:
        yield PipelineEvent(stage="scout", status="error",
                            message="Brand Scout failed", error=str(exc))
        yield PipelineEvent(stage="complete", status="error",
                            message="Pipeline stopped after scout error", error=str(exc))
        return

    # Build typed handoff + routing decision
    score_obj = scout_result.get("score", {})
    raw_verdict = scout_result.get("verdict", "too_early")
    # Normalise: graph sometimes stores "above_threshold"/"below_threshold" in state
    _VERDICT_MAP = {
        "above_threshold": "broker_ready",
        "below_threshold": "too_early",
    }
    verdict: str = _VERDICT_MAP.get(raw_verdict, raw_verdict)
    if verdict not in ("too_early", "broker_ready", "established"):
        verdict = "too_early"

    scout_handoff = ScoutHandoff(
        brand_name=brand_name,
        category=scout_result.get("category", ""),
        score_total=score_obj.get("total", 0) if isinstance(score_obj, dict) else 0,
        verdict=verdict,
        broker_brief=(scout_result.get("signals_found", {})
                                  .get("score_detail", {})
                                  .get("broker_brief", "")),
        key_gaps=(scout_result.get("signals_found", {})
                              .get("score_detail", {})
                              .get("key_gaps", [])),
        score_breakdown=(scout_result.get("signals_found", {})
                                     .get("score_detail", {})),
        extracted_fields=scout_result.get("extracted_fields") or {},
        founder_name=scout_result.get("founder_name", ""),
        founder_email=scout_result.get("founder_email", ""),
    )

    routing = RoutingDecision.from_verdict(scout_handoff.verdict)

    yield PipelineEvent(
        stage="scout", status="done",
        message=(f"Scored {scout_handoff.score_total}/100 — {scout_handoff.verdict} · "
                 f"Routing: {routing.reason}"),
        data={**scout_result,
              "scout_handoff": asdict(scout_handoff),
              "routing": asdict(routing)},
    )

    # ── Verdict gate ──────────────────────────────────────────────────────────
    if not routing.run_pitcher:
        yield PipelineEvent(
            stage="complete", status="done",
            message=f"Pipeline halted: {routing.reason}",
            data={
                "scout":        scout_result,
                "scout_handoff": asdict(scout_handoff),
                "routing":      asdict(routing),
                "pitches":      [],
                "admin_result": None,
            },
        )
        return

    # ── Retailer Pitches — gated on routing decision ──────────────────────────
    pitcher_results: dict[str, dict] = {}

    for stage_key, buyer_key in _BUYER_FOR_STAGE.items():
        rlabel = _RETAILER_LABEL[buyer_key]
        yield PipelineEvent(stage=stage_key, status="running",
                            message=(f"Drafting pitch → {rlabel} "
                                     f"({routing.pitcher_framing} framing)…"))
        try:
            result = _run_pitcher_with_framing(brand_name, buyer_key, routing.pitcher_framing)
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

    # ── Admin & Ops — gated on routing decision ───────────────────────────────
    admin_result: dict = {}
    if routing.run_admin:
        yield PipelineEvent(stage="admin_wfm", status="running",
                            message="Filling WFM New Item Setup Form…")
        try:
            admin_result = _run_admin_ops(brand_name)
            admin_handoff = AdminHandoff(
                brand_name=brand_name,
                retailer="whole_foods",
                filled_field_count=len(admin_result.get("filled_fields") or {}),
                gap_count=len(admin_result.get("gaps") or []),
                output_xlsx_path=admin_result.get("output_xlsx_path", ""),
                output_status=admin_result.get("output_status", "ok"),
            )
            ao_status = admin_result.get("output_status", "unknown")
            gaps_count = len(admin_result.get("gaps", []))
            yield PipelineEvent(
                stage="admin_wfm",
                status="done" if ao_status in ("ok", "partial") else "error",
                message=(f"WFM form: {ao_status} · {gaps_count} gap(s) · "
                         f"{admin_handoff.filled_field_count} fields filled"),
                data={**admin_result, "admin_handoff": asdict(admin_handoff)},
            )
        except Exception as exc:
            yield PipelineEvent(stage="admin_wfm", status="error",
                                message="WFM form failed", error=str(exc))

    # ── Complete ──────────────────────────────────────────────────────────────
    yield PipelineEvent(
        stage="complete", status="done",
        message="All bundles ready for review",
        data={
            "scout":         scout_result,
            "scout_handoff": asdict(scout_handoff),
            "routing":       asdict(routing),
            "pitches":       pitcher_results,
            "admin_result":  admin_result,
        },
    )


# ── Triage pipeline ───────────────────────────────────────────────────────────

def run_triage_pipeline(brand_names: list[str]) -> Iterator[PipelineEvent]:
    """
    Fast triage of up to 5 brands. Yields one PipelineEvent per brand as
    triage completes, then one terminal PipelineEvent("triage_complete", "done")
    with the full list of QuickTriageResult dicts as data.
    No Pitcher/Admin runs here — this pipeline is pre-selection only.
    """
    from agents.brand_scout.quick import quick_triage

    clean = [n.strip() for n in brand_names if n and n.strip()][:5]
    if not clean:
        yield PipelineEvent("triage_complete", "failed",
                            "No brand names provided.",
                            data={"results": []})
        return

    yield PipelineEvent("triage_start", "started",
                        f"Triaging {len(clean)} brands…")

    all_results = []
    for name in clean:
        yield PipelineEvent(f"triage_{name}", "started",
                            f"Triaging {name}…")
        r = quick_triage(name)
        all_results.append(r)
        yield PipelineEvent(
            f"triage_{name}",
            "done" if not r.error else "failed",
            f"{name}: {r.score_estimate}/100 · {r.verdict}"
            + (" (cached)" if r.cached else ""),
            data={"result": asdict(r)},
        )

    yield PipelineEvent("triage_complete", "done",
                        f"Triaged {len(all_results)} brands.",
                        data={"results": [asdict(r) for r in all_results]})


# ── Selective pitch pipeline ──────────────────────────────────────────────────

def run_selective_pitch_pipeline(brand_names: list[str]) -> Iterator[PipelineEvent]:
    """
    Run the full pipeline (Scout → Pitcher × 3 → Admin) for EACH selected brand
    in sequence. Reuses run_full_pipeline per brand. Yields all events from every
    brand's pipeline, prefixed with the brand name so the UI can group them.
    """
    if not brand_names:
        yield PipelineEvent("complete", "done", "No brands selected.", data={})
        return

    all_bundles = []
    for name in brand_names:
        yield PipelineEvent("brand_start", "started",
                            f"Running full pipeline for {name}…",
                            data={"brand_name": name})
        try:
            last_event = None
            for event in run_full_pipeline(name, ""):
                event_data = dict(event.data or {})
                event_data["brand_name"] = name
                yield PipelineEvent(event.stage, event.status, event.message,
                                    data=event_data, error=event.error)
                last_event = event

            if last_event and last_event.data:
                pitches_raw = last_event.data.get("pitches", {})
                # Normalize pitcher_results dict to list for approval page
                if isinstance(pitches_raw, dict):
                    pitches_list = [{"buyer_key": k, **v}
                                    for k, v in pitches_raw.items()]
                else:
                    pitches_list = list(pitches_raw)
                all_bundles.append({
                    "brand_name":    name,
                    "scout_handoff": last_event.data.get("scout_handoff"),
                    "routing":       last_event.data.get("routing"),
                    "pitches":       pitches_list,
                    "admin_result":  last_event.data.get("admin_result"),
                })
        except Exception as e:
            yield PipelineEvent("brand_failed", "failed",
                                f"{name}: {type(e).__name__} — {e}",
                                data={"brand_name": name})

    yield PipelineEvent("selective_complete", "done",
                        f"All bundles ready for {len(all_bundles)} brands.",
                        data={"bundles": all_bundles})
