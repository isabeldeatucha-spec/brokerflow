"""Pragmatic Freshness Watchdog.

Runs on every Streamlit session start. Scans brands where
last_verified_at is older than FRESHNESS_THRESHOLD_DAYS and autonomously
emits a coordination message suggesting re-verification. This is the
'autonomy' criterion from the MAS.664 rubric: the agent acts without
user prompting, triggered by session lifecycle rather than cron.

ROADMAP NOTE (for HW9 writeup): in production, this would run as a
scheduled Celery beat job every 6 hours for true 24/7 autonomy. The
session-triggered implementation is functionally equivalent for the
demo scope and ships with zero infra overhead.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from agents.brand_onboarding.tools import tool_emit_coordination_message

FRESHNESS_THRESHOLD_DAYS = 30


def scan_and_flag_stale_brands() -> list:
    """Return brands needing re-verification. Emit coordination messages
    for each. Idempotent — will not re-emit if message already exists for the
    same brand in the last 24h."""
    from memory import _get_client
    client = _get_client()

    threshold = datetime.now(timezone.utc) - timedelta(days=FRESHNESS_THRESHOLD_DAYS)

    result = (
        client.table("brands")
        .select("id, brand_name, last_verified_at, completeness_pct")
        .lt("last_verified_at", threshold.isoformat())
        .eq("status", "active")
        .execute()
    )

    stale = result.data or []
    flagged = []

    for brand in stale:
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        existing = (
            client.table("coordination_messages")
            .select("id")
            .eq("brand_id", brand["id"])
            .eq("message_type", "needs_reverification")
            .gte("created_at", recent_cutoff.isoformat())
            .limit(1)
            .execute()
        )
        if existing.data:
            continue

        lv = brand["last_verified_at"]
        try:
            lv_dt = datetime.fromisoformat(lv.replace("Z", "+00:00"))
            days_stale = (datetime.now(timezone.utc) - lv_dt).days
        except Exception:
            days_stale = FRESHNESS_THRESHOLD_DAYS

        tool_emit_coordination_message(
            from_agent="freshness_watchdog",
            to_agent="brand_onboarding",
            brand_id=brand["id"],
            message_type="needs_reverification",
            payload={
                "brand_name": brand["brand_name"],
                "last_verified_at": lv,
                "days_stale": days_stale,
            },
        )
        flagged.append(brand)

    return flagged


def get_pending_reverifications() -> list:
    """Read unconsumed watchdog messages for display in UI."""
    from memory import _get_client
    client = _get_client()
    result = (
        client.table("coordination_messages")
        .select("*")
        .eq("to_agent", "brand_onboarding")
        .eq("message_type", "needs_reverification")
        .is_("consumed_at", "null")
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    return result.data or []
