"""Situational factor — home / travel / rest / short-week / fatigue (one bounded fn).

The week's *game situation* nudges team volume: a home game is a small boost; a short week,
long travel, or a short rest window compound into a small fatigue penalty. Kept intentionally
gentle (±~4%) and combined multiplicatively — the seam clamp is the hard backstop, this band
is the honest one. Missing situation → identity, so the draft path is untouched.

Context: ``ctx.context["game_situation"] = {team_code: {home: bool, travel_miles: float,
rest_days: int, short_week: bool}}`` (any key optional).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from blitz_engine.projection.factors.base import clamp, player_teams

if TYPE_CHECKING:
    from blitz_engine.projection.model import FactorContext

_NORMAL_REST = 6  # rest days below this start to bite (fatigue)


def _situation_mult(s: dict) -> float:
    m = 1.01 if s.get("home") else (0.99 if "home" in s else 1.0)
    rest = s.get("rest_days")
    if isinstance(rest, (int, float)) and rest < _NORMAL_REST:
        m *= 1.0 - clamp((_NORMAL_REST - rest) * 0.005, 0.0, 0.02)
    if s.get("short_week"):
        m *= 0.985
    travel = s.get("travel_miles")
    if isinstance(travel, (int, float)) and travel > 0:
        m *= 1.0 - clamp(float(travel) / 10000 * 0.02, 0.0, 0.02)
    return clamp(m, 0.96, 1.02)


class SituationalFactor:
    """Bounded, degrade-neutral home/travel/rest/fatigue adjustment to opportunity."""

    name = "situational"

    def __call__(self, ctx: FactorContext) -> np.ndarray:
        sit = ctx.context.get("game_situation") or {}
        teams = player_teams(ctx.data)
        out = np.ones(ctx.data.n_players, dtype=np.float64)
        if not isinstance(sit, dict) or not sit:
            return out
        for i, team in enumerate(teams):
            s = sit.get(team)
            if isinstance(s, dict) and s:
                out[i] = _situation_mult(s)
        return out
