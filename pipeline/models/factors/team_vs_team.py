"""
TeamVsTeamFactor (E1) — weekly opponent-defense matchup adjustment.

A skill player's weekly projection is nudged by how the opponent's defense fares
against that player's position: a soft matchup boosts, a stout one discounts. This
is a WEEKLY signal — it only fires when the context carries both an ``opponent``
and a ``week`` (i.e. a per-week Monte Carlo run). A season-long draft projection
(``opponent is None``) is left untouched (identity 1.0), and the factor degrades to
identity whenever no opponent-defense rating is available — so it never regresses
the offline/draft path and only shapes value where real schedule data exists.

Reshaping the mean here means both the ``VorpEngine`` and the ``MonteCarloEngine``
consume the matchup-adjusted distribution (value_engine samples it), which is how
"roster strength vs projected opponents" reaches the Monte Carlo sim (spec cat 8).

Rating source (metadata escape-hatch, per the F3 contract, tried in order):
  * ``ctx.metadata["opp_def_vs_pos"]`` — a direct 0..1 softness for THIS matchup
    (0 = toughest defense vs the position, 1 = softest). Used verbatim if present.
  * ``ctx.metadata["opp_def_rank"]``   — the opponent's rank at defending
    ``ctx.position`` (1 = best/toughest .. 32 = worst/softest). Mapped to 0..1.
Absent both → identity. The swing is bounded to a realistic weekly band.
"""
from __future__ import annotations

from .base import Factor, FactorContext, MULTIPLIER

_SWING = 0.08  # ±8% max weekly matchup swing (bounded; softest → ×1.08, toughest → ×0.92)
_RANKS = 32    # NFL defenses


class TeamVsTeamFactor(Factor):
    kind = MULTIPLIER
    positions = ("QB", "RB", "WR", "TE")  # matchup shapes skill output; K/DST priced elsewhere

    def applies(self, ctx: FactorContext) -> bool:
        # weekly-only: needs a concrete opponent and week to be meaningful
        return super().applies(ctx) and bool(ctx.opponent) and ctx.week is not None

    def _softness(self, ctx: FactorContext) -> float | None:
        """Opponent-defense softness vs this position in [0, 1] (0 tough, 1 soft),
        or None when no rating is available (→ identity)."""
        meta = ctx.metadata or {}
        direct = meta.get("opp_def_vs_pos")
        if isinstance(direct, (int, float)):
            return max(0.0, min(1.0, float(direct)))
        rank = meta.get("opp_def_rank")
        if isinstance(rank, (int, float)) and rank:
            return max(0.0, min(1.0, (float(rank) - 1.0) / (_RANKS - 1)))
        return None

    def compute(self, ctx: FactorContext) -> float:
        soft = self._softness(ctx)
        if soft is None:
            return 1.0
        # centre at neutral (0.5): soft matchup → >1, tough matchup → <1, bounded ±_SWING
        return 1.0 + _SWING * (soft - 0.5) * 2.0
