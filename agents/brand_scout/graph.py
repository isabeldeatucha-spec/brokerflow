"""
Brand Scout — LangGraph graph definition.

Flow:
  discover_brands
       ↓
  research_brand ←──────────────────┐
       ↓                            │ (if critical gaps, max 2x)
  reflect_and_decide ───────────────┘
       ↓ (no critical gaps or limit reached)
  detect_category_node
       ↓
  score_brand ──[below_threshold]──→ END
       ↓ [above_threshold]
  store_memory
       ↓
  draft_outreach
       ↓
  human_approval ──[rejected]──→ END
       ↓ [approved]
  send_email
       ↓
      END
"""
import json
import os

import anthropic
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt, Command

from sedge.state import BrandScoutState, ScoreBreakdown
from sedge.memory import memory, get_config, store_brand_evaluation, retrieve_similar_brands, retrieve_brand_history
from sedge.agents.brand_scout.prompts import SCORE_THRESHOLDS, SCORING_PROMPT, DRAFT_PROMPT, REFLECTION_PROMPT
from sedge.agents.brand_scout.tools import (
    scrape_whole_foods_new_arrivals,
    scrape_target_new_arrivals,
    scrape_walmart_new_arrivals,
    scrape_sprouts_new_arrivals,
    scrape_brand_website,
    scrape_amazon_listing,
    scrape_faire_listing,
    search,
    search_velocity_signals,
    search_press_and_story,
    search_funding_and_team,
    find_founder_contact,
    send_email,
)
from sedge.agents.brand_scout.skills.category_benchmarks import detect_category, get_benchmark


# ── Nodes ─────────────────────────────────────────────────────────────────────

def discover_brands(state: BrandScoutState) -> dict:
    """Search retailer new-arrivals via Tavily and return deduplicated brand list."""
    cli_brand_early = state.get("brand_name", "")
    found: list[dict] = []
    found.extend(scrape_whole_foods_new_arrivals(brand_name=cli_brand_early))
    found.extend(scrape_target_new_arrivals(brand_name=cli_brand_early))
    found.extend(scrape_walmart_new_arrivals())
    found.extend(scrape_sprouts_new_arrivals(brand_name=cli_brand_early))

    valid: list[dict] = []
    seen_names: set[str] = set()
    for b in found:
        if "error" in b or not b.get("brand_name"):
            continue
        key = b["brand_name"].lower()
        if key not in seen_names:
            seen_names.add(key)
            valid.append(b)

    errors = [b for b in found if "error" in b]

    cli_brand = cli_brand_early
    cli_url = state.get("website_url", "")
    if cli_brand:
        return {
            "brand_name": cli_brand,
            "website_url": cli_url,
            "sources_checked": ["whole_foods", "target", "sprouts"],
            "signals_found": {"discovery": valid, "discovery_errors": errors},
            "follow_up_queries": [],
            "reflection_count": 0,
            "reflection_notes": [],
            "category": "",
            "benchmark": {},
        }

    if not valid:
        return {
            "brand_name": "Unknown Brand",
            "website_url": "",
            "sources_checked": ["whole_foods", "target", "sprouts"],
            "signals_found": {"discovery_errors": errors},
            "follow_up_queries": [],
            "reflection_count": 0,
            "reflection_notes": [],
            "category": "",
            "benchmark": {},
        }

    brand = valid[0]
    return {
        "brand_name": brand["brand_name"],
        "website_url": brand.get("website_url", ""),
        "sources_checked": ["whole_foods", "target", "sprouts"],
        "signals_found": {"discovery": valid, "discovery_errors": errors},
        "follow_up_queries": [],
        "reflection_count": 0,
        "reflection_notes": [],
        "category": "",
        "benchmark": {},
    }


def research_brand(state: BrandScoutState) -> dict:
    """Pull signals from all sources. On follow-up loops, also run specific queries."""
    brand_name = state["brand_name"]
    website_url = state["website_url"]
    existing_signals = state.get("signals_found", {})

    # Check brand history in Mem0 on first pass only
    brand_history = ""
    if state.get("reflection_count", 0) == 0:
        brand_history = retrieve_brand_history(brand_name)

    website_data = scrape_brand_website(website_url)
    amazon_data = scrape_amazon_listing(brand_name)
    faire_data = scrape_faire_listing(brand_name)
    velocity_data = search_velocity_signals(brand_name)
    press_data = search_press_and_story(brand_name)
    funding_data = search_funding_and_team(brand_name)

    # On reflection follow-up loops, run the specific queries the agent requested
    follow_up_results: dict = {}
    for query in state.get("follow_up_queries", []):
        results = search(query, max_results=5)
        follow_up_results[query] = [
            {"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content", "")[:300]}
            for r in results if "error" not in r
        ]

    new_signals = {
        **existing_signals,
        "website": website_data,
        "amazon": amazon_data,
        "faire": faire_data,
        "velocity": velocity_data,
        "press": press_data,
        "funding": funding_data,
    }
    if brand_history:
        new_signals["brand_history"] = brand_history
    if follow_up_results:
        new_signals["follow_up_research"] = follow_up_results

    return {
        "sources_checked": state.get("sources_checked", []) + [
            "website", "amazon", "faire", "spins_instacart", "press", "funding"
        ],
        "signals_found": new_signals,
        "follow_up_queries": [],  # clear after executing
    }


