"""`blitz_engine.projection.talent` — E1-talent true-talent dynamics.

Plugs E1-core's `TalentPriorHook` seam (`priors.py`) with a real per-player talent estimate
built from a career arc, in-season Kalman update, per-position aging and an HMM regime, plus
a wide rookie prior. The public surface:

    TalentModel      fit on player history → a drop-in `talent_prior=` hook for the projector
    PlayerTalent     one veteran's resolved talent record (loc/scale + regime + arc)
    RegimeFeatures   the breakout/steady/decline/hurt label + leading indicators (E2 hazard)
    AgingCurves      per-position age→talent curves (peak-age + adjustment accessors)
    RookiePrior(s)   draft-capital + archetype + optional-CFBD rookie priors + degrade path
    CareerArc        GP-trend + Kalman-momentum arc (per-player dynamics)

Everything degrades to neutral (loc 0 / default scale) for unknown players, so injecting
this hook can never worsen the base fit — the seam's hard guarantee.
"""
from __future__ import annotations

from blitz_engine.projection.talent.aging import AgingCurves
from blitz_engine.projection.talent.dynamics import CareerArc, fit_career_arc, learn_lengthscale
from blitz_engine.projection.talent.model import PlayerTalent, TalentModel
from blitz_engine.projection.talent.regime import REGIMES, RegimeFeatures, label_regime
from blitz_engine.projection.talent.rookie import RookiePrior, RookiePriors

__all__ = [
    "REGIMES",
    "AgingCurves",
    "CareerArc",
    "PlayerTalent",
    "RegimeFeatures",
    "RookiePrior",
    "RookiePriors",
    "TalentModel",
    "fit_career_arc",
    "label_regime",
    "learn_lengthscale",
]
