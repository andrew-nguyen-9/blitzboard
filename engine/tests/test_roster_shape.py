"""E6 — the derived bench shape.

These tests police the *derivation*, not a hand-set dict: that the checked-in
`fixtures/bench_shape.json` is internally consistent, that `bench_bounds` answers for every one of
the 432 matrix rows (e8b iterates all of them), that the config actually moves the answer
(superflex raises the QB ceiling; a 14-team league differs from an 8-team one), that re-running
the measurement with the same seed is bit-identical, and that the derived K/DST timing is a
plausible round. The one live simulation here is deliberately tiny (one row, two arms).
"""
from __future__ import annotations

import numpy as np
import pytest

from blitz_engine.testing import matrix
from blitz_engine.value import roster_shape as rshape
from blitz_engine.value.roster_shape import (
    BENCH_POSITIONS,
    BenchBounds,
    bench_bounds,
    bounds_from_study,
    kdst_timing,
    roster_size,
    starters_tuple,
    to_requirements,
)
from blitz_engine.value.roster_solver import Player, solve_roster

_CHEAP = "t8-1qb-std-te0.0-b4-ir0"  # the smallest smoke row — the only one we re-simulate


# ── the fixture is well-formed ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("row", matrix.smoke(), ids=lambda r: r["id"])
def test_measured_rows_are_present_and_ordered(row: dict) -> None:
    bounds = bench_bounds(row)
    assert bounds.measured, f"{row['id']} should be in the derived fixture"
    for pos in BENCH_POSITIONS:
        assert 0 <= bounds.lo[pos] <= bounds.hi[pos], (pos, bounds.lo, bounds.hi)


@pytest.mark.parametrize("row", matrix.all(), ids=lambda r: r["id"])
def test_every_matrix_row_has_bounds_inside_its_bench_budget(row: dict) -> None:
    # e8b iterates matrix.all(); an unmeasured row must still answer, by interpolation.
    bounds = bench_bounds(row)
    bench = int(row["bench_slots"])
    assert bounds.bench_slots == bench
    assert sum(bounds.lo.values()) <= bench, bounds.lo
    for pos in BENCH_POSITIONS:
        assert bounds.lo[pos] <= bounds.hi[pos] <= bench, (pos, bounds.lo, bounds.hi)


def test_bounds_are_a_band_not_a_point() -> None:
    # The whole reason e6 ships bounds: at least one position must admit more than one depth,
    # or e8b's invariant is as brittle as the hardcoded dict it replaces.
    rows = matrix.smoke()
    widths = [
        max(bench_bounds(r).hi[p] - bench_bounds(r).lo[p] for p in BENCH_POSITIONS) for r in rows
    ]
    assert min(widths) >= 1, widths


def test_contains_predicate_matches_the_bounds() -> None:
    bounds = bench_bounds(matrix.by_id(_CHEAP))
    inside = {p: bounds.lo[p] for p in BENCH_POSITIONS}
    assert bounds.contains(inside)
    over = dict(inside)
    over["RB"] = bounds.hi["RB"] + 1
    assert not bounds.contains(over)


# ── the config actually moves the answer ───────────────────────────────────────────────


def _pair(a: str, b: str) -> tuple[BenchBounds, BenchBounds]:
    return bench_bounds(matrix.by_id(a)), bench_bounds(matrix.by_id(b))


def test_superflex_raises_the_qb_bound() -> None:
    # The headline config effect, stated as the measurement supports it: across the MEASURED rows,
    # a league that starts more than one QB carries a deeper bench QB ceiling than a 1QB league.
    measured = [r for r in matrix.smoke()]
    one = [bench_bounds(r).hi["QB"] for r in measured if r["qb_mode"] == "1qb"]
    many = [bench_bounds(r).hi["QB"] for r in measured if r["qb_mode"] != "1qb"]
    assert np.mean(many) > np.mean(one), (many, one)
    # ...and only a multi-QB league ever demands a bench QB as a floor.
    floors = {r["qb_mode"] for r in measured if bench_bounds(r).lo["QB"] > 0}
    assert floors and "1qb" not in floors, floors


def test_league_size_changes_the_bounds() -> None:
    small, large = _pair("t8-1qb-std-te0.0-b8-ir0", "t14-1qb-half-te0.0-b8-ir0")
    assert (small.lo, small.hi) != (large.lo, large.hi)


def test_bench_budget_changes_the_bounds() -> None:
    thin, deep = _pair("t8-1qb-std-te0.0-b4-ir0", "t8-1qb-std-te0.0-b8-ir0")
    assert (thin.lo, thin.hi) != (deep.lo, deep.hi)
    assert max(thin.hi.values()) <= thin.bench_slots
    assert max(deep.hi.values()) <= deep.bench_slots


