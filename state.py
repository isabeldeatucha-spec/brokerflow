"""
Shared state types for all Sedge agents.

Each agent defines its own TypedDict that extends or mirrors these base shapes.
Adding a new agent? Drop its state class here so the UI and memory layer can
reference it without importing from a specific agent package.
"""
import operator
from typing import Annotated, Any, Optional
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
    cache_hit: bool      # True when check_cache node served result from Supabase
    force_refresh: bool  # True to bypass cache and re-research

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


# ── Retailer Pitcher ─────────────────────────────────────────────────────────

class RetailerPitcherState(TypedDict):
    # Input / handoff
    brand_name: str
    buyer_key: str           # "whole_foods" | "sprouts" | "erewhon"
    scout_context: dict      # snapshot loaded from shared memory (Brand Scout eval)

    # Status of the handoff itself — distinct from artifact-generation status
    handoff_status: str      # "ok" | "miss" | "stale"
    handoff_error: Optional[str]

    # Generated artifacts
    email_subject: str
    email_body: str
    sell_sheet_html: str
    artifact_status: str     # "ok" | "partial" | "failed"
    # Parallel email/sell-sheet nodes both append errors and add tokens.
    # Annotated reducers let LangGraph merge concurrent updates safely.
    artifact_errors: Annotated[list[str], operator.add]
    input_tokens: Annotated[int, operator.add]
    output_tokens: Annotated[int, operator.add]

    # Human gate
    approved: Optional[bool]
    rejection_reason: Optional[str]


# ── Admin & Ops ───────────────────────────────────────────────────────────────

class AdminOpsFormFillState(TypedDict):
    # Input
    brand_name: str
    retailer: str              # "whole_foods" | future: "kehe", "unfi"

    # Handoff context
    scout_context: dict        # loaded from brand_evaluations (Supabase)
    pitcher_context: dict      # loaded from retailer_pitches if exists, else {}
    handoff_status: str        # "ok" | "miss" | "stale"
    handoff_error: Optional[str]

    # Form schema and fill results
    form_schema: list[dict]              # static list of WFM form fields
    filled_fields: dict[str, Any]        # field_id -> value the agent filled
    field_confidence: dict[str, str]     # field_id -> "high" | "medium" | "low" | "missing"
    field_sources: dict[str, str]        # field_id -> provenance string

    # Gaps — fields the agent couldn't fill
    # each gap: {field_id, label, reason, suggested_action}
    gaps: list[dict]

    # Output
    output_xlsx_path: str      # path to the filled .xlsx written to disk
    output_status: str         # "ok" | "partial" | "failed"
    artifact_errors: Annotated[list[str], operator.add]

    # Human gate
    approved: Optional[bool]
    rejection_reason: Optional[str]


# ── Future agents — add state classes here as they're built ──────────────────
# class PortfolioManagerState(TypedDict): ...
