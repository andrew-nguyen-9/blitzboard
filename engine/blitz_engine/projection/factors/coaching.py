"""Coaching-tendency factor — a bounded pass/run prior that softens on regime change.

A coaching staff carries a stable pass/run lean; used as a *prior* it tilts QB/WR/TE vs RB
opportunity much like ``PassRateFactor``, but sourced from staff tendency rather than this
season's play-by-play. The brief also asks that a **coaching change widen variance**: the
factor seam only reshapes the opportunity mean (variance is a prior/latent concern owned by
E1-talent/E1-latents), so the degrade-neutral analog here is to **shrink the tendency toward
neutral on a new regime** — an unknown staff earns a less-confident, closer-to-1.0 prior.

Context: ``ctx.context["coaching"] = {team_code: {pass_bias: float, new_regime: bool}}``
where ``pass_bias`` is a signed lean (>0 pass-leaning). Missing → identity.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from blitz_engine.projection.factors.base import clamp, player_positions, player_teams

if TYPE_CHECKING:
    from blitz_engine.projection.model import FactorContext

_PASS_CATCHERS = ("QB", "WR", "TE")
_NEW_REGIME_SHRINK = 0.4  # a fresh staff's tendency prior counts 40% (pulled toward 1.0)


class CoachingTendencyFactor:
    """Bounded, degrade-neutral coaching pass/run prior (softens on regime change)."""

    name = "coaching"

    def __call__(self, ctx: FactorContext) -> np.ndarray:
        coaching = ctx.context.get("coaching") or {}
        teams = player_teams(ctx.data)
        positions = player_positions(ctx.data)
        out = np.ones(ctx.data.n_players, dtype=np.float64)
        if not isinstance(coaching, dict) or not coaching:
            return out
        for i, (pos, team) in enumerate(zip(positions, teams, strict=True)):
            c = coaching.get(team)
            if not isinstance(c, dict) or pos not in ("QB", "RB", "WR", "TE"):
                continue
            bias = float(c.get("pass_bias", 0.0))
            direction = 1.0 if pos in _PASS_CATCHERS else -1.0
            m = 1.0 + direction * bias * 0.6
            if c.get("new_regime"):  # unknown staff → shrink prior toward neutral
                m = 1.0 + (m - 1.0) * _NEW_REGIME_SHRINK
            out[i] = clamp(m, 0.95, 1.05)
        return out
