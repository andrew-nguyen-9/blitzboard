"""VONA + positional-run probability — how much a player's slot decays before your next turn.

VONA (Value Over Next Available) is the draft-timing companion to VORP: it asks not *"how
much better than replacement is this player?"* but *"how much of this player's edge evaporates
if I wait one round?"*. The answer is driven by the **positional run** — the number of players
at his position the intervening opponents take before my pick comes back around.

Given the opponent field's per-pick position distributions (`opponent.py`), the count taken at
a position before my next turn is a **Poisson-binomial** (independent picks, differing success
probabilities). A small DP gives its full pmf; assuming opponents draft a position value-greedily,
a run of ``j`` removes the top ``j`` remaining players there, so the expected best-available at
my turn is ``Σ_j P(run=j)·value[j]`` and VONA is the drop from the current best.

`ponytail:` the pmf is a length-(n+1) DP folded over the picks; there is no sampling and no
sim on this path — it is the live-fast scarcity signal the draft board reads every pick.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


def run_pmf(pick_position_probs: Sequence[Mapping[str, float]], position: str) -> list[float]:
    """Poisson-binomial pmf of how many ``position`` players go before your next turn.

    ``pick_position_probs``: for each intervening opponent pick (in order), P(position) — the
    output of `OpponentField.pick_position_sequence`. Returns ``pmf`` where ``pmf[j]`` is
    P(exactly ``j`` players at ``position`` are drafted), ``len(pmf) == len(picks) + 1``.
    """
    pmf = [1.0]  # 0 picks seen so far -> 0 taken w.p. 1
    for probs in pick_position_probs:
        p = min(max(float(probs.get(position, 0.0)), 0.0), 1.0)
        nxt = [0.0] * (len(pmf) + 1)
        for j, mass in enumerate(pmf):
            nxt[j] += mass * (1.0 - p)  # this pick was some other position
            nxt[j + 1] += mass * p  # this pick was `position`
        pmf = nxt
    return pmf


def run_probability(
    pick_position_probs: Sequence[Mapping[str, float]], position: str, k: int = 1
) -> float:
    """P(at least ``k`` players at ``position`` are taken before your next turn) — the "run"."""
    if k <= 0:
        return 1.0
    pmf = run_pmf(pick_position_probs, position)
    return float(sum(pmf[j] for j in range(min(k, len(pmf)), len(pmf))))


def expected_best_available(
    sorted_values: Sequence[float],
    pick_position_probs: Sequence[Mapping[str, float]],
    position: str,
) -> float:
    """E[value of the best remaining ``position`` player at your next turn].

    ``sorted_values``: this position's available player values, **descending**. Assumes a run
    of ``j`` removes the top ``j`` (value-greedy opponents); if the position is exhausted the
    remaining value is 0 (a truly empty slot is worth nothing).
    """
    if not sorted_values:
        return 0.0
    pmf = run_pmf(pick_position_probs, position)
    exp = 0.0
    for j, mass in enumerate(pmf):
        exp += mass * (sorted_values[j] if j < len(sorted_values) else 0.0)
    return float(exp)


@dataclass(frozen=True)
class VonaResult:
    """One position's VONA read at the current pick."""

    position: str
    best_now: float  # value of the best player available at this position right now
    expected_next: float  # expected best-available at this position at your next turn
    vona: float  # best_now - expected_next  (the edge lost by waiting)
    run_prob: float  # P(>=1 player at this position taken before your next turn)


def vona(
    position: str,
    sorted_values: Sequence[float],
    pick_position_probs: Sequence[Mapping[str, float]],
) -> VonaResult:
    """Value-over-next-available for ``position`` given the intervening opponent picks.

    VONA is ``best_now - E[best_available_at_next_turn]``: large when the position is about to
    run (scarce + coveted), ~0 when you can comfortably wait. Pair with VORP: draft the player
    whose ``VORP`` you would most regret losing, i.e. the biggest ``VORP`` protected by ``VONA``.
    """
    best_now = float(sorted_values[0]) if sorted_values else 0.0
    exp_next = expected_best_available(sorted_values, pick_position_probs, position)
    return VonaResult(
        position=position,
        best_now=best_now,
        expected_next=exp_next,
        vona=max(0.0, best_now - exp_next),
        run_prob=run_probability(pick_position_probs, position, k=1),
    )


def vona_board(
    values_by_position: Mapping[str, Sequence[float]],
    pick_position_probs: Sequence[Mapping[str, float]],
) -> dict[str, VonaResult]:
    """VONA for every position on the board — the per-pick scarcity map the draft room reads."""
    return {
        pos: vona(pos, vals, pick_position_probs) for pos, vals in values_by_position.items()
    }
