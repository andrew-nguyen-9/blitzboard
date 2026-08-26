"""`blitz_engine.lineup` — win-probability-optimal weekly start/sit (E5).

Picks the weekly lineup that maximises P(beat THIS opponent) over the E3 correlated
Monte-Carlo, reusing E4fix's IP slot-legality. Floor (weak opponent) and ceiling (strong
opponent) both fall out of that ONE win-prob objective — no separate heuristics. Degrades to
the best-per-week (max expected points) lineup when the league schedule isn't synced.

    optimal_lineup   opponent → (lineup + win-prob + per-slot "why")
    LineupPlayer     one week's marginal (mean/stdev) + correlation keys
    LineupDecision   starters / bench / win_prob / posture / why

E4 adds the *season-shaped* companion: instead of one week against one opponent, weeks 1–18 of
"can this roster be fielded at all, and what does the week cost?" — byes hard-enforced,
availability from e2a, injury from e3, per league config.

    feasibility_surface  roster + config → 18 × (legal, expected_points, cost_vs_baseline)
    sample_surface       the same chain drawn, for callers that need the distribution
    InjuryDynamics       e3's published clinical-injury model as a weekly Markov chain
"""
from __future__ import annotations

from blitz_engine.lineup.feasibility import (
    WEEKS,
    FeasibilitySurface,
    InjuryDynamics,
    WeekFeasibility,
    feasibility_surface,
    requirements_from_row,
    sample_surface,
)
from blitz_engine.lineup.winprob import (
    LineupDecision,
    LineupPlayer,
    SlotWhy,
    optimal_lineup,
)

__all__ = [
    "WEEKS",
    "FeasibilitySurface",
    "InjuryDynamics",
    "LineupDecision",
    "LineupPlayer",
    "SlotWhy",
    "WeekFeasibility",
    "feasibility_surface",
    "optimal_lineup",
    "requirements_from_row",
    "sample_surface",
]
