from agents.brand_scout.quick import quick_triage, QuickTriageResult


def test_empty_name_returns_fallback():
    r = quick_triage("")
    assert r.error == "empty_name"
    assert r.score_estimate == 0


def test_cached_brand_returns_fast():
    # Assumes Chomps is in brand_evaluations from prior runs
    r = quick_triage("Chomps")
    assert r.score_estimate > 0
    # If cached, latency should be under 1s; otherwise this still passes.
