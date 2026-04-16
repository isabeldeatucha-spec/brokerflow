"""Retailer Pitcher — LangGraph graph.

Flow:
  load_scout_context
       ↓
  [handoff_status = "miss" or "stale"] ──→ END (no artifacts)
       ↓ "ok"
  select_buyer
       ↓
  draft_email   ┐
                ├─ parallel
  draft_sell_sheet ┘
       ↓
  store_artifacts
       ↓
  human_approval ──[rejected]──→ END
       ↓ [approved]
  mark_sent
       ↓
      END

Coordination contract: Brand Scout writes to Supabase `brand_evaluations`.
Pitcher reads that row. Any lag / race condition surfaces as
`handoff_status = "miss"` (row absent) or `"stale"` (row older than
HANDOFF_FRESHNESS_SECONDS). This is what HW8 E4 measures.
"""
from __future__ import annotations

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import anthropic
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt

from memory import memory, _get_client
from state import RetailerPitcherState
from agents.retailer_pitcher.prompts import (
    EMAIL_SYSTEM,
    EMAIL_USER_TEMPLATE,
    SELL_SHEET_SYSTEM,
    SELL_SHEET_USER_TEMPLATE,
)
from agents.retailer_pitcher.skills.buyer_personas import (
    BUYER_PERSONAS,
    get_persona,
    select_buyer_for_brand,
)
from agents.retailer_pitcher.skills.sell_sheet_template import (
    SellSheetFields,
    render,
)


logger = logging.getLogger(__name__)

HANDOFF_FRESHNESS_SECONDS = 24 * 60 * 60   # beyond this, Scout data is "stale"
MODEL = "claude-haiku-4-5-20251001"


# ── Nodes ────────────────────────────────────────────────────────────────────

def load_scout_context(state: RetailerPitcherState) -> dict:
    """Read the Brand Scout evaluation from shared memory. Detects handoff races."""
    brand_name = state["brand_name"]
    try:
        client = _get_client()
        res = (
            client.table("brand_evaluations")
            .select("*")
            .ilike("brand_name", brand_name)
            .limit(1)
            .execute()
        )
        if not res.data:
            return {
                "handoff_status": "miss",
                "handoff_error": f"No Brand Scout row for {brand_name!r}",
                "scout_context": {},
            }

        row = res.data[0]
        evaluated_at = row.get("evaluated_at", "")
        if evaluated_at:
            try:
                ts = datetime.fromisoformat(evaluated_at.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - ts).total_seconds()
                if age > HANDOFF_FRESHNESS_SECONDS:
                    return {
                        "handoff_status": "stale",
                        "handoff_error": f"Scout row is {int(age/3600)}h old",
                        "scout_context": row,
                    }
            except ValueError:
                pass

        return {"handoff_status": "ok", "handoff_error": None, "scout_context": row}

    except Exception as exc:  # noqa: BLE001
        return {
            "handoff_status": "miss",
            "handoff_error": f"{type(exc).__name__}: {exc}",
            "scout_context": {},
        }


def select_buyer(state: RetailerPitcherState) -> dict:
    """Pick the buyer persona. Honors explicit override; otherwise heuristic."""
    if state.get("buyer_key"):
        return {"buyer_key": state["buyer_key"]}
    ctx = state["scout_context"]
    buyer_key = select_buyer_for_brand(
        category=ctx.get("category", ""),
        score=ctx.get("score", 0),
    )
    return {"buyer_key": buyer_key}


