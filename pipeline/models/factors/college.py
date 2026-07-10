"""
CollegeProspectFactor (E2) — a college-derived projection adjustment for rookies.

Rookies and near-rookies have little-to-no NFL history, so the ensemble's
history-driven signals fall back to a flat positional prior (see
``HeuristicProjector.project`` — the "unproven discount"). This factor nudges that
prior UP for productive college prospects and DOWN for unproductive ones, using a
single normalized ``prospect_score`` ∈ [0, 1] that ``ingest/college_ingest.py``
condenses from CollegeFootballData production (0.5 = neutral).

Contract (F3, one-file-per-factor, auto-discovered — ZERO ``projector.py`` edit):
  * kind = MULTIPLIER, identity 1.0.
  * Reads ``ctx.metadata["college_production"]["prospect_score"]`` — the escape-hatch
    dict the college ingest merges into ``players.metadata`` (see FACTOR_CONTRACT
    §context.metadata and DATA_SOURCES §College stats).
  * DEGRADES to identity when there is no college context, when the player is not a
    rookie, or off the skill positions — so shipping it regresses NO backtest (no
    historical fixture row carries ``college_production``).

Bounded to ±12% so a single college signal can shade, but never dominate, the
model. Orthogonal to predictability f(ρ), which the ValueEngine applies later on
value (FACTOR_CONTRACT §orthogonality) — do not double-count here.
"""
from __future__ import annotations

from .base import Factor, FactorContext, MULTIPLIER

# Rookies (years_exp 0) plus true second-year "new players" (years_exp 1), where a
# strong/weak college profile is still the best available production prior.
ROOKIE_MAX_EXP = 1
# Max shade around the neutral 1.0 multiplier (prospect_score 0 → 0.88, 1 → 1.12).
SPREAD = 0.12


class CollegeProspectFactor(Factor):
    kind = MULTIPLIER
    positions = ("QB", "RB", "WR", "TE")   # skill positions only; K/DEF have no college prospect signal
    enabled = True

    def applies(self, ctx: FactorContext) -> bool:
        """Rookies/new players at a skill position only. Unknown experience → skip
        (identity), never guess."""
        if ctx.position not in (self.positions or ()):
            return False
        ye = ctx.years_exp
        return ye is not None and ye <= ROOKIE_MAX_EXP

    def compute(self, ctx: FactorContext) -> float:
        prod = (ctx.metadata or {}).get("college_production")
        if not isinstance(prod, dict):
            return 1.0                       # no college context → identity (degrade)
        score = prod.get("prospect_score")
        if not isinstance(score, (int, float)):
            return 1.0
        score = max(0.0, min(1.0, float(score)))
        # neutral 0.5 → 1.0; 0 → 1-SPREAD; 1 → 1+SPREAD
        return round(1.0 + SPREAD * (score - 0.5) * 2.0, 4)
