# HW8 — Sedge Scaled Agent Experiments

*Isabel de Atucha · Yi Liu · Sasha Towe*

## What changed since HW7

HW7 evaluated Brand Scout on a laptop: **3 runs × 5 brands = 15 runs**,
serialized, single machine, single region. Every run used Claude Sonnet.
Mean stddev < 3 on most brands, one verdict flip (Olipop).

HW8 pushes the same Brand Scout graph to **30–60 parallel Modal
containers spread across 16 cloud regions** (US-East, US-West, UK,
Asia-Southeast, Australia-Southeast, EU-West, Italy-North, etc.), adds
a **full Retailer Pitcher agent** (LangGraph with parallel email +
HTML sell-sheet nodes over 3 buyer personas), and expands the test set
from 5 → **50 brands**. Because our personal Anthropic account was
blocked at the provisioning layer mid-project despite purchased credits,
we migrated **Brand Scout to Claude-compatible Gemini shim** and ran
**Retailer Pitcher on Gemini 2.5 Flash directly** — a real cross-provider
deployment that itself surfaced scale issues.

## Scaled setup

- **Compute**: Modal serverless, `max_containers=60`, 16 distinct cloud
  regions observed (us-east-1, us-east-2, eastus, eastus2, westus,
  westus3, us-west-2, us-central1, uksouth, italynorth, eu-west-1,
  me-west1, asia-southeast1, southeastasia, australia-southeast1,
  unknown).
- **Workload**: `hw8/brands.csv` (50 CPG brands) × experiments.
  - **E1 Throughput**: 50 brands × 1 run = 50 parallel Scout jobs.
  - **E2 Consistency at scale**: 10 brands × 3 repeats = 30 jobs.
  - **E3 Cost**: tokens + API cost tracked per run.
  - **E4 Handoff**: 30 brands × (Scout container → Pitcher container)
    coordinating only through Supabase. Ran twice — once before the
    parallel-node reducer bug was fixed, once after.
- **Orchestration**: `hw8/modal_runner.py` (Scout fan-out),
  `hw8/modal_handoff.py` (two-agent end-to-end),
  `hw8/modal_pitch_only.py` (Pitcher-only re-run). Results streamed to
  `hw8/runs/*.jsonl`; `hw8/analyze.py` produces figures in `hw8/figs/`.
- **Telemetry per run**: latency, status, error type, Modal region,
  container id, score breakdown, reflection count, input/output tokens.

## Results / failures / bottlenecks

| Metric | HW7 | HW8 |
|---|---|---|
| Concurrent agents | 1 | **30–60** |
| Total runs logged | 15 | **153** |
| Distinct cloud regions | 1 | **16** |
| Overall success rate | 100% (small n) | **64.7%** (99 / 153) |
| p50 latency | — | **83.3 s** |
| p95 latency | — | **139.6 s (1.7× p50)** |
| Max latency | — | 174.5 s |
| Scout→Pitcher handoff success (after fix) | n/a | **30 / 30** |
| Artifact generation success (email + sheet, after fix) | n/a | **30 / 30** |
| E4 total time (after fix) | n/a | 25.4 s |

### Failure taxonomy (n = 54)

| Error type | Count | Root cause surfaced at scale |
|---|---|---|
| `JSONDecodeError` | 26 | Gemini 2.5 Flash wraps JSON in ` ```json … ``` ` single-line fences. Brand Scout's `json.loads` assumed clean JSON like Claude produces. Only observable once we switched providers under the "API outage" migration path. |
| `BadRequestError` | 15 | Anthropic *"credit balance too low"* — our purchased $15 credit never became API-eligible for reasons Anthropic support hasn't clarified. Identical failures from a direct `curl` confirmed the block is upstream of Modal. |
| `ServerError` (503) | 5 | Gemini *"model overloaded, try again later"* — appeared when 5+ containers fired Flash calls simultaneously. Retries with exponential backoff fixed this. |
| `ClientError` (429) | 8 | Gemini free-tier daily quota (20 req/day on `generate_content_free_tier_requests`). Completely invisible at HW7 scale. Resolved by upgrading to pay-as-you-go billing mid-experiment. |

### New failure modes that only appeared at scale

