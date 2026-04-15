# Google Slides — 1 slide for HW8

Paste / adapt into the shared deck.

---

## Title
**Sedge — Scaling Brand Scout from 1 → 30+ cloud agents**

## Subtitle
Independent food-broker AI · Isabel de Atucha, Yi Liu, Sasha Towe

## Left column — "From HW7"
- Brand Scout: single LangGraph agent, laptop-local
- 3 repeats × 5 brands = **15 runs**
- Stddev <3 on most brands, one verdict flip (Olipop)
- Never tested under concurrency

## Right column — "HW8 at scale"
- **30–60 Modal containers**, 2 US regions, independent processes
- 50-brand benchmark
- **Built full Retailer Pitcher agent** (email + HTML sell sheet, 3 buyer
  personas) — sibling of Brand Scout, handoff via Supabase
- **Cross-provider by design**: Scout on Claude Sonnet 4.5, Pitcher on
  Gemini 2.5 Flash — 30× cheaper Pitcher + independent rate-limit regimes
- Measured: latency p50/p95, failure taxonomy, per-brand consistency drift,
  handoff-layer vs artifact-layer success rates

## Bottom band — "What breaks at scale"
1. Firecrawl 429s at 30-way concurrency (no HW7 signal — credits ran out silently)
2. Anthropic per-org rate limit → p95 latency ≫ p50
3. `handoff_miss`: Pitcher fires before Scout commits memory — our first
   real multi-agent race condition
4. Region-dependent scraping drift widens verdict disagreement

## Visual (one image on the slide)
Use `hw8/figs/latency.png` — sorted per-run latency, p50 / p95 lines.
Caption: *"p95 latency is 3× p50 once we cross 30 concurrent agents —
the system degrades gracefully on Brand Scout, hard on Retailer Pitcher."*
