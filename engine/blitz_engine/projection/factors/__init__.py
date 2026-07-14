"""`blitz_engine.projection.factors` — bounded, OPTIONAL, degrade-neutral context factors.

These plug into E1-core's ``FactorHook`` seam: each is a small pure fn that maps the core's
player universe to a per-player raw *opportunity* multiplier (identity ``1.0``); the projector
clamps every one to ``FACTOR_BOUNDS`` and applies it on log-opportunity. rel=DEGRADE — a
factor that has no data for a player (or, for H2H, no significant signal) returns ``1.0``, so
the base fit is never made worse and dependents proceed.

    WeatherFactor            forecast near game, climatology far out   (QB/WR/TE ↓, RB ↑)
    AltitudeDomeFactor       dome / altitude venue effects (ported)
    PaceFactor, PassRateFactor  offensive pace + pass/run tendency (ported)
    CoachingTendencyFactor   pass/run prior, softens on regime change
    SituationalFactor        home / travel / rest / short-week / fatigue
    TeamH2HFactor            matchup nudge — GATED by ablation significance (drops if noise)

`default_factors()` returns the full tuple, ready to hand to
``HierarchicalProjector(factors=...)``. All read their inputs from ``FactorContext.context``
(keyed by team code / player id) so a hook never re-queries the store.
"""
from __future__ import annotations

from collections.abc import Sequence

from blitz_engine.projection.factors.coaching import CoachingTendencyFactor
from blitz_engine.projection.factors.environment import STADIUMS, AltitudeDomeFactor
from blitz_engine.projection.factors.scheme import PaceFactor, PassRateFactor
from blitz_engine.projection.factors.situational import SituationalFactor
from blitz_engine.projection.factors.team_vs_team import TeamH2HFactor
from blitz_engine.projection.factors.weather import WeatherFactor

__all__ = [
    "STADIUMS",
    "AltitudeDomeFactor",
    "CoachingTendencyFactor",
    "PaceFactor",
    "PassRateFactor",
    "SituationalFactor",
    "TeamH2HFactor",
    "WeatherFactor",
    "default_factors",
]


def default_factors() -> Sequence[object]:
    """The full bounded/degrade-neutral factor bank, in composition order."""
    return (
        WeatherFactor(),
        AltitudeDomeFactor(),
        PaceFactor(),
        PassRateFactor(),
        CoachingTendencyFactor(),
        SituationalFactor(),
        TeamH2HFactor(),
    )
