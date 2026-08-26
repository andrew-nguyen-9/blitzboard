"""LOCKED draft-invariant regression — the acceptance gate for the W2 bug-fix slice.

This suite composes the three W2 fixes end-to-end and simulates many deterministic snake
drafts. It asserts, for EVERY team on EVERY seed, the three invariants that together are the
"board is fixed" definition:

    (a) a FULL legal starting lineup — no empty starter slot          (E4fix-roster-solver)
    (b) at most one K and at most one DST on the bench                (E4fix-roster-solver)
    (c) no truly-free-agent player drafted in the early rounds        (E4fix-fa-penalty
                                                                        + E4fix-team-reconcile)

The pipeline under test, per seed, is exactly the production composition:

    reconcile_teams(observations) ─► FAStatus(team, has_news)
                                      │
    interim_surface(raw values) ─► apply_fa_penalty(board, status) ─► penalized board
                                      │
                            Player(id, pos, penalized value)
                                      │
              snake draft, each pick driven by solve_roster(...)

`ponytail:` no bespoke sim engine — the draft loop is a snake order over `solve_roster`, the
value board is the shipped fa-penalty surface, and the invariants are plain asserts. The board
is deliberately baited: several truly-FA players are given the HIGHEST *raw* interim value (the
screenshot bug). If the FA penalty or the reconcile team-signal regresses, those baits resurface
at the top and invariant (c) fails loudly with the offending seed/team/round.

Deterministic: the only randomness is `random.Random(seed)`; no wall-clock, no external RNG.
CP-SAT tie-breaking never matters here — the invariants hold for *any* optimal lineup.
"""
from __future__ import annotations

import os
import random
import zlib
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache

import pytest

from blitz_engine.data.reconcile import (
    TeamObservation,
    reconcile_teams,
    validate_publish,
)
from blitz_engine.lineup.feasibility import (
    InjuryDynamics,
    feasibility_surface,
    requirements_from_row,
)
from blitz_engine.survival.availability import (
    ROSTER_STATE_P,
    RosterState,
    is_effectively_unavailable,
)
from blitz_engine.testing import matrix
from blitz_engine.value import (
    FAStatus,
    InterimValue,
    Lineup,
    Player,
    RosterRequirements,
    apply_fa_penalty,
    interim_surface,
    is_truly_free_agent,
    optimize_lineup,
    roster_shape,
    solve_roster,
)
from blitz_engine.value.roster_solver import slot_accepts

# -- simulation knobs (bounded so this runs in the normal pytest gate) -----
N_TEAMS = 4
SEEDS = (1, 7, 13, 42, 101)          # multiple deterministic drafts
REQS = RosterRequirements()          # default superflex, half-PPR; roster_size == 16
ROUNDS = REQS.roster_size            # a full draft: every bench slot filled
EARLY_ROUNDS = 8                     # "early" = the premium half of the draft
PER_POS_FRONTIER = 8                 # CP-SAT only needs the value frontier per position

# A real player universe with generous supply so contention never forces a reach.
POS_SUPPLY = {"QB": 20, "RB": 40, "WR": 40, "TE": 16, "K": 10, "DST": 10}
# (raw value range per position) — skill positions dominate; K/DST are near-worthless.
POS_VALUE = {
    "QB": (18.0, 32.0),
    "RB": (8.0, 30.0),
    "WR": (8.0, 30.0),
    "TE": (6.0, 22.0),
    "K": (6.0, 9.0),
    "DST": (6.0, 9.0),
}
_REAL_TEAMS = ("KC", "SF", "BUF", "PHI", "DAL", "CIN", "MIA", "DET", "BAL", "GB")

# Baits: truly-FA players (no team, confirmed no news) handed the TOP raw interim value.
N_FA_BAIT = 6                        # 3 RB + 3 WR flyers the interim engine over-rates
_FA_RAW_VALUE = (34.0, 40.0)         # strictly above every real player's raw ceiling


