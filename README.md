# BrokerFlow

An AI-powered operating system for independent CPG food brokers. BrokerFlow replaces the manual research, pitching, and paperwork that brokers do by hand with a multi-agent workspace that runs continuously across their entire book of business.

**[Live app](https://retailer-pitcher-production.up.railway.app)** · **[Documentation](https://retailer-pitcher-production.up.railway.app/?page=docs)** · **[GitHub](https://github.com/isabeldeatucha-spec/sedge)**

---

## What it does

### Your book of business
A persistent workspace for every brand a broker represents. Two agents — Retailer Pitcher and Admin & Ops — run continuously across the book and surface items that need human review. Brokers see what each agent has done, approve or edit drafts, and onboard new brands.

### Brand Scout (new brand qualification)
Evaluates whether a CPG brand is worth pursuing. Enter a brand name; BrokerFlow researches it across Amazon, Instacart, Faire, social media, and trade press, then scores it on five criteria:

| Criterion | Weight | What it measures |
|---|---|---|
| Velocity Proof | 25 pts | Amazon ratings/reviews, Subscribe & Save, SPINS mentions |
| Distribution Density | 20 pts | Door count, retail chain presence, Faire listing |
| Margin Viability | 20 pts | SRP vs. category benchmarks, funding raised |
| Brand Story Clarity | 20 pts | Hero SKU, certifications, social following, press |
| Promotional Independence | 15 pts | DTC channel, TPR frequency, Subscribe & Save |

Verdict thresholds: **Established** (70+), **Broker Ready** (45–69), **Too Early** (<45).

### Retailer Pitcher
Drafts buyer-persona-tailored outreach emails and one-page sell sheets for Whole Foods, Sprouts, and Erewhon. Each pitch is adapted to what the specific buyer cares about, what kills a pitch with them, and which proof points resonate.

### Admin & Ops
Autofills the Whole Foods New Item Setup Form (~70 fields across 10 sections) from everything BrokerFlow knows about the brand. Two-pass fill: deterministic rule-based first, LLM inference for ambiguous fields. Exports a ready-to-submit Excel file and flags required gaps.

### Brand Onboarding
Three-step onboarding flow (brand info form → agent processing → review) that adds a brand to the book, extracts a canonical record from uploaded materials (PDF, DOCX, XLSX), and hands off to Retailer Pitcher and Admin & Ops automatically.

---

## Architecture

```
ui/brokerflow_app.py              ← Streamlit app, workspace router
ui/per_agent_page.py         ← Retailer Pitcher + Admin & Ops agent pages
ui/onboarding_flow.py        ← Brand onboarding 3-step UI

agents/
  brand_scout/               ← Research + scoring (LangGraph, 10-tool ReAct loop)
  retailer_pitcher/          ← Email + sell sheet generation per buyer persona
  admin_ops/                 ← WFM form autofill + gap flagging
  brand_onboarding/          ← Canonical record extraction from uploaded docs
  retailer_matcher/          ← Buyer heuristic (score + category → buyer_key)
  orchestrator/              ← Pipeline wiring all agents together
  llm_shim.py                ← Routes anthropic.Anthropic() calls to Gemini or Claude

memory.py                    ← Supabase client + persistence helpers
state.py                     ← Shared TypedDict state types

supabase/
  schema.sql                 ← Full schema reference
  migrations/                ← Applied migration files
```

### Agent coordination — BrokerFlow Coordination Protocol v1

BrokerFlow implements a typed pub-sub coordination protocol on top of a shared Supabase blackboard. Inspired by MCP/A2A, specialized for the broker-agent domain. Agents do not call each other directly — they publish typed events, and a background runner dispatches them to subscribers.

**Primitives** (see [agents/coordination/protocol.py](agents/coordination/protocol.py)):

| Primitive | Implementation |
|---|---|
| **Typed events** | Versioned `EventType` enum (`v1.brand_onboarded`, `v1.pitch_drafted`, ...) |
| **Publish** | `publish(from_agent, to_agent, brand_id, event_type, payload)` → blackboard insert |
| **Subscribe** | `@subscribe(EventType.X, subscriber="agent_name")` decorator on a handler |
| **Dispatch** | Background daemon polls unconsumed messages every 3s, routes to handlers |
| **Ack** | `consumed_at` timestamp set on success — at-least-once delivery semantics |
| **Idempotency** | In-tick dedup on `(brand_id, message_type)` to handle retries |
| **Failure handling** | On handler exception, publish `v1.handler_failed` event, ack original |

**Demo chain — fully autonomous after one trigger:**

```
user → BRAND_ONBOARDED
              ↓ (runner picks up, dispatches to subscriber)
       Retailer Pitcher
              ↓ PITCH_DRAFTED  (or PITCH_FAILED — chain continues either way)
       Admin & Ops
              ↓ FORM_GAPS_FLAGGED
       Whole Foods (simulated retailer)
              ↓ PO_RECEIVED
       PO Processing
              ↓ PO_VALIDATED  or  PO_DISPUTE_NEEDED
            END
```

The full chain runs without any further human input. Each agent reads from Supabase, calls its tools (LLM, Excel, web), writes typed events back to the blackboard, and the runner routes the next agent. Failure of any single agent does not stall the chain — `PITCH_FAILED` is a first-class event that Admin & Ops also subscribes to.

**Why this qualifies as a coordination protocol, not just plumbing:**

- **Autonomy** — agents act without prompting; runner ticks every 3s
- **Memory** — Supabase persists every message + ack state; survives process restart
- **Tool use** — Anthropic, Supabase, openpyxl, Firecrawl, Excel template
- **Coordination** — typed pub-sub, multi-agent task chain, failure-resilient

**Live observability** — the book-of-business page renders the live message bus ([ui/coordination_log.py](ui/coordination_log.py)) so you can watch typed events flow between agents in real-time. Click "▶ Run demo chain" to kick off an end-to-end run on Olipop.

State within a single agent run is managed by LangGraph's `MemorySaver` checkpointer (in-process, per thread).

### Database schema

| Table | Written by | Read by |
|---|---|---|
| `brands` | Brand Onboarding | All agents |
| `brand_evaluations` | Brand Scout | Retailer Pitcher, Admin & Ops |
| `brand_events` | Brand Onboarding | — |
| `coordination_messages` | All agents | Book of business UI |
| `retailer_pitches` | Retailer Pitcher | Book of business UI |
| `new_item_forms` | Admin & Ops | Book of business UI |

### LLM routing

The `llm_shim` module patches `anthropic.Anthropic` at import time. By default (`SEDGE_LLM_PROVIDER=claude`) all calls go to the real Anthropic SDK. Set `SEDGE_LLM_PROVIDER=gemini` to route all Claude model calls through Gemini 2.5 Flash instead (haiku → Flash Lite, sonnet → Flash), which reduces cost ~50× at some quality tradeoff.

---

## Setup

### Prerequisites

- Python 3.10+
- A [Supabase](https://supabase.com) project
- An [Anthropic API key](https://console.anthropic.com) **or** a [Google AI Studio / Gemini API key](https://aistudio.google.com)
- A [Firecrawl API key](https://www.firecrawl.dev) (for Brand Scout web scraping)

### 1. Clone and install

```bash
git clone https://github.com/isabeldeatucha-spec/sedge.git brokerflow
cd brokerflow
pip install -r requirements.txt
```

### 2. Environment variables

Create a `.env` file in the repo root:

```env
# LLM — pick one provider
ANTHROPIC_API_KEY=sk-ant-...          # required if SEDGE_LLM_PROVIDER=claude (default)
GEMINI_API_KEY=AIza...                # required if SEDGE_LLM_PROVIDER=gemini
SEDGE_LLM_PROVIDER=claude             # "claude" (default) or "gemini"

# Supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJ...                   # anon or service-role key

# Web scraping (Brand Scout)
FIRECRAWL_API_KEY=fc-...
```

### 3. Database setup

Run the following SQL files against your Supabase project in order (Supabase SQL editor or CLI):

```
supabase/schema.sql                              ← base tables
supabase/migrations/2026_04_22_brand_onboarding.sql   ← brands, brand_events, coordination_messages
supabase/migrations/2026_04_22_sku_fields.sql    ← adds product catalog columns
```

The `sent_bundles` table is auto-created on first use via `memory.store_sent_bundle()`.

### 4. Run

```bash
streamlit run ui/brokerflow_app.py
```

The app opens at `http://localhost:8501`.

### 5. Try the sandbox

On the "Your book of business" page, expand "Dev utilities" at the bottom and click **Load sandbox brands** to seed five pre-built CPG brands (Chomps, Fishwife, Graza, Olipop, Magic Spoon) with realistic agent activity, so you can explore the UI without running the agents first.

---

## Deployment

BrokerFlow is configured for [Railway](https://railway.app) via `railway.json`. The start command is:

```
python3 -m streamlit run ui/brokerflow_app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
```

Set the same environment variables in your Railway project settings.

---

## Limitations

**Brand Scout accuracy** — Scores are estimates from public signals (Amazon, Instacart, Faire, trade press). They are not sourced from SPINS, Nielsen, or any paid data provider. Door counts and velocity figures are inferred, not authoritative.

**Retailer Pitcher buyers** — Three buyer personas supported (Whole Foods, Sprouts, Erewhon). KeHE, UNFI, Kroger, and Costco are on the roadmap but not yet wired.

**Admin & Ops forms** — Only the Whole Foods New Item Setup Form is implemented. The form template is the 2018 version; field layouts change periodically.

**No email sending** — BrokerFlow drafts and exports pitches and forms but does not send email. "Send to buyer" buttons are UI placeholders.

**No PO or deduction ingestion** — PO processing, deduction tracking, demo spend reconciliation, and commission reconciliation are on the roadmap (Q2–Q3) but not yet implemented.

**LangGraph checkpointer** — Agent state uses `MemorySaver` (in-process). If the Streamlit process restarts mid-run, in-flight graph state is lost. This does not affect persisted Supabase data.

**Firecrawl dependency** — Brand Scout's web scraping relies on Firecrawl. Without a valid API key, Brand Scout falls back to reduced signal coverage and scores will be less reliable.

---

## Roadmap

| Quarter | Feature |
|---|---|
| Q2 2026 | PO processing (EDI + email ingest) |
| Q2 2026 | Deduction tracking and dispute drafting |
| Q3 2026 | Multi-buyer batch pitches |
| Q3 2026 | Demo spend reconciliation |
| Q3 2026 | Commission reconciliation |
| Q3 2026 | SLA tracking and weekly digest |
| Q3 2026 | More retailers (KeHE, UNFI, Kroger, Costco) |
| Q4 2026 | Buyer relationship tracking |
| Q4 2026 | Multi-broker platform |
