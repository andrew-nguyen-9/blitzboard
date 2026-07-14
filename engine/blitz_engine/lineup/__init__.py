"""`blitz_engine.lineup` — win-probability-optimal weekly start/sit (E5).

Picks the weekly lineup that maximises P(beat THIS opponent) over the E3 correlated
Monte-Carlo, reusing E4fix's IP slot-legality. Floor (weak opponent) and ceiling (strong
opponent) both fall out of that ONE win-prob objective — no separate heuristics. Degrades to
the best-per-week (max expected points) lineup when the league schedule isn't synced.

    optimal_lineup   opponent → (lineup + win-prob + per-slot "why")
    LineupPlayer     one week's marginal (mean/stdev) + correlation keys
    LineupDecision   starters / bench / win_prob / posture / why
"""
from __future__ import annotations

from blitz_engine.lineup.winprob import (
    LineupDecision,
    LineupPlayer,
    SlotWhy,
    optimal_lineup,
)

__all__ = [
    "LineupDecision",
    "LineupPlayer",
    "SlotWhy",
    "optimal_lineup",
]
