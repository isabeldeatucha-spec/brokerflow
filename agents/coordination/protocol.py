"""Sedge Coordination Protocol (SCP) v1.

A typed, observable pub-sub protocol for agent-to-agent coordination,
backed by Supabase. Inspired by MCP/A2A, specialized for the
broker-agent domain.

Primitives
----------
1. **Typed events** — versioned message_type strings (`v1.brand_onboarded`)
2. **Publish**       — write a message to the blackboard
3. **Subscribe**     — declare a handler for a message type
4. **Dispatch**      — runner pulls unconsumed messages, calls handlers
5. **Ack**           — set `consumed_at` on success; mark failed on error
6. **Idempotency**   — dedup by (brand_id, message_type) within a tick

Delivery semantics: at-least-once. Handlers should be idempotent.

Backward compat
---------------
Pre-v1 message types (`new_brand_onboarded`, `brand_ready_for_forms`)
are supported via the LEGACY_TYPE_MAP — they're treated as v1 events
without breaking the existing UI activity feed.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("sedge.scp")


# ── Event taxonomy ──────────────────────────────────────────────────────────

class EventType(str, Enum):
    """Typed event names. Versioned so we can evolve without breaking subscribers."""

    # Brand lifecycle
    BRAND_ONBOARDED       = "v1.brand_onboarded"

    # Retailer Pitcher
    PITCH_REQUESTED       = "v1.pitch_requested"
    PITCH_DRAFTED         = "v1.pitch_drafted"
    PITCH_FAILED          = "v1.pitch_failed"

    # Admin & Ops
    FORM_FILL_REQUESTED   = "v1.form_fill_requested"
    FORM_FILLED           = "v1.form_filled"
    FORM_GAPS_FLAGGED     = "v1.form_gaps_flagged"

    # PO Processing
    PO_RECEIVED           = "v1.po_received"
    PO_VALIDATED          = "v1.po_validated"
    PO_DISPUTE_NEEDED     = "v1.po_dispute_needed"

    # Generic
    HANDLER_FAILED        = "v1.handler_failed"


# Map legacy untyped strings to v1 events so existing graphs keep working.
LEGACY_TYPE_MAP: dict[str, EventType] = {
    "new_brand_onboarded":  EventType.BRAND_ONBOARDED,
    "brand_ready_for_forms": EventType.FORM_FILL_REQUESTED,
}


def normalize_type(raw: str) -> Optional[EventType]:
    """Map a raw message_type string to an EventType, honoring legacy aliases."""
    if not raw:
        return None
    if raw in LEGACY_TYPE_MAP:
        return LEGACY_TYPE_MAP[raw]
    try:
        return EventType(raw)
    except ValueError:
        return None


# ── Message envelope ────────────────────────────────────────────────────────

@dataclass
class Envelope:
    """A single coordination message in the protocol."""
    id:           str
    from_agent:   str
    to_agent:     str
    brand_id:     str
    message_type: str          # raw string from DB; normalize via normalize_type()
    payload:      dict
    created_at:   str
    consumed_at:  Optional[str] = None


# ── Subscription registry ───────────────────────────────────────────────────

# message_type (str) -> list of (subscriber_name, handler_callable)
_HANDLERS: dict[str, list[tuple[str, Callable[[Envelope], Any]]]] = {}


def subscribe(event_type: EventType, subscriber: str = ""):
    """Decorator: register `handler(envelope)` to fire for `event_type` messages."""
    def decorator(func: Callable[[Envelope], Any]):
        sub_name = subscriber or func.__module__
        _HANDLERS.setdefault(event_type.value, []).append((sub_name, func))
        # Also register under any legacy alias that maps to this event
        for legacy, mapped in LEGACY_TYPE_MAP.items():
            if mapped == event_type:
                _HANDLERS.setdefault(legacy, []).append((sub_name, func))
        return func
    return decorator


def get_handlers(message_type: str) -> list[tuple[str, Callable]]:
    return _HANDLERS.get(message_type, [])


def list_subscriptions() -> dict[str, list[str]]:
    """Return a snapshot of who's subscribed to what — for the UI/debugging."""
    return {k: [s for s, _ in v] for k, v in _HANDLERS.items()}


# ── Publish / consume / fetch ───────────────────────────────────────────────

def publish(
    *,
    from_agent:   str,
    to_agent:     str,
    brand_id:     str,
    event_type:   EventType,
    payload:      Optional[dict] = None,
) -> Optional[str]:
    """Write a typed event to the blackboard. Returns inserted row id, or None on failure.

    Events with no registered subscriber are auto-acked at publish time
    (fire-and-forget status events), so they don't sit forever in the
    unconsumed queue and inflate the active_chains metric.
    """
    from memory import _get_client
    try:
        has_subscriber = bool(_HANDLERS.get(event_type.value))
        row = {
            "from_agent":   from_agent,
            "to_agent":     to_agent,
            "brand_id":     brand_id,
            "message_type": event_type.value,
            "payload":      payload or {},
        }
        # Fire-and-forget if no subscriber — visible in the log but not queued
        if not has_subscriber:
            row["consumed_at"] = datetime.now(timezone.utc).isoformat()
        client = _get_client()
        result = client.table("coordination_messages").insert(row).execute()
        rows = result.data or []
        return rows[0]["id"] if rows else None
    except Exception as exc:
        logger.warning("publish(%s) failed: %s", event_type.value, exc)
        return None


