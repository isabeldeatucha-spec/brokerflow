"""Anthropic-compatible shim that routes calls to Gemini.

Purpose
-------
Brand Scout (`agents/brand_scout/graph.py`) is hard-coded to use the
`anthropic` Python client at 6 call sites. During HW8 the team's personal
Anthropic account got blocked at the provisioning layer even though
credits had been purchased; switching to Gemini Flash unblocked the work
and cut per-run cost roughly 50×. Rather than edit 6 call sites, we
monkey-patch the `anthropic` module here so `anthropic.Anthropic(...)` and
`client.messages.create(...)` transparently route to Gemini.

Activation
----------
Set `SEDGE_LLM_PROVIDER=gemini` (default) to route through Gemini.
Set `SEDGE_LLM_PROVIDER=claude` to use the real Anthropic SDK.

Model mapping
-------------
  claude-sonnet-*     → gemini-2.5-flash
  claude-haiku-*      → gemini-2.5-flash-lite (falls back to flash)
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any


def _provider() -> str:
    # Default to Claude so the existing Railway deployment keeps working
    # unchanged. Set SEDGE_LLM_PROVIDER=gemini locally / in Modal to route
    # through the Gemini-backed shim.
    return os.environ.get("SEDGE_LLM_PROVIDER", "claude").lower()


def _map_model(claude_model: str) -> str:
    if "haiku" in claude_model:
        return os.environ.get("GEMINI_MODEL_LITE", "gemini-2.5-flash-lite")
    return os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


# ── Fake anthropic response objects ─────────────────────────────────────────

@dataclass
class _TextBlock:
    text: str
    type: str = "text"


@dataclass
class _Usage:
    input_tokens: int
    output_tokens: int


@dataclass
class _Message:
    content: list[_TextBlock]
    usage: _Usage
    id: str = "msg_gemini_shim"
    stop_reason: str = "end_turn"
    type: str = "message"
    role: str = "assistant"
    model: str = "gemini-2.5-flash"


# ── The shim client ─────────────────────────────────────────────────────────

def _strip_code_fence(text: str) -> str:
    """Gemini often wraps JSON in ```json ... ```; Brand Scout's json.loads chokes.

    Accepts fences with or without newlines (Gemini 2.5 Flash often emits
    ```json {...}``` all on one line).
    """
    if not text:
        return text
    t = text.strip()
    # Leading fence
    if t.startswith("```"):
        t = t[3:]
        # Drop language tag if present (json, JSON, yaml, etc.)
        if t[:4].lower() == "json":
            t = t[4:]
        elif t[:4].lower() == "yaml":
            t = t[4:]
        t = t.lstrip()
    # Trailing fence
    if t.rstrip().endswith("```"):
        t = t.rstrip()[:-3]
    return t.strip()


def _looks_like_json_request(system: str | None, user: str) -> bool:
    blob = ((system or "") + "\n" + user).lower()
    return "json" in blob


class _GeminiMessages:
    def create(
        self,
        *,
        model: str,
        messages: list[dict],
        max_tokens: int = 1024,
        system: str | None = None,
        temperature: float | None = None,
        **_: Any,
    ) -> _Message:
        from google import genai
        from google.genai import types as genai_types

        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

        # Flatten user/assistant turns into Gemini contents.
        contents: list[str] = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if isinstance(content, list):
                content = "\n".join(
                    c.get("text", "") if isinstance(c, dict) else str(c)
                    for c in content
                )
            prefix = "User: " if role == "user" else "Assistant: "
            contents.append(prefix + content)
        joined_user = "\n\n".join(contents) if contents else ""

        # Give Gemini a lot of headroom — many Brand Scout prompts request
        # structured JSON, Gemini is verbose, and truncation breaks json.loads.
        bumped_max_tokens = max(max_tokens * 4, 4096)

        config_kwargs: dict[str, Any] = {"max_output_tokens": bumped_max_tokens}
        if system:
            config_kwargs["system_instruction"] = system
        if temperature is not None:
            config_kwargs["temperature"] = temperature

        # Gemini 2.5 Flash enables "thinking" by default — it consumes
        # output tokens before the visible answer and leaves the caller
        # with truncated or empty text. We want plain generation.
        try:
            config_kwargs["thinking_config"] = genai_types.ThinkingConfig(
                thinking_budget=0
            )
        except Exception:  # older google-genai versions
            pass

        # Re-enable JSON mime type when the prompt clearly asks for JSON.
        if _looks_like_json_request(system, joined_user):
            config_kwargs["response_mime_type"] = "application/json"

        # Gemini free tier 503s under concurrency — retry with exponential backoff.
        import random
        import time as _time
        resp = None
        last_exc: Exception | None = None
        for attempt in range(5):
            try:
                resp = client.models.generate_content(
                    model=_map_model(model),
                    contents=joined_user,
                    config=genai_types.GenerateContentConfig(**config_kwargs),
                )
                break
            except Exception as exc:  # noqa: BLE001
                msg = str(exc)
                transient = any(t in msg for t in (
                    "503", "UNAVAILABLE", "overloaded", "429",
                    "RESOURCE_EXHAUSTED", "DEADLINE_EXCEEDED",
                ))
                last_exc = exc
                if not transient or attempt == 4:
                    raise
                delay = (2 ** attempt) + random.uniform(0, 1.5)
                print(f"[llm_shim] retry {attempt+1}/4 after {delay:.1f}s — {type(exc).__name__}: {msg[:120]}")
                _time.sleep(delay)
        if resp is None:  # should not happen — raise logic above
            raise last_exc if last_exc else RuntimeError("empty response")

        text_raw = resp.text or ""
        text = _strip_code_fence(text_raw)
        usage = getattr(resp, "usage_metadata", None)
        tin = getattr(usage, "prompt_token_count", 0) or 0
        tout = getattr(usage, "candidates_token_count", 0) or 0

        # Diagnostics — print a preview of every response for HW8 debugging.
        finish = None
        try:
            finish = resp.candidates[0].finish_reason  # type: ignore[attr-defined]
        except Exception:
            pass
        preview = text_raw.replace("\n", " ")[:160]
        print(f"[llm_shim] model={_map_model(model)} json_mode="
              f"{config_kwargs.get('response_mime_type') == 'application/json'} "
              f"tok_out={tout}/{bumped_max_tokens} finish={finish} "
              f"preview={preview!r}")

        return _Message(
            content=[_TextBlock(text=text)],
            usage=_Usage(input_tokens=tin, output_tokens=tout),
            model=_map_model(model),
        )


class _AnthropicShim:
    """Drop-in replacement for `anthropic.Anthropic(...)`."""

    def __init__(self, *_, **__) -> None:
        self.messages = _GeminiMessages()


# ── Install the shim ────────────────────────────────────────────────────────

def install() -> None:
    """Replace `anthropic.Anthropic` with the Gemini-backed shim, idempotent."""
    if _provider() != "gemini":
        return
    try:
        import anthropic  # type: ignore
    except ImportError:
        anthropic = type(sys)("anthropic")
        sys.modules["anthropic"] = anthropic

    # Preserve the real class so downstream code can probe isinstance if needed.
    if not getattr(anthropic, "_sedge_shim_installed", False):
        anthropic._real_Anthropic = getattr(anthropic, "Anthropic", None)
        anthropic.Anthropic = _AnthropicShim  # type: ignore[attr-defined]
        anthropic._sedge_shim_installed = True  # type: ignore[attr-defined]


install()
