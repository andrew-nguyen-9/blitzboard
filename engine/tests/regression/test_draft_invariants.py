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

import random
from collections import defaultdict
from dataclasses import dataclass

import pytest

from blitz_engine.data.reconcile import (
    TeamObservation,
    reconcile_teams,
    validate_publish,
)
from blitz_engine.value import (
    FAStatus,
    InterimValue,
    Player,
    RosterRequirements,
    apply_fa_penalty,
    interim_surface,
    is_truly_free_agent,
    optimize_lineup,
    solve_roster,
)

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