def reflect_and_decide(state: BrandScoutState) -> dict:
    """
    ReAct reflection node: review signals collected, identify critical gaps,
    decide whether to loop back for targeted follow-up or proceed to scoring.
    Max 2 reflection loops.
    """
    reflection_count = state.get("reflection_count", 0)

    # Always proceed after 2 loops regardless of gaps
    if reflection_count >= 2:
        notes = state.get("reflection_notes", [])
        return {
            "reflection_notes": notes + ["Reflection limit reached (2/2) — proceeding to score with available data."],
            "follow_up_queries": [],
        }

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    prompt = REFLECTION_PROMPT.format(
        brand_name=state["brand_name"],
        website_url=state["website_url"],
        reflection_count=reflection_count + 1,
        signals_json=json.dumps(state["signals_found"], indent=2),
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw)

    notes = state.get("reflection_notes", [])
    reasoning = data.get("reasoning", "")
    contradictions = data.get("contradictions_found", [])
    gaps = data.get("critical_gaps", [])

    note = reasoning
    if contradictions:
        note += f" | Contradictions: {'; '.join(contradictions)}"
    if gaps:
        note += f" | Critical gaps: {'; '.join(gaps)}"

    follow_up = data.get("follow_up_queries", []) if data.get("should_dig_deeper") else []

    return {
        "reflection_count": reflection_count + 1,
        "reflection_notes": notes + [note],
        "follow_up_queries": follow_up,
    }


def detect_category_node(state: BrandScoutState) -> dict:
    """Detect product category and load benchmark — runs once before scoring."""
    category = detect_category(state["brand_name"], state["signals_found"])
    benchmark = get_benchmark(category)
    return {"category": category, "benchmark": benchmark}


