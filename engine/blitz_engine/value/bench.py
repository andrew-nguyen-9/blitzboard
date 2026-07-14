"""Bench valuation — value a reserve by expected *contribution*, not raw talent.

A bench player's worth is what he adds **as a reserve**: the weeks he actually gets
started, times his value in those weeks, times his availability, plus insurance
(handcuff / injury cover), bye-week coverage, and boom-week upside:

    bench_value = availability * E[starts] * value_when_started
                  + upside + handcuff_cover + bye_cover

A second kicker or second defense earns ~0 here — you start exactly one, they almost never
vacate the slot for a bench player, and you stream the position — so the roster solver
(`roster_solver.py`) never trades a startable flyer for a second K/DST.

Scalars are plain Python floats (float32-friendly; the whole roster problem is tiny).
"""
from __future__ import annotations

# Per-week probability the player directly ahead becomes unavailable (injury / benching),
# i.e. how often a start opens up for the reserve. Kickers/defenses almost never vacate the
# slot for a *rostered* backup (you stream instead) -> ~0, which is what zeroes a 2nd K/DST.
POSITION_VACATE_RATE: dict[str, float] = {
    "RB": 0.09,
    "WR": 0.06,
    "TE": 0.05,
    "QB": 0.04,
    "K": 0.005,
    "DST": 0.01,
}

# No-depth-info fallback: bench worth as a fraction of start value. K/DST ~ 0 so a second one
# is near-worthless even when the caller supplies no explicit E[starts].
BENCH_DISCOUNT: dict[str, float] = {
    "QB": 0.35,
    "RB": 0.45,
    "WR": 0.40,
    "TE": 0.30,
    "K": 0.02,
    "DST": 0.05,
}

_DEFAULT_VACATE = 0.05
_DEFAULT_DISCOUNT = 0.30


def bench_value(
    value_when_started: float,
    e_starts: float,
    availability: float = 1.0,
    *,
    upside: float = 0.0,
    handcuff_cover: float = 0.0,
    bye_cover: float = 0.0,
) -> float:
    """Expected reserve contribution (see module docstring for the formula).

    Args:
        value_when_started: The player's value in a week he actually starts.
        e_starts: Expected number of weeks the reserve is promoted into a start.
        availability: Probability he is healthy/active when needed (0..1).
        upside: Bonus for boom-week ceiling (spot-start league-winners).
        handcuff_cover: Insurance value if the starter ahead of him is lost.
        bye_cover: Value of covering a starter's bye week.

    A 2nd K/DST has ``e_starts`` ~ 0, so its value collapses to ~0 regardless of talent.
    """
    core = max(0.0, availability) * max(0.0, e_starts) * value_when_started
    return float(core + upside + handcuff_cover + bye_cover)


def expected_bench_starts(
    position: str,
    depth_rank: int,
    weeks: int = 17,
    bye_weeks_covered: float = 0.0,
) -> float:
    """Expected weeks a reserve is promoted into a start.

    Args:
        position: Player position (drives the per-week vacate rate).
        depth_rank: 1 = first reserve behind the starter, 2 = second, ...
        weeks: Regular-season weeks.
        bye_weeks_covered: Explicit bye-week fills this reserve absorbs.

    A reserve starts in a week only when everyone ahead of him is out; approximated as
    ``vacate_rate ** depth_rank`` per week, plus explicit bye fills. For K/DST the vacate rate
    is ~0, so a rostered backup kicker/defense expects ~0 starts.
    """
    if depth_rank < 1:
        raise ValueError("depth_rank must be >= 1 (1 = first reserve behind the starter)")
    rate = POSITION_VACATE_RATE.get(position, _DEFAULT_VACATE)
    return float(weeks * (rate**depth_rank) + bye_weeks_covered)


def default_bench_value(position: str, value: float) -> float:
    """No-depth-info bench worth: a position-scaled discount of start value.

    Used by the solver when a pool player carries no precomputed bench value. K/DST discount
    to ~0 so the fallback preserves the "never hoard a 2nd kicker" invariant on its own.
    """
    return float(value * BENCH_DISCOUNT.get(position, _DEFAULT_DISCOUNT))
