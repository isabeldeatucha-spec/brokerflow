"""Background coordination runner.

A daemon thread that polls the SCP blackboard every TICK_SECONDS and
dispatches unconsumed messages to subscribers via a ThreadPoolExecutor.
Multiple handlers run truly concurrently — the runner waits for all
handlers in a tick to complete before fetching the next batch (so the
consume marker doesn't race).

Started once per Streamlit process via `start()`. Idempotent.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from agents.coordination import handlers as _handlers  # noqa: F401  (registers subscriptions)
from agents.coordination.protocol import dispatch_tick, latency_stats

logger = logging.getLogger("sedge.runner")

TICK_SECONDS = float(os.getenv("SCP_TICK_SECONDS", "3"))
MAX_WORKERS  = int(os.getenv("SCP_MAX_WORKERS", "5"))

_thread:    threading.Thread | None = None
_executor:  ThreadPoolExecutor | None = None
_stop_evt   = threading.Event()
_lock       = threading.Lock()
_started_at: float | None = None
_tick_count: int = 0
_dispatch_count: int = 0


def _loop() -> None:
    global _tick_count, _dispatch_count
    logger.info("[scp.runner] loop start (tick=%.1fs, workers=%d)", TICK_SECONDS, MAX_WORKERS)
    while not _stop_evt.is_set():
        try:
            n = dispatch_tick(executor=_executor)
            _tick_count += 1
            _dispatch_count += n
            if n:
                logger.info("[scp.runner] tick #%d dispatched %d", _tick_count, n)
        except Exception:
            logger.exception("[scp.runner] tick failed")
        for _ in range(int(TICK_SECONDS * 10)):
            if _stop_evt.is_set():
                break
            time.sleep(0.1)


def start() -> bool:
    """Start the background runner. Idempotent. Returns True if newly started."""
    global _thread, _executor, _started_at
    with _lock:
        if _thread and _thread.is_alive():
            return False
        _stop_evt.clear()
        _executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="scp-handler")
        t = threading.Thread(target=_loop, daemon=True, name="scp-runner")
        t.start()
        _thread = t
        _started_at = time.time()
        return True


def stop() -> None:
    _stop_evt.set()
    if _executor:
        try:
            _executor.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            _executor.shutdown(wait=False)


# ── Metrics ────────────────────────────────────────────────────────────────

def _live_metrics() -> dict:
    """Pull cross-brand metrics from Supabase. Cheap to call (single batch)."""
    from datetime import datetime, timezone, timedelta
    from memory import _get_client
    out = {
        "active_chains":      0,
        "active_brand_ids":   [],
        "msgs_per_minute":    0,
        "failures_last_hour": 0,
    }
    try:
        client = _get_client()
        now = datetime.now(timezone.utc)
        one_min  = (now - timedelta(seconds=60)).isoformat()
        one_hour = (now - timedelta(hours=1)).isoformat()

        # Active chains = distinct brands with any unconsumed v1.* message
        unconsumed = (
            client.table("coordination_messages")
            .select("brand_id")
            .is_("consumed_at", "null")
            .like("message_type", "v1.%")
            .execute()
            .data or []
        )
        active_ids = {r["brand_id"] for r in unconsumed if r.get("brand_id")}
        out["active_chains"] = len(active_ids)
        out["active_brand_ids"] = list(active_ids)

        # Msgs/min: count of v1.* events in last 60s
        recent = (
            client.table("coordination_messages")
            .select("id", count="exact")
            .like("message_type", "v1.%")
            .gte("created_at", one_min)
            .execute()
        )
        out["msgs_per_minute"] = recent.count or 0

        # Failures last hour
        fails = (
            client.table("coordination_messages")
            .select("id", count="exact")
            .eq("message_type", "v1.handler_failed")
            .gte("created_at", one_hour)
            .execute()
        )
        out["failures_last_hour"] = fails.count or 0
    except Exception:
        logger.exception("metrics fetch failed")
    return out


def status() -> dict:
    """Lightweight introspection for the UI — runner state + chain metrics + latency."""
    base = {
        "running":        bool(_thread and _thread.is_alive()),
        "tick_seconds":   TICK_SECONDS,
        "max_workers":    MAX_WORKERS,
        "started_at":     _started_at,
        "uptime_seconds": (time.time() - _started_at) if _started_at else 0,
        "ticks":          _tick_count,
        "dispatched":     _dispatch_count,
    }
    base.update(_live_metrics())
    base.update(latency_stats())
    return base
