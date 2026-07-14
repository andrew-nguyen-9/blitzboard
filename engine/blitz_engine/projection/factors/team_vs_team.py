"""Team head-to-head factor — a matchup nudge, GATED BY ABLATION SIGNIFICANCE.

A team's historical H2H record vs an opponent is a noisy signal: mostly it reflects the same
roster/scheme edges already priced elsewhere, and small samples invite overfitting. The brief
is explicit — weight it **only if it survives an ablation-significance test, else drop it**.

So this factor is the one that can *turn itself off*: it computes the per-team matchup
multiplier from ``ctx.context["h2h"]`` (a 0..1 softness, 0 tough → 1 soft), but applies it
ONLY when ``ctx.context["h2h_ablation"] = {"signal": [...], "outcome": [...]}`` shows the
signal correlates with the outcome beyond chance (permutation test, see ``ablation.py``).
No ablation evidence, or non-significant → every player returns ``1.0`` (degrade-neutral).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from blitz_engine.projection.factors.ablation import is_significant
from blitz_engine.projection.factors.base import clamp, player_positions, player_teams

if TYPE_CHECKING:
    from blitz_engine.projection.model import FactorContext

_SWING = 0.08  # ±8% max matchup swing (softest → ×1.08, toughest → ×0.92)
_SKILL = ("QB", "RB", "WR", "TE")


class TeamH2HFactor:
    """Bounded matchup factor that DROPS to neutral unless the signal beats an ablation test."""

    name = "h2h"

    def __init__(self, alpha: float = 0.05) -> None:
        self.alpha = alpha

    def __call__(self, ctx: FactorContext) -> np.ndarray:
        out = np.ones(ctx.data.n_players, dtype=np.float64)
        h2h = ctx.context.get("h2h") or {}
        if not isinstance(h2h, dict) or not h2h:
            return out

        # ABLATION GATE: no evidence, or the signal is noise → drop the whole factor.
        abl = ctx.context.get("h2h_ablation") or {}
        if not isinstance(abl, dict) or not is_significant(
            abl.get("signal"), abl.get("outcome"), self.alpha
        ):
            return out

        teams = player_teams(ctx.data)
        positions = player_positions(ctx.data)
        for i, (pos, team) in enumerate(zip(positions, teams, strict=True)):
            soft = h2h.get(team)
            if soft is None or pos not in _SKILL:
                continue
            centred = clamp(float(soft), 0.0, 1.0) - 0.5  # 0.5 neutral
            out[i] = 1.0 + _SWING * centred * 2.0
        return out