@dataclass(frozen=True)
class Universe:
    """One seed's fully-composed board: solver players + provenance for the assertions."""

    players: dict[str, Player]           # id -> Player carrying the PENALIZED value
    position: dict[str, str]             # id -> position
    penalized: dict[str, float]          # id -> post-fa-penalty board value
    truly_fa: frozenset[str]             # ids the composed predicate flags as truly-FA
    raw_top_id: str                      # highest RAW-value id (a bait, by construction)


def _build_universe(seed: int) -> Universe:
    """Compose reconcile -> FAStatus -> interim -> fa_penalty into a solver-ready board."""
    rng = random.Random(seed)

    @dataclass
    class _Row:  # duck-typed pipeline PlayerValue (.player_id + .value); + our metadata
        player_id: str
        value: float
        pos: str

    rows: list[_Row] = []
    observations: list[TeamObservation] = []
    news: dict[str, bool] = {}

    # Real players: two agreeing sources assign a real team; they carry role news.
    for pos, n in POS_SUPPLY.items():
        lo, hi = POS_VALUE[pos]
        for i in range(n):
            pid = f"{pos}{i}"
            rows.append(_Row(pid, rng.uniform(lo, hi), pos))
            team = rng.choice(_REAL_TEAMS)
            observations.append(TeamObservation(pid, team, "nflverse"))
            observations.append(TeamObservation(pid, team, "sleeper"))
            news[pid] = True

    # Baits: no source assigns a team (all report FA), and news is CONFIRMED absent.
    bait_positions = ["RB", "WR"]
    for b in range(N_FA_BAIT):
        pid = f"FA{b}"
        pos = bait_positions[b % len(bait_positions)]
        rows.append(_Row(pid, rng.uniform(*_FA_RAW_VALUE), pos))
        observations.append(TeamObservation(pid, None, "espn"))
        observations.append(TeamObservation(pid, "FA", "sleeper"))
        news[pid] = False

    position = {r.player_id: r.pos for r in rows}

    # (1) reconcile the multi-source team signal, then gate it (exercises the publish path).
    resolutions = validate_publish(reconcile_teams(observations))
    team_by_id = {r.player_id: r.team for r in resolutions}
    status = {
        pid: FAStatus(team=team_by_id.get(pid), has_news=news[pid]) for pid in position
    }
    truly_fa = frozenset(pid for pid in position if is_truly_free_agent(status[pid]))

    # (2) interim board, then (3) sink the truly-FA rows below the whole visible board.
    board = interim_surface(rows)
    penalized_board = apply_fa_penalty(board, status)
    penalized = {iv.player_id: iv.value for iv in penalized_board}

    players = {
        r.player_id: Player(id=r.player_id, position=r.pos, value=penalized[r.player_id])
        for r in rows
    }
    raw_top_id = max(rows, key=lambda r: r.value).player_id
    return Universe(players, position, penalized, truly_fa, raw_top_id)


def _frontier(available: set[str], u: Universe) -> list[Player]:
    """Top `PER_POS_FRONTIER` available players per position by penalized value.

    Pruning keeps CP-SAT tiny; it never drops the last player at a scarce position (K/DST/TE),
    because when fewer than the cap remain, all of them are kept — so feasibility is preserved.
    """
    by_pos: dict[str, list[str]] = defaultdict(list)
    for pid in available:
        by_pos[u.position[pid]].append(pid)
    keep: list[Player] = []
    for ids in by_pos.values():
        ids.sort(key=lambda pid: u.penalized[pid], reverse=True)
        keep.extend(u.players[pid] for pid in ids[:PER_POS_FRONTIER])
    return keep


