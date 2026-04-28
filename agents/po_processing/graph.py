"""PO Processing — LangGraph agent.

Flow:
  load_brand_pricing
       ↓
  generate_synthetic_po       (LLM: realistic PO for the brand × Whole Foods)
       ↓
  validate_pricing            (compares PO line-item prices to brand wholesale range)
       ↓
  decide_outcome              (confirm if within tolerance, dispute if not)
       ↓
  publish_outcome             (writes typed coord event)
       ↓
      END

This is intentionally medium-depth: real LLM call to make the PO realistic,
real validation against the canonical brand record. Real EDI/email parsing
remains on the Q2 roadmap.
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, TypedDict

import anthropic
from langgraph.graph import StateGraph, END

from agents.coordination.protocol import EventType, publish
from memory import _get_client


logger = logging.getLogger("sedge.po_processing")
MODEL = "claude-haiku-4-5-20251001"
DISPUTE_TOLERANCE_PCT = 5.0  # PO unit cost may not deviate >5% from agreed wholesale


class POState(TypedDict, total=False):
    brand_id:      str
    brand_name:    str
    brand_pricing: dict       # {wholesale_low, wholesale_high, flagship_sku, ...}
    po_data:       dict       # {po_number, retailer, line_items: [...], total}
    validation:    dict       # {ok, issues, severity}
    outcome:       str        # "confirmed" | "dispute_needed" | "skipped"
    errors:        list


# ── Helpers ─────────────────────────────────────────────────────────────────

def _parse_dollar_range(rng: str) -> tuple[Optional[float], Optional[float]]:
    """Parse '$2.50-$3.00' or '$42/case of 6' into (low, high) USD."""
    if not rng:
        return None, None
    nums = re.findall(r"\d+(?:\.\d+)?", rng.replace(",", ""))
    if not nums:
        return None, None
    vals = [float(n) for n in nums]
    if len(vals) == 1:
        return vals[0], vals[0]
    return min(vals), max(vals)


# ── Nodes ───────────────────────────────────────────────────────────────────

def load_brand_pricing(state: POState) -> dict:
    """Look up the brand's canonical wholesale price + flagship SKU."""
    brand_name = state["brand_name"]
    try:
        client = _get_client()
        res = (
            client.table("brands")
            .select("id, brand_name, wholesale_price_range, retail_price_range, "
                    "flagship_sku, products, current_retailers, category")
            .ilike("brand_name", brand_name)
            .limit(1)
            .execute()
        )
        if not res.data:
            return {
                "brand_pricing": {},
                "errors":        [f"brand_not_found: {brand_name}"],
            }
        row = res.data[0]
        wlow, whigh = _parse_dollar_range(row.get("wholesale_price_range") or "")

        # Pull flagship product details from the JSONB products array if present
        products = row.get("products") or []
        flagship = next((p for p in products if p.get("is_flagship")), products[0] if products else {})

        pricing = {
            "brand_id":         row["id"],
            "wholesale_low":    wlow,
            "wholesale_high":   whigh,
            "flagship_sku":     flagship.get("sku_name") or row.get("flagship_sku") or f"{brand_name} Hero SKU",
            "flagship_cost":    flagship.get("wholesale_cost"),
            "flagship_msrp":    flagship.get("msrp"),
            "case_pack":        flagship.get("case_pack") or 12,
            "category":         row.get("category", ""),
        }
        return {
            "brand_id":      row["id"],
            "brand_pricing": pricing,
        }
    except Exception as exc:
        return {"errors": [f"load_brand_pricing: {type(exc).__name__}: {exc}"]}


