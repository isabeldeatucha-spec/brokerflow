from agents.retailer_matcher.matcher import (
    recommend_retailers, _rule_based_recommendation,
)


def test_too_early_skips_all():
    recs = recommend_retailers("Unknown", "unknown", "too_early", 30)
    assert all(r.fit_score < 70 for r in recs)


def test_established_beverage_favors_whole_foods():
    recs = _rule_based_recommendation("beverage_rtd", "established")
    assert recs[0].retailer == "whole_foods"
    assert recs[0].tier in ("strong", "possible")


def test_supplement_favors_sprouts_erewhon():
    recs = _rule_based_recommendation("supplement_functional", "established")
    top_two = [r.retailer for r in recs[:2]]
    assert "sprouts" in top_two or "erewhon" in top_two