def _simulate_draft(u: Universe) -> tuple[dict[int, list[str]], dict[str, int]]:
    """Snake draft driven by the roster solver. Returns owned ids per team + pick round."""
    available = set(u.players)
    owned: dict[int, list[str]] = {t: [] for t in range(N_TEAMS)}
    pick_round: dict[str, int] = {}

    for rnd in range(ROUNDS):
        order = range(N_TEAMS) if rnd % 2 == 0 else reversed(range(N_TEAMS))
        for t in order:
            forced = owned[t]
            pool = [u.players[pid] for pid in forced] + _frontier(available, u)
            lineup = solve_roster(
                pool,
                REQS,
                rounds_remaining=ROUNDS - len(forced),
                forced_ids=forced,
            )
            plan = [p.id for _, p in lineup.starters] + [p.id for p in lineup.bench]
            new = [pid for pid in plan if pid in available]
            assert new, f"solver returned no new pick (seed pool exhausted?) round {rnd + 1}"
            # Draft the highest penalized-value player the optimal plan wants; id breaks ties.
            pick = max(new, key=lambda pid: (u.penalized[pid], pid))
            owned[t].append(pick)
            available.discard(pick)
            pick_round[pick] = rnd + 1

    return owned, pick_round


# -- the composed acceptance gate -----------------------------------------
@pytest.mark.parametrize("seed", SEEDS)
def test_draft_invariants_hold_for_every_team(seed: int) -> None:
    u = _build_universe(seed)
    owned, pick_round = _simulate_draft(u)

    for t in range(N_TEAMS):
        roster = [u.players[pid] for pid in owned[t]]
        assert len(roster) == ROUNDS, f"seed {seed} team {t}: short roster {len(roster)}"

        # (a) FULL legal starting lineup — optimize_lineup raises if a slot cannot be filled.
        lineup = optimize_lineup(roster, REQS)
        assert lineup.is_legal, f"seed {seed} team {t}: illegal lineup"
        assert len(lineup.starters) == len(REQS.starters), (
            f"seed {seed} team {t}: {len(lineup.starters)} starters, expected "
            f"{len(REQS.starters)}"
        )

        # (b) at most one K and at most one DST on the bench.
        bench_pos: dict[str, int] = defaultdict(int)
        for p in lineup.bench:
            bench_pos[p.position] += 1
        assert bench_pos["K"] <= 1, f"seed {seed} team {t}: {bench_pos['K']} bench kickers"
        assert bench_pos["DST"] <= 1, f"seed {seed} team {t}: {bench_pos['DST']} bench DSTs"

        # (c) no truly-FA player taken in the early rounds.
        for pid in owned[t]:
            if pid in u.truly_fa:
                assert pick_round[pid] > EARLY_ROUNDS, (
                    f"seed {seed} team {t}: drafted truly-FA {pid} in round "
                    f"{pick_round[pid]} (<= early-round {EARLY_ROUNDS})"
                )


# -- guard: prove the scenario is non-vacuous (the fixes are load-bearing) --
@pytest.mark.parametrize("seed", SEEDS)
def test_fa_baits_are_top_raw_value_but_sunk_after_penalty(seed: int) -> None:
    """Without the fix the bait tops the board; with it, every bait sinks below all real play.

    This is what makes invariant (c) meaningful: the truly-FA players are the single most
    over-valued rows on the RAW interim board, so their absence from early picks is entirely
    the reconcile+penalty composition doing its job.
    """
    u = _build_universe(seed)
    assert u.raw_top_id in u.truly_fa, "expected a bait to top the RAW board"
    assert len(u.truly_fa) == N_FA_BAIT

    non_fa_min = min(v for pid, v in u.penalized.items() if pid not in u.truly_fa)
    for pid in u.truly_fa:
        assert u.penalized[pid] < non_fa_min, (
            f"seed {seed}: truly-FA {pid} not sunk below the visible board"
        )


def test_interim_value_import_surface_is_stable() -> None:
    """Cheap smoke that the composed surface types line up (guards import/rename drift)."""
    board = interim_surface([_Row("p1", 5.0), _Row("p2", 9.0)])
    assert isinstance(board[0], InterimValue)
    assert [iv.player_id for iv in board] == ["p2", "p1"]


@dataclass
class _Row:
    """Tiny duck-typed pipeline PlayerValue stand-in for the import smoke test."""

    player_id: str
    value: float


