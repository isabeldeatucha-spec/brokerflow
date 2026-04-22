-- Sedge platform — live Supabase schema (reference only, do not re-execute)
--
-- Reverse-engineered from memory.py, agents/*/graph.py, and hw8/*.py.
-- Supabase has pgcrypto enabled by default; gen_random_uuid() is available everywhere.
-- All timestamptz columns store UTC. Clients write ISO-8601 strings; Postgres parses them.

-- ── brand_evaluations ────────────────────────────────────────────────────────
-- Written by Brand Scout (memory.store_brand_evaluation).
-- Upserted on brand_name (title-cased before write).
-- Read by Retailer Pitcher (load_scout_context) and Admin & Ops (load_brand_context).

CREATE TABLE brand_evaluations (
    brand_name        text        PRIMARY KEY,  -- title-cased (e.g. "Chomps", "Graza")
    score             integer,                  -- 0–100 composite score
    verdict           text,                     -- "established" | "broker_ready" | "too_early"
    category          text,                     -- category key from category_benchmarks.py
    key_gaps          jsonb,                    -- list[str] — gaps the broker should verify
    key_signals       jsonb,                    -- dict: instacart_banners, trade_press, social_signals, funding
    broker_brief      text,                     -- 3-4 sentence human-readable summary
    score_breakdown   jsonb,                    -- dict: velocity_proof, distribution_density, etc.
    reflection_notes  jsonb,                    -- list[str] — ReAct loop reasoning notes
    email_draft       text,                     -- full outreach email text (Subject + body)
    email_subject     text,                     -- extracted Subject line from email_draft
    founder_name      text,
    founder_email     text,
    evaluated_at      timestamptz               -- ISO-8601 UTC string written by Python datetime.now()
);


-- ── retailer_pitches ─────────────────────────────────────────────────────────
-- Written by Retailer Pitcher (store_artifacts node).
-- Inserted (not upserted) on each run — multiple pitches per brand are kept.
-- Read by pitcher_demo.py (latest row by created_at).

CREATE TABLE retailer_pitches (
    id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_name       text        NOT NULL,
    buyer            text,                      -- human retailer name, e.g. "Whole Foods"
    buyer_key        text,                      -- snake_case key, e.g. "whole_foods"
    email_subject    text,
    email_body       text,
    sell_sheet_html  text,
    artifact_status  text,                      -- "ok" | "partial" | "failed"
    artifact_errors  jsonb,                     -- list[str] — errors from parallel draft nodes
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ON retailer_pitches (brand_name, created_at DESC);


-- ── new_item_forms ────────────────────────────────────────────────────────────
-- Written by Admin & Ops (generate_filled_xlsx node via memory.store_new_item_form).
-- Upserted on (brand_name, retailer) — one live record per brand+retailer pair.
-- Run this block manually in the Supabase SQL editor to create the table.

CREATE TABLE new_item_forms (
    id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_name        text        NOT NULL,
    retailer          text        NOT NULL,     -- "whole_foods" | future: "kehe", "unfi"
    filled_fields     jsonb       NOT NULL DEFAULT '{}',   -- field_id -> value
    field_confidence  jsonb       NOT NULL DEFAULT '{}',   -- field_id -> "high"|"medium"|"low"|"missing"
    field_sources     jsonb       NOT NULL DEFAULT '{}',   -- field_id -> provenance string
    gaps              jsonb       NOT NULL DEFAULT '[]',   -- list[{field_id, label, reason, suggested_action}]
    output_xlsx_path  text,                     -- /tmp path on the server that ran the agent
    output_status     text,                     -- "ok" | "partial" | "failed"
    generated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (brand_name, retailer)
);
