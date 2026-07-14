"""Trade evaluator — fairness + Δequity win-win swaps, ranked and explained (E5).

A trade is worth making when it raises *both* teams' championship equity — which is possible
whenever each side trades from a positional *surplus* into the other's *need*. The right value
of a player to a team is therefore not his raw ROS points but his **marginal contribution to
that team's best legal starting lineup**: a third startable RB on a team that already starts
two is nearly free to give up, and gold to a team starting a replacement-level RB. E4fix's
lineup IP already computes that starting-lineup value exactly, so a trade's ΔstarterValue for a
team is just ``lineup_value(after) − lineup_value(before)`` — positional need falls out for
free.

ΔstarterValue is in points·week⁻¹; each side scales it by its own equity **sensitivity**
(``dP(champion)/d(points·week⁻¹)`` from E4's `calibrate_equity_sensitivity`) to get a Δchampion
equity per team (default sensitivity 1.0 leaves the board in raw value units). *Fairness* is how
balanced those two equity deltas are, and *win-win* is simply "both deltas positive".

`ponytail:` the whole evaluator is two `optimize_lineup` solves per team (before/after) minus
each other; the equity map is one scalar multiply per side. Reuses `roster_solver.Player` as-is
— no new player type. No re-sim: the sensitivity is E4's one first-order link to the league sim.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from blitz_engine.value.roster_solver import (
    InfeasibleRosterError,
    Player,
    RosterRequirements,
    optimize_lineup,
)

_DEFAULT_REQS = RosterRequirements()
_EPS = 1e-9


@dataclass(frozen=True)
class TradeSide:
    """One team in a trade: its full roster + its equity sensitivity.

    ``sensitivity`` is ``dP(champion)/d(points·week⁻¹)`` from E4's `calibrate_equity_sensitivity`
    — how much a marginal point of weekly starting value raises this team's title odds. The
    default 1.0 leaves equity deltas in raw points·week⁻¹ units (useful before calibration).
    """

    roster_id: str
    roster: tuple[Player, ...]
    sensitivity: float = 1.0


@dataclass(frozen=True)
class TradeEval:
    """One evaluated swap: per-side Δvalue/Δequity, fairness, and a win-win verdict."""

    a_sends: tuple[str, ...]
    b_sends: tuple[str, ...]
    delta_value_a: float      # ΔstarterValue for side A (points·week⁻¹)
    delta_value_b: float
    delta_equity_a: float     # ΔP(champion) for A = sensitivity_a · Δvalue_a
    delta_equity_b: float
    fairness: float           # 1 = both sides gain equally; → 0 as the deltas diverge/oppose
    win_win: bool             # both equity deltas strictly positive
    legal: bool               # both post-trade rosters can still field a legal lineup
    reason: str


def _starter_value(
    roster: Sequence[Player], reqs: RosterRequirements, week: int | None
) -> float | None:
    """Best legal starting-lineup value for ``roster`` (None if it can't field one)."""
    try:
        return optimize_lineup(list(roster), reqs, week=week).starter_value
    except InfeasibleRosterError:
        return None


def _apply(roster: Sequence[Player], remove: set[str], add: Sequence[Player]) -> list[Player]:
    """``roster`` with ``remove`` ids taken out and ``add`` players brought in."""
    return [p for p in roster if p.id not in remove] + list(add)


def _fairness(da: float, db: float) -> float:
    """Balance of two equity deltas: 1 when equal, → 0 as they diverge or oppose in sign."""
    denom = abs(da) + abs(db)
    if denom < _EPS:
        return 1.0
    return max(0.0, 1.0 - abs(da - db) / denom)


def evaluate_trade(
    a: TradeSide,
    b: TradeSide,
    *,
    a_sends: Sequence[str],
    b_sends: Sequence[str],
    requirements: RosterRequirements = _DEFAULT_REQS,
    week: int | None = None,
) -> TradeEval:
    """Evaluate one proposed swap: A sends ``a_sends`` to B, B sends ``b_sends`` to A.

    Computes each team's ΔstarterValue (best-lineup value after − before) via E4fix's lineup IP,
    scales it by that team's equity sensitivity, and reports fairness + a win-win verdict.

    Raises:
        KeyError: an id in ``a_sends``/``b_sends`` isn't on the corresponding roster.
    """
    a_send_set, b_send_set = set(a_sends), set(b_sends)
    a_by_id = {p.id: p for p in a.roster}
    b_by_id = {p.id: p for p in b.roster}
    missing = (a_send_set - a_by_id.keys()) | (b_send_set - b_by_id.keys())
    if missing:
        raise KeyError(f"traded ids not on the sending roster: {sorted(missing)}")

    a_out = [a_by_id[i] for i in a_sends]
    b_out = [b_by_id[i] for i in b_sends]
    a_after = _apply(a.roster, a_send_set, b_out)
    b_after = _apply(b.roster, b_send_set, a_out)

    before_a = _starter_value(a.roster, requirements, week)
    before_b = _starter_value(b.roster, requirements, week)
    after_a = _starter_value(a_after, requirements, week)
    after_b = _starter_value(b_after, requirements, week)
    legal = after_a is not None and after_b is not None

    dva = (after_a - before_a) if (after_a is not None and before_a is not None) else 0.0
    dvb = (after_b - before_b) if (after_b is not None and before_b is not None) else 0.0
    dea = a.sensitivity * dva
    deb = b.sensitivity * dvb

    win_win = legal and dea > _EPS and deb > _EPS
    fairness = _fairness(dea, deb) if legal else 0.0

    if not legal:
        verdict = "breaks a starting lineup — not viable"
    elif win_win:
        verdict = f"win-win (fairness {fairness:.0%})"
    elif dea > _EPS or deb > _EPS:
        gainer = a.roster_id if dea >= deb else b.roster_id
        verdict = f"lopsided — only {gainer} clearly gains"
    else:
        verdict = "neither side gains"
    reason = (
        f"{a.roster_id} Δequity {dea:+.3f} (Δvalue {dva:+.1f}), "
        f"{b.roster_id} Δequity {deb:+.3f} (Δvalue {dvb:+.1f}) — {verdict}."
    )
    return TradeEval(
        a_sends=tuple(a_sends),
        b_sends=tuple(b_sends),
        delta_value_a=dva,
        delta_value_b=dvb,
        delta_equity_a=dea,
        delta_equity_b=deb,
        fairness=fairness,
        win_win=win_win,
        legal=legal,
        reason=reason,
    )


def propose_trades(
    a: TradeSide,
    b: TradeSide,
    *,
    requirements: RosterRequirements = _DEFAULT_REQS,
    week: int | None = None,
    limit: int | None = None,
    win_win_only: bool = False,
) -> tuple[TradeEval, ...]:
    """Enumerate 1-for-1 swaps between A and B, ranked win-win-first then most mutually fair.

    Every (a_player, b_player) pair is evaluated; the ranking surfaces trades that help *both*
    teams first, breaking ties by the smaller of the two equity gains (so a balanced win-win
    beats a lopsided one) and then by fairness.

    Args:
        limit: keep only the top ``limit`` proposals (None → all).
        win_win_only: drop everything that isn't strictly win-win.

    Returns:
        Ranked `TradeEval`s, best-first.
    """
    evals = [
        evaluate_trade(
            a, b, a_sends=[pa.id], b_sends=[pb.id], requirements=requirements, week=week
        )
        for pa in a.roster
        for pb in b.roster
    ]
    if win_win_only:
        evals = [e for e in evals if e.win_win]
    evals.sort(
        key=lambda e: (
            e.win_win,
            min(e.delta_equity_a, e.delta_equity_b),
            e.fairness,
            e.delta_equity_a + e.delta_equity_b,
        ),
        reverse=True,
    )
    return tuple(evals if limit is None else evals[:limit])