def fetch_unconsumed(limit: int = 25) -> list[Envelope]:
    """Pull unconsumed messages whose type we have a handler for."""
    from memory import _get_client
    try:
        client = _get_client()
        # Only fetch types we have handlers for
        wanted = list(_HANDLERS.keys())
        if not wanted:
            return []
        res = (
            client.table("coordination_messages")
            .select("id, from_agent, to_agent, brand_id, message_type, payload, created_at, consumed_at")
            .is_("consumed_at", "null")
            .in_("message_type", wanted)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        rows = res.data or []
        return [
            Envelope(
                id           = r["id"],
                from_agent   = r.get("from_agent", ""),
                to_agent     = r.get("to_agent", ""),
                brand_id     = r.get("brand_id", "") or "",
                message_type = r.get("message_type", ""),
                payload      = r.get("payload") or {},
                created_at   = r.get("created_at", ""),
                consumed_at  = r.get("consumed_at"),
            )
            for r in rows
        ]
    except Exception as exc:
        logger.warning("fetch_unconsumed failed: %s", exc)
        return []


def ack(envelope_id: str) -> None:
    """Mark a message consumed. Idempotent."""
    from memory import _get_client
    try:
        client = _get_client()
        client.table("coordination_messages").update({
            "consumed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", envelope_id).execute()
    except Exception as exc:
        logger.warning("ack(%s) failed: %s", envelope_id, exc)


# ── Dispatch (single tick) ──────────────────────────────────────────────────

# Per-handler latency log (rolling, in-memory). Used by runner.status().
import collections
import time as _time
_LATENCY_LOG: collections.deque = collections.deque(maxlen=200)


def _run_envelope(env: Envelope) -> None:
    """Run all subscribers for one envelope, then ack. Used by dispatch_tick."""
    handlers = get_handlers(env.message_type)
    for sub_name, handler in handlers:
        t0 = _time.monotonic()
        try:
            logger.info("dispatch %s → %s (brand=%s)",
                        env.message_type, sub_name, env.brand_id)
            handler(env)
            _LATENCY_LOG.append(("ok", (_time.monotonic() - t0) * 1000))
        except Exception as exc:
            _LATENCY_LOG.append(("fail", (_time.monotonic() - t0) * 1000))
            logger.exception("handler %s failed for %s", sub_name, env.message_type)
            publish(
                from_agent="scp_runner",
                to_agent=sub_name,
                brand_id=env.brand_id,
                event_type=EventType.HANDLER_FAILED,
                payload={
                    "original_type": env.message_type,
                    "subscriber":    sub_name,
                    "error":         f"{type(exc).__name__}: {exc}",
                },
            )
    ack(env.id)


def dispatch_tick(executor=None) -> int:
    """Pull unconsumed messages and route to handlers. Returns # processed.

    If `executor` (a ThreadPoolExecutor) is provided, handlers run in parallel.
    Each tick still blocks until all handlers in that batch complete, so the
    next tick sees a clean state. This is what lets multiple chains run
    truly concurrently without races on the consume marker.
    """
    pending = fetch_unconsumed()
    seen_keys: set[tuple] = set()
    to_dispatch: list[Envelope] = []

    for env in pending:
        # Idempotency within a tick: skip duplicate (brand_id, type) pairs
        key = (env.brand_id, env.message_type)
        if key in seen_keys:
            ack(env.id)
            continue
        seen_keys.add(key)
        if not get_handlers(env.message_type):
            continue
        to_dispatch.append(env)

    if not to_dispatch:
        return 0

    if executor is not None:
        futures = [executor.submit(_run_envelope, env) for env in to_dispatch]
        for f in futures:
            try:
                f.result(timeout=120)
            except Exception:
                logger.exception("envelope future failed")
    else:
        for env in to_dispatch:
            _run_envelope(env)

    return len(to_dispatch)


def latency_stats() -> dict:
    """Return p50/avg of recent handler latencies in ms."""
    if not _LATENCY_LOG:
        return {"avg_ms": 0.0, "p50_ms": 0.0, "samples": 0, "fail_pct": 0.0}
    durs = sorted([d for _, d in _LATENCY_LOG])
    fails = sum(1 for tag, _ in _LATENCY_LOG if tag == "fail")
    n = len(durs)
    return {
        "avg_ms":   sum(durs) / n,
        "p50_ms":   durs[n // 2],
        "samples":  n,
        "fail_pct": 100 * fails / n,
    }


# ── Live coordination log fetch (UI) ────────────────────────────────────────

def recent_traffic(brand_id: Optional[str] = None, limit: int = 30) -> list[Envelope]:
    """Most recent messages — for the live coordination-log UI."""
    from memory import _get_client
    try:
        client = _get_client()
        q = (
            client.table("coordination_messages")
            .select("id, from_agent, to_agent, brand_id, message_type, payload, created_at, consumed_at")
            .order("created_at", desc=True)
            .limit(limit)
        )
        if brand_id:
            q = q.eq("brand_id", brand_id)
        res = q.execute()
        rows = res.data or []
        return [
            Envelope(
                id           = r["id"],
                from_agent   = r.get("from_agent", ""),
                to_agent     = r.get("to_agent", ""),
                brand_id     = r.get("brand_id", "") or "",
                message_type = r.get("message_type", ""),
                payload      = r.get("payload") or {},
                created_at   = r.get("created_at", ""),
                consumed_at  = r.get("consumed_at"),
            )
            for r in rows
        ]
    except Exception:
        return []