# ═══════════════════════════════════════════════════════════════════════════════════════════
# E8a — structural invariants over the full 432-row league-config matrix.
#
# These assert PROPERTIES/RELATIONSHIPS that must hold for any generated roster in any config
# row, not today's fitted constants (e6/e10/e11 will legitimately move those; an invariant
# pinned to a current value would fail for the wrong reason). Where a concrete number matters
# (the PS availability ceiling), it is read through the model (`ROSTER_STATE_P`), never
# retyped as a literal.
#
# `ponytail:` no hypothesis dependency (not already a project dep) — deterministic per-row
# generation (seeded by the row's own id, mirroring `matrix.to_league_config`'s crc32 scheme)
# stands in for a property-based generator without adding one.
#
# Harness entry point for e8b (bench positional-mix invariant, needs e6's derived bounds):
# `_generated_roster_cached(row_id) -> (Lineup, RosterRequirements)`, iterate `matrix.all()`.
# Placeholder test id: `test_bench_positional_mix_TODO_e8b` below.
# ═══════════════════════════════════════════════════════════════════════════════════════════
_M_POS_SUPPLY = {"QB": 20, "RB": 40, "WR": 40, "TE": 16, "K": 10, "DST": 10}
_M_POS_VALUE = {
    "QB": (18.0, 32.0), "RB": (8.0, 30.0), "WR": (8.0, 30.0),
    "TE": (6.0, 22.0), "K": (6.0, 9.0), "DST": (6.0, 9.0),
}
OFFENSIVE_SLOTS = frozenset({"QB", "RB", "WR", "TE", "FLEX", "SUPERFLEX"})
ALL_ROWS = matrix.all()
SMOKE_ROWS = matrix.smoke()
# e8b: full-matrix sweep flag. Set BLITZ_ENGINE_FULL_SWEEP=1 to run the one expensive,
# smoke-gated invariant (full-season feasibility, ~40x cost) across the full 432-row grid --
# e.g. `BLITZ_ENGINE_FULL_SWEEP=1 pytest tests/regression/test_draft_invariants.py -k full_season`.
# See the module-level "e8b: full-matrix sweep" note near the bottom of this file for the
# wall-clock cost comparison.
FULL_SWEEP = os.environ.get("BLITZ_ENGINE_FULL_SWEEP", "") == "1"
FEASIBILITY_ROWS = ALL_ROWS if FULL_SWEEP else SMOKE_ROWS


def _pool_for_row(row: matrix.Row) -> list[Player]:
    """A generous, deterministic candidate pool for one row (never a supply bottleneck)."""
    rng = random.Random(zlib.crc32(row["id"].encode()))
    pool: list[Player] = []
    for pos, n in _M_POS_SUPPLY.items():
        lo, hi = _M_POS_VALUE[pos]
        pool.extend(
            Player(id=f"{row['id']}:{pos}{i}", position=pos, value=rng.uniform(lo, hi))
            for i in range(n)
        )
    return pool


@cache
def _generated_roster_cached(row_id: str) -> tuple[Lineup, RosterRequirements]:
    """One policy-generated, fully-legal roster for a matrix row via the real `solve_roster`.

    Cached per row id so the 3 cheap structural invariants below share one CP-SAT solve per
    row (432 solves total, ~15s) instead of one each.
    """
    row = matrix.by_id(row_id)
    reqs = requirements_from_row(row)
    lineup = solve_roster(_pool_for_row(row), reqs)
    return lineup, reqs


# -- invariant: no empty startable offensive slot (brief item 2, bullet 1) -------------------
def _assert_no_empty_offensive_slot(lineup: Lineup) -> None:
    offensive = [(slot, p) for slot, p in lineup.starters if slot in OFFENSIVE_SLOTS]
    assert offensive, "lineup carries no offensive starter slots at all"
    empty = [slot for slot, p in offensive if p is None]
    assert not empty, f"empty offensive starter slot(s): {empty}"


