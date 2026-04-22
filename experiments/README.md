# Experiments

Reproducible benchmarks for the Sedge Coordination Protocol.

## compare_strategies.py

Compares sequenced + verdict-gated orchestration (our protocol) against a
concurrent baseline. Outputs a markdown report + raw JSON.

### Run

```bash
python -m experiments.compare_strategies --brands Chomps Fishwife Graza
```

Results land in `experiments/results/`.

### Expected output

On cached brands (brands already in `brand_evaluations`), the sequenced
strategy completes in 2–5 seconds per brand. The concurrent strategy
completes faster if no rate limits or state races are hit, and fails
with `InvalidUpdateError` or 429 if the LangGraph reducers are disabled
or the API free tier is exhausted.

See the generated `comparison_*.md` report for interpretation.
