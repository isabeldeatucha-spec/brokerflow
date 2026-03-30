"""
Brand Scout — entry point.

Modes:
    python -m sedge.main                          CLI evaluation (interactive)
    python -m sedge.main --brand "Chomps"         evaluate a specific brand
    python -m sedge.main --telegram               start the Telegram bot
"""
import argparse
import sys
import uuid

from langgraph.types import Command

from sedge.agents.brand_scout.graph import graph
from sedge.memory import get_config


def run(brand_name: str = "", website_url: str = ""):
    thread_id = str(uuid.uuid4())
    config = get_config(thread_id)

    initial_state = {
        "brand_name": brand_name,
        "website_url": website_url,
        "sources_checked": [],
        "signals_found": {},
        "follow_up_queries": [],
        "reflection_count": 0,
        "reflection_notes": [],
        "category": "",
        "benchmark": {},
        "score": {},
        "verdict": "",
        "founder_name": "",
        "founder_email": "",
        "email_draft": "",
        "approved": None,
        "rejection_reason": None,
    }

    print(f"\n[Brand Scout] Starting run — thread {thread_id}\n")

    for chunk in graph.stream(initial_state, config=config, stream_mode="updates"):
        for node in chunk:
            print(f"  ✓ {node}")

        state_snapshot = graph.get_state(config)
        if state_snapshot.next and "human_approval" in state_snapshot.next:
            print("\n[Interrupt] Graph paused at human_approval.")
            print("In CLI mode, auto-approving for demo purposes.\n")

            final = graph.invoke(
                Command(resume={"approved": True, "rejection_reason": ""}),
                config=config,
            )
            _print_result(final)
            return final

    final = graph.get_state(config).values
    _print_result(final)
    return final


def _print_result(state: dict):
    print("\n[Brand Scout] Run complete.")
    print(f"  Brand:    {state.get('brand_name')}")
    print(f"  Category: {state.get('category', 'unknown')}")
    score = state.get("score", {})
    print(f"  Score:    {score.get('total')}/100")
    print(f"  Verdict:  {state.get('verdict')}")
    print(f"  Approved: {state.get('approved')}")

    # ── Reflection chain ──────────────────────────────────────────────────────
    reflection_notes = state.get("reflection_notes", [])
    reflection_count = state.get("reflection_count", 0)
    if reflection_notes:
        print(f"\n── Agent Reflection Chain ({reflection_count} loop(s)) ──────────────────")
        for i, note in enumerate(reflection_notes, 1):
            print(f"\n  Round {i}: {note}")

    # ── Memory ────────────────────────────────────────────────────────────────
    brand_history = state.get("signals_found", {}).get("brand_history", "")
    print(f"\n── Memory ───────────────────────────────────────────────────")
    if brand_history:
        print(f"  Previously evaluated: Yes\n  {brand_history[:300]}")
    else:
        print(f"  Previously evaluated: No")

    detail = state.get("signals_found", {}).get("score_detail", {})
    if not detail:
        print()
        return

    criteria = [
        ("velocity_proof",           25),
        ("distribution_density",     20),
        ("margin_viability",         20),
        ("brand_story_clarity",      20),
        ("promotional_independence", 15),
    ]

    print("\n── Score Breakdown ──────────────────────────────────────────")
    for key, max_pts in criteria:
        entry = detail.get(key, {})
        pts = entry.get("score", score.get(key, "?")) if isinstance(entry, dict) else score.get(key, "?")
        label = key.replace("_", " ").title()
        print(f"\n  {label}: {pts}/{max_pts}")
        if isinstance(entry, dict):
            print(f"    Reasoning:    {entry.get('reasoning', '')}")
            signals = entry.get("signals_used", [])
            if signals:
                print(f"    Signals used: {', '.join(str(s) for s in signals)}")

    broker_brief = detail.get("broker_brief", "")
    if broker_brief:
        print(f"\n── Broker Brief ─────────────────────────────────────────────")
        print(f"  {broker_brief}")

    key_gaps = detail.get("key_gaps", [])
    if key_gaps:
        print(f"\n── Key Gaps ──────────────────────────────────────────────────")
        for gap in key_gaps:
            print(f"  • {gap}")
    print()


def run_cli() -> None:
    parser = argparse.ArgumentParser(description="Brand Scout CLI")
    parser.add_argument("--brand", default="", help="Brand name")
    parser.add_argument("--url",   default="", help="Brand website URL")
    args = parser.parse_args()
    run(brand_name=args.brand, website_url=args.url)


if __name__ == "__main__":
    if "--telegram" in sys.argv:
        from sedge.telegram_bot import run_bot
        run_bot()
    else:
        run_cli()