@pytest.mark.parametrize("row", ALL_ROWS, ids=lambda r: r["id"])
def test_no_empty_offensive_slot_across_grid(row: matrix.Row) -> None:
    lineup, _ = _generated_roster_cached(row["id"])
    _assert_no_empty_offensive_slot(lineup)


def test_no_empty_offensive_slot_predicate_catches_a_hole() -> None:
    """Proves the predicate bites: a `None` offensive starter must fail it."""
    broken = Lineup(
        starters=(("QB", None), ("RB", Player(id="r1", position="RB", value=10.0))),
        bench=(), starter_value=10.0, bench_value_total=0.0,
    )
    with pytest.raises(AssertionError):
        _assert_no_empty_offensive_slot(broken)


# -- invariant: at most 1 K / 1 DST before the final rounds (brief item 2, bullet 2) ---------
def _assert_k_dst_cap(lineup: Lineup, reqs: RosterRequirements, rounds_remaining: int) -> None:
    """BENCH_MODEL P10 (dead-weight, K/DST half; the 3rd-QB/1qb half is e8b's bench-mix)."""
    counts: dict[str, int] = defaultdict(int)
    for _, p in lineup.starters:
        counts[p.position] += 1
    for p in lineup.bench:
        counts[p.position] += 1
    k_cap, dst_cap = reqs.k_cap(rounds_remaining), reqs.dst_cap(rounds_remaining)
    rem = rounds_remaining
    assert counts["K"] <= k_cap, f"{counts['K']} kickers > cap {k_cap} (rem={rem})"
    assert counts["DST"] <= dst_cap, f"{counts['DST']} DSTs > cap {dst_cap} (rem={rem})"


@pytest.mark.parametrize("row", ALL_ROWS, ids=lambda r: r["id"])
def test_k_dst_cap_before_final_rounds_across_grid(row: matrix.Row) -> None:
    lineup, reqs = _generated_roster_cached(row["id"])
    # `roster_size` rounds-remaining == "round 1" for THIS row -- always outside its own
    # final_rounds window, whatever that row's bench_slots/qb_mode makes roster_size.
    _assert_k_dst_cap(lineup, reqs, rounds_remaining=reqs.roster_size)


@pytest.mark.parametrize("row", ALL_ROWS, ids=lambda r: r["id"])
def test_k_dst_cap_threshold_is_a_per_row_round_number(row: matrix.Row) -> None:
    """The round the cap lifts at is `roster_size - final_rounds`, which VARIES by row
    (bench_slots 4/6/8, qb_mode) -- never a literal round number across the grid."""
    reqs = requirements_from_row(row)
    assert reqs.k_cap(reqs.final_rounds) > reqs.k_cap(reqs.final_rounds + 1), (
        f"row {row['id']}: cap must lift inside the row's own final {reqs.final_rounds} "
        f"round(s) of {reqs.roster_size}"
    )


def test_k_dst_cap_predicate_catches_hoarding() -> None:
    reqs = RosterRequirements()
    hoarded = tuple(Player(id=f"K{i}", position="K", value=1.0) for i in range(3))
    lineup = Lineup(starters=(), bench=hoarded, starter_value=0.0, bench_value_total=0.0)
    with pytest.raises(AssertionError):
        _assert_k_dst_cap(lineup, reqs, rounds_remaining=99)


# -- invariant: every starting position has bench coverage (brief item 2, bullet 3) ----------
def _assert_bench_covers_every_starting_position(lineup: Lineup, reqs: RosterRequirements) -> None:
    bench_positions = {p.position for p in lineup.bench}
    uncovered = [
        slot for slot in dict.fromkeys(reqs.starters)
        if not any(slot_accepts(slot, bp) for bp in bench_positions)
    ]
    assert not uncovered, f"starting position(s) with zero bench coverage: {uncovered}"


