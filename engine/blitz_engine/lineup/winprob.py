"""Win-probability-optimal weekly lineup (E5) — start/sit that maximises P(beat THIS opponent).

The weekly start/sit decision is *not* "start your highest projections". Against a weak
opponent you want a **floor** (don't blow a game you should win); against a strong opponent
you want a **ceiling** (you have to get lucky to win). Crucially, both of those postures fall
out of ONE objective — maximise P(your starters outscore the opponent) over the E3 correlated
Monte-Carlo — with no floor/ceiling special-casing anywhere in the code.

The trick that makes an inherently non-linear win-probability directly IP-solvable (reusing
E4fix's slot-legality assignment): draw the correlated sim once, then over a subsample of
draws add a boolean ``win[d]`` and a big-M link ``my_score[d] >= opp_score[d] + 1`` gated on
it. Maximising ``sum(win[d])`` *is* maximising the empirical P(beat opponent); the slot
constraints (exactly-one per slot, FLEX/SUPERFLEX eligibility, byes) are the same hard
assignment E4fix already models. Against a weak opponent the solver racks up wins by playing
consistent scorers (floor); against a strong one it can only win the hard draws with upside
(ceiling) — same objective, opposite lineup, zero heuristics.

Opponent-aware when the league schedule is synced (a real opponent roster is passed); otherwise
it degrades to the **best-per-week** lineup (maximise expected points) — the sensible default
when there's nobody specific to beat.

`ponytail:` one win-prob objective over the EXISTING correlated sim (`sample_correlated`) + the
EXISTING IP assignment (E4fix `slot_accepts` / `RosterRequirements`); no bespoke sampler, no
hand-rolled floor/ceiling scores, no second solver.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import pandas as pd
from ortools.sat.python import cp_model

from blitz_engine.simulation.correlation import (
    CorrelationSpec,
    build_correlation,
    cholesky_factor,
)
from blitz_engine.simulation.mc import sample_correlated
from blitz_engine.value.roster_solver import (
    InfeasibleRosterError,
    RosterRequirements,
    optimize_lineup,
    slot_accepts,
)
from blitz_engine.value.roster_solver import (
    Player as RosterPlayer,
)

__all__ = [
    "LineupDecision",
    "LineupPlayer",
    "SlotWhy",
    "optimal_lineup",
]

_DEFAULT_REQS = RosterRequirements()
_DEFAULT_SPEC = CorrelationSpec()
_POINT_SCALE = 10  # fantasy points → ints (0.1-pt resolution) for the integer CP-SAT objective


@dataclass(frozen=True)
class LineupPlayer:
    """A rostered player for a single week: marginal (`mean`, `stdev`) + correlation keys.

    `team` / `opponent` feed the E3 correlation build (QB↔WR stacks, DST↔opposing offense,
    same-game shootouts). Missing keys degrade to independence — never a crash.
    """

    id: str
    position: str
    mean: float
    stdev: float
    team: str | None = None
    opponent: str | None = None
    bye_week: int | None = None


@dataclass(frozen=True)
class SlotWhy:
    """Plain rationale for one filled starter slot."""

    slot: str
    player_id: str
    reason: str


@dataclass(frozen=True)
class LineupDecision:
    """The chosen weekly lineup plus its win-probability and a per-decision "why"."""

    starters: tuple[tuple[str, LineupPlayer], ...]  # (slot label, player), requirement order
    bench: tuple[LineupPlayer, ...]
    win_prob: float | None            # P(beat opponent) over the sim; None when unsynced
    my_projected: float               # sum of starters' mean points
    opp_projected: float | None       # opponent's projected starter total (None when unsynced)
    posture: str                      # "ceiling (underdog)" / "floor (favorite)" / best-per-week
    why: tuple[SlotWhy, ...]
    narrative: str
    opponent_synced: bool


def _meta_frame(players: Sequence[LineupPlayer]) -> pd.DataFrame:
    """Per-player frame for `build_correlation`; all-None team/opponent columns are dropped so
    a missing correlation key degrades to independence (E3 contract) rather than tripping NA."""
    data: dict[str, list[object]] = {
        "player_id": [p.id for p in players],
        "position": [p.position for p in players],
    }
    if any(p.team is not None for p in players):
        data["team"] = [p.team for p in players]
    if any(p.opponent is not None for p in players):
        data["opponent"] = [p.opponent for p in players]
    return pd.DataFrame(data)


def _draw_points(
    players: Sequence[LineupPlayer], n: int, spec: CorrelationSpec, seed: int
) -> npt.NDArray[np.float32]:
    """One correlated draw set (`n × len(players)`); columns follow `players` order."""
    corr = build_correlation(_meta_frame(players), spec)
    chol = cholesky_factor(corr)
    mean = np.array([p.mean for p in players], dtype=np.float64)
    sd = np.clip(np.array([p.stdev for p in players], dtype=np.float64), 1e-9, None)
    rng = np.random.default_rng(seed)
    return sample_correlated(mean, sd, chol, n, rng)


def _opponent_start_cols(
    opponent: Sequence[LineupPlayer],
    offset: int,
    reqs: RosterRequirements,
    week: int | None,
) -> list[int] | None:
    """Columns (in the combined draw matrix) of the opponent's expected-best starters.

    The opponent fields the lineup that maximises *their* expected points — the standard
    "assume a competent opponent" model. Returns None if they can't field a legal lineup.
    """
    pool = [
        RosterPlayer(id=p.id, position=p.position, value=p.mean, bye_week=p.bye_week)
        for p in opponent
    ]
    try:
        lineup = optimize_lineup(pool, reqs, week=week)
    except InfeasibleRosterError:
        return None
    started = {p.id for _, p in lineup.starters}
    return [offset + j for j, p in enumerate(opponent) if p.id in started]


def _solve_winprob(
    roster: Sequence[LineupPlayer],
    my_pts: npt.NDArray[np.float32],
    opp_score: npt.NDArray[np.float32],
    reqs: RosterRequirements,
    week: int | None,
    opt_draws: int,
    time_limit: float,
    seed: int,
) -> list[tuple[str, LineupPlayer]]:
    """IP assignment maximising the count of sim draws in which the lineup beats the opponent.

    `my_pts` is `n × len(roster)`, `opp_score` is `n`. Optimises over a `opt_draws` subsample
    (win-prob is smooth, so a few hundred draws pin the argmax); the reported win-prob is later
    re-measured on the full draw set.
    """
    n = my_pts.shape[0]
    m = len(roster)
    sub = min(opt_draws, n)
    idx = np.linspace(0, n - 1, sub).astype(int) if sub < n else np.arange(n)
    pi = np.rint(my_pts[idx] * _POINT_SCALE).astype(np.int64)   # (sub, m)
    oi = np.rint(opp_score[idx] * _POINT_SCALE).astype(np.int64)  # (sub,)
    big_m = int(oi.max(initial=0)) + 1

    model = cp_model.CpModel()
    slots = list(enumerate(reqs.starters))
    start: dict[tuple[int, int], cp_model.IntVar] = {}
    for i, p in enumerate(roster):
        if week is not None and p.bye_week == week:
            continue
        for s_idx, slot in slots:
            if slot_accepts(slot, p.position):
                start[i, s_idx] = model.new_bool_var(f"start_{i}_{s_idx}")

    for s_idx, slot in slots:
        cands = [start[i, s_idx] for i in range(m) if (i, s_idx) in start]
        if not cands:
            raise InfeasibleRosterError(
                f"no roster player can fill starter slot {slot!r} (index {s_idx})"
            )
        model.add_exactly_one(cands)
    for i in range(m):
        starts_i = [start[i, s_idx] for s_idx, _ in slots if (i, s_idx) in start]
        if starts_i:
            model.add(sum(starts_i) <= 1)

    wins: list[cp_model.IntVar] = []
    for d in range(sub):
        w = model.new_bool_var(f"win_{d}")
        my_d = sum(int(pi[d, i]) * start[i, s_idx] for (i, s_idx) in start)
        # w ⇒ my_score[d] ≥ opp_score[d] + 1 (a strict win); w free otherwise (big-M slack).
        model.add(my_d >= int(oi[d]) + 1 - big_m * (1 - w))
        wins.append(w)
    model.maximize(sum(wins))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.random_seed = seed
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise InfeasibleRosterError("no legal lineup under slot / bye constraints")

    chosen: list[tuple[str, LineupPlayer]] = []
    for s_idx, slot in slots:
        for i in range(m):
            if (i, s_idx) in start and solver.value(start[i, s_idx]):
                chosen.append((slot, roster[i]))
                break
    return chosen


def _build_why(
    chosen: Sequence[tuple[str, LineupPlayer]],
    bench: Sequence[LineupPlayer],
    *,
    win_mode: bool,
) -> tuple[SlotWhy, ...]:
    """A one-line rationale per slot: what was started and the best benched alternative it beat."""
    out: list[SlotWhy] = []
    for slot, player in chosen:
        alts = [b for b in bench if slot_accepts(slot, b.position)]
        best = max(alts, key=lambda b: b.mean, default=None)
        head = f"proj {player.mean:.1f} ±{player.stdev:.1f}"
        if best is None:
            reason = f"{head}; only eligible {slot} available."
        elif win_mode and player.stdev > best.stdev and player.mean <= best.mean + 1e-9:
            reason = (
                f"{head}; started over {best.id} (proj {best.mean:.1f} ±{best.stdev:.1f}) "
                f"for the higher ceiling this matchup needs."
            )
        elif win_mode and player.stdev < best.stdev and player.mean <= best.mean + 1e-9:
            reason = (
                f"{head}; started over {best.id} (proj {best.mean:.1f} ±{best.stdev:.1f}) "
                f"for the safer floor this matchup favors."
            )
        else:
            reason = f"{head}; started over {best.id} (proj {best.mean:.1f})."
        out.append(SlotWhy(slot=slot, player_id=player.id, reason=reason))
    return tuple(out)


def _fallback(
    roster: Sequence[LineupPlayer], reqs: RosterRequirements, week: int | None
) -> LineupDecision:
    """Best-per-week lineup (maximise expected points) — the unsynced default opponent."""
    by_id = {p.id: p for p in roster}
    pool = [
        RosterPlayer(id=p.id, position=p.position, value=p.mean, bye_week=p.bye_week)
        for p in roster
    ]
    lineup = optimize_lineup(pool, reqs, week=week)
    chosen = [(slot, by_id[p.id]) for slot, p in lineup.starters]
    started = {p.id for _, p in chosen}
    bench = tuple(p for p in roster if p.id not in started)
    my_proj = sum(p.mean for _, p in chosen)
    return LineupDecision(
        starters=tuple(chosen),
        bench=bench,
        win_prob=None,
        my_projected=my_proj,
        opp_projected=None,
        posture="best-per-week (no opponent synced)",
        why=_build_why(chosen, bench, win_mode=False),
        narrative=(
            f"No opponent synced → best-per-week lineup, maximising expected points "
            f"({my_proj:.1f})."
        ),
        opponent_synced=False,
    )


def optimal_lineup(
    roster: Sequence[LineupPlayer],
    *,
    opponent: Sequence[LineupPlayer] | None = None,
    requirements: RosterRequirements = _DEFAULT_REQS,
    week: int | None = None,
    spec: CorrelationSpec = _DEFAULT_SPEC,
    n_draws: int = 2_000,
    opt_draws: int = 400,
    seed: int = 20240813,
    time_limit: float = 10.0,
) -> LineupDecision:
    """Weekly start/sit that maximises P(beat ``opponent``); best-per-week when unsynced.

    Args:
        roster: Your rostered players (marginals + correlation keys) for this week.
        opponent: The opponent's roster when the league schedule is synced. ``None`` (or an
            opponent that can't field a legal lineup) → best-per-week fallback.
        requirements: Slot layout (defaults = superflex, half-PPR); reuses E4fix legality.
        week: If given, players on their bye can't start.
        spec: E3 correlation spec (stacks / game correlation).
        n_draws: Correlated draws used to *measure* the reported win-probability.
        opt_draws: Draw subsample the IP optimises over (win-prob is smooth in the lineup).
        seed: RNG + solver seed (deterministic).
        time_limit: CP-SAT wall-clock cap (seconds).

    Returns:
        A `LineupDecision`: chosen starters, bench, win-prob (or None), posture, and a
        per-slot "why".

    Raises:
        InfeasibleRosterError: Your roster can't field a legal lineup.
    """
    if opponent is None:
        return _fallback(roster, requirements, week)

    combined = list(roster) + list(opponent)
    if len({p.id for p in combined}) != len(combined):
        raise ValueError("roster and opponent player_ids must be unique across both")

    opp_cols = _opponent_start_cols(opponent, len(roster), requirements, week)
    if opp_cols is None:
        return _fallback(roster, requirements, week)

    pts = _draw_points(combined, n_draws, spec, seed)
    my_pts = pts[:, : len(roster)]
    opp_score = pts[:, opp_cols].sum(axis=1)

    chosen = _solve_winprob(
        roster, my_pts, opp_score, requirements, week, opt_draws, time_limit, seed
    )
    started = {p.id for _, p in chosen}
    bench = tuple(p for p in roster if p.id not in started)

    start_cols = [j for j, p in enumerate(roster) if p.id in started]
    my_score = my_pts[:, start_cols].sum(axis=1)
    win_prob = float(np.mean(my_score > opp_score))
    my_proj = sum(p.mean for _, p in chosen)
    opp_proj = float(pts[:, opp_cols].mean(axis=0).sum())

    underdog = my_proj < opp_proj
    posture = "ceiling (underdog)" if underdog else "floor (favorite)"
    lean = "ceiling-leaning" if underdog else "floor-leaning"
    narrative = (
        f"vs opponent (proj {opp_proj:.1f}); you project {my_proj:.1f} → {lean}. "
        f"Win probability {win_prob:.0%}."
    )
    return LineupDecision(
        starters=tuple(chosen),
        bench=bench,
        win_prob=win_prob,
        my_projected=my_proj,
        opp_projected=opp_proj,
        posture=posture,
        why=_build_why(chosen, bench, win_mode=True),
        narrative=narrative,
        opponent_synced=True,
    )
