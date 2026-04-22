from agents.orchestrator.contracts import (
    ScoutHandoff, PitcherHandoff, AdminHandoff, RoutingDecision,
)


def test_scout_handoff_ok():
    h = ScoutHandoff(brand_name="Chomps", verdict="established", score_total=87)
    assert h.is_ok()
    assert not h.is_stale()


def test_scout_handoff_miss():
    h = ScoutHandoff.miss("Nonexistent")
    assert h.handoff_status == "miss"
    assert not h.is_ok()


def test_routing_too_early():
    r = RoutingDecision.from_verdict("too_early")
    assert not r.run_pitcher and not r.run_admin


def test_routing_broker_ready():
    r = RoutingDecision.from_verdict("broker_ready")
    assert r.run_pitcher and r.run_admin
    assert r.pitcher_framing == "standard"


def test_routing_established():
    r = RoutingDecision.from_verdict("established")
    assert r.run_pitcher and r.run_admin
    assert r.pitcher_framing == "upgrade_broker"