def _claude_call(system: str, user: str) -> tuple[str, int, int]:
    """Single-shot Claude Haiku call. Returns (text, input_tokens, output_tokens)."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = resp.content[0].text if resp.content else ""
    tin = resp.usage.input_tokens
    tout = resp.usage.output_tokens
    return text, tin, tout


def draft_email(state: RetailerPitcherState) -> dict:
    ctx = state["scout_context"]
    persona = get_persona(state["buyer_key"])

    user = EMAIL_USER_TEMPLATE.format(
        brand_name=ctx.get("brand_name", state["brand_name"]),
        category=ctx.get("category", "unknown"),
        score=ctx.get("score", "?"),
        verdict=ctx.get("verdict", "unknown"),
        broker_brief=ctx.get("broker_brief", ""),
        key_gaps=ctx.get("key_gaps", []),
        key_signals=json.dumps(ctx.get("key_signals", {}))[:1500],
        retailer=persona["retailer"],
        buyer_title=persona["buyer_title"],
        cares_about="; ".join(persona["cares_about"]),
        kills_pitch="; ".join(persona["kills_pitch"]),
        proof_points="; ".join(persona["proof_points"]),
        tone=persona["tone"],
    )

    try:
        text, tin, tout = _claude_call(EMAIL_SYSTEM, user)
    except Exception as exc:  # noqa: BLE001
        # Reducers on artifact_errors / *_tokens: return deltas only.
        return {
            "email_subject": "",
            "email_body": "",
            "artifact_errors": [f"email: {type(exc).__name__}: {exc}"],
            "input_tokens": 0,
            "output_tokens": 0,
        }

    subject, body = _split_email(text)
    return {
        "email_subject": subject,
        "email_body": body,
        "input_tokens": tin,
        "output_tokens": tout,
    }


def _split_email(raw: str) -> tuple[str, str]:
    subject = "Introduction from your broker"
    lines = raw.strip().splitlines()
    body_start = 0
    for i, line in enumerate(lines):
        if line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
            body_start = i + 1
            break
    while body_start < len(lines) and not lines[body_start].strip():
        body_start += 1
    return subject[:200], "\n".join(lines[body_start:]).strip()


def draft_sell_sheet(state: RetailerPitcherState) -> dict:
    ctx = state["scout_context"]
    persona = get_persona(state["buyer_key"])

    user = SELL_SHEET_USER_TEMPLATE.format(
        brand_name=ctx.get("brand_name", state["brand_name"]),
        category=ctx.get("category", "unknown"),
        score=ctx.get("score", 0),
        broker_brief=ctx.get("broker_brief", ""),
        key_signals=json.dumps(ctx.get("key_signals", {}))[:1500],
        score_breakdown=json.dumps(ctx.get("score_breakdown", {})),
        retailer=persona["retailer"],
        buyer_title=persona["buyer_title"],
        cares_about="; ".join(persona["cares_about"]),
        proof_points="; ".join(persona["proof_points"]),
    )

    try:
        text, tin, tout = _claude_call(SELL_SHEET_SYSTEM, user)
        payload = _extract_json(text)
    except Exception as exc:  # noqa: BLE001
        return {
            "sell_sheet_html": "",
            "artifact_errors": [f"sell_sheet: {type(exc).__name__}: {exc}"],
            "input_tokens": 0,
            "output_tokens": 0,
        }

    # Pull confirmed retailer names straight from Scout's extracted fields so
    # the badge wall shows concrete evidence, not LLM-generated claims.
    extracted = (ctx.get("score_breakdown", {}) or {}).get("extracted_fields", {}) or {}
    if not extracted:
        extracted = ctx.get("key_signals", {}) or {}
    retailer_flags = [
        ("Whole Foods", extracted.get("whole_foods_confirmed")),
        ("Sprouts",     extracted.get("sprouts_confirmed")),
        ("Target",      extracted.get("target_confirmed")),
        ("Walmart",     extracted.get("walmart_confirmed")),
        ("Costco",      extracted.get("costco_confirmed")),
    ]
    retailer_badges = [name for name, confirmed in retailer_flags if confirmed]

    certifications = extracted.get("certifications") or (
        (ctx.get("key_signals", {}) or {}).get("certifications", [])
    )

    fields: SellSheetFields = {
        "brand_name": ctx.get("brand_name", state["brand_name"]),
        "category": ctx.get("category", "unknown"),
        "buyer_retailer": persona["retailer"],
        "hero_line": payload.get("hero_line", ""),
        "why_now": payload.get("why_now", ""),
        "proof_points": payload.get("proof_points", [])[:4],
        "velocity_label": payload.get("velocity_label", "Data pending"),
        "margin_label": payload.get("margin_label", "Terms on request"),
        "retail_count_label": payload.get(
            "retail_count_label",
            f"{len(retailer_badges)} confirmed banners" if retailer_badges else "DTC-first",
        ),
        "retailers_text": payload.get("retailers_text", ""),
        "retailer_badges": retailer_badges,
        "certifications": certifications or [],
        "category_fit": payload.get("category_fit", ""),
        "next_step": payload.get(
            "next_step",
            f"15-minute call in the next two weeks to review category fit for {persona['retailer']}",
        ),
        "score": ctx.get("score", 0),
    }

    html_doc = render(fields)
    return {
        "sell_sheet_html": html_doc,
        "input_tokens": tin,
        "output_tokens": tout,
    }


def _extract_json(text: str) -> dict[str, Any]:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        preview = (text or "").replace("\n", " ")[:200]
        print(f"[_extract_json] No JSON found. Response preview (first 200 chars): {preview!r}")
        raise ValueError("No JSON object in response")
    return json.loads(text[start:end + 1])


def store_artifacts(state: RetailerPitcherState) -> dict:
    """Persist artifacts to Supabase `retailer_pitches`. Also classifies artifact_status."""
    # artifact_errors has an Annotated reducer, so we return only new deltas.
    existing_errors = state.get("artifact_errors", [])
    has_email = bool(state.get("email_body"))
    has_sheet = bool(state.get("sell_sheet_html"))

    if has_email and has_sheet:
        status = "ok"
    elif has_email or has_sheet:
        status = "partial"
    else:
        status = "failed"

    new_errors: list[str] = []
    try:
        client = _get_client()
        client.table("retailer_pitches").insert({
            "brand_name": state["brand_name"],
            "buyer": BUYER_PERSONAS[state["buyer_key"]]["retailer"],
            "buyer_key": state["buyer_key"],
            "email_subject": state.get("email_subject", ""),
            "email_body": state.get("email_body", ""),
            "sell_sheet_html": state.get("sell_sheet_html", ""),
            "artifact_status": status,
            "artifact_errors": existing_errors,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as exc:  # noqa: BLE001
        new_errors.append(f"store: {type(exc).__name__}: {exc}")
        if status == "ok":
            status = "failed"

    return {"artifact_status": status, "artifact_errors": new_errors}


def human_approval(state: RetailerPitcherState) -> dict:
    decision = interrupt({
        "brand_name": state["brand_name"],
        "buyer": BUYER_PERSONAS[state["buyer_key"]]["retailer"],
        "email_subject": state["email_subject"],
        "email_body": state["email_body"],
        "sell_sheet_html": state["sell_sheet_html"],
    })
    return {
        "approved": decision.get("approved", False),
        "rejection_reason": decision.get("rejection_reason", ""),
    }


def mark_sent(state: RetailerPitcherState) -> dict:
    """Record that broker approved the artifacts. Actual send is out of scope for HW8."""
    return {}


# ── Routing ──────────────────────────────────────────────────────────────────

def _route_after_handoff(state: RetailerPitcherState) -> str:
    return "ok" if state["handoff_status"] == "ok" else "stop"


def _route_after_approval(state: RetailerPitcherState) -> str:
    return "sent" if state.get("approved") else "rejected"


# ── Graph ────────────────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(RetailerPitcherState)

    g.add_node("load_scout_context", load_scout_context)
    g.add_node("select_buyer", select_buyer)
    g.add_node("draft_email", draft_email)
    g.add_node("draft_sell_sheet", draft_sell_sheet)
    g.add_node("store_artifacts", store_artifacts)
    g.add_node("human_approval", human_approval)
    g.add_node("mark_sent", mark_sent)

    g.set_entry_point("load_scout_context")

    g.add_conditional_edges(
        "load_scout_context",
        _route_after_handoff,
        {"ok": "select_buyer", "stop": END},
    )

    g.add_edge("select_buyer", "draft_email")
    g.add_edge("select_buyer", "draft_sell_sheet")
    g.add_edge("draft_email", "store_artifacts")
    g.add_edge("draft_sell_sheet", "store_artifacts")

    g.add_conditional_edges(
        "human_approval",
        _route_after_approval,
        {"sent": "mark_sent", "rejected": END},
    )
    g.add_edge("store_artifacts", "human_approval")
    g.add_edge("mark_sent", END)

    return g.compile(checkpointer=memory)


graph = build_graph()


# ── Direct run helper (used by hw8/modal_handoff.py) ─────────────────────────

def run_pitch_once(brand_name: str, auto_approve: bool = True) -> dict:
    """Invoke the Pitcher graph for one brand and return a flat telemetry dict."""
    import uuid
    from langgraph.types import Command
    from memory import get_config

    thread_id = str(uuid.uuid4())
    config = get_config(thread_id)
    initial: RetailerPitcherState = {
        "brand_name": brand_name,
        "buyer_key": "",
        "scout_context": {},
        "handoff_status": "",
        "handoff_error": None,
        "email_subject": "",
        "email_body": "",
        "sell_sheet_html": "",
        "artifact_status": "",
        "artifact_errors": [],
        "input_tokens": 0,
        "output_tokens": 0,
        "approved": None,
        "rejection_reason": None,
    }

    t0 = time.time()
    final_state: dict = {}

    try:
        for _chunk in graph.stream(initial, config=config, stream_mode="updates"):
            snap = graph.get_state(config)
            if snap.next and "human_approval" in snap.next:
                if auto_approve:
                    graph.invoke(
                        Command(resume={"approved": True, "rejection_reason": ""}),
                        config=config,
                    )
                break
        final_state = graph.get_state(config).values
    except Exception as exc:  # noqa: BLE001
        final_state = {"artifact_status": "failed",
                       "artifact_errors": [f"{type(exc).__name__}: {exc}"]}

    return {
        "brand_name": brand_name,
        "buyer_key": final_state.get("buyer_key", ""),
        "handoff_status": final_state.get("handoff_status", "unknown"),
        "handoff_error": final_state.get("handoff_error"),
        "artifact_status": final_state.get("artifact_status", "unknown"),
        "artifact_errors": final_state.get("artifact_errors", []),
        "email_chars": len(final_state.get("email_body", "")),
        "sell_sheet_chars": len(final_state.get("sell_sheet_html", "")),
        "input_tokens": final_state.get("input_tokens", 0),
        "output_tokens": final_state.get("output_tokens", 0),
        "latency_s": round(time.time() - t0, 2),
    }
