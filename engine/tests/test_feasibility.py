"""E4 — feasibility surface: byes x availability x injury, per week, per league config."""
from __future__ import annotations

import numpy as np
import pytest

from blitz_engine.lineup.feasibility import (
    WEEKS,
    InjuryDynamics,
    feasibility_surface,
    requirements_from_row,
    sample_surface,
)
from blitz_engine.survival.availability import ZERO_AVAILABILITY_EPS
from blitz_engine.testing import matrix
from blitz_engine.value.roster_solver import Player, RosterRequirements

SEED = 7
HEALTHY = InjuryDynamics.healthy()


def _player(pid: str, pos: str, value: float, bye: int | None = None) -> Player:
    return Player(id=pid, position=pos, value=value, bye_week=bye)


def _roster(byes: dict[str, int] | None = None) -> list[Player]:
    """A deep, config-agnostic roster: fills 1qb / 2qb / superflex boards alike."""
    byes = byes or {}
    counts = {"QB": 3, "RB": 5, "WR": 6, "TE": 3, "K": 2, "DST": 2}
    out: list[Player] = []
    for pos, n in counts.items():
        for i in range(n):
            pid = f"{pos}{i + 1}"
            out.append(_player(pid, pos, value=20.0 - 2.0 * i, bye=byes.get(pid)))
    return out


# -- e3's dynamics are read, not re-derived --------------------------------------------------
def test_published_event_is_clinical_injury_not_snap_presence():
    """The guard against a silent double-count: e2a is snap presence, e3 must not be."""
    dyn = InjuryDynamics.load()
    assert "clinical injury" in dyn.event
    assert "NOT snap-presence" in dyn.event


@pytest.mark.parametrize("position", ["QB", "RB", "WR", "TE", "K"])
def test_chain_stationary_out_mass_reproduces_published_rate(position):
    """The renewal-identity recovery is calibrated: stationary P(out) == e3's `injuryRate`."""
    dyn = InjuryDynamics.load()
    assert dyn.stationary(position)[-1] == pytest.approx(dyn.rate[position], abs=5e-3)


def test_no_injury_rate_is_hard_coded_here():
    """Every number comes from the fixture — a healthy model has no injuries at all."""
    assert HEALTHY.play_weight("RB", WEEKS).min() == pytest.approx(1.0)
    assert InjuryDynamics.load().play_weight("RB", WEEKS).max() < 1.0


def test_out_now_player_recovers_over_the_surface():
    dyn = InjuryDynamics.load()
    w = dyn.play_weight("RB", WEEKS, out_now=True)
    assert w[0] == pytest.approx(0.0)
    assert np.all(np.diff(w[:8]) > 0)  # monotone recovery toward the stationary level


# -- the surface -----------------------------------------------------------------------------
def test_all_available_roster_costs_zero_every_week():
    """No byes, no exclusions -> the stationary chain gives every week the same expectation."""
    surface = feasibility_surface(_roster(), injury=InjuryDynamics.load())
    assert surface.legal
    assert surface.costs().max() == pytest.approx(0.0, abs=1e-3)
    assert surface.total_cost() == pytest.approx(0.0, abs=1e-2)


def test_whole_starting_lineup_on_one_bye_is_infeasible_or_maximally_costly():
    reqs = RosterRequirements(
        starters=("QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DST"), bench_size=0
    )
    starters = [
        _player(pid, pos, 20.0, bye=9)
        for pid, pos in [
            ("QB1", "QB"), ("RB1", "RB"), ("RB2", "RB"), ("WR1", "WR"),
            ("WR2", "WR"), ("TE1", "TE"), ("RB3", "RB"), ("K1", "K"), ("DST1", "DST"),
        ]
    ]
    surface = feasibility_surface(starters, reqs, injury=HEALTHY)
    week9 = surface.week(9)
    assert not week9.legal
    assert week9.expected_points == 0.0
    assert week9.cost_vs_baseline == pytest.approx(surface.baseline)
    assert surface.infeasible_weeks() == (9,)


def test_bench_cover_at_the_shortfall_position_reduces_cost_monotonically():
    """Each added TE covers more of the week-9 TE shortfall; cost never increases."""
    reqs = RosterRequirements(starters=("QB", "RB", "WR", "TE"), bench_size=4)
    base = [
        _player("QB1", "QB", 20.0), _player("RB1", "RB", 18.0),
        _player("WR1", "WR", 16.0), _player("TE1", "TE", 14.0, bye=9),
    ]
    covers = [_player("TE2", "TE", 6.0), _player("TE3", "TE", 11.0)]
    costs = [
        feasibility_surface(base + covers[:k], reqs, injury=HEALTHY).week(9).cost_vs_baseline
        for k in range(len(covers) + 1)
    ]
    assert costs[0] == pytest.approx(sum(p.value for p in base))  # illegal -> full baseline
    assert all(later <= earlier + 1e-6 for earlier, later in zip(costs, costs[1:], strict=False))
    assert costs[-1] < costs[0]


def test_superflex_changes_the_verdict_for_a_qb_thin_roster():
    """One QB is legal in 1qb, and infeasible in 2qb — legality is config-dependent."""
    thin = [
        _player("QB1", "QB", 22.0), _player("RB1", "RB", 18.0), _player("RB2", "RB", 15.0),
        _player("WR1", "WR", 17.0), _player("WR2", "WR", 14.0), _player("TE1", "TE", 11.0),
        _player("RB3", "RB", 9.0), _player("WR3", "WR", 8.0),
        _player("K1", "K", 8.0), _player("DST1", "DST", 7.0),
    ]
    rows = {r["qb_mode"]: r for r in matrix.all() if r["teams"] == 12 and r["scoring"] == "ppr"}
    verdicts = {
        mode: feasibility_surface(thin, row, injury=HEALTHY).legal for mode, row in rows.items()
    }
    assert verdicts["1qb"] is True
    assert verdicts["superflex"] is True  # a RB/WR/TE may fill SUPERFLEX
    assert verdicts["2qb"] is False  # a second true QB does not exist on this roster