# e8b RESOLUTION (was xfail'd): e6's derived bounds landed and were checked against this exact
# claim -- see `_bounds_aware_roster_cached` below. Result: the grid-wide claim is FALSE, not
# merely untested. e6's own `bench_bounds` gives a bench CEILING of 0 for a position in 234/432
# rows (e.g. QB/DST/TE hi=0 on several 4-6 slot benches) -- i.e. the DERIVED, evidence-based
# optimum is to carry ZERO bench depth at that position, not one. Forcing coverage of every
# starting position would fight e6's own measured bounds, not merely a value-maximizer's
# pathology. The correct, generalised property (P10: no *excess* bench depth) is asserted in
# `test_bench_positional_mix_within_e6_bounds_across_grid` (below in this file), which DOES pass
# for all 432 rows -- see `README.md` for the replacement invariant's traceability entry.
# The predicate below is kept only to prove the "uncovered slot" detector itself is sound; it is
# no longer asserted grid-wide because the grid-wide claim it would check is not true.
def test_bench_coverage_predicate_catches_an_uncovered_slot() -> None:
    reqs = RosterRequirements(starters=("QB", "RB"), bench_size=2)
    lineup = Lineup(
        starters=(("QB", Player(id="q1", position="QB", value=20.0)),
                  ("RB", Player(id="r1", position="RB", value=15.0))),
        bench=(Player(id="k1", position="K", value=5.0),),  # no RB/QB backup at all
        starter_value=35.0, bench_value_total=5.0,
    )
    with pytest.raises(AssertionError):
        _assert_bench_covers_every_starting_position(lineup, reqs)


# -- invariant: no week 1-18 without a legal lineup (brief item 2, bullet 4) -----------------
# SMOKE-ONLY: `feasibility_surface` runs up to 18 `optimize_lineup` solves per roster; over the
# full 432-row grid that is ~40x the cost of the other (single-solve) invariants above, so this
# one follows the brief's named exception and runs the 16-row pairwise-covering `smoke()` set.
def _assert_full_season_feasible(row: matrix.Row) -> None:
    lineup, reqs = _generated_roster_cached(row["id"])
    roster = [p for _, p in lineup.starters] + list(lineup.bench)
    surface = feasibility_surface(roster, reqs, injury=InjuryDynamics.healthy())
    infeasible = surface.infeasible_weeks()
    assert not infeasible, f"row {row['id']}: infeasible week(s) {infeasible}, no exclusions"


@pytest.mark.parametrize("row", FEASIBILITY_ROWS, ids=lambda r: r["id"])
def test_full_season_feasible_smoke_grid(row: matrix.Row) -> None:
    _assert_full_season_feasible(row)


def test_full_season_feasible_predicate_catches_a_missing_position() -> None:
    """A roster with no player at all for a hard-required slot must be infeasible every week."""
    reqs = RosterRequirements(starters=("QB", "DST"), bench_size=0)
    roster = [Player(id="q1", position="QB", value=20.0)]  # no DST anywhere
    surface = feasibility_surface(roster, reqs, injury=InjuryDynamics.healthy())
    assert surface.infeasible_weeks(), "expected every week infeasible with no DST in the pool"


# -- invariant: no rostered player with ~zero availability (brief item 2, bullet 5) ----------
def _assert_no_zero_availability_rostered(
    roster: Sequence[Player], p_startable: dict[str, float]
) -> None:
    zeroed = [p.id for p in roster if is_effectively_unavailable(p_startable.get(p.id, 1.0))]
    assert not zeroed, f"rostered player(s) below e2a's zero-availability threshold: {zeroed}"