def score_brand(state: BrandScoutState) -> dict:
    """Score broker-readiness using Claude with category context and memory comparables."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    category = state.get("category", "unknown")
    benchmark = state.get("benchmark", {})

    # Pull comparable brands from Mem0 for context
    score_estimate = 50  # rough midpoint before we know the real score
    comparable_brands = retrieve_similar_brands(category, (score_estimate - 15, score_estimate + 15))

    prompt = SCORING_PROMPT.format(
        brand_name=state["brand_name"],
        website_url=state["website_url"],
        category=category,
        category_benchmark_json=json.dumps(benchmark, indent=2),
        comparable_brands=comparable_brands or "No comparable brands evaluated yet.",
        signals_json=json.dumps(state["signals_found"], indent=2),
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw)

    def _extract_score(key: str) -> int:
        val = data[key]
        return val["score"] if isinstance(val, dict) else int(val)

    score: ScoreBreakdown = {
        "velocity_proof": _extract_score("velocity_proof"),
        "distribution_density": _extract_score("distribution_density"),
        "margin_viability": _extract_score("margin_viability"),
        "brand_story_clarity": _extract_score("brand_story_clarity"),
        "promotional_independence": _extract_score("promotional_independence"),
        "total": data["total"],
    }

    total = score["total"]
    if total >= SCORE_THRESHOLDS["broker_ready"]:
        graph_verdict = "above_threshold"
    elif total >= SCORE_THRESHOLDS["promising"]:
        graph_verdict = "promising"
    else:
        graph_verdict = "below_threshold"

    return {
        "score": score,
        "verdict": graph_verdict,
        "signals_found": {
            **state.get("signals_found", {}),
            "score_detail": data,
        },
    }


def store_memory_node(state: BrandScoutState) -> dict:
    """Persist this evaluation to Mem0 for future cross-run comparisons."""
    detail = state.get("signals_found", {}).get("score_detail", {})
    key_gaps = detail.get("key_gaps", [])

    key_signals = {
        "amazon_reviews": state.get("signals_found", {}).get("amazon", {}).get("review_count"),
        "amazon_rating": state.get("signals_found", {}).get("amazon", {}).get("average_rating"),
        "price_range": state.get("signals_found", {}).get("website", {}).get("price_range"),
        "retail_partners": state.get("signals_found", {}).get("website", {}).get("retail_partners"),
        "trade_press_hits": len(state.get("signals_found", {}).get("press", {}).get("trade_press_hits", [])),
    }

    store_brand_evaluation(
        brand_name=state["brand_name"],
        score=state["score"]["total"],
        verdict=detail.get("verdict", state.get("verdict", "")),
        category=state.get("category", "unknown"),
        key_signals=key_signals,
        key_gaps=key_gaps,
    )
    return {}  # no state changes — memory is a side effect


def draft_outreach(state: BrandScoutState) -> dict:
    """Find founder contact and draft a personalized outreach email using Claude."""
    contact = find_founder_contact(state["brand_name"], state["website_url"])
    founder_name = contact["founder_name"]
    founder_email = contact["founder_email"]

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    score = state["score"]

    prompt = DRAFT_PROMPT.format(
        brand_name=state["brand_name"],
        founder_name=founder_name,
        total=score["total"],
        velocity_proof=score["velocity_proof"],
        distribution_density=score["distribution_density"],
        margin_viability=score["margin_viability"],
        brand_story_clarity=score["brand_story_clarity"],
        promotional_independence=score["promotional_independence"],
        signals_json=json.dumps(state["signals_found"], indent=2),
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    return {
        "founder_name": founder_name,
        "founder_email": founder_email,
        "email_draft": message.content[0].text.strip(),
    }


def human_approval(state: BrandScoutState) -> dict:
    """Pause the graph for broker review."""
    decision = interrupt(
        {
            "brand_name": state["brand_name"],
            "score": state["score"],
            "signals_found": state["signals_found"],
            "founder_name": state["founder_name"],
            "founder_email": state["founder_email"],
            "email_draft": state["email_draft"],
        }
    )
    return {
        "approved": decision.get("approved", False),
        "rejection_reason": decision.get("rejection_reason", ""),
    }


def send_email_node(state: BrandScoutState) -> dict:
    """Send the approved outreach email."""
    lines = state["email_draft"].strip().splitlines()
    subject = "Introduction from your broker"
    body_start = 0

    for i, line in enumerate(lines):
        if line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
            body_start = i + 1
            break

    while body_start < len(lines) and not lines[body_start].strip():
        body_start += 1

    body = "\n".join(lines[body_start:])
    result = send_email(to=state["founder_email"], subject=subject, body=body)
    return {"signals_found": {**state["signals_found"], "email_send_result": result}}


# ── Routing ───────────────────────────────────────────────────────────────────

def _route_after_reflect(state: BrandScoutState) -> str:
    """Loop back to research if the agent identified critical gaps; otherwise score."""
    queries = state.get("follow_up_queries", [])
    if queries:
        return "research_brand"
    return "detect_category_node"


def _route_after_score(state: BrandScoutState) -> str:
    return state["verdict"]


def _route_after_approval(state: BrandScoutState) -> str:
    return "send_email" if state.get("approved") else "rejected"


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_graph():
    builder = StateGraph(BrandScoutState)

    builder.add_node("discover_brands", discover_brands)
    builder.add_node("research_brand", research_brand)
    builder.add_node("reflect_and_decide", reflect_and_decide)
    builder.add_node("detect_category_node", detect_category_node)
    builder.add_node("score_brand", score_brand)
    builder.add_node("store_memory", store_memory_node)
    builder.add_node("draft_outreach", draft_outreach)
    builder.add_node("human_approval", human_approval)
    builder.add_node("send_email", send_email_node)

    builder.set_entry_point("discover_brands")
    builder.add_edge("discover_brands", "research_brand")
    builder.add_edge("research_brand", "reflect_and_decide")

    builder.add_conditional_edges(
        "reflect_and_decide",
        _route_after_reflect,
        {"research_brand": "research_brand", "detect_category_node": "detect_category_node"},
    )

    builder.add_edge("detect_category_node", "score_brand")
    builder.add_edge("score_brand", "store_memory")

    builder.add_conditional_edges(
        "store_memory",
        _route_after_score,
        {"above_threshold": "draft_outreach", "promising": END, "below_threshold": END},
    )

    builder.add_edge("draft_outreach", "human_approval")

    builder.add_conditional_edges(
        "human_approval",
        _route_after_approval,
        {"send_email": "send_email", "rejected": END},
    )

    builder.add_edge("send_email", END)

    return builder.compile(checkpointer=memory)


graph = build_graph()
