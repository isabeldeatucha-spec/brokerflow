"""
Memory layer for all Sedge agents.

Two distinct systems:
  1. LangGraph checkpointer (MemorySaver) — in-process thread state for graph interrupts.
     Exported as `memory` and `get_config`. Used by graph.compile(checkpointer=memory).

  2. Mem0 persistent memory — cross-run brand evaluation history.
     Exported as store_brand_evaluation, retrieve_similar_brands, retrieve_brand_history.
     Falls back gracefully if OPENAI_API_KEY (required by Mem0's default embedder) is absent.
"""
from datetime import datetime

from langgraph.checkpoint.memory import MemorySaver

# ── LangGraph checkpointer ────────────────────────────────────────────────────

memory = MemorySaver()


def get_config(thread_id: str) -> dict:
    """Return a LangGraph-compatible config dict for the given thread."""
    return {"configurable": {"thread_id": thread_id}}


# ── Mem0 persistent memory ────────────────────────────────────────────────────

_mem0_client = None


def _get_mem0():
    """Lazy-init Mem0 client. Returns None if unavailable."""
    global _mem0_client
    if _mem0_client is not None:
        return _mem0_client
    try:
        from mem0 import Memory
        _mem0_client = Memory()
        return _mem0_client
    except Exception:
        return None


def store_brand_evaluation(
    brand_name: str,
    score: int,
    verdict: str,
    category: str,
    key_signals: dict,
    key_gaps: list,
) -> None:
    """Persist the outcome of a brand evaluation for future reference."""
    m = _get_mem0()
    if m is None:
        return
    content = (
        f"Brand: {brand_name}\n"
        f"Category: {category}\n"
        f"Score: {score}/100\n"
        f"Verdict: {verdict}\n"
        f"Key signals: {key_signals}\n"
        f"Key gaps: {key_gaps}\n"
        f"Evaluated: {datetime.now().isoformat()}"
    )
    try:
        m.add(content, user_id="broker_memory")
    except Exception:
        pass


def retrieve_similar_brands(category: str, score_range: tuple) -> str:
    """Return previously evaluated brands in the same category and score range."""
    m = _get_mem0()
    if m is None:
        return ""
    query = (
        f"brands evaluated in {category} category "
        f"with scores between {score_range[0]} and {score_range[1]}"
    )
    try:
        results = m.search(query, user_id="broker_memory")
        memories = (results or {}).get("results", [])
        if not memories:
            return ""
        return "\n".join(r["memory"] for r in memories[:3])
    except Exception:
        return ""


def retrieve_brand_history(brand_name: str) -> str:
    """Check if this brand has been evaluated before. Returns memory string or empty."""
    m = _get_mem0()
    if m is None:
        return ""
    try:
        results = m.search(f"brand evaluation for {brand_name}", user_id="broker_memory")
        memories = (results or {}).get("results", [])
        return memories[0]["memory"] if memories else ""
    except Exception:
        return ""


def retrieve_all_evaluations() -> list[dict]:
    """
    Return all stored brand evaluations as structured dicts.
    Each dict has keys: brand_name, score, verdict, category, evaluated_at, raw.
    Returns empty list if Mem0 is unavailable or no evaluations exist.
    """
    m = _get_mem0()
    if m is None:
        return []
    try:
        results = m.search("brand evaluation score verdict category", user_id="broker_memory")
        memories = (results or {}).get("results", [])
    except Exception:
        return []

    evaluations = []
    for mem in memories:
        raw = mem.get("memory", "")
        entry = {"raw": raw, "brand_name": "", "score": 0, "verdict": "", "category": "", "evaluated_at": ""}
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("Brand:"):
                entry["brand_name"] = line.split(":", 1)[1].strip()
            elif line.startswith("Score:"):
                try:
                    entry["score"] = int(line.split(":", 1)[1].strip().split("/")[0])
                except (ValueError, IndexError):
                    pass
            elif line.startswith("Verdict:"):
                entry["verdict"] = line.split(":", 1)[1].strip()
            elif line.startswith("Category:"):
                entry["category"] = line.split(":", 1)[1].strip()
            elif line.startswith("Evaluated:"):
                entry["evaluated_at"] = line.split(":", 1)[1].strip()
        if entry["brand_name"]:
            evaluations.append(entry)

    evaluations.sort(key=lambda e: e["score"], reverse=True)
    return evaluations