# ── K/DST timing ───────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("row", matrix.all(), ids=lambda r: r["id"])
def test_kdst_timing_is_a_plausible_round(row: dict) -> None:
    timing = kdst_timing(row)
    # A cap must be a real round of this row's draft, and must at least leave room for K + DST.
    assert 2 <= timing.cap_rounds_from_end <= roster_size(row), timing
    assert timing.soft_penalty >= 0.0
    assert timing.confidence in ("high", "low")
    # Penalty is zero at/after the cap and grows one round at a time before it.
    assert timing.penalty_for(timing.cap_rounds_from_end) == 0.0
    early = timing.penalty_for(timing.cap_rounds_from_end + 3)
    assert early == pytest.approx(3 * timing.soft_penalty)


def test_kdst_confidence_flag_is_live() -> None:
    # Block-release honesty: e5 models no K/DST STREAMING, so the metric over-rewards locking in a
    # good kicker early and some rows measure a cap far outside the defensible band. Those rows
    # must be FLAGGED, not silently shipped to e10 as if proven.
    flags = {r["id"]: kdst_timing(r).confidence for r in matrix.smoke()}
    assert set(flags.values()) == {"high", "low"}, flags
    for rid, flag in flags.items():
        row = matrix.by_id(rid)
        cap = kdst_timing(row).cap_rounds_from_end
        expected = "high" if cap <= row["bench_slots"] + 2 else "low"
        assert flag == expected, (rid, flag)


def test_kdst_timing_is_not_a_constant() -> None:
    caps = {kdst_timing(r).cap_rounds_from_end for r in matrix.smoke()}
    pens = {round(kdst_timing(r).soft_penalty, 3) for r in matrix.smoke()}
    assert len(caps) > 1 or len(pens) > 1, (caps, pens)


# ── the roster_solver consumer ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("row", matrix.smoke(), ids=lambda r: r["id"])
def test_to_requirements_uses_derived_numbers(row: dict) -> None:
    reqs = to_requirements(row)
    assert reqs.starters == starters_tuple(row)
    assert reqs.bench_size == int(row["bench_slots"])
    assert reqs.roster_size == roster_size(row)
    assert reqs.final_rounds == kdst_timing(row).cap_rounds_from_end
    bounds = bench_bounds(row)
    assert reqs.bench_bounds == bounds.as_pairs()
    assert reqs.bench_floor() == {p: v for p, v in bounds.lo.items() if v > 0}


def test_solver_honours_the_derived_bench_bounds() -> None:
    # The e8a gap: bench.BENCH_DISCOUNT lets a value-maximising solve bench six RBs. With e6's
    # bounds wired in, that is now infeasible rather than merely unlikely.
    row = matrix.by_id(_CHEAP)
    bounds = bench_bounds(row)
    reqs = to_requirements(row, bounds)
    pool = [
        Player(id=f"{pos}{i}", position=pos, value=100.0 - i if pos == "RB" else 40.0 - i)
        for pos in ("QB", "RB", "WR", "TE", "K", "DST")
        for i in range(10)
    ]
    lineup = solve_roster(pool, reqs, rounds_remaining=0)
    starters = {}
    for _slot, p in lineup.starters:
        starters[p.position] = starters.get(p.position, 0) + 1
    bench_counts = {p: 0 for p in BENCH_POSITIONS}
    for p in lineup.bench:
        bench_counts[p.position] += 1
    assert bounds.contains(bench_counts), (bench_counts, bounds.lo, bounds.hi)


def test_default_requirements_are_unconstrained() -> None:
    # Backwards compatibility: e4/e8a build RosterRequirements without bounds and must not change.
    from blitz_engine.value.roster_solver import RosterRequirements

    reqs = RosterRequirements()
    assert reqs.bench_bounds == ()
    assert reqs.bench_floor() == {} and reqs.bench_ceiling() == {}


# ── the derivation itself: seeded and reproducible ─────────────────────────────────────


def test_same_seed_gives_identical_measurements() -> None:
    row = matrix.by_id(_CHEAP)
    arms = ["RB:1", "kdst_at:3"]
    kw = {"n_seasons": 2, "arms": arms}
    first = rshape.measure(row, **kw)
    second = rshape.measure(row, **kw)
    assert [first.arms[a].delta for a in arms] == [second.arms[a].delta for a in arms]
    assert bounds_from_study(first).as_pairs() == bounds_from_study(second).as_pairs()
    # ...and a different seed genuinely resamples (the seed is live, not decorative).
    other = rshape.measure(row, n_seasons=2, arms=arms, seed=rshape.SHAPE_SEED + 7)
    assert [other.arms[a].delta for a in arms] != [first.arms[a].delta for a in arms]


