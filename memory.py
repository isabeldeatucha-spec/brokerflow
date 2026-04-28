"""
Memory layer for all BrokerFlow agents.

Two distinct systems:
  1. LangGraph checkpointer (MemorySaver) — in-process thread state for graph interrupts.
  2. Supabase persistent memory — cross-run brand evaluation history.
"""
import os
from datetime import datetime

from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from supabase import create_client, Client

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ── LangGraph checkpointer ────────────────────────────────────────────────────

memory = MemorySaver()


def get_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


# ── Supabase ──────────────────────────────────────────────────────────────────

def _get_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError(f"Missing credentials — SUPABASE_URL={url!r} SUPABASE_KEY={'set' if key else 'NOT SET'}")
    return create_client(url, key)


def store_brand_evaluation(
    brand_name: str,
    score: int,
    verdict: str,
    category: str,
    key_signals: dict,
    key_gaps: list,
    broker_brief: str = "",
    score_breakdown: dict = {},
    reflection_notes: list = [],
    email_draft: str = "",
    founder_name: str = "",
    founder_email: str = "",
) -> None:
    brand_name = brand_name.strip().title()
    # Extract subject line from email draft if present
    email_subject = ""
    if email_draft:
        for line in email_draft.split("\n"):
            if line.lower().startswith("subject:"):
                email_subject = line.split(":", 1)[-1].strip()
                break
    try:
        client = _get_client()
        client.table("brand_evaluations").upsert({
            "brand_name":       brand_name,
            "score":            score,
            "verdict":          verdict,
            "category":         category,
            "key_gaps":         key_gaps,
            "key_signals":      key_signals,
            "broker_brief":     broker_brief,
            "score_breakdown":  score_breakdown,
            "reflection_notes": reflection_notes,
            "email_draft":      email_draft,
            "email_subject":    email_subject,
            "founder_name":     founder_name,
            "founder_email":    founder_email,
            "evaluated_at":     datetime.now().isoformat(),
        }, on_conflict="brand_name").execute()
        print(f"[Memory] Stored {brand_name} {score}/100 to Supabase")
    except Exception as e:
        print(f"[Memory] Store failed: {e}")


def retrieve_all_evaluations() -> list:
    try:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        print(f"[Memory] SUPABASE_URL set: {bool(url)}, SUPABASE_KEY set: {bool(key)}")
        client = _get_client()
        result = (
            client.table("brand_evaluations")
            .select("brand_name, score, verdict, category, evaluated_at")
            .order("score", desc=True)
            .limit(20)
            .execute()
        )
        print(f"[Memory] Retrieved {len(result.data or [])} evaluations")
        return result.data or []
    except Exception as e:
        print(f"[Memory] retrieve_all_evaluations failed: {e}")
        return []


def retrieve_brand_history(brand_name: str) -> str:
    try:
        client = _get_client()
        result = (
            client.table("brand_evaluations")
            .select("*")
            .ilike("brand_name", brand_name)
            .limit(1)
            .execute()
        )
        if result.data:
            item = result.data[0]
            return (
                f"Previously evaluated on {item['evaluated_at'][:10]} — "
                f"Score: {item['score']}/100, Verdict: {item['verdict']}"
            )
        return ""
    except Exception as e:
        print(f"[Memory] History lookup failed: {e}")
        return ""


def store_new_item_form(
    brand_name: str,
    retailer: str,
    filled_fields: dict,
    field_confidence: dict,
    field_sources: dict,
    gaps: list,
    output_xlsx_path: str,
    output_status: str,
) -> None:
    try:
        client = _get_client()
        client.table("new_item_forms").upsert({
            "brand_name":       brand_name.strip().title(),
            "retailer":         retailer,
            "filled_fields":    filled_fields,
            "field_confidence": field_confidence,
            "field_sources":    field_sources,
            "gaps":             gaps,
            "output_xlsx_path": output_xlsx_path,
            "output_status":    output_status,
            "generated_at":     datetime.now().isoformat(),
        }, on_conflict="brand_name,retailer").execute()
        print(f"[Memory] Stored new_item_form for {brand_name} / {retailer}")
    except Exception as e:
        print(f"[Memory] store_new_item_form failed: {e}")


def store_sent_bundle(
    brand_name: str,
    bundle_type: str,
    retailer: str,
    email_subject: str = "",
    email_body: str = "",
    sell_sheet_html: str = "",
    form_xlsx_path: str = "",
    status: str = "sent",
) -> None:
    """
    Record a sent pitch/form bundle in the sent_bundles table.

    Requires this table in Supabase (run once):
        CREATE TABLE sent_bundles (
          id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          brand_name    text NOT NULL,
          bundle_type   text NOT NULL,
          retailer      text NOT NULL,
          email_subject text,
          email_body    text,
          sell_sheet_html text,
          form_xlsx_path  text,
          status        text NOT NULL,
          sent_at       timestamptz NOT NULL DEFAULT now()
        );
    """
    try:
        client = _get_client()
        client.table("sent_bundles").insert({
            "brand_name":      brand_name.strip().title(),
            "bundle_type":     bundle_type,
            "retailer":        retailer,
            "email_subject":   email_subject,
            "email_body":      email_body,
            "sell_sheet_html": sell_sheet_html,
            "form_xlsx_path":  form_xlsx_path,
            "status":          status,
            "sent_at":         datetime.now().isoformat(),
        }).execute()
        print(f"[Memory] Stored sent_bundle for {brand_name} / {retailer}")
    except Exception as e:
        print(f"[Memory] store_sent_bundle failed: {e}")


def retrieve_similar_brands(category: str, score_range: tuple) -> str:
    try:
        client = _get_client()
        result = (
            client.table("brand_evaluations")
            .select("brand_name, score, verdict")
            .eq("category", category)
            .gte("score", score_range[0])
            .lte("score", score_range[1])
            .limit(3)
            .execute()
        )
        if not result.data:
            return "No comparable brands evaluated yet."
        return "\n".join(
            f"{d['brand_name']}: {d['score']}/100 ({d['verdict']})"
            for d in result.data
        )
    except Exception:
        return "No comparable brands evaluated yet."