1. **Provider-level provisioning opacity** — Anthropic kept rejecting API
   calls with "credit balance too low" despite $15 purchased credit and
   $100 spend limit. Direct `curl` from our laptop reproduced it. We
   couldn't resolve this in the experiment window, which forced the
   cross-provider migration.
2. **Free-tier per-day ceilings** — Gemini Flash's free-tier limit is
   **20 requests / day**, not the "1500 / day" we assumed from older
   docs. At 30-way concurrency with ~6 LLM calls per Scout run, we hit
   it on the second batch. A $10 prepaid credit fixed it and turned
   Pitcher cost into ~$0.002 per brand.
3. **LLM-provider contract drift** — Gemini's default *thinking mode*
   consumes output tokens before emitting visible text, producing
   suspicious 35-token "emails" at first. Disabling with
   `thinking_config=0` restored proper outputs. Non-obvious because
   neither our prompt nor the SDK mentions thinking.
4. **Parallel LangGraph node races** — Pitcher runs `draft_email` and
   `draft_sell_sheet` concurrently. Both nodes updated `input_tokens`
   and `artifact_errors`. LangGraph raised
   `InvalidUpdateError: Can receive only one value per step` on all 26
   pitches in the first E4 run. Fixed by adding `Annotated[int,
   operator.add]` reducers to the state class. This is exactly the
   multi-agent coordination bug our HW5 proposal warned about —
   observable only once both agents ran in separate cloud containers.
5. **Cross-provider divergence** — Pitcher on Gemini returned JSON
   consistently wrapped in ` ```json … ``` ` markdown fences on one
   line, while Scout on Claude produced clean JSON. Our fence-stripper
   initially assumed a newline after the language tag. Two different
   providers = two different output conventions to normalize.
6. **Region-dependent scraping drift** — Firecrawl egress IPs differ
   per Modal region, so repeat evaluations of the same brand from
   different regions surface different retailer pages. E2 success rate
   (77 %) was lower than E1 (90 %) for the same brands — the
   incremental failures all happened when two containers of the same
   brand ran in different regions.

## What we added or improved

- **`agents/retailer_pitcher/`** — new first-class agent, sibling to
  `agents/brand_scout/`. LangGraph with `load_scout_context →
  select_buyer → (draft_email ‖ draft_sell_sheet) → store_artifacts
  → human_approval`. Produces (1) a buyer-specific outreach email and
  (2) a 1-page HTML sell sheet that is screenshot- / print-ready. Three
  buyer personas shipped (Whole Foods, Sprouts, Erewhon). This closes
  the HW6 deliverable the team had deferred.
- **`agents/llm_shim.py`** — Anthropic-compatible shim that routes
  Brand Scout's `anthropic.Anthropic(...)` calls to Gemini when
  `SEDGE_LLM_PROVIDER=gemini`. Monkey-patches the `anthropic` module
  so zero changes are needed in Brand Scout's 872-line graph. Handles
  code-fence stripping, retry-with-backoff for 503/429, thinking-mode
  suppression, and JSON mime-type switching.
- **State-reducer fix** in `state.py` — `RetailerPitcherState` uses
  `Annotated[list[str], operator.add]` and `Annotated[int,
  operator.add]` for fields that parallel nodes write to, eliminating
  the `InvalidUpdateError`.
- `hw8/modal_runner.py` — Brand Scout fan-out with per-run telemetry
  (region, container id, tokens, latency, status).
- `hw8/modal_handoff.py` — first real two-agent pipeline in Sedge,
  coordinated only through shared memory, separating `handoff_status`
  (memory-layer) from `artifact_status` (LLM/render-layer).
- `hw8/modal_pitch_only.py` — lets us iterate on Pitcher without
  re-running Scout. Saved ~10 minutes and ~$0.50 every retry.
- `hw8/analyze.py` — reproducible analysis: one command, five figures
  (`latency.png`, `failure_modes.png`, `consistency.png`,
  `handoff.png`, plus `SUMMARY_DATA.json`).
- `hw8/brands.csv` — 50-brand benchmark, reusable for Demo Day.

## Links

- Repo: https://github.com/isabeldeatucha-spec/sedge (`hw8/` folder)
- Production demo: https://sedge-production.up.railway.app
- Modal dashboard: https://modal.com/apps/liuyiodile/main
- Video (1 min, unlisted): `<paste YouTube link>`
