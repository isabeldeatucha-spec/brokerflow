# 1-minute YouTube video script (HW8)

Target: 55–60 seconds. Screen-record Modal dashboard + terminal + one figure.

---

**[0:00 – 0:08] Recap HW7 (voiceover over HW7 score table)**
> "In HW7, Sedge's Brand Scout agent ran on one laptop — three agents, five
> brands, fifteen total runs. Consistent scores, happy path."

**[0:08 – 0:18] The question (cut to terminal)**
> "HW8 question: what happens when we scale this to thirty agents running
> on the cloud in parallel — the setting a real broker serving twenty
> brands would actually hit?"

**[0:18 – 0:32] The setup (Modal dashboard showing live containers)**
> "We deployed Brand Scout to Modal — one container per evaluation, up to
> sixty concurrent, two US regions. Fifty-brand benchmark. And we added a
> second agent, the Retailer Pitcher, so Brand Scout hands off state to it
> through shared memory — a true cross-agent handoff."

**[0:32 – 0:48] Results (cut to latency.png, then failure_modes.png)**
> "What we learned: p95 latency is roughly three times p50 once we cross
> thirty agents. Firecrawl rate-limits and Anthropic concurrent-request
> caps are the real ceiling, not our graph. And the handoff has a race —
> about one in seven Pitcher calls fires before Brand Scout has committed
> its memory row."

**[0:48 – 0:60] What's next (cut to SUMMARY.md)**
> "Next up: retry and back-pressure around Firecrawl, an explicit handoff
> barrier between agents, and adding Admin Ops and Portfolio Manager for
> Demo Day."

---

## Recording checklist

1. Open Modal dashboard — filter to `sedge-hw8` app; show concurrent container count.
2. Terminal: `modal run hw8/modal_runner.py --brands hw8/brands.csv --repeats 1`
3. Let it run ~30s; switch to `python hw8/analyze.py`; show `figs/latency.png`
   and `figs/failure_modes.png`.
4. End on `hw8/SUMMARY.md` open in VS Code.
5. Export 1080p, upload unlisted, paste link into `SUMMARY.md`.
