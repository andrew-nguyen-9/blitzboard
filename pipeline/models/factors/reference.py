"""
ReferenceFactor — the canonical MINIMAL example (F3).

It is INTENTIONALLY an identity (multiplier 1.0). It exists to (a) prove the
auto-discovery + composition wiring end-to-end and (b) show downstream authors the
exact shape to copy. Because it is identity, shipping it changes NO projection and
regresses NO backtest.

Real domain factors — injury (E1/E5), college (E2), team-vs-team / weather /
scheme (E3), betting (E5) — are added by those units as their OWN files here. Do
NOT extend this one; copy its shape into a new module.

Template for a real factor::

    from .base import Factor, FactorContext, MULTIPLIER

    class MyFactor(Factor):
        kind = MULTIPLIER
        positions = ("RB", "WR")          # or None for all
        def compute(self, ctx: FactorContext) -> float:
            # read ctx.position / ctx.nfl_team / ctx.opponent / ctx.week /
            # ctx.injury_status / ctx.metadata / ctx.store … return a multiplier
            return 1.0
"""
from __future__ import annotations

from .base import Factor, FactorContext, MULTIPLIER


class ReferenceFactor(Factor):
    kind = MULTIPLIER          # identity multiplier = 1.0 (no-op by design)
    positions = None           # applies to every position

    def compute(self, ctx: FactorContext) -> float:
        return 1.0
