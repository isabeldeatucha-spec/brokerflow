"""Subscription handlers — wire each agent to events on the SCP blackboard.

Importing this module installs the handlers in the registry. The runner
imports it once on startup.
"""
from __future__ import annotations

import logging

from agents.coordination.protocol import (
    Envelope,
    EventType,
    publish,
    subscribe,
)

logger = logging.getLogger("sedge.scp.handlers")


# ── Pitcher subscribes to BRAND_ONBOARDED ───────────────────────────────────

@subscribe(EventType.BRAND_ONBOARDED, subscriber="retailer_pitcher")
def on_brand_onboarded__draft_pitch(env: Envelope) -> None:
    """When a brand finishes onboarding, draft a Whole Foods pitch."""
    brand_name = (env.payload or {}).get("brand_name")
    if not brand_name:
        logger.warning("BRAND_ONBOARDED missing brand_name; skipping")
        return

    logger.info("[pitcher] picking up %s", brand_name)
    publish(
        from_agent="retailer_pitcher",
        to_agent="user",
        brand_id=env.brand_id,
        event_type=EventType.PITCH_REQUESTED,
        payload={
            "brand_name":   brand_name,
            "buyer_key":    "whole_foods",
            "action_label": f"Drafting Whole Foods pitch for {brand_name}…",
            "agent_status": "in_progress",
        },
    )

    try:
        from agents.orchestrator.pipeline import _run_pitcher_with_framing
        result = _run_pitcher_with_framing(brand_name, "whole_foods", "")
        artifact_status = result.get("artifact_status", "unknown")
        subj = result.get("email_subject", "")[:60]

        if artifact_status == "ok":
            publish(
                from_agent="retailer_pitcher",
                to_agent="admin_ops",
                brand_id=env.brand_id,
                event_type=EventType.PITCH_DRAFTED,
                payload={
                    "brand_name":    brand_name,
                    "buyer_key":     "whole_foods",
                    "email_subject": subj,
                    "action_label":  f"Drafted Whole Foods pitch — “{subj}”",
                    "agent_status":  "completed",
                },
            )
        else:
            publish(
                from_agent="retailer_pitcher",
                to_agent="user",
                brand_id=env.brand_id,
                event_type=EventType.PITCH_FAILED,
                payload={
                    "brand_name":   brand_name,
                    "errors":       result.get("artifact_errors", []),
                    "action_label": f"Pitch draft failed for {brand_name}",
                    "agent_status": "awaiting_review",
                },
            )
    except Exception as exc:
        logger.exception("pitcher handler failed")
        publish(
            from_agent="retailer_pitcher",
            to_agent="user",
            brand_id=env.brand_id,
            event_type=EventType.PITCH_FAILED,
            payload={
                "brand_name":   brand_name,
                "errors":       [f"{type(exc).__name__}: {exc}"],
                "action_label": f"Pitch draft errored for {brand_name}",
                "agent_status": "awaiting_review",
            },
        )


# ── Admin & Ops subscribes to PITCH_DRAFTED *and* PITCH_FAILED ──────────────
# Subscribing to both means a pitch failure does not break the chain —
# Admin & Ops can still fill the form from the canonical brand record.

@subscribe(EventType.PITCH_DRAFTED, subscriber="admin_ops")
@subscribe(EventType.PITCH_FAILED, subscriber="admin_ops")
def on_pitch_drafted__fill_form(env: Envelope) -> None:
    """When a pitch is drafted (or fails), fill the WFM new-item form."""
    brand_name = (env.payload or {}).get("brand_name")
    if not brand_name:
        return

    logger.info("[admin_ops] picking up %s", brand_name)
    publish(
        from_agent="admin_ops",
        to_agent="user",
        brand_id=env.brand_id,
        event_type=EventType.FORM_FILL_REQUESTED,
        payload={
            "brand_name":   brand_name,
            "retailer":     "whole_foods",
            "action_label": f"Filling Whole Foods new-item form for {brand_name}…",
            "agent_status": "in_progress",
        },
    )

    try:
        from agents.admin_ops.graph import run_admin_ops
        result = run_admin_ops(brand_name, retailer="whole_foods")
        filled = len(result.get("filled_fields") or {})
        gaps   = len(result.get("gaps") or [])

        if gaps > 0:
            publish(
                from_agent="admin_ops",
                to_agent="user",
                brand_id=env.brand_id,
                event_type=EventType.FORM_GAPS_FLAGGED,
                payload={
                    "brand_name":           brand_name,
                    "retailer":             "whole_foods",
                    "filled_count":         filled,
                    "gaps_count":           gaps,
                    "pending_review_count": gaps,
                    "action_label":         f"WFM form filled: {filled} fields, {gaps} gaps to review",
                    "agent_status":         "awaiting_review",
                },
            )
        else:
            publish(
                from_agent="admin_ops",
                to_agent="po_processing",
                brand_id=env.brand_id,
                event_type=EventType.FORM_FILLED,
                payload={
                    "brand_name":   brand_name,
                    "retailer":     "whole_foods",
                    "filled_count": filled,
                    "action_label": f"WFM form complete ({filled} fields, no gaps)",
                    "agent_status": "completed",
                },
            )

        # NOTE: We don't publish PO_RECEIVED from here — the simulated
        # retailer publishes it via the FORM_GAPS_FLAGGED / FORM_FILLED
        # subscribers below. This avoids double-triggering PO Processing.
    except Exception as exc:
        logger.exception("admin_ops handler failed")


# ── PO Processing subscribes to PO_RECEIVED ─────────────────────────────────

@subscribe(EventType.PO_RECEIVED, subscriber="po_processing")
def on_po_received__validate(env: Envelope) -> None:
    """When a PO arrives, parse, validate pricing, confirm or dispute."""
    payload = env.payload or {}
    # Skip the synthetic 'awaiting' marker we publish from admin_ops
    if payload.get("agent_status") == "in_progress":
        return

    brand_name = payload.get("brand_name")
    if not brand_name:
        return

    logger.info("[po_processing] picking up PO for %s", brand_name)
    try:
        from agents.po_processing.graph import run_po_processing
        run_po_processing(brand_name)
    except Exception as exc:
        logger.exception("po_processing handler failed")


# ── Trigger PO arrival for the demo chain ───────────────────────────────────
# When admin_ops finishes, it publishes PO_RECEIVED with status=in_progress
# (a placeholder "awaiting PO" marker). To actually run PO processing,
# we publish a second PO_RECEIVED with no agent_status, which the handler
# above will pick up.

@subscribe(EventType.FORM_GAPS_FLAGGED, subscriber="po_processing_trigger")
def on_form_gaps_flagged__trigger_po(env: Envelope) -> None:
    """After form fill, simulate a PO arriving from the retailer."""
    brand_name = (env.payload or {}).get("brand_name")
    if not brand_name:
        return
    publish(
        from_agent="whole_foods_retailer",
        to_agent="po_processing",
        brand_id=env.brand_id,
        event_type=EventType.PO_RECEIVED,
        payload={
            "brand_name":   brand_name,
            "source":       "EDI_inbound_simulated",
            "action_label": "PO inbound from Whole Foods…",
        },
    )


@subscribe(EventType.FORM_FILLED, subscriber="po_processing_trigger")
def on_form_filled__trigger_po(env: Envelope) -> None:
    """Same trigger when there are no gaps."""
    on_form_gaps_flagged__trigger_po(env)
