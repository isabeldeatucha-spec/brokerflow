"""Shared utilities used across BrokerFlow agents.

Currently:
  - pdf_generator: ReportLab templates for sell sheets, brand one-pagers,
    and new-item forms.
  - doc_storage:  Persists PDFs (Supabase Storage if available, local
    fallback to ui/static/agent_docs/) and tracks them in the documents
    table — also with a session-state fallback when the table doesn't
    exist or RLS blocks writes.
"""
