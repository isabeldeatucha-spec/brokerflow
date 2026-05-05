"""Lazy PDF generation for the queue's six seed cards.

Called once per Streamlit session via ensure_seed_docs(). The actual
payload data lives in agents/_shared/document_data.py — both this
module and the in-app side-panel preview pull from there so the PDF
artifact and the in-app view never drift.
"""
from __future__ import annotations

import streamlit as st

from agents._shared import doc_storage, document_data


def ensure_seed_docs() -> None:
    """Generate any seed PDFs that aren't on disk yet. Idempotent.
    Cached in session_state so we only check once per session."""
    if st.session_state.get("_seed_docs_ready"):
        return

    for card_id, doc_type, agent, payload in document_data.all_seed_entries():
        try:
            doc_storage.ensure_pdf(card_id, agent, doc_type, payload)
        except Exception as exc:  # noqa: BLE001
            print(f"[seed_docs] {card_id}/{doc_type} failed: "
                  f"{type(exc).__name__}: {exc}")

    st.session_state["_seed_docs_ready"] = True