def _fallback_po(brand_name: str, pricing: dict) -> dict:
    """Deterministic synthetic PO when the LLM is unavailable. Demo never stalls."""
    import random
    random.seed(hash(brand_name) % (2**31))
    flagship_sku = pricing.get("flagship_sku", f"{brand_name} Hero SKU")
    cost         = pricing.get("flagship_cost") or pricing.get("wholesale_high") or 3.50
    case_pack    = pricing.get("case_pack") or 12
    cases        = random.randint(15, 40)
    # Inject a small price discrepancy 30% of the time so disputes are demoable
    actual_cost  = round(cost * (1 + random.choice([0, 0, 0.04, 0.09]) * random.choice([-1, 1])), 2)
    extended     = round(case_pack * cases * actual_cost, 2)
    po_number    = f"WFM-{datetime.now(timezone.utc).strftime('%Y%m')}-{random.randint(1000, 9999)}"
    return {
        "po_number":     po_number,
        "retailer":      "Whole Foods Market",
        "po_date":       datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "delivery_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "line_items": [{
            "sku_name":      flagship_sku,
            "upc":           "0" * 12,
            "case_pack":     case_pack,
            "cases_ordered": cases,
            "unit_cost":     actual_cost,
            "extended_cost": extended,
        }],
        "total_cases":   cases,
        "total_dollars": extended,
        "_source":       "fallback_synthetic",
    }


def generate_synthetic_po(state: POState) -> dict:
    """Use Claude to draft a realistic PO from Whole Foods for this brand."""
    pricing = state.get("brand_pricing") or {}
    if not pricing:
        return {"po_data": {}, "errors": (state.get("errors") or [])
                + ["po_generation_skipped: no_pricing"]}

    brand_name   = state["brand_name"]
    flagship_sku = pricing.get("flagship_sku", "Hero SKU")
    cost         = pricing.get("flagship_cost") or pricing.get("wholesale_high") or 3.50
    case_pack    = pricing.get("case_pack") or 12

    user_prompt = f"""Generate a realistic Purchase Order from Whole Foods Market
for the CPG brand {brand_name!r}.

Use this canonical brand data:
- Flagship SKU: {flagship_sku}
- Agreed wholesale unit cost: ${cost}
- Case pack: {case_pack} units/case

Generate 1-3 line items. For ONE of them, simulate a realistic real-world
issue 30% of the time — pick exactly one of:
  - Slightly off unit cost (within 3-7% of agreed) due to outdated cost sheet
  - A price more than 8% off (would need a dispute)
  - A wrong UPC that needs correction

For the other line items, use the agreed price exactly.

Return ONLY valid JSON. No markdown fences, no commentary. Schema:
{{
  "po_number":  "string (e.g. WFM-2026-04-1234)",
  "retailer":   "Whole Foods Market",
  "po_date":    "YYYY-MM-DD",
  "delivery_date": "YYYY-MM-DD",
  "line_items": [
    {{
      "sku_name":     "string",
      "upc":          "string (12-digit)",
      "case_pack":    {case_pack},
      "cases_ordered": <int 5-50>,
      "unit_cost":    <float>,
      "extended_cost": <float, = case_pack * cases_ordered * unit_cost>
    }}
  ],
  "total_cases":   <int>,
  "total_dollars": <float>
}}"""

    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system="You generate realistic CPG purchase order JSON. Return JSON only.",
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = resp.content[0].text if resp.content else ""
        text = text.strip()
        # Strip code fences if Claude added them
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip("` \n")
        po = json.loads(text)
        return {"po_data": po}
    except json.JSONDecodeError as exc:
        # LLM returned malformed JSON — fall back to deterministic synthetic PO
        return {
            "po_data": _fallback_po(brand_name, pricing),
            "errors":  (state.get("errors") or []) + [f"po_json_parse_fallback: {exc}"],
        }
    except Exception as exc:
        # LLM call itself failed (auth, network, etc.) — fall back so chain continues
        return {
            "po_data": _fallback_po(brand_name, pricing),
            "errors":  (state.get("errors") or []) + [f"po_llm_fallback: {type(exc).__name__}"],
        }


