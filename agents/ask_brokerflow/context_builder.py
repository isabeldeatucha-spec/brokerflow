"""Build a markdown context block from live Supabase data + queue state.

Every section is wrapped in try/except so a missing/empty table degrades
gracefully — the LLM is then expected to surface the gap in its answer.

Token budget: ~8000 tokens (~32k chars at 4 chars/tok). When over budget,
sections are dropped from lowest priority first, per spec ordering.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Optional

# Section build order = display order (top to bottom in the prompt).
# Drop priority = REVERSE of this when over budget (last section drops first).
_SECTION_ORDER = [
    "ACCRUAL BALANCES",
    "ACTIVE POs",
    "RECENT EMAIL THREADS",
    "AGENT ACTIVITY",
    "TODAY'S QUEUE",
    "YOUR BOOK",
    "DEMOS / END CAPS",
]

_TOKEN_BUDGET = 8000
_CHARS_PER_TOKEN = 4

# In-process cache to avoid hammering Supabase between Streamlit reruns.
# We don't use st.cache_data here so this module stays UI-agnostic.
_CACHE: dict = {"ts": 0.0, "ctx": ""}
_CACHE_TTL_SEC = 60


def _client():
    from memory import _get_client
    return _get_client()


def _safe_query(fn, *args, **kwargs):
    """Run a Supabase query, returning [] on any failure (missing table,
    network blip, etc.). Logs to stdout for Railway."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        print(f"[ask_brokerflow.context] query failed: "
              f"{type(exc).__name__}: {str(exc)[:160]}")
        return []


def _ago(iso: str) -> str:
    try:
        ts = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - ts
        s = int(delta.total_seconds())
        if s < 60:   return "just now"
        if s < 3600: return f"{s // 60}m ago"
        if s < 86400: return f"{s // 3600}h ago"
        return f"{delta.days}d ago"
    except Exception:
        return ""


# ── Section builders ────────────────────────────────────────────────────────

def _book_section() -> str:
    """`brands` table — broker's active book."""
    rows = _safe_query(
        lambda: _client().table("brands")
        .select("brand_name, category, status")
        .limit(100).execute().data
    ) or []
    if not rows:
        return ""
    lines = ["## YOUR BOOK"]
    for r in rows:
        cat = r.get("category") or "—"
        status = r.get("status") or "active"
        lines.append(f"- {r['brand_name']} ({cat}, {status})")
    return "\n".join(lines)


def _accruals_section() -> str:
    """`accruals` table — may not exist yet."""
    rows = _safe_query(
        lambda: _client().table("accruals")
        .select("brand_name, retailer, region, balance, fiscal_year, days_remaining")
        .limit(200).execute().data
    ) or []
    if not rows:
        return ""
    by_brand: dict[str, list[dict]] = {}
    fy = ""
    days = ""
    for r in rows:
        by_brand.setdefault(r.get("brand_name", "?"), []).append(r)
        fy = fy or r.get("fiscal_year", "")
        days = days or str(r.get("days_remaining", ""))

    head = "## ACCRUAL BALANCES"
    if fy or days:
        head += f" ({fy}{', ' + days + ' days remaining' if days else ''})"
    out = [head]
    for brand in sorted(by_brand):
        out.append(f"{brand}:")
        for r in by_brand[brand]:
            ret = r.get("retailer") or "?"
            reg = r.get("region") or ""
            bal = r.get("balance") or 0
            label = f"{ret} {reg}".strip()
            out.append(f"  - {label}: ${bal:,}")
    return "\n".join(out)


