"""Background coordination runner.

A daemon thread that polls the SCP blackboard every TICK_SECONDS and
dispatches unconsumed messages to subscribers. This is the autonomy
layer — agents react to events without human prompting.

Started once per Streamlit process via `start()`. Idempotent.
"""
from __future__ import annotations

import logging
import os
import threading
import time

from agents.coordination import handlers as _handlers  # noqa: F401  (registers subscriptions)
from agents.coordination.protocol import dispatch_tick

logger = logging.getLogger("sedge.runner")

TICK_SECONDS = float(os.getenv("SCP_TICK_SECONDS", "3"))

_thread: threading.Thread | None = None
_stop_evt = threading.Event()
_lock = threading.Lock()
_started_at: float | None = None
_tick_count: int = 0
_dispatch_count: int = 0


def _loop() -> None:
    global _tick_count, _dispatch_count
    logger.info("[scp.runner] loop start (tick=%.1fs)", TICK_SECONDS)
    while not _stop_evt.is_set():
        try:
            n = dispatch_tick()
            _tick_count += 1
            _dispatch_count += n
            if n:
                logger.info("[scp.runner] tick #%d dispatched %d", _tick_count, n)
        except Exception:
            logger.exception("[scp.runner] tick failed")
        # Sleep with stop responsiveness
        for _ in range(int(TICK_SECONDS * 10)):
            if _stop_evt.is_set():
                break
            time.sleep(0.1)


def start() -> bool:
    """Start the background runner. Idempotent. Returns True if newly started."""
    global _thread, _started_at
    with _lock:
        if _thread and _thread.is_alive():
            return False
        _stop_evt.clear()
        t = threading.Thread(target=_loop, daemon=True, name="scp-runner")
        t.start()
        _thread = t
        _started_at = time.time()
        return True


def stop() -> None:
    _stop_evt.set()


def status() -> dict:
    """Lightweight introspection for the UI."""
    return {
        "running":         bool(_thread and _thread.is_alive()),
        "tick_seconds":    TICK_SECONDS,
        "started_at":      _started_at,
        "uptime_seconds":  (time.time() - _started_at) if _started_at else 0,
        "ticks":           _tick_count,
        "dispatched":      _dispatch_count,
    }
