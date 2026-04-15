# HW8 — Sedge: Scaled Multi-Agent Experiments

**Isabel de Atucha · Yi Liu · Sasha Towe** | Repo: `github.com/isabeldeatucha-spec/sedge` | Demo: `sedge-production.up.railway.app` | Video: `<paste YouTube link>`

## What changed since HW7
HW7 ran **Brand Scout on a laptop**: 3 agents × 5 brands = 15 serial runs, single LLM (Claude Sonnet), single region. HW8 deploys the same graph to **30–60 parallel Modal containers across 16 cloud regions**, adds the **full Retailer Pitcher agent** (LangGraph: email + HTML sell sheet, 3 buyer personas), expands the test set 5 → **50 brands**, and migrates Brand Scout to a **cross-provider stack** (Claude shim → Gemini Flash) after our personal Anthropic account was blocked at the provisioning layer mid-experiment.

## Scaled setup
- **Compute**: Modal serverless, `max_containers=60`, observed 16 distinct cloud regions (us-east-1/2, us-west-2/3, eastus, eastus2, westus3, uksouth, italynorth, eu-west-1, me-west1, asia-southeast1, southeastasia, australia-southeast1, us-central1).
- **Agents**: Brand Scout (existing) + Retailer Pitcher (new — `agents/retailer_pitcher/`). Coordination via Supabase shared memory only — no shared process between Scout and Pitcher containers.
- **Workload**: 50 CPG brands. **E1** Throughput (50 × 1 = 50 jobs). **E2** Consistency (10 × 3 = 30 jobs). **E3** Cost (per-run tokens). **E4** Two-agent handoff (30 brands × Scout-container → Pitcher-container).
- **Telemetry per run**: latency, status, error type, region, container id, score breakdown, input/output tokens.

## Results / failures / bottlenecks

| Metric | HW7 | HW8 |
|---|---|---|
| Concurrent agents | 1 | **30–60** |
| Distinct cloud regions | 1 | **16** |
| Total runs logged | 15 | **153** |
| Overall success rate | 100% (n=15) | **64.7%** (99/153, includes debugging) |
| p50 / p95 / max latency | — | **83 / 140 / 175 s** (p95 = 1.7× p50) |
| E4 Scout→Pitcher handoff (after fix) | n/a | **30/30** memory + **30/30** artifact in 25 s |

**Failure taxonomy (n=54)**: `JSONDecodeError` 26 (Gemini wrapped JSON in single-line ` ```json …``` ` fences — Claude-tuned parser broke), `BadRequestError` 15 (Anthropic billing rejected purchased credit), `ServerError 503` 5 (Gemini overloaded under concurrency), `ClientError 429` 8 (Gemini free-tier 20/day ceiling).

**Four scale-only bugs** that did **not** show up in HW7:
1. **Provider provisioning opacity** — Claude $15 purchased credit unusable through API; reproduced with `curl`. Triggered cross-provider migration mid-experiment.
2. **Hidden free-tier per-day ceiling** — Gemini Flash limits free tier to **20 requests/day**, not the "1500/day" we believed. Hit on the second batch. Fixed by upgrading to pay-as-you-go (~$1 total).
3. **LLM contract drift** — Gemini's default *thinking mode* consumes output tokens before emitting visible text → 35-token "emails". Disabled with `thinking_config=0`. Different markdown-fence conventions per provider also broke our JSON parser.
4. **Parallel LangGraph node race** — Pitcher's `draft_email` and `draft_sell_sheet` both wrote `input_tokens`. LangGraph raised `InvalidUpdateError: Can receive only one value per step` on **all 26** pitches in the first E4 run. Fixed with `Annotated[int, operator.add]` reducers in the state class — the exact multi-agent coordination bug HW5 warned about, observable only once both agents ran in separate containers.

Two more scale-pressure observations: (a) E2 success rate dropped to 77% (vs E1's 90%) because repeating the same brand from different Modal egress regions surfaces different Firecrawl snapshots; (b) p95 latency stretches to 1.7× p50 once we cross 30 concurrent agents — the system degrades gracefully, but the long tail is real.

## What we added or improved
- **`agents/retailer_pitcher/`** — first-class LangGraph agent (sibling to Brand Scout) with `load_scout_context → select_buyer → (draft_email ‖ draft_sell_sheet) → store_artifacts → human_approval`. Three buyer personas (Whole Foods, Sprouts, Erewhon). Closes the HW6 deliverable our team had deferred.
- **`agents/llm_shim.py`** — Anthropic-compatible shim that monkey-patches `anthropic.Anthropic` to route Brand Scout's 6 LLM call sites to Gemini, with code-fence stripping, exponential-backoff retry on 503/429, thinking-mode suppression, and JSON mime-type switching. Zero changes needed in Brand Scout's 872-line graph.
- **State reducer fix** in `state.py` — `Annotated` reducers on `input_tokens`, `output_tokens`, `artifact_errors` for parallel-write safety.
- **`hw8/`** harness — `modal_runner.py`, `modal_handoff.py`, `modal_pitch_only.py` (lets us iterate on Pitcher without re-running Scout — saved ~10 min and ~$0.50 every retry), `analyze.py` (one command, four figures + JSON summary), `brands.csv` (50-brand benchmark, reusable for Demo Day).
