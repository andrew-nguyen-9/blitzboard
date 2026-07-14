"""Team-scheme factors — offensive pace and pass/run tendency (ported from the pipeline).

How a player's *offense* plays reshapes his volume regardless of his own line:

  * **Pace** — fast offenses run more plays → more opportunity for every skill player.
  * **Pass rate** — pass-heavy offenses lift QB/WR/TE and trim RB rushing volume (the two
    directions of one team tendency).

Both are FREE-derivable from play-by-play (plays/game, pass rate) and hydrated onto
``ctx.context``. League-relative and clamped, so an average offense is a true no-op and only
genuine outliers move a projection. Missing team data → identity.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from blitz_engine.projection.factors.base import clamp, player_positions, player_teams

if TYPE_CHECKING:
    from blitz_engine.projection.model import FactorContext

_LEAGUE_PLAYS = 63.0
_LEAGUE_PASS_RATE = 0.58
_SKILL = ("QB", "RB", "WR", "TE")
_PASS_CATCHERS = ("QB", "WR", "TE")


class PaceFactor:
    """Fast offenses → more plays → more volume for every skill player (±6%)."""

    name = "pace"

    def __call__(self, ctx: FactorContext) -> np.ndarray:
        pace = ctx.context.get("team_pace") or {}
        teams = player_teams(ctx.data)
        positions = player_positions(ctx.data)
        out = np.ones(ctx.data.n_players, dtype=np.float64)
        if not isinstance(pace, dict) or not pace:
            return out
        for i, (pos, team) in enumerate(zip(positions, teams, strict=True)):
            v = pace.get(team)
            if not v or pos not in _SKILL:
                continue
            rel = (float(v) - _LEAGUE_PLAYS) / _LEAGUE_PLAYS
            out[i] = clamp(1.0 + rel * 0.35, 0.94, 1.06)
        return out


class PassRateFactor:
    """Pass-heavy offenses lift QB/WR/TE, trim RB rushing volume (±5%)."""

    name = "pass_rate"

    def __call__(self, ctx: FactorContext) -> np.ndarray:
        rate = ctx.context.get("pass_rate") or {}
        teams = player_teams(ctx.data)
        positions = player_positions(ctx.data)
        out = np.ones(ctx.data.n_players, dtype=np.float64)
        if not isinstance(rate, dict) or not rate:
            return out
        for i, (pos, team) in enumerate(zip(positions, teams, strict=True)):
            pr = rate.get(team)
            if not pr or pos not in _SKILL:
                continue
            edge = float(pr) - _LEAGUE_PASS_RATE
            direction = 1.0 if pos in _PASS_CATCHERS else -1.0  # RB moves opposite
            out[i] = clamp(1.0 + direction * edge * 0.6, 0.95, 1.05)
        return out