def _pos_section() -> str:
    """`purchase_orders` table — may not exist yet."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    rows = _safe_query(
        lambda: _client().table("purchase_orders")
        .select("brand_name, retailer, po_number, status, requested_pickup, created_at")
        .gte("created_at", cutoff)
        .order("created_at", desc=True)
        .limit(50).execute().data
    ) or []
    if not rows:
        return ""
    lines = ["## ACTIVE POs (last 90 days)"]
    for r in rows:
        po = r.get("po_number") or "?"
        brand = r.get("brand_name") or "?"
        ret = r.get("retailer") or "?"
        pickup = r.get("requested_pickup") or "?"
        status = r.get("status") or "?"
        lines.append(
            f"- PO #{po} · {brand} → {ret} · pickup {pickup} · {status}"
        )
    return "\n".join(lines)


def _emails_section(query: Optional[str] = None) -> str:
    """`email_threads` table — may not exist yet. Falls back to
    coordination_messages email-related events if available."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    rows = _safe_query(
        lambda: _client().table("email_threads")
        .select("brand_name, retailer_contact, subject, snippet, direction, timestamp")
        .gte("timestamp", cutoff)
        .order("timestamp", desc=True)
        .limit(40).execute().data
    ) or []
    if not rows:
        return ""

    if query:
        ql = query.lower()
        scored = sorted(
            rows,
            key=lambda r: -sum(
                1 for w in ql.split()
                if w in (r.get("subject", "") + " " + r.get("snippet", "")).lower()
            ),
        )
        rows = scored[:20]
    else:
        rows = rows[:20]

    lines = ["## RECENT EMAIL THREADS"]
    for r in rows:
        contact = r.get("retailer_contact") or "?"
        subj = r.get("subject") or "(no subject)"
        direction = r.get("direction") or ""
        ago = _ago(r.get("timestamp", ""))
        brand = r.get("brand_name") or ""
        snippet = (r.get("snippet") or "").replace("\n", " ")[:140]
        meta = f"[{direction}, {ago}]" if direction or ago else ""
        lines.append(
            f"- {contact} re: {subj}{f' ({brand})' if brand else ''} {meta}"
        )
        if snippet:
            lines.append(f"    {snippet}")
    return "\n".join(lines)


def _brand_scout_section() -> str:
    rows = _safe_query(
        lambda: _client().table("brand_evaluations")
        .select("brand_name, score, verdict, broker_brief, evaluated_at")
        .order("evaluated_at", desc=True)
        .limit(15).execute().data
    ) or []
    if not rows:
        return ""
    lines = ["Brand Scout — recent verdicts:"]
    for r in rows:
        ago = _ago(r.get("evaluated_at", ""))
        brief = (r.get("broker_brief") or "").split(".")[0][:140]
        lines.append(
            f"- {r['brand_name']}: {r.get('score', '?')}/100, "
            f"{r.get('verdict', '?')} {f'({ago})' if ago else ''}"
        )
        if brief:
            lines.append(f"    {brief}.")
    return "\n".join(lines)


def _retailer_pitcher_section() -> str:
    rows = _safe_query(
        lambda: _client().table("retailer_pitches")
        .select("brand_name, buyer, artifact_status, created_at")
        .order("created_at", desc=True)
        .limit(15).execute().data
    ) or []
    if not rows:
        return ""
    lines = ["Retailer Pitcher — recent drafts:"]
    for r in rows:
        ago = _ago(r.get("created_at", ""))
        lines.append(
            f"- {r['brand_name']} → {r.get('buyer', '?')}: "
            f"{r.get('artifact_status', '?')} {f'({ago})' if ago else ''}"
        )
    return "\n".join(lines)


def _new_item_forms_section() -> str:
    rows = _safe_query(
        lambda: _client().table("new_item_forms")
        .select("brand_name, retailer, gaps, output_status, generated_at")
        .order("generated_at", desc=True)
        .limit(15).execute().data
    ) or []
    if not rows:
        return ""
    lines = ["New Item Forms — pending:"]
    for r in rows:
        gaps = r.get("gaps") or []
        gap_n = len(gaps) if isinstance(gaps, list) else 0
        ago = _ago(r.get("generated_at", ""))
        retailer = (r.get("retailer") or "?").replace("_", " ").title()
        lines.append(
            f"- {r['brand_name']} → {retailer}: "
            f"{gap_n} field{'s' if gap_n != 1 else ''} outstanding "
            f"{f'({ago})' if ago else ''}"
        )
    return "\n".join(lines)


def _agent_activity_section() -> str:
    """Combine output from all three live agents."""
    parts = []
    for fn in (_brand_scout_section, _retailer_pitcher_section,
               _new_item_forms_section):
        s = fn()
        if s:
            parts.append(s)
    if not parts:
        return ""
    return "## AGENT ACTIVITY\n" + "\n\n".join(parts)


