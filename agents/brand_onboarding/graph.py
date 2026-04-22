"""Onboarding Agent as a LangGraph StateGraph.

Six nodes demonstrating the full agent lifecycle:
  1. load_prior_knowledge     (coordination: read from Brand Scout)
  2. extract_from_uploads     (tool use: file parse + LLM)
  3. merge_and_reconcile      (autonomy: decides conflicts without user input)
  4. score_completeness       (pure function)
  5. persist_and_log          (memory: canonical write + event log)
  6. notify_downstream        (coordination: message Matcher + Admin)
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from agents.brand_onboarding.state import OnboardingState
from agents.brand_onboarding.tools import (
    tool_parse_uploaded_file,
    tool_fetch_scout_evaluation,
    tool_llm_extract_structured,
    tool_persist_brand_record,
    tool_append_event,
    tool_emit_coordination_message,
)
from agents.orchestrator.contracts import (
    PriorKnowledge, OnboardingHandoff
)

# Canonical target schema (~18 fields) for demo reliability
TARGET_SCHEMA = {
    "category": "string (e.g., 'snacks', 'beverages')",
    "subcategory": "string (e.g., 'meat snacks', 'sparkling water')",
    "founded_year": "integer or null",
    "hq_city": "string or null",
    "hq_state": "string or null",
    "founder_name": "string or null",
    "founder_email": "string or null",
    "product_count": "integer",
    "flagship_sku": "string",
    "wholesale_price_range": "string (e.g., '$2.50-$3.00')",
    "retail_price_range": "string",
    "margin_range": "string",
    "distributor_list": "array of strings",
    "current_retailers": "array of strings",
    "target_retailers": "array of strings",
    "certifications": "array of strings (e.g., ['Non-GMO','Organic'])",
    "brand_story": "string, 2-3 sentences max",
    "key_differentiators": "array of strings, 3-5 items",
}


def node_load_prior_knowledge(state: OnboardingState) -> dict:
    """Coordination: check if Brand Scout has prior signals on this brand."""
    brand_name = state["input"].brand_name
    scout_data = tool_fetch_scout_evaluation(brand_name)

    if scout_data:
        pk = PriorKnowledge(
            source_agent="brand_scout",
            found=True,
            scout_score=scout_data.get("score"),
            scout_verdict=scout_data.get("verdict"),
            scout_category=scout_data.get("category"),
            scout_signals=scout_data.get("score_breakdown", {}),
            evaluated_at=scout_data.get("evaluated_at"),
        )
    else:
        pk = PriorKnowledge(source_agent="none", found=False)

    return {
        "prior_knowledge": pk,
        "tool_calls": ["fetch_scout_evaluation"],
    }


def node_extract_from_uploads(state: OnboardingState) -> dict:
    """Tool use: parse files + LLM extraction."""
    files = state["input"].uploaded_file_paths
    brand_name = state["input"].brand_name

    if not files:
        return {
            "extracted_fields": {},
            "tool_calls": ["extract_skipped_no_files"],
        }

    all_text = []
    tool_log = []
    for fp in files:
        result = tool_parse_uploaded_file(fp)
        tool_log.append(f"parse:{fp}:{'ok' if result['ok'] else 'fail'}")
        if result["ok"]:
            all_text.append(f"--- {result['source']} ---\n{result['text']}")

    combined = "\n\n".join(all_text)
    if not combined:
        return {
            "extracted_fields": {},
            "tool_calls": tool_log,
            "errors": ["no_text_extracted"],
        }

    extraction = tool_llm_extract_structured(combined, TARGET_SCHEMA, brand_name)
    tool_log.append(f"llm_extract:{'ok' if extraction['ok'] else 'fail'}")

    if not extraction["ok"]:
        return {
            "extracted_fields": {},
            "tool_calls": tool_log,
            "errors": [f"extraction: {extraction.get('error')}"],
        }

    return {
        "extracted_fields": extraction["fields"],
        "tool_calls": tool_log,
    }


def node_merge_and_reconcile(state: OnboardingState) -> dict:
    """Autonomy: agent decides conflicts without asking the user.

    Merge priority: manual_overrides > extraction > prior_knowledge > null.
    When extraction and prior_knowledge disagree on a field, the agent flags
    it as a conflict BUT resolves it (takes extraction as more recent) so the
    pipeline does not stall.
    """
    pk = state.get("prior_knowledge")
    extracted = state.get("extracted_fields", {}) or {}
    overrides = state["input"].manual_overrides or {}

    merged: dict = {}
    conflicts: list = []

    # Seed from prior knowledge (Scout) if available
    if pk and pk.found:
        if pk.scout_category:
            merged["category"] = pk.scout_category

    # Layer in extraction
    for key, value in extracted.items():
        if value is None:
            continue
        if key in merged and merged[key] != value:
            conflicts.append({
                "field": key,
                "scout_value": merged[key],
                "extracted_value": value,
                "resolution": "used_extraction_as_more_recent",
            })
        merged[key] = value

    # Manual overrides always win
    for key, value in overrides.items():
        if key in merged and merged[key] != value and value not in (None, ""):
            conflicts.append({
                "field": key,
                "scout_value": merged.get(key),
                "extracted_value": merged.get(key),
                "resolution": "user_override",
            })
        if value not in (None, ""):
            merged[key] = value

    merged["brand_name"] = state["input"].brand_name
    if state["input"].website_url:
        merged["website_url"] = state["input"].website_url
    merged["source_files"] = [
        fp.split("/")[-1] for fp in state["input"].uploaded_file_paths
    ]

    return {
        "merged_record": merged,
        "conflicts": conflicts,
        "tool_calls": ["merge_reconcile"],
    }


def node_score_completeness(state: OnboardingState) -> dict:
    """Compute % of target schema fields that are populated."""
    merged = state.get("merged_record", {})
    required = list(TARGET_SCHEMA.keys())
    filled = [k for k in required if merged.get(k) not in (None, "", [], {})]
    missing = [k for k in required if k not in filled]
    pct = round(100 * len(filled) / len(required), 1) if required else 0.0

    return {
        "completeness_pct": pct,
        "missing_fields": missing,
        "tool_calls": ["score_completeness"],
    }


def node_persist_and_log(state: OnboardingState) -> dict:
    """Memory: canonical record + append-only event log."""
    merged = dict(state["merged_record"])
    merged["completeness_pct"] = state["completeness_pct"]

    persist_result = tool_persist_brand_record(merged)
    tool_log = [f"persist_brand:{'ok' if persist_result['ok'] else 'fail'}"]

    if not persist_result["ok"]:
        return {
            "tool_calls": tool_log,
            "errors": [f"persist: {persist_result.get('error')}"],
        }

    brand_id = persist_result["brand_id"]
    events_logged: list[str] = []

    tool_append_event(
        brand_id=brand_id,
        event_type="brand_onboarded",
        field_name=None,
        old_value=None,
        new_value={
            "completeness_pct": state["completeness_pct"],
            "source_files": merged.get("source_files", []),
        },
        source="brand_onboarding_agent",
        confidence=state["completeness_pct"] / 100.0,
    )
    events_logged.append("brand_onboarded")

    for c in state.get("conflicts", []):
        tool_append_event(
            brand_id=brand_id,
            event_type="conflict_resolved",
            field_name=c["field"],
            old_value=c.get("scout_value"),
            new_value=c.get("extracted_value"),
            source=c["resolution"],
        )
        events_logged.append(f"conflict:{c['field']}")

    tool_log.append(f"events_logged:{len(events_logged)}")

    return {
        "brand_id": brand_id,
        "events_logged": events_logged,
        "tool_calls": tool_log,
    }


def node_notify_downstream(state: OnboardingState) -> dict:
    """Coordination: write blackboard messages for Matcher and Admin."""
    brand_id = state.get("brand_id")
    if not brand_id:
        return {
            "tool_calls": ["notify_skipped_no_brand_id"],
            "errors": ["cannot_notify: missing brand_id"],
        }

    messages: list[str] = []
    pct = state.get("completeness_pct", 0)
    missing = state.get("missing_fields", [])
    merged = state.get("merged_record", {})

    ready_for_matcher = pct >= 50 and "category" in merged
    ready_for_admin = pct >= 40 and "wholesale_price_range" in merged

    if ready_for_matcher:
        tool_emit_coordination_message(
            from_agent="brand_onboarding",
            to_agent="retailer_matcher",
            brand_id=brand_id,
            message_type="new_brand_onboarded",
            payload={
                "brand_name": merged["brand_name"],
                "category": merged.get("category"),
                "completeness_pct": pct,
            },
        )
        messages.append("matcher_notified")

    if ready_for_admin:
        tool_emit_coordination_message(
            from_agent="brand_onboarding",
            to_agent="admin_ops",
            brand_id=brand_id,
            message_type="brand_ready_for_forms",
            payload={
                "brand_name": merged["brand_name"],
                "wholesale_price_range": merged.get("wholesale_price_range"),
            },
        )
        messages.append("admin_notified")

    if pct >= 50:
        status = "ok"
    elif pct >= 30:
        status = "partial"
    else:
        status = "conflict_unresolved"

    handoff = OnboardingHandoff(
        brand_id=brand_id,
        brand_name=merged["brand_name"],
        completeness_pct=pct,
        missing_fields=missing,
        conflicts=state.get("conflicts", []),
        canonical_record=merged,
        handoff_status=status,
        ready_for_matcher=ready_for_matcher,
        ready_for_admin=ready_for_admin,
    )

    return {
        "handoff": handoff,
        "messages_emitted": messages,
        "tool_calls": [f"notify:{m}" for m in messages],
    }


def build_onboarding_graph():
    g = StateGraph(OnboardingState)
    g.add_node("load_prior_knowledge", node_load_prior_knowledge)
    g.add_node("extract_from_uploads", node_extract_from_uploads)
    g.add_node("merge_and_reconcile", node_merge_and_reconcile)
    g.add_node("score_completeness", node_score_completeness)
    g.add_node("persist_and_log", node_persist_and_log)
    g.add_node("notify_downstream", node_notify_downstream)

    g.set_entry_point("load_prior_knowledge")
    g.add_edge("load_prior_knowledge", "extract_from_uploads")
    g.add_edge("extract_from_uploads", "merge_and_reconcile")
    g.add_edge("merge_and_reconcile", "score_completeness")
    g.add_edge("score_completeness", "persist_and_log")
    g.add_edge("persist_and_log", "notify_downstream")
    g.add_edge("notify_downstream", END)

    return g.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_onboarding_graph()
    return _graph
