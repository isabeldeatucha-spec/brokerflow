"""
Shared state types for all Sedge agents.

Each agent defines its own TypedDict that extends or mirrors these base shapes.
Adding a new agent? Drop its state class here so the UI and memory layer can
reference it without importing from a specific agent package.
"""
from typing import Any, Optional
from typing_extensions import TypedDict


# ── Shared primitives ─────────────────────────────────────────────────────────

class ScoreBreakdown(TypedDict):
    velocity_proof: int         # /25 — review count, reorder signals, sales rank
    distribution_density: int   # /20 — retailer count and banner quality
    margin_viability: int       # /20 — wholesale vs SRP, price point
    brand_story_clarity: int    # /20 — positioning and target consumer clarity
    promotional_independence: int  # /15 — runs own promos, not broker-dependent
    total: int                  # /100


# ── Brand Scout ───────────────────────────────────────────────────────────────

class BrandScoutState(TypedDict):
    # Input
    brand_name: str
    website_url: str

    # Research
    sources_checked: list[str]
    signals_found: dict[str, Any]

    # ReAct reflection loop
    follow_up_queries: list[str]   # queries the agent decided to investigate further
    reflection_count: int          # number of reflection loops completed
    reflection_notes: list[str]    # agent reasoning about what it found and why it dug deeper

    # Category
    category: str         # detected product category key
    benchmark: dict       # category benchmark from skills/category_benchmarks.py

    # Scoring
    score: ScoreBreakdown
    verdict: str            # "above_threshold" | "below_threshold"

    # Outreach
    founder_name: str
    founder_email: str
    email_draft: str

    # Extracted fields (structured data pulled from raw signals by Haiku)
    extracted_fields: dict

    # Human gate
    approved: Optional[bool]
    rejection_reason: Optional[str]


# ── Future agents — add state classes here as they're built ──────────────────
# class RetailerPitcherState(TypedDict): ...
# class AdminOpsState(TypedDict): ...
# class PortfolioManagerState(TypedDict): ...
