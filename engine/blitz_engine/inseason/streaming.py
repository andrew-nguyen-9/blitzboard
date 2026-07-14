"""Matchup-driven streaming — win-prob-framed weekly streamer pick (E5).

Streaming (DST, QB, K, TE — the positions you cycle off waivers each week) is *not* "start the
highest-projected free agent". The right streamer depends on the **matchup**: against a strong
opponent you want the streamer that maximises your *ceiling*, against a weak one the one that
protects your *floor*. That is exactly the win-probability posture the E5 lineup optimiser
already reasons about — so streaming is framed as: for each candidate streamer, drop them onto
the roster, solve the win-prob-optimal lineup, and rank the candidates by the resulting P(win
this week).

`ponytail:` this is a thin loop over `lineup.optimal_lineup` — one solve per candidate, ranked
by its win probability (or expected points when no opponent is synced). No new sampler, no
bespoke matchup model; the correlation-aware sim and the floor/ceiling posture are inherited
wholesale from the lineup unit.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from blitz_engine.lineup.winprob import LineupDecision, LineupPlayer, optimal_lineup
from blitz_engine.simulation.correlation import CorrelationSpec
from blitz_engine.value.roster_solver import InfeasibleRosterError, RosterRequirements

_DEFAULT_REQS = RosterRequirements()
_DEFAULT_SPEC = CorrelationSpec()


@dataclass(frozen=True)
class StreamOption:
    """One streamer candidate scored by the win-prob-optimal lineup it produces."""

    id: str
    position: str
    win_prob: float | None       # P(win this week) with this streamer; None when unsynced
    my_projected: float          # projected starter total of the resulting lineup
    started: bool                # did the streamer actually crack the optimal lineup?
    lift: float                  # win-prob (or projected) edge over the worst candidate
    decision: LineupDecision     # the full resulting lineup + "why"
    reason: str


@dataclass(frozen=True)
class StreamBoard:
    """Ranked streamer options for one open slot this week."""

    position: str
    ranked: tuple[StreamOption, ...]
    opponent_synced: bool

    def best(self) -> StreamOption | None:
        """The recommended streamer (None if no candidate could field a legal lineup)."""
        return self.ranked[0] if self.ranked else None


def stream_position(
    base_roster: Sequence[LineupPlayer],
    candidates: Sequence[LineupPlayer],
    *,
    opponent: Sequence[LineupPlayer] | None = None,
    requirements: RosterRequirements = _DEFAULT_REQS,
    week: int | None = None,
    spec: CorrelationSpec = _DEFAULT_SPEC,
    n_draws: int = 2000,
    opt_draws: int = 400,
    seed: int = 20240813,
    time_limit: float = 10.0,
) -> StreamBoard:
    """Rank streamer candidates by the win probability of the lineup each one enables.

    For every candidate the streamer is added to ``base_roster`` and `lineup.optimal_lineup`
    solves the win-prob-optimal start/sit against ``opponent`` (or the best-per-week lineup when
    no opponent is synced). Candidates are ranked by that win probability — so the matchup, not
    a raw projection, drives the pick: a high-ceiling streamer wins the ranking exactly when the
    matchup needs a ceiling.

    Args:
        base_roster: Your rostered players for the week *excluding* the slot being streamed.
        candidates: The streamer options (must not share ids with the roster/opponent).
        opponent: The opponent's roster when the schedule is synced; ``None`` → best-per-week.
        requirements / week / spec / n_draws / opt_draws / seed / time_limit: passed straight to
            `optimal_lineup`.

    Returns:
        A `StreamBoard` with candidates ranked best-first. Candidates whose addition can't field
        a legal lineup are dropped.
    """
    scored: list[StreamOption] = []
    synced = False
    for cand in candidates:
        roster = [*base_roster, cand]
        try:
            decision = optimal_lineup(
                roster,
                opponent=opponent,
                requirements=requirements,
                week=week,
                spec=spec,
                n_draws=n_draws,
                opt_draws=opt_draws,
                seed=seed,
                time_limit=time_limit,
            )
        except InfeasibleRosterError:
            continue
        synced = synced or decision.opponent_synced
        started = any(p.id == cand.id for _, p in decision.starters)
        scored.append(
            StreamOption(
                id=cand.id,
                position=cand.position,
                win_prob=decision.win_prob,
                my_projected=decision.my_projected,
                started=started,
                lift=0.0,  # filled in once the field is known
                decision=decision,
                reason="",
            )
        )

    if not scored:
        return StreamBoard(position="", ranked=(), opponent_synced=False)

    def metric(o: StreamOption) -> float:
        return o.win_prob if o.win_prob is not None else o.my_projected

    scored.sort(key=lambda o: (metric(o), o.my_projected, o.id), reverse=True)
    worst = metric(scored[-1])
    ranked = tuple(_finalise(o, metric(o) - worst) for o in scored)
    return StreamBoard(position=scored[0].position, ranked=ranked, opponent_synced=synced)


def _finalise(o: StreamOption, lift: float) -> StreamOption:
    """Attach the field-relative lift and a plain-language reason to a scored option."""
    role = "starts" if o.started else "benched — the roster already covers the slot"
    if o.win_prob is not None:
        tail = (
            f"win prob {o.win_prob:.0%} ({o.decision.posture}); "
            f"+{lift:.1%} vs the weakest streamer."
        )
    else:
        tail = (
            f"projects {o.my_projected:.1f} (best-per-week); +{lift:.1f} vs the weakest streamer."
        )
    return StreamOption(
        id=o.id,
        position=o.position,
        win_prob=o.win_prob,
        my_projected=o.my_projected,
        started=o.started,
        lift=lift,
        decision=o.decision,
        reason=f"{o.id} {role}; {tail}",
    )
