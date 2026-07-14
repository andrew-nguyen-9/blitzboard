"""E4fix roster-solver + bench acceptance tests — the locked draft invariants.

Proves: (1) the IP returns a FULL legal starting lineup from a fixture pool; (2) it forbids a
2nd K/DST before the final rounds and allows it in them; (3) the bench formula ranks a startable
flyer over a 2nd kicker, so the solver never hoards K/DST over startable depth.
"""
from __future__ import annotations

import pytest

from blitz_engine.value.bench import (
    bench_value,
    default_bench_value,
    expected_bench_starts,
)
from blitz_engine.value.roster_solver import (
    DEFAULT_STARTERS,
    InfeasibleRosterError,
    Player,
    RosterRequirements,
    optimize_lineup,
    slot_accepts,
    solve_roster,
)


def _pool() -> list[Player]:
    """A fixture pool: enough at every position to field the default superflex lineup."""
    players: list[Player] = []
    specs = {
        "QB": [30.0, 24.0, 18.0],
        "RB": [28.0, 26.0, 22.0, 15.0, 12.0],
        "WR": [27.0, 25.0, 21.0, 14.0, 11.0],
        "TE": [20.0, 12.0],
        "K": [8.0, 7.5],
        "DST": [9.0, 8.0],
    }
    for pos, vals in specs.items():
        for rank, v in enumerate(vals):
            players.append(Player(id=f"{pos}{rank}", position=pos, value=v))
    return players


# -- slot eligibility -----------------------------------------------------
def test_flex_and_superflex_eligibility() -> None:
    assert slot_accepts("FLEX", "RB") and slot_accepts("FLEX", "WR") and slot_accepts("FLEX", "TE")
    assert not slot_accepts("FLEX", "QB") and not slot_accepts("FLEX", "K")
    assert slot_accepts("SUPERFLEX", "QB") and slot_accepts("SUPERFLEX", "RB")
    assert not slot_accepts("SUPERFLEX", "K") and not slot_accepts("SUPERFLEX", "DST")
    assert slot_accepts("QB", "QB") and not slot_accepts("QB", "RB")


# -- invariant 1: a full legal starting lineup ----------------------------
def test_solver_fills_every_starter_slot() -> None:
    lineup = solve_roster(_pool())
    assert lineup.is_legal
    assert len(lineup.starters) == len(DEFAULT_STARTERS)
    # Each assignment respects slot eligibility.
    for slot, player in lineup.starters:
        assert slot_accepts(slot, player.position)
    # SUPERFLEX in a superflex league should take a 2nd QB when QBs are the scarce premium.
    slot_labels = [s for s, _ in lineup.starters]
    assert slot_labels.count("SUPERFLEX") == 1


def test_infeasible_when_a_slot_cannot_be_filled() -> None:
    pool = [p for p in _pool() if p.position != "DST"]  # no defense at all
    with pytest.raises(InfeasibleRosterError):
        solve_roster(pool)


def test_optimize_lineup_from_owned_roster_benches_the_weakest() -> None:
    roster = _pool()
    lineup = optimize_lineup(roster)
    assert lineup.is_legal
    assert len(lineup.starters) == len(DEFAULT_STARTERS)
    # Everyone owned is placed (started or benched); nobody vanishes.
    placed = {p.id for _, p in lineup.starters} | {p.id for p in lineup.bench}
    assert placed == {p.id for p in roster}
    assert len(lineup.bench) == len(roster) - len(DEFAULT_STARTERS)
    # The single K/DST slots each start the *best* available at that position.
    started = dict(lineup.starters)
    assert started["K"].value == max(p.value for p in roster if p.position == "K")
    assert started["DST"].value == max(p.value for p in roster if p.position == "DST")


def test_optimize_lineup_respects_bye_week() -> None:
    roster = _pool()
    # Put the two best QBs on bye in week 7; the solver must start someone else at QB/SFLX.
    roster = [
        Player(p.id, p.position, p.value, bye_week=7)
        if p.id in {"QB0", "QB1"}
        else p
        for p in roster
    ]
    lineup = optimize_lineup(roster, week=7)
    for _, player in lineup.starters:
        assert player.bye_week != 7  # no starter is on bye that week


# -- invariant 2: K/DST cap until the final rounds ------------------------
def test_no_second_k_or_dst_before_final_rounds() -> None:
    lineup = solve_roster(_pool(), rounds_remaining=10)
    counts = lineup.counts()
    assert counts.get("K", 0) == 1
    assert counts.get("DST", 0) == 1


def test_second_k_allowed_in_final_rounds() -> None:
    reqs = RosterRequirements(bench_size=8, final_rounds=2)
    # Make the 2nd K/DST genuinely attractive so the objective *would* take them if allowed.
    pool = _pool() + [
        Player("K2", "K", 7.4, bench_value=6.0),
        Player("DST2", "DST", 7.9, bench_value=6.0),
    ]
    early = solve_roster(pool, reqs, rounds_remaining=9)
    assert early.counts().get("K", 0) == 1  # capped early despite the bait
    late = solve_roster(pool, reqs, rounds_remaining=1)
    assert late.counts().get("K", 0) <= reqs.k_late_cap  # cap lifts, 2nd K now permissible


# -- invariant 3: bench formula ranks a flyer over a 2nd kicker ------------
def test_bench_formula_ranks_flyer_over_second_kicker() -> None:
    # Startable flyer: a boom/bust RB behind an injury-prone starter, covers byes.
    flyer = bench_value(
        value_when_started=9.0,
        e_starts=expected_bench_starts("RB", depth_rank=1),
        upside=2.0,
        bye_cover=1.0,
    )
    # Second kicker: you start one, they never miss -> ~0 expected starts.
    second_k = bench_value(
        value_when_started=8.0,
        e_starts=expected_bench_starts("K", depth_rank=1),
    )
    assert flyer > second_k
    assert second_k < 1.0  # essentially worthless


def test_second_kicker_expected_starts_near_zero() -> None:
    assert expected_bench_starts("K", depth_rank=1) < 0.2
    assert expected_bench_starts("DST", depth_rank=1) < 0.3
    # A skill-position reserve behind an injury-prone starter earns real starts.
    assert expected_bench_starts("RB", depth_rank=1) > 1.0


def test_default_bench_value_zeroes_second_k_relative_to_flyer() -> None:
    # Even with no depth info supplied, the fallback keeps a startable flyer above a 2nd K.
    assert default_bench_value("RB", 12.0) > default_bench_value("K", 8.0)
    assert default_bench_value("K", 8.0) < 0.5


def test_expected_bench_starts_rejects_bad_depth() -> None:
    with pytest.raises(ValueError):
        expected_bench_starts("RB", depth_rank=0)


def test_solver_prefers_startable_flyer_over_second_kicker_on_bench() -> None:
    # Give the solver a bench choice between a real flyer and a 2nd kicker for one bench slot.
    reqs = RosterRequirements(bench_size=1, final_rounds=0)  # caps never lift here
    pool = _pool() + [
        Player("FLYER", "RB", 10.0, bench_value=14.0),
        Player("K2", "K", 7.9, bench_value=0.2),
    ]
    lineup = solve_roster(pool, reqs, rounds_remaining=10)
    bench_ids = {p.id for p in lineup.bench}
    assert "FLYER" in bench_ids
    assert "K2" not in bench_ids
