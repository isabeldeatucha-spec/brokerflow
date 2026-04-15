# HW8 — Scaled Brand Scout Experiments

Self-contained HW8 harness. Does **not** modify anything your teammates
deployed on Railway. Uses Modal to fan out the existing Brand Scout graph
across 30+ parallel cloud containers.

## One-time setup

1. Install Modal locally:
   ```
   pip install modal
   modal token new
   ```
2. Create a Modal secret. Brand Scout uses Claude (unchanged from HW7);
   Retailer Pitcher uses **Gemini Flash** — cross-provider by design, cuts
   Pitcher cost ~30× and gives the scale experiment a real multi-provider
   data point.
   ```
   modal secret create sedge-env \
     ANTHROPIC_API_KEY=sk-ant-... \
     GEMINI_API_KEY=AIza... \
     FIRECRAWL_API_KEY=fc-... \
     PARALLEL_API_KEY=... \
     SUPABASE_URL=https://...supabase.co \
     SUPABASE_KEY=...
   ```
3. In Supabase, add the Retailer Pitcher table (stores both artifacts):
   ```sql
   create table retailer_pitches (
     id bigserial primary key,
     brand_name text not null,
     buyer text,
     buyer_key text,
     email_subject text,
     email_body text,
     sell_sheet_html text,
     artifact_status text,
     artifact_errors jsonb,
     created_at timestamptz default now()
   );
   ```

## Run experiments

```bash
# E1 — throughput: 50 brands, 1 run each, up to 60 concurrent containers
modal run hw8/modal_runner.py --brands hw8/brands.csv --repeats 1

# E2 — consistency at scale: 10 brands × 3 repeats = 30 jobs
modal run hw8/modal_runner.py --brands hw8/brands.csv --repeats 3 --limit 10

# E4 — two-agent handoff across containers (30 brands)
modal run hw8/modal_handoff.py --brands hw8/brands.csv --limit 30

# Analyze everything that landed in hw8/runs/
python hw8/analyze.py
```

Figures appear in `hw8/figs/`, raw data stays in `hw8/runs/*.jsonl`, and
`hw8/SUMMARY_DATA.json` holds the numbers cited in `SUMMARY.md`.

## Files

| File | Purpose |
|---|---|
| `brands.csv` | 50-brand benchmark |
| `modal_runner.py` | Brand Scout fan-out on Modal |
| `modal_handoff.py` | E4 — Scout → Pitcher two-container handoff |
| `../agents/retailer_pitcher/` | Full Retailer Pitcher agent (email + sell sheet) |
| `analyze.py` | Aggregation + figures |
| `SUMMARY.md` | 1-page deliverable |
| `slide.md` | Slide content for the class deck |
| `video_script.md` | 60-second video plan |