def validate_pricing(state: POState) -> dict:
    """Compare each line item's unit cost to the agreed wholesale range."""
    pricing = state.get("brand_pricing") or {}
    po      = state.get("po_data") or {}

    if not po or not po.get("line_items"):
        return {"validation": {"ok": False, "issues": ["empty_po"], "severity": "error"}}

    agreed = pricing.get("flagship_cost") or pricing.get("wholesale_high")
    if not agreed:
        return {"validation": {"ok": True, "issues": ["no_agreed_price_to_compare"], "severity": "info"}}

    issues: list[dict] = []
    for li in po["line_items"]:
        unit_cost = float(li.get("unit_cost") or 0)
        if not unit_cost:
            continue
        deviation_pct = abs(unit_cost - agreed) / agreed * 100
        if deviation_pct > DISPUTE_TOLERANCE_PCT:
            issues.append({
                "sku_name":      li.get("sku_name"),
                "po_unit_cost":  unit_cost,
                "agreed_cost":   agreed,
                "deviation_pct": round(deviation_pct, 2),
                "severity":      "dispute" if deviation_pct > 8 else "review",
            })

    overall_severity = "ok"
    if any(i["severity"] == "dispute" for i in issues):
        overall_severity = "dispute"
    elif any(i["severity"] == "review" for i in issues):
        overall_severity = "review"

    return {
        "validation": {
            "ok":              overall_severity == "ok",
            "issues":          issues,
            "severity":        overall_severity,
            "agreed_cost":     agreed,
            "tolerance_pct":   DISPUTE_TOLERANCE_PCT,
        },
    }


def decide_outcome(state: POState) -> dict:
    """Decide whether to confirm the PO or kick it to dispute."""
    val = state.get("validation") or {}
    sev = val.get("severity", "ok")
    if sev == "dispute":
        return {"outcome": "dispute_needed"}
    if sev == "review":
        return {"outcome": "review_needed"}
    return {"outcome": "confirmed"}


def publish_outcome(state: POState) -> dict:
    """Emit a typed coordination event with the PO outcome."""
    brand_id   = state.get("brand_id", "") or ""
    brand_name = state.get("brand_name", "?")
    po         = state.get("po_data") or {}
    val        = state.get("validation") or {}
    outcome    = state.get("outcome", "confirmed")

    if not brand_id:
        return state

    # NOTE: We do NOT republish PO_RECEIVED here — that would re-trigger this
    # handler in the dispatch loop. PO_RECEIVED is the *input* event; this
    # node only emits the *outcome* (PO_VALIDATED or PO_DISPUTE_NEEDED).

    if outcome == "confirmed":
        publish(
            from_agent="po_processing",
            to_agent="user",
            brand_id=brand_id,
            event_type=EventType.PO_VALIDATED,
            payload={
                "brand_name":    brand_name,
                "po_number":     po.get("po_number"),
                "total_dollars": po.get("total_dollars"),
                "agreed_cost":   val.get("agreed_cost"),
                "action_label":  f"PO {po.get('po_number','?')} validated — pricing matches agreed cost",
                "agent_status":  "completed",
            },
        )
    else:
        publish(
            from_agent="po_processing",
            to_agent="user",
            brand_id=brand_id,
            event_type=EventType.PO_DISPUTE_NEEDED,
            payload={
                "brand_name":            brand_name,
                "po_number":             po.get("po_number"),
                "issues":                val.get("issues", []),
                "agreed_cost":           val.get("agreed_cost"),
                "tolerance_pct":         val.get("tolerance_pct"),
                "pending_review_count":  len(val.get("issues", [])),
                "action_label":          f"PO {po.get('po_number','?')} flagged: "
                                          f"{len(val.get('issues',[]))} pricing discrepancy(ies)",
                "agent_status":          "awaiting_review",
            },
        )

    return state


# ── Graph build ─────────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(POState)
    g.add_node("load_brand_pricing",     load_brand_pricing)
    g.add_node("generate_synthetic_po",  generate_synthetic_po)
    g.add_node("validate_pricing",       validate_pricing)
    g.add_node("decide_outcome",         decide_outcome)
    g.add_node("publish_outcome",        publish_outcome)

    g.set_entry_point("load_brand_pricing")
    g.add_edge("load_brand_pricing",    "generate_synthetic_po")
    g.add_edge("generate_synthetic_po", "validate_pricing")
    g.add_edge("validate_pricing",      "decide_outcome")
    g.add_edge("decide_outcome",        "publish_outcome")
    g.add_edge("publish_outcome", END)
    return g.compile()


_graph = None
def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_po_processing(brand_name: str) -> dict:
    """Run the PO Processing graph end-to-end for one brand."""
    initial: POState = {"brand_name": brand_name}
    final_state: dict = {}
    for chunk in get_graph().stream(initial):
        for v in chunk.values():
            final_state.update(v)
    return final_state
