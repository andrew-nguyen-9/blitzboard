"""Tests for multi-source NFL team reconciliation + publish gate.

Covers the bug this unit fixes (Mixon/Najee reported as FA by one source must
resolve to the real team), authority precedence, recency tie-breaks, confidence,
alias-driven false mismatches, and the publish gate (pass + block).
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from blitz_engine.data.reconcile import (
    PublishBlocked,
    TeamObservation,
    canon_team,
    from_sleeper,
    reconcile_teams,
    validate_publish,
)


def _obs(pid, team, source, day=1):
    return TeamObservation(pid, team, source, datetime(2025, 9, day, tzinfo=UTC))


def test_assigned_beats_fa_mixon_najee():
    """The core bug: a source calling a player FA must not win over a real team."""
    obs = [
        _obs("mixon", None, "sleeper"),      # stale/incomplete → FA
        _obs("mixon", "CIN", "nflverse"),    # canonical truth
        _obs("najee", "FA", "espn"),
        _obs("najee", "PIT", "nflverse"),
    ]
    res = {r.player_id: r for r in reconcile_teams(obs)}
    assert res["mixon"].team == "CIN"
    assert res["najee"].team == "PIT"
    assert not res["mixon"].unassigned


def test_disagreement_resolves_to_authoritative_team():
    """Two sources assign different teams → the more authoritative one wins."""
    obs = [
        _obs("p1", "NYJ", "espn"),        # authority 1, wrong
        _obs("p1", "BUF", "nflverse"),    # authority 3, right
    ]
    (r,) = reconcile_teams(obs)
    assert r.team == "BUF"
    assert r.source == "nflverse"
    assert r.mismatch is True
    assert r.confidence == 0.5  # 1 of 2 assigning sources agreed with winner


def test_recency_breaks_ties_within_same_authority():
    obs = [
        _obs("p1", "DEN", "sleeper", day=1),
        _obs("p1", "LV", "sleeper", day=20),  # fresher same-authority source wins
    ]
    (r,) = reconcile_teams(obs)
    assert r.team == "LV"


def test_alias_not_counted_as_mismatch_and_full_confidence():
    obs = [
        _obs("p1", "JAC", "sleeper"),
        _obs("p1", "JAX", "nflverse"),  # same team, drifted abbrev
    ]
    (r,) = reconcile_teams(obs)
    assert r.team == "JAX"
    assert r.mismatch is False
    assert r.confidence == 1.0


def test_no_source_assigns_team_is_unassigned():
    obs = [_obs("ghost", None, "sleeper"), _obs("ghost", "FA", "espn")]
    (r,) = reconcile_teams(obs)
    assert r.team is None
    assert r.unassigned
    assert r.confidence == 0.0


def test_canon_team_markers():
    assert canon_team("fa") is None
    assert canon_team("") is None
    assert canon_team(None) is None
    assert canon_team(" wsh ") == "WAS"
    assert canon_team("KC") == "KC"


def test_reconcile_is_deterministic_and_pure():
    obs = [_obs("b", "SF", "nflverse"), _obs("a", "GB", "nflverse")]
    first = reconcile_teams(obs)
    second = reconcile_teams(obs)
    assert first == second
    assert [r.player_id for r in first] == ["a", "b"]  # ordered by player id


def test_publish_gate_passes_when_clean():
    obs = [_obs(f"p{i}", "KC", "nflverse") for i in range(20)]
    res = reconcile_teams(obs)
    assert validate_publish(res) == res  # returns unchanged on pass


def test_publish_gate_blocks_on_too_many_unassigned():
    obs = []
    for i in range(10):
        team = None if i < 3 else "KC"  # 30% unassigned > 10% default threshold
        obs.append(_obs(f"p{i}", team, "nflverse"))
    res = reconcile_teams(obs)
    with pytest.raises(PublishBlocked) as exc:
        validate_publish(res)
    assert set(exc.value.unassigned) == {"p0", "p1", "p2"}


def test_publish_gate_blocks_on_too_many_mismatches():
    obs = []
    for i in range(10):
        obs.append(_obs(f"p{i}", "KC", "nflverse"))
        if i < 3:  # 30% mismatch > 5% default threshold
            obs.append(_obs(f"p{i}", "DEN", "espn"))
    res = reconcile_teams(obs)
    with pytest.raises(PublishBlocked) as exc:
        validate_publish(res)
    assert set(exc.value.mismatched) == {"p0", "p1", "p2"}


def test_publish_gate_empty_is_noop():
    assert validate_publish([]) == []


def test_from_sleeper_accepts_mapping_keyed_by_id():
    """Sleeper /players/nfl shape: dict keyed by player id → observations."""
    payload = {"4034": {"team": "CIN"}, "6813": {"team": None}}
    obs = from_sleeper(payload)
    by_id = {o.player_id: o for o in obs}
    assert by_id["4034"].team == "CIN"
    assert by_id["4034"].source == "sleeper"
    assert by_id["6813"].team is None