def _today_queue_section() -> str:
    """Surface what's currently in the broker's queue, since the demo seeds
    it in-memory rather than from Supabase. Lets Ask BrokerFlow answer
    questions like 'what needs my approval right now?' against the actual
    cards the broker is staring at."""
    try:
        from ui.queue_view import SEED_CARDS
    except Exception:
        return ""

    sent = []
    skipped = []
    try:
        import streamlit as st  # only available in Streamlit context
        sent = st.session_state.get("queue_sent_ids", set())
        skipped = st.session_state.get("queue_skipped_ids", set())
    except Exception:
        pass

    active = [c for c in SEED_CARDS if c.id not in sent and c.id not in skipped]
    if not active:
        return ""
    lines = ["## TODAY'S QUEUE (live, awaiting broker action)"]
    for c in active:
        # Strip <b>...</b> from summary HTML so the prompt stays clean
        import re
        plain_summary = re.sub(r"<[^>]+>", "", c.summary_html)
        needs = " (NEEDS YOU)" if c.needs_you else ""
        lines.append(
            f"- [{c.type}{needs}] {c.context} · {c.elapsed} ago"
        )
        lines.append(f"    {plain_summary}")
    return "\n".join(lines)


def _demos_section() -> str:
    """`demos` or `events` table — may not exist yet."""
    rows = _safe_query(
        lambda: _client().table("demos")
        .select("brand_name, retailer, type, status, date")
        .order("date", desc=True)
        .limit(20).execute().data
    ) or []
    if not rows:
        return ""
    lines = ["## DEMOS / END CAPS"]
    for r in rows:
        lines.append(
            f"- {r.get('brand_name', '?')} · {r.get('retailer', '?')} · "
            f"{r.get('type', '?')} · {r.get('date', '?')} · "
            f"{r.get('status', '?')}"
        )
    return "\n".join(lines)


# ── Assemble + budget ──────────────────────────────────────────────────────

_BUILDERS: dict[str, callable] = {
    "ACCRUAL BALANCES":      _accruals_section,
    "ACTIVE POs":            _pos_section,
    "RECENT EMAIL THREADS":  _emails_section,
    "AGENT ACTIVITY":        _agent_activity_section,
    "TODAY'S QUEUE":         _today_queue_section,
    "YOUR BOOK":             _book_section,
    "DEMOS / END CAPS":      _demos_section,
}


def _assemble(query: Optional[str], debug: bool) -> str:
    sections: dict[str, str] = {}
    for name in _SECTION_ORDER:
        try:
            if name == "RECENT EMAIL THREADS":
                sections[name] = _emails_section(query)
            else:
                sections[name] = _BUILDERS[name]()
        except Exception as exc:  # noqa: BLE001
            print(f"[ask_brokerflow.context] section {name!r} build failed: "
                  f"{type(exc).__name__}: {str(exc)[:120]}")
            sections[name] = ""

    # Drop empty sections, preserve display order
    ordered = [(n, sections[n]) for n in _SECTION_ORDER if sections[n]]
    if not ordered:
        return "_(No book data available — Supabase tables empty or unreachable.)_"

    # Token budget: drop lowest-priority sections (end of _SECTION_ORDER) first.
    # Per spec: keep ACCRUAL > POs > emails > agents > queue > book > demos.
    # _SECTION_ORDER is already in keep-priority order, so drop from the tail.
    while ordered:
        joined = "\n\n".join(s for _, s in ordered)
        if len(joined) // _CHARS_PER_TOKEN <= _TOKEN_BUDGET:
            break
        dropped, _ = ordered.pop()
        print(f"[ask_brokerflow.context] over budget — dropped {dropped}")

    out = "\n\n".join(s for _, s in ordered)

    if debug:
        print("=" * 60)
        print("[ask_brokerflow] CONTEXT (chars=%d ≈ tokens=%d):"
              % (len(out), len(out) // _CHARS_PER_TOKEN))
        print(out)
        print("=" * 60)

    return out


def build_context(query: Optional[str] = None, debug: bool = False) -> str:
    """Public entry — returns a markdown context string.

    Cached for _CACHE_TTL_SEC seconds to avoid hammering Supabase between
    Streamlit reruns. Pass debug=True to dump the assembled context to
    stdout (useful while iterating)."""
    now = time.time()
    if (now - _CACHE["ts"]) < _CACHE_TTL_SEC and _CACHE["ctx"] and not debug:
        return _CACHE["ctx"]
    ctx = _assemble(query, debug)
    _CACHE["ts"] = now
    _CACHE["ctx"] = ctx
    return ctx


def invalidate_cache() -> None:
    _CACHE["ts"] = 0.0
    _CACHE["ctx"] = ""