def test_measure_pairs_every_seat_exactly_once() -> None:
    # The mirrored half-league design is what cancels the snake-draft-slot effect. If it ever
    # stops mirroring, the numbers silently become draft-position noise.
    row = matrix.by_id(_CHEAP)
    study = rshape.measure(row, n_seasons=2, arms=["WR:1"])
    assert study.arms["WR:1"].n_pairs == int(row["teams"]) * 2


def test_marginal_curve_is_reported_with_the_bounds() -> None:
    # "plus the marginal value curve that produced them" — the audit trail must survive.
    study = rshape.measure(matrix.by_id(_CHEAP), n_seasons=2, arms=["RB:1", "RB:2"])
    curve = study.marginal("RB")
    assert len(curve) == 2
    assert curve[0] == pytest.approx(study.value("RB", 1))
    assert curve[1] == pytest.approx(study.value("RB", 2) - study.value("RB", 1))


def test_shape_arm_actually_changes_the_bench() -> None:
    # The arm string has to reach the draft, or every measurement is a null by construction.
    from blitz_engine.simulation import season_eval as se

    row = matrix.by_id(_CHEAP)
    pool = se.build_players(2024, row["id"])
    rosters, seats = se.draft_league(
        pool, row, policies=["QB:2", "filler"], pick_fn=rshape.shape_pick_fn()
    )
    starters = sum(int(n) for n in row["starting_slots"].values())
    by_arm: dict[str, list[int]] = {}
    for arm, roster in zip(seats, rosters, strict=True):
        qbs = sum(1 for p in roster[starters:] if p.position == "QB")
        by_arm.setdefault(arm, []).append(qbs)
    assert min(by_arm["QB:2"]) >= 1 > max(by_arm["filler"]), by_arm


# ── block release: no weight ships without an ablation + a no-regression check ─────────


#: The one smoke row where the derived shape measurably LOSES to v4's constants (-25.3 pts/season,
#: p=0.0025): a 14-team 2QB league with only 4 bench slots, where the derived ceilings leave no
#: room for the second QB body v4's `overfillDepth.QB = 3` buys. Named, not hidden — e10 must not
#: apply e6's numbers to thin-bench multi-QB rows without re-deriving them.
KNOWN_REGRESSION_ROW = "t14-2qb-std-te0.5-b4-ir1"


def test_derived_numbers_beat_the_v4_hand_set_constants() -> None:
    # THE BLOCK-RELEASE GATE. `e6` (derived floors/ceilings + derived K/DST round) head to head
    # against v4's `overfillDepth {QB:3,RB:5,WR:5,TE:2,K:1,DST:1}` + `kdstCapRoundsFromEnd: 2`,
    # mirrored half-league, scored on SeasonEvalResult.started_points — never on the retired
    # hindsight metric.
    #
    # The claim this licenses is exactly what was measured and no more: the derived shape wins on
    # the MAJORITY of the smoke grid and on AVERAGE, not on every row. A per-row superiority claim
    # is NOT supported (t12-1qb-half-te0.5-b8-ir0 is a null at p=0.96) and is deliberately not
    # asserted here.
    deltas = {r["id"]: rshape.ablate(r, n_seasons=8).delta for r in matrix.smoke()}
    wins = [rid for rid, d in deltas.items() if d > 0.0]
    assert float(np.mean(list(deltas.values()))) > 0.0, deltas
    assert len(wins) > len(deltas) / 2, deltas
    assert deltas[KNOWN_REGRESSION_ROW] < 0.0, (
        "the documented regression row turned positive — re-measure and update the note"
    )


@pytest.mark.parametrize("row", matrix.smoke(), ids=lambda r: r["id"])
def test_no_regression_derived_requirements_stay_solvable(row: dict) -> None:
    # No-regression: wiring the derived bounds into RosterRequirements must never make a real
    # row's roster infeasible — the failure mode a hand-set positional floor would introduce.
    reqs = to_requirements(row)
    pool = [
        Player(id=f"{pos}{i}", position=pos, value=float(60 - i))
        for pos in ("QB", "RB", "WR", "TE", "K", "DST")
        for i in range(12)
    ]
    lineup = solve_roster(pool, reqs, rounds_remaining=0)
    assert lineup.is_legal
    assert len(lineup.starters) == len(reqs.starters)


def test_bye_stacking_beats_bye_spreading_on_a_deep_bench() -> None:
    # e1 BENCH_MODEL P1: `byeStackPenalty: 12` is the most-suspect v4 constant. The measured arms
    # say it is WRONG-SIGNED on a deep bench — clustering bench byes with the starters' own byes
    # BEATS spreading them. Recorded from the derivation fixture, not re-simulated here.
    arms = rshape._load_fixture()["rows"]["t12-1qb-half-te0.5-b8-ir0"]["arms"]
    assert arms["bye_cluster"]["delta"] > 0.0 > arms["bye_spread"]["delta"], arms
    assert arms["bye_cluster"]["p"] < 0.05, arms["bye_cluster"]
