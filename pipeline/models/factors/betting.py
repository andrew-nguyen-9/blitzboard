"""BettingFactor (E5) — a BOUNDED, confidence-weighted nudge from betting markets.

Betting is a LIGHT, acknowledged signal: it must NOT swing projections
significantly and must be logged as its OWN factor, never folded silently into
value. This factor is the model half of E5 (the ingest half is
``adapters/odds.py``).

Contract (F3, ``factors/base.py``):
    * ``kind = MULTIPLIER``; identity ``1.0``.
    * Reads ONLY ``ctx.metadata["betting"]`` — the escape-hatch the Factor
      protocol reserves for signals like this. Absent/empty → exact identity, so
      until the projector joins odds into player metadata this factor is a
      provable no-op (zero backtest regression), exactly like the reference
      factor. It activates the instant odds metadata is present.
    * Signal = Vegas *implied team total* vs a league baseline, normalized,
      **hard-capped** at ``NUDGE_CAP`` and scaled by a market-confidence weight
      in ``[0, 1]``. The multiplier is therefore ALWAYS within
      ``[1 - NUDGE_CAP, 1 + NUDGE_CAP]`` regardless of input — proven by the
      ablation test (``tests/test_betting_factor.py``).
    * The F3 framework logs every non-identity factor by name in
      ``projection.by_stat["factors"]`` → this nudge is separately auditable.

Metadata shape (populated later when odds are joined onto player rows):
    ctx.metadata["betting"] = {"team_total": float, "confidence": float}
``team_total`` is the player's team's Vegas-implied points; ``confidence`` (opt,
default 1.0) is bookmaker agreement in ``[0, 1]``.
"""
from __future__ import annotations

from .base import MULTIPLIER, Factor, FactorContext

# League-average implied team total (NFL ~22-23 pts/team). A team projected to
# score above this gets a slight upward nudge for its offensive players; below,
# a slight downward one.
_BASELINE_TEAM_TOTAL = 22.5

# The HARD cap on the nudge. ±4% — small enough that betting can never dominate a
# projection, large enough to register. This is the documented ablation bound.
NUDGE_CAP = 0.04


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


class BettingFactor(Factor):
    kind = MULTIPLIER
    # Offensive skill + kicker: a team's implied total speaks to its offensive
    # output. Defenses/others are left untouched (identity).
    positions = ("QB", "RB", "WR", "TE", "K")
    enabled = True  # safe: exact identity until odds metadata exists (see module doc)

    def compute(self, ctx: FactorContext) -> float:
        bet = ctx.metadata.get("betting") if ctx.metadata else None
        if not isinstance(bet, dict):
            return 1.0
        team_total = bet.get("team_total")
        if team_total is None:
            return 1.0
        confidence = _clamp(float(bet.get("confidence", 1.0)), 0.0, 1.0)
        # Normalize deviation from baseline into [-1, 1], then cap + confidence-weight.
        signal = _clamp((float(team_total) - _BASELINE_TEAM_TOTAL) / _BASELINE_TEAM_TOTAL, -1.0, 1.0)
        return 1.0 + signal * NUDGE_CAP * confidence
