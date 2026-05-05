"""Persist agent-generated PDFs and look them up at view time.

Two storage backends, tried in order:
  1. Supabase Storage bucket "agent_docs" — preferred (signed URLs).
  2. Local filesystem under ui/static/agent_docs/ — fallback when the
     bucket isn't set up or the anon key is RLS-blocked.

The `documents` table tracks what each card produced. If the table or
RLS blocks writes, we fall back to an in-process dict.

Public API:
  ensure_pdf(card_id, agent, doc_type, payload) -> {"url", "filename",
                                                     "size_kb", "pages"}
      Generates the PDF on first call, persists it, and returns view info.
      Subsequent calls hit the cache and skip generation.

  list_for_card(card_id) -> list[dict]
      Returns all docs registered for a card (id, doc_type, label, url, …).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agents._shared import pdf_generator


# ── Local storage paths ─────────────────────────────────────────────────────

# Streamlit serves files in <app_dir>/static/ when enableStaticServing=true.
# brokerflow_app.py runs from ui/, so static = brokerflow/ui/static/.
_STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "ui" / "static"
_LOCAL_DIR  = _STATIC_DIR / "agent_docs"
_LOCAL_DIR.mkdir(parents=True, exist_ok=True)

# In-process cache: key is (card_id, doc_type) -> view dict.
_CACHE: dict[tuple[str, str], dict] = {}


def _local_url(filename: str) -> str:
    """Streamlit static URL — files in app_dir/static/ are served at
    /app/static/<path>. Same-origin so the iframe loads cleanly."""
    return f"/app/static/agent_docs/{filename}"


def _supabase_client():
    try:
        from memory import _get_client
        return _get_client()
    except Exception as exc:
        print(f"[doc_storage] supabase unavailable: {exc}")
        return None


def _try_supabase_upload(storage_path: str, pdf_bytes: bytes) -> str | None:
    """Upload to Supabase Storage. Returns a signed URL on success, else
    None. Idempotent — overwrites if the same path exists."""
    client = _supabase_client()
    if not client:
        return None
    bucket = "agent_docs"
    try:
        # Upsert via upload + replace=true; some SDK versions need separate
        # remove before upload, so try both paths.
        try:
            client.storage.from_(bucket).upload(
                storage_path, pdf_bytes,
                {"content-type": "application/pdf", "upsert": "true"},
            )
        except Exception:
            # Try delete + upload
            try:
                client.storage.from_(bucket).remove([storage_path])
            except Exception:
                pass
            client.storage.from_(bucket).upload(
                storage_path, pdf_bytes,
                {"content-type": "application/pdf"},
            )
        signed = client.storage.from_(bucket).create_signed_url(
            storage_path, expires_in=3600,
        )
        url = signed.get("signedURL") or signed.get("signedUrl")
        if url:
            print(f"[doc_storage] uploaded {storage_path} → supabase signed URL")
        return url
    except Exception as exc:
        print(f"[doc_storage] supabase upload failed for {storage_path}: "
              f"{type(exc).__name__}: {str(exc)[:160]}")
        return None


def _try_documents_record(card_id: str, agent: str, doc_type: str,
                          storage_path: str) -> None:
    """Best-effort insert into the `documents` table. Silently no-ops
    if the table doesn't exist or RLS blocks the write — the in-process
    cache covers the demo case."""
    client = _supabase_client()
    if not client:
        return
    try:
        client.table("documents").upsert({
            "card_id":      card_id,
            "agent":        agent,
            "doc_type":     doc_type,
            "storage_path": storage_path,
        }, on_conflict="card_id,doc_type").execute()
    except Exception as exc:
        msg = str(exc)
        if "documents" in msg or "schema cache" in msg:
            print("[doc_storage] documents table not present — using "
                  "in-process cache only (run the migration to enable "
                  "cross-session persistence)")
        else:
            print(f"[doc_storage] documents row failed: "
                  f"{type(exc).__name__}: {msg[:160]}")


def _page_count(pdf_bytes: bytes) -> int:
    """Cheap page count — counts /Type /Page objects in the PDF stream.
    Good enough for the demo, no extra dep."""
    try:
        return max(1, pdf_bytes.count(b"/Type /Page") -
                       pdf_bytes.count(b"/Type /Pages"))
    except Exception:
        return 1


def ensure_pdf(card_id: str, agent: str, doc_type: str,
               payload: dict[str, Any]) -> dict:
    """Make sure the PDF for (card_id, doc_type) exists and return its
    view metadata. Generates + persists on first call.
    """
    cache_key = (card_id, doc_type)
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    # Generate
    pdf_bytes = pdf_generator.generate(doc_type, payload)
    filename = f"{card_id}_{doc_type}.pdf"
    storage_path = f"{agent}/{card_id}/{doc_type}.pdf"

    # Try Supabase first
    url = _try_supabase_upload(storage_path, pdf_bytes)

    # Always also write locally so the static URL is available regardless
    local_path = _LOCAL_DIR / filename
    try:
        local_path.write_bytes(pdf_bytes)
    except Exception as exc:
        print(f"[doc_storage] local write failed for {local_path}: "
              f"{type(exc).__name__}: {exc}")

    # Prefer Supabase signed URL when it exists; fall back to local
    if not url:
        url = _local_url(filename)

    _try_documents_record(card_id, agent, doc_type, storage_path)

    info = {
        "card_id":  card_id,
        "agent":    agent,
        "doc_type": doc_type,
        "filename": filename,
        "url":      url,
        "size_kb":  round(len(pdf_bytes) / 1024, 1),
        "pages":    _page_count(pdf_bytes),
    }
    _CACHE[cache_key] = info
    return info


def list_for_card(card_id: str) -> list[dict]:
    return [v for (cid, _), v in _CACHE.items() if cid == card_id]


def get(card_id: str, doc_type: str) -> dict | None:
    return _CACHE.get((card_id, doc_type))


def clear_cache() -> None:
    _CACHE.clear()


# ── Schema migration helper (printed in README, run by hand) ───────────────

DOCUMENTS_TABLE_SQL = """\
-- Run once in Supabase SQL editor.
CREATE TABLE IF NOT EXISTS documents (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id       text        NOT NULL,
    agent         text        NOT NULL,
    doc_type      text        NOT NULL,
    storage_path  text        NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (card_id, doc_type)
);

-- And in Storage UI: create a bucket named "agent_docs" (private).
"""