def test_requirements_from_row_bakes_qb_mode_into_legality():
    by_mode = {r["qb_mode"]: requirements_from_row(r) for r in matrix.all() if r["teams"] == 8}
    assert by_mode["1qb"].starters.count("QB") == 1
    assert "SUPERFLEX" not in by_mode["1qb"].starters
    assert by_mode["2qb"].starters.count("QB") == 2
    assert by_mode["superflex"].starters.count("SUPERFLEX") == 1


# -- e2a's availability, read through its own interface --------------------------------------
def test_effectively_unavailable_players_are_excluded_not_discounted():
    """e2a moved practice squad to ~0.004 — below its eps, so the body is dropped outright."""
    reqs = RosterRequirements(starters=("QB", "RB"), bench_size=2)
    roster = [_player("QB1", "QB", 20.0), _player("RB1", "RB", 18.0), _player("RB2", "RB", 5.0)]
    ps = ZERO_AVAILABILITY_EPS / 2.0
    surface = feasibility_surface(
        roster, reqs, availability={"RB1": ps}, injury=HEALTHY
    )
    assert surface.excluded == ("RB1",)
    assert surface.week(1).expected_points == pytest.approx(25.0)  # RB2 starts, not a discount


def test_availability_scales_expected_points_linearly():
    reqs = RosterRequirements(starters=("QB",), bench_size=0)
    roster = [_player("QB1", "QB", 20.0)]
    full = feasibility_surface(roster, reqs, injury=HEALTHY).week(1).expected_points
    half = (
        feasibility_surface(roster, reqs, availability={"QB1": 0.5}, injury=HEALTHY)
        .week(1)
        .expected_points
    )
    assert half == pytest.approx(full * 0.5)


def test_ir_slots_absorb_the_excluded_and_overflow_is_reported():
    row = next(r for r in matrix.all() if r["ir_slots"] == 1 and r["qb_mode"] == "1qb")
    roster = _roster()
    unavailable = dict.fromkeys(["WR5", "WR6"], ZERO_AVAILABILITY_EPS / 10.0)
    surface = feasibility_surface(roster, row, availability=unavailable, injury=HEALTHY)
    assert set(surface.excluded) == {"WR5", "WR6"}
    assert (surface.ir_stashed, surface.ir_overflow) == (1, 1)


# -- config matrix ---------------------------------------------------------------------------
def test_surface_never_raises_across_the_whole_matrix():
    roster = _roster(byes={"QB1": 5, "RB1": 5, "WR1": 9, "TE1": 12, "K1": 5, "DST1": 9})
    for row in matrix.all():
        surface = feasibility_surface(roster, row, injury=HEALTHY)
        assert len(surface.weeks) == WEEKS
        assert surface.baseline > 0.0
        assert all(w.cost_vs_baseline >= -1e-6 for w in surface.weeks)


def test_bye_weeks_are_the_only_costly_weeks():
    roster = _roster(byes={"QB1": 7, "QB2": 7, "QB3": 7})
    surface = feasibility_surface(roster, matrix.by_id("t12-2qb-ppr-te0.0-b6-ir1"), injury=HEALTHY)
    assert surface.infeasible_weeks() == (7,)
    assert all(w.cost_vs_baseline == 0.0 for w in surface.weeks if w.week != 7)


# -- the distribution, from the same chain ---------------------------------------------------
def test_sample_surface_is_deterministic_and_brackets_the_expectation():
    roster = _roster(byes={"RB1": 6, "WR1": 6})
    row = matrix.smoke()[0]
    kw = {"n_samples": 24, "weeks": 6, "injury": InjuryDynamics.load()}
    points_a, illegal_a = sample_surface(roster, row, rng=SEED, **kw)
    points_b, illegal_b = sample_surface(roster, row, rng=SEED, **kw)
    np.testing.assert_array_equal(points_a, points_b)
    np.testing.assert_array_equal(illegal_a, illegal_b)

    expected = feasibility_surface(roster, row, weeks=6, injury=kw["injury"]).points()
    # A deep roster substitutes around injuries, so the sample mean tracks the expectation.
    assert points_a.mean(axis=0) == pytest.approx(expected, rel=0.25)
    # Deep, but not immune: two kickers can both be out in the same sampled week.
    assert illegal_a.max() < 0.1


def test_sampled_illegality_appears_where_the_expectation_cannot_show_it():
    """Injury is binary in one season: a thin board can fail even when its expectation is legal."""
    reqs = RosterRequirements(starters=("QB", "QB"), bench_size=0)
    roster = [_player("QB1", "QB", 20.0), _player("QB2", "QB", 18.0)]
    dyn = InjuryDynamics.load()
    assert feasibility_surface(roster, reqs, injury=dyn).legal
    _, illegal = sample_surface(roster, reqs, rng=SEED, n_samples=64, weeks=6, injury=dyn)
    assert illegal.max() > 0.0


def test_sample_and_expectation_share_one_chain():
    """Mean sampled multiplier converges to the analytic one — not a second fit."""
    dyn = InjuryDynamics.load()
    rng = np.random.default_rng(SEED)
    drawn = dyn.sample_weight("WR", WEEKS, 4000, rng)
    np.testing.assert_allclose(drawn.mean(axis=0), dyn.play_weight("WR", WEEKS), atol=0.02)