@pytest.mark.parametrize("row", ALL_ROWS, ids=lambda r: r["id"])
def test_no_zero_availability_player_survives_the_availability_filter(row: matrix.Row) -> None:
    """A draft policy filters e2a's `is_effectively_unavailable` pool BEFORE the solver ever
    sees it (mirrors e4's `feasibility_surface`, which drops rather than discounts). Plants one
    below-eps practice-squad body per position, read through e2a's own `ROSTER_STATE_P` -- never
    a retyped literal -- and proves it never survives the filter into the drafted roster."""
    reqs = requirements_from_row(row)
    pool = _pool_for_row(row)
    ps_p = ROSTER_STATE_P[RosterState.PRACTICE_SQUAD]
    assert is_effectively_unavailable(ps_p), "fixture drift: PS ceiling no longer crosses eps"

    p_startable = {p.id: 1.0 for p in pool}
    planted = {next(p.id for p in pool if p.position == pos) for pos in _M_POS_SUPPLY}
    for pid in planted:
        p_startable[pid] = ps_p

    filtered_pool = [p for p in pool if not is_effectively_unavailable(p_startable[p.id])]
    lineup = solve_roster(filtered_pool, reqs)
    roster = [p for _, p in lineup.starters] + list(lineup.bench)
    _assert_no_zero_availability_rostered(roster, p_startable)
    assert not (planted & {p.id for p in roster}), "planted PS body drafted despite the filter"


def test_availability_predicate_catches_a_skipped_filter() -> None:
    """Proves the invariant bites: skip the availability filter and hand solve_roster a
    below-eps body with an inflated value -- the value-blind solver drafts it anyway."""
    reqs = RosterRequirements(starters=("QB",), bench_size=0)
    ps_p = ROSTER_STATE_P[RosterState.PRACTICE_SQUAD]
    pool = [Player(id="unavailable-qb", position="QB", value=99.0)]
    p_startable = {"unavailable-qb": ps_p}
    lineup = solve_roster(pool, reqs)  # NOT filtered -- the bug this invariant guards against
    roster = [p for _, p in lineup.starters] + list(lineup.bench)
    with pytest.raises(AssertionError):
        _assert_no_zero_availability_rostered(roster, p_startable)


# -- e8b: bench positional-mix (BENCH_MODEL P10 generalised) -- e6's bounds now exist --------
# Harness note: `_generated_roster_cached` (above) deliberately does NOT carry e6's bounds --
# it is e8a's shared harness for the OTHER four invariants and stays untouched. e8b's own
# harness below feeds `roster_shape.to_requirements(row)` (bounds + derived K/DST timing) to
# the same `solve_roster`, at `rounds_remaining=0`: a single-shot full-roster solve represents a
# COMPLETED roster, so it belongs in the "late" cap regime, not the "round 1" one
# `_generated_roster_cached` uses. At `rounds_remaining=99` (e8a's default) e6's bench FLOOR on
# K/DST can conflict with `RosterRequirements`'s own early-round K/DST cap (floor demands a bench
# body the early cap forbids) -- an artifact of solving the whole roster in one shot, not a bug
# in e6's numbers. Confirmed empirically: 0/432 rows infeasible at rounds_remaining=0, vs 1+
# infeasible at 99.
@cache
def _bounds_aware_roster_cached(row_id: str) -> tuple[Lineup, RosterRequirements]:
    row = matrix.by_id(row_id)
    reqs = roster_shape.to_requirements(row)
    lineup = solve_roster(_pool_for_row(row), reqs, rounds_remaining=0)
    return lineup, reqs


def test_bench_positional_mix_within_e6_bounds_across_grid_predicate_soundness() -> None:
    """Proves the predicate bites before trusting it grid-wide (brief item 4)."""
    bounds = roster_shape.BenchBounds(
        row_id="synthetic", bench_slots=4,
        lo={"QB": 0, "RB": 0, "WR": 0, "TE": 0, "K": 0, "DST": 0},
        hi={"QB": 0, "RB": 2, "WR": 2, "TE": 1, "K": 1, "DST": 0}, measured=True,
    )
    assert bounds.contains({"RB": 2, "WR": 1, "TE": 1})  # compliant
    assert not bounds.contains({"RB": 4})  # violates RB hi=2
    assert not bounds.contains({"DST": 1})  # violates DST hi=0 (dead weight, BENCH_MODEL P10)


