"""Dynamic, demand-derived replacement level → live VORP (E4-deep).

Classic VORP nails a *static* replacement baseline — the Nth-best player at a position, N =
league starter demand — and never moves it. That misreads a live draft: once a position has
been hammered, the player you can *actually still get next turn* is far worse than that fixed
baseline, so the true value-over-replacement of what's on the board right now is higher. This
module makes replacement **demand-derived and per-pick**: the baseline is the player you expect
to still be available at your next turn, given the opponent field's likely picks (`opponent.py`).

`ponytail:` the demand-aware baseline is exactly `vona.expected_best_available` (best-available-
next-turn), so VORP and VONA share one replacement definition instead of two hand-tuned ones.
The static baseline stays as a cheap prior for the cold start / offline path.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from blitz_engine.value.vona import expected_best_available

# Default starter demand per position for a superflex, half-PPR league (SUPERFLEX ≈ +1 QB,
# FLEX ≈ +1 RB/WR). Used only by the static baseline; the live path is demand-derived.
DEFAULT_STARTER_DEMAND: Mapping[str, float] = {
    "QB": 2.0, "RB": 2.5, "WR": 2.5, "TE": 1.0, "K": 1.0, "DST": 1.0,
}


def demand_by_position(
    pick_position_probs: Sequence[Mapping[str, float]],
) -> dict[str, float]:
    """Expected number of each position drafted before your next turn (Poisson-binomial mean).

    The sum of per-pick position probabilities over the intervening opponent picks — the
    "demand" that erodes each position's board between now and when you pick again.
    """
    out: dict[str, float] = {}
    for probs in pick_position_probs:
        for pos, p in probs.items():
            out[pos] = out.get(pos, 0.0) + float(p)
    return out


def demand_replacement_levels(
    values_by_position: Mapping[str, Sequence[float]],
    pick_position_probs: Sequence[Mapping[str, float]],
) -> dict[str, float]:
    """Per-position replacement value = the player you expect to still get next turn.

    ``values_by_position``: available player values per position, **descending**. Recompute
    this every pick — both the board (values shrink) and the demand (opponent beliefs update)
    change. Positions with no upcoming picks fall back to the current best (nothing erodes).
    """
    return {
        pos: expected_best_available(vals, pick_position_probs, pos)
        for pos, vals in values_by_position.items()
    }


def static_replacement_levels(
    values_by_position: Mapping[str, Sequence[float]],
    demand: Mapping[str, float] = DEFAULT_STARTER_DEMAND,
) -> dict[str, float]:
    """Classic fixed VORP baseline: the ``demand``-th best available player per position.

    A cheap cold-start / offline prior with no opponent model. Fractional demand interpolates
    between adjacent ranks; an exhausted position replaces at 0.
    """
    out: dict[str, float] = {}
    for pos, vals in values_by_position.items():
        if not vals:
            out[pos] = 0.0
            continue
        d = max(0.0, float(demand.get(pos, 1.0)))
        lo = int(d)
        frac = d - lo
        v_lo = vals[lo] if lo < len(vals) else 0.0
        v_hi = vals[lo + 1] if lo + 1 < len(vals) else 0.0
        out[pos] = float(v_lo * (1.0 - frac) + v_hi * frac)
    return out


def dynamic_vorp(player_value: float, position: str, replacement: Mapping[str, float]) -> float:
    """Value over replacement for one player at ``position`` given a replacement-level map.

    ``max(0, value - replacement[pos])`` — a player at or below what you can still get next
    turn adds no marginal draft value. This is the scarcity-aware value the equity proxy scales.
    """
    return max(0.0, float(player_value) - float(replacement.get(position, 0.0)))


def vorp_board(
    players_by_position: Mapping[str, Sequence[tuple[str, float]]],
    replacement: Mapping[str, float],
) -> dict[str, float]:
    """player_id -> dynamic VORP for every (id, value) on the board under one replacement map.

    ``players_by_position``: per-position sequence of ``(player_id, value)``. The result is the
    per-pick live VORP board the draft room ranks by (after equity scaling).
    """
    out: dict[str, float] = {}
    for pos, players in players_by_position.items():
        for pid, val in players:
            out[pid] = dynamic_vorp(val, pos, replacement)
    return out
