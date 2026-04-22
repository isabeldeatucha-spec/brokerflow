"""Tools the Onboarding Agent uses. Each is a distinct external capability."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


def tool_parse_uploaded_file(file_path: str) -> dict:
    """TOOL 1: Extract text from uploaded brand materials (PDF, DOCX, CSV)."""
    path = Path(file_path)
    if not path.exists():
        return {"ok": False, "error": f"File not found: {file_path}"}

    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(path))
                text = "\n".join(p.extract_text() or "" for p in reader.pages)
            except ImportError:
                return {"ok": False, "error": "pypdf not installed"}
        elif ext == ".docx":
            try:
                import docx
                doc = docx.Document(str(path))
                text = "\n".join(p.text for p in doc.paragraphs)
            except ImportError:
                return {"ok": False, "error": "python-docx not installed"}
        elif ext in (".csv", ".txt", ".md"):
            text = path.read_text(errors="replace")
        else:
            return {"ok": False, "error": f"Unsupported extension: {ext}"}
        return {"ok": True, "text": text[:40000], "source": path.name}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_fetch_scout_evaluation(brand_name: str) -> Optional[dict]:
    """TOOL 2: Read prior knowledge from Brand Scout's output."""
    from memory import _get_client
    client = _get_client()
    result = (
        client.table("brand_evaluations")
        .select("*")
        .ilike("brand_name", brand_name)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def tool_llm_extract_structured(
    raw_text: str, target_schema: dict, brand_name: str
) -> dict:
    """TOOL 3: LLM-powered structured extraction."""
    import agents.llm_shim  # noqa: F401
    import anthropic

    prompt = f"""You are extracting structured data about a CPG brand for a
broker's onboarding record.

Brand name: {brand_name}

Source text (from uploaded materials):
---
{raw_text[:30000]}
---

Extract the following fields. Return ONLY valid JSON matching this schema.
Use null for any field you cannot determine with confidence. Do not guess.

Schema:
{json.dumps(target_schema, indent=2)}

Return JSON only. No markdown fences, no commentary."""

    try:
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = ""
        for block in msg.content:
            if hasattr(block, "text"):
                text += block.text
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip("` \n")
        return {"ok": True, "fields": json.loads(text)}
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"JSON parse: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


_VALID_BRAND_COLUMNS = {
    "brand_name", "website_url", "category", "subcategory", "founded_year",
    "hq_city", "hq_state", "founder_name", "founder_email", "product_count",
    "flagship_sku", "wholesale_price_range", "retail_price_range", "margin_range",
    "distributor_list", "current_retailers", "target_retailers", "certifications",
    "brand_story", "key_differentiators", "completeness_pct", "source_files",
    "is_sandbox", "last_verified_at", "status", "unit_velocity_range",
    "slotting_fees_paid", "best_seller_sku", "products",
}

_BRAND_FIELD_REMAP = {
    "brand_description": "brand_story",
    "distributor":       "distributor_list",
    "hero_sku":          "flagship_sku",
    "srp_range":         "retail_price_range",
    "wholesale_price":   "wholesale_price_range",
}

_ARRAY_BRAND_COLUMNS = {
    "distributor_list", "current_retailers", "target_retailers",
    "certifications", "key_differentiators", "source_files",
}


def _coerce_brand_field(key: str, value):
    if key in _ARRAY_BRAND_COLUMNS:
        if isinstance(value, list):
            return value
        if isinstance(value, str) and value.strip():
            return [v.strip() for v in value.split(",") if v.strip()]
        return []
    return value


def tool_persist_brand_record(record: dict) -> dict:
    """TOOL 4: Upsert canonical brand record to Supabase."""
    remapped = {_BRAND_FIELD_REMAP.get(k, k): v for k, v in record.items()}
    clean = {
        k: _coerce_brand_field(k, v)
        for k, v in remapped.items()
        if k in _VALID_BRAND_COLUMNS
    }
    from memory import _get_client
    client = _get_client()
    try:
        result = (
            client.table("brands")
            .upsert(clean, on_conflict="brand_name")
            .execute()
        )
        return {"ok": True, "brand_id": result.data[0]["id"]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_append_event(
    brand_id: str, event_type: str, field_name: Optional[str],
    old_value, new_value, source: str, confidence: Optional[float] = None
) -> dict:
    """TOOL 5: Append-only event log write. This is the memory primitive."""
    from memory import _get_client
    client = _get_client()
    try:
        client.table("brand_events").insert({
            "brand_id": brand_id,
            "event_type": event_type,
            "field_name": field_name,
            "old_value": old_value,
            "new_value": new_value,
            "source": source,
            "confidence": confidence,
        }).execute()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_read_event_history(brand_id: str, limit: int = 50) -> list:
    """TOOL 6: Read prior events for a brand (memory read)."""
    from memory import _get_client
    client = _get_client()
    result = (
        client.table("brand_events")
        .select("*")
        .eq("brand_id", brand_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def tool_emit_coordination_message(
    from_agent: str, to_agent: str, brand_id: str,
    message_type: str, payload: dict
) -> dict:
    """TOOL 7: Write a message to the coordination blackboard."""
    from memory import _get_client
    client = _get_client()
    try:
        client.table("coordination_messages").insert({
            "from_agent": from_agent,
            "to_agent": to_agent,
            "brand_id": brand_id,
            "message_type": message_type,
            "payload": payload,
        }).execute()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
