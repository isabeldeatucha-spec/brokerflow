"""Ask BrokerFlow handler — orchestrates context build → LLM stream."""
from __future__ import annotations

import os
from typing import Generator, Optional

# Install the Gemini shim before any anthropic-style call paths run.
import agents.llm_shim  # noqa: F401
from agents import llm_shim
from agents.ask_brokerflow.context_builder import build_context
from agents.ask_brokerflow.prompt import SYSTEM_PROMPT


# Print the assembled context the first few times for sanity-checking.
_DEBUG_CTX_REMAINING = int(os.environ.get("ASK_BF_DEBUG_CTX_RUNS", "3"))


def stream_ask(
    query: str,
    conversation_history: Optional[list[dict]] = None,
) -> Generator[str, None, None]:
    """Stream a BrokerFlow response to `query`.

    conversation_history: list of {"role": "user"|"assistant", "content": str}
                          — prior turns, NOT including the current `query`.
    """
    global _DEBUG_CTX_REMAINING

    history = conversation_history or []
    debug = _DEBUG_CTX_REMAINING > 0
    if debug:
        _DEBUG_CTX_REMAINING -= 1

    # 1. Build context from Supabase + queue state
    try:
        context = build_context(query=query, debug=debug)
    except Exception as exc:  # noqa: BLE001
        print(f"[ask_brokerflow] context build failed: "
              f"{type(exc).__name__}: {str(exc)[:200]}")
        yield (
            "Couldn't load your book data — try again in a moment."
        )
        return

    # 2. Compose messages (system filled with context, then prior turns,
    #    then current user query)
    system = SYSTEM_PROMPT.format(context=context)
    messages = list(history) + [{"role": "user", "content": query}]

    # 3. Stream tokens — llm_shim.stream_chat handles error fallbacks itself
    yield from llm_shim.stream_chat(
        messages=messages,
        system=system,
        model="claude-sonnet-4-5",
        max_tokens=900,
        temperature=0.4,
    )
