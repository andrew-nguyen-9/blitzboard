"""Weather factor — forecast distribution near the game, climatology far out.

Bad weather reshapes *volume/game-script*: cold, wind, and precipitation suppress passing
(QB/WR/TE opportunity) and nudge game-script toward the run (RB opportunity up). The core
applies factors on log-opportunity, so this is a game-script signal, not an efficiency one.

Horizon handling (brief): a forecast is trustworthy near kickoff and mush far out, so we
**shrink the forecast deviation toward climatology** as ``horizon_days`` grows — full effect
inside ~3 days, a residual climatology-weight floor by ~2 weeks. Missing weather (or an
indoor game) ⇒ identity, so a context-free/dome player is a true no-op.

Context: ``ctx.context["weather"] = {team_code: {temp_f, wind_mph, precip, indoor,
horizon_days}}`` (any key optional; hydrated upstream by E0-sources).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from blitz_engine.projection.factors.base import clamp, player_positions, player_teams

if TYPE_CHECKING:
    from blitz_engine.projection.model import FactorContext

_PASS = ("QB", "WR", "TE")


def _forecast_mult(pos: str, w: dict) -> float:
    """Raw multiplier from a per-game weather blob (identity indoors / no data)."""
    if w.get("indoor"):
        return 1.0
    temp = w.get("temp_f")
    wind = w.get("wind_mph")
    precip = bool(w.get("precip"))
    if pos in _PASS:
        m = 1.0
        if temp is not None and temp < 32:
            m *= 1.0 - clamp((32 - temp) / 5 * 0.01, 0.0, 0.06)
        if wind is not None and wind > 15:
            m *= 1.0 - clamp((wind - 15) * 0.01, 0.0, 0.08)
        if precip:
            m *= 0.97
        return clamp(m, 0.85, 1.0)
    if pos == "RB":
        boost = 0.0
        if wind is not None and wind > 15:
            boost += clamp((wind - 15) * 0.004, 0.0, 0.02)
        if temp is not None and temp < 32:
            boost += 0.01
        if precip:
            boost += 0.01
        return clamp(1.0 + boost, 1.0, 1.04)
    return 1.0


def _horizon_weight(horizon_days: object) -> float:
    """Confidence in the forecast: 1.0 by kickoff (~≤3d), floor 0.2 (climatology) far out."""
    if not isinstance(horizon_days, (int, float)):
        return 1.0
    return clamp(1.0 - (float(horizon_days) - 3.0) / 11.0, 0.2, 1.0)


class WeatherFactor:
    """Bounded, degrade-neutral weather adjustment to opportunity (game-script)."""

    name = "weather"

    def __call__(self, ctx: FactorContext) -> np.ndarray:
        weather = ctx.context.get("weather") or {}
        teams = player_teams(ctx.data)
        positions = player_positions(ctx.data)
        out = np.ones(ctx.data.n_players, dtype=np.float64)
        if not isinstance(weather, dict) or not weather:
            return out
        for i, (pos, team) in enumerate(zip(positions, teams, strict=True)):
            w = weather.get(team)
            if not isinstance(w, dict):
                continue
            raw = _forecast_mult(pos, w)
            k = _horizon_weight(w.get("horizon_days"))
            out[i] = 1.0 + (raw - 1.0) * k  # shrink deviation toward climatology far out
        return out