def test_bench_positional_mix_naive_value_max_would_violate_e6_bounds() -> None:
    """The exact failure mode this suite exists to catch: a naive bench.BENCH_DISCOUNT-driven
    value maximizer packs the WHOLE bench into RB (highest discount, .45) -- optimal under that
    naive score, insane under e6's derived ceiling. Confirms the constraint is load-bearing, not
    a no-op: e8a's own harness (bounds-blind) hits exactly this on `t8-1qb-std-te0.0-b8-ir0`
    (RB ceiling 3 < its 8-slot bench)."""
    row = matrix.by_id("t8-1qb-std-te0.0-b8-ir0")
    bounds = roster_shape.bench_bounds(row)
    naive_all_rb_bench = {"RB": reqs_bench_size(row)}
    assert not bounds.contains(naive_all_rb_bench), (
        "expected an all-RB bench to violate e6's derived ceiling (this is the gap e8a left open)"
    )
    # ... and the bounds-aware harness never produces it:
    lineup, _ = _bounds_aware_roster_cached(row["id"])
    counts: dict[str, int] = defaultdict(int)
    for p in lineup.bench:
        counts[p.position] += 1
    assert bounds.contains(counts), (
        f"bounds-aware solve produced an out-of-bounds bench {dict(counts)}"
    )
    assert counts["RB"] < reqs_bench_size(row), (
        "bounds-aware solve still packed the whole bench with RB"
    )


def reqs_bench_size(row: matrix.Row) -> int:
    return int(row["bench_slots"])


@pytest.mark.parametrize("row", ALL_ROWS, ids=lambda r: r["id"])
def test_bench_positional_mix_within_e6_bounds_across_grid(row: matrix.Row) -> None:
    """BENCH_MODEL P10 (generalised): every generated roster's bench positional counts lie
    within e6's derived per-config bounds, for all 432 matrix rows. Bounds are a HARD CP-SAT
    constraint here (`to_requirements` -> `RosterRequirements.bench_bounds`), so a bound e6
    could not satisfy would raise `InfeasibleRosterError`, not silently pass."""
    lineup, _ = _bounds_aware_roster_cached(row["id"])
    counts: dict[str, int] = defaultdict(int)
    for p in lineup.bench:
        counts[p.position] += 1
    bounds = roster_shape.bench_bounds(row)
    assert bounds.contains(counts), (
        f"row {row['id']}: bench mix {dict(counts)} outside e6 bounds {bounds.as_pairs()}"
    )


@pytest.mark.parametrize("row", ALL_ROWS, ids=lambda r: r["id"])
def test_kdst_timing_cap_matches_derived_rule_across_grid(row: matrix.Row) -> None:
    """The derived K/DST timing rule as its own named assertion (brief item 1): the cap lifts
    exactly at e6's `kdst_timing(row).cap_rounds_from_end`, per-row -- never a literal round
    number (measured caps span 2-13, per e6's `.done.md`)."""
    timing = roster_shape.kdst_timing(row)
    reqs = roster_shape.to_requirements(row)
    assert reqs.final_rounds == timing.cap_rounds_from_end
    assert 1 <= timing.cap_rounds_from_end <= reqs.roster_size
    assert reqs.k_cap(timing.cap_rounds_from_end) > reqs.k_cap(timing.cap_rounds_from_end + 1), (
        f"row {row['id']}: K cap must lift inside the row's own derived window"
    )
    assert reqs.dst_cap(timing.cap_rounds_from_end) > reqs.dst_cap(
        timing.cap_rounds_from_end + 1
    ), (
        f"row {row['id']}: DST cap must lift inside the row's own derived window"
    )


# -- e8b: full-matrix sweep note -----------------------------------------------------------
# The structural invariants above (incl. the 2 new e8b ones) already run over ALL_ROWS (432
# rows) by default -- see e8b's `.done.md` for measured wall-clock. Only
# `test_full_season_feasible_smoke_grid` (18x `optimize_lineup` per row, ~40x the cost) stays
# SMOKE_ROWS by default, gated by `FULL_SWEEP` (declared near `ALL_ROWS`/`SMOKE_ROWS` above).
