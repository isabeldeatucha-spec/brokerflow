"""
Sedge Coordination Protocol — handoff contracts.

These dataclasses are the typed messages that pass between agents via the
Supabase blackboard. Agents read/write through these contracts, not through
raw dicts.

Protocol primitives implemented here:
  P1 (Blackboard):         Contracts are loaded from and persisted to Supabase.
  P2 (Verdict-gated):      ScoutHandoff.verdict drives orchestrator routing.
  Handoff validation:      Each contract has an explicit handoff_status field.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Literal, Optional


HandoffStatus = Literal["ok", "miss", "stale"]
Verdict = Literal["too_early", "broker_ready", "established"]

STALE_THRESHOLD_DAYS = 7


@dataclass
class HandoffEnvelope:
    """Base envelope for every inter-agent handoff."""
    brand_name: str
    handoff_status: HandoffStatus = "ok"
    handoff_error: Optional[str] = None
    source_agent: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def is_ok(self) -> bool:
        return self.handoff_status == "ok"

    def is_stale(self, reference_iso: Optional[str] = None) -> bool:
        """Returns True if created_at is older than STALE_THRESHOLD_DAYS."""
        try:
            created = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        except Exception:
            return True
        age = datetime.now(timezone.utc) - created
        return age > timedelta(days=STALE_THRESHOLD_DAYS)


@dataclass
class ScoutHandoff(HandoffEnvelope):
    """
    Emitted by Brand Scout, consumed by Retailer Pitcher and Admin & Ops.
    This is the protocol's primary coordination message.
    """
    source_agent: str = "brand_scout"
    category: str = ""
    score_total: int = 0
    verdict: Verdict = "too_early"  # drives downstream routing
    broker_brief: str = ""
    key_gaps: list = field(default_factory=list)
    score_breakdown: dict = field(default_factory=dict)
    extracted_fields: dict = field(default_factory=dict)
    founder_name: str = ""
    founder_email: str = ""

    @classmethod
    def from_supabase_row(cls, row: dict) -> "ScoutHandoff":
        """Construct a ScoutHandoff from a brand_evaluations row."""
        breakdown = row.get("score_breakdown") or {}
        return cls(
            brand_name=row["brand_name"],
            handoff_status="ok",
            category=row.get("category", ""),
            score_total=row.get("score", 0),
            verdict=row.get("verdict", "too_early"),
            broker_brief=row.get("broker_brief", ""),
            key_gaps=row.get("key_gaps") or [],
            score_breakdown=breakdown,
            extracted_fields=row.get("extracted_fields") or {},
            founder_name=row.get("founder_name", ""),
            founder_email=row.get("founder_email", ""),
            created_at=row.get("evaluated_at", datetime.now(timezone.utc).isoformat()),
        )

    @classmethod
    def miss(cls, brand_name: str, error: str = "No record in blackboard") -> "ScoutHandoff":
        return cls(brand_name=brand_name, handoff_status="miss", handoff_error=error)


@dataclass
class PitcherHandoff(HandoffEnvelope):
    """Emitted by Retailer Pitcher per buyer, consumed by orchestrator (and optionally Admin)."""
    source_agent: str = "retailer_pitcher"
    buyer_key: str = ""                  # "whole_foods" | "sprouts" | "erewhon"
    email_subject: str = ""
    email_body: str = ""
    sell_sheet_html: str = ""
    framing: Literal["standard", "upgrade_broker"] = "standard"


@dataclass
class AdminHandoff(HandoffEnvelope):
    """Emitted by Admin & Ops, consumed by orchestrator."""
    source_agent: str = "admin_ops"
    retailer: str = "whole_foods"
    filled_field_count: int = 0
    gap_count: int = 0
    output_xlsx_path: str = ""
    output_status: Literal["ok", "partial", "failed"] = "ok"


# ── Routing decision ──────────────────────────────────────────────────────────

@dataclass
class RoutingDecision:
    """
    Produced by the orchestrator after reading a ScoutHandoff.
    Encodes the verdict-gated routing rule (Protocol Primitive 2).
    """
    run_pitcher: bool
    run_admin: bool
    pitcher_framing: Literal["standard", "upgrade_broker"]
    reason: str

    @classmethod
    def from_verdict(cls, verdict: Verdict) -> "RoutingDecision":
        if verdict == "too_early":
            return cls(
                run_pitcher=False,
                run_admin=False,
                pitcher_framing="standard",
                reason="Brand scored below 45 — saving to watchlist, no outreach.",
            )
        if verdict == "broker_ready":
            return cls(
                run_pitcher=True,
                run_admin=True,
                pitcher_framing="standard",
                reason="Brand in sweet spot — full pipeline with standard framing.",
            )
        if verdict == "established":
            return cls(
                run_pitcher=True,
                run_admin=True,
                pitcher_framing="upgrade_broker",
                reason="Established brand — pitching against incumbent broker.",
            )
        # Defensive default
        return cls(
            run_pitcher=False,
            run_admin=False,
            pitcher_framing="standard",
            reason=f"Unknown verdict '{verdict}' — refusing to route.",
        )
