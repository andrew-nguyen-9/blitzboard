"""
InjuryFactor (E1) — availability discount from a player's injury designation.

Reads ``ctx.injury_status`` (populated by ``player_ingest`` from the players row;
the underlying data arrives via an F2-shape injury adapter keyed on
``INJURY_API_KEY``). When no status is present the factor is a TRUE identity
(multiplier 1.0), so with no injury source configured every projection is
unchanged — zero regression, per the F3 factor contract and the F2 degrade
contract.

Designations map to a season-availability multiplier: week-to-week tags
(Questionable/Doubtful) shave a little; longer-term absences
(Out/IR/PUP/Suspended/NFI) shave more. The reshaped mean feeds BOTH the
``VorpEngine`` and the ``MonteCarloEngine`` (value_engine samples the adjusted
distribution), so an injured player's availability-adjusted value correctly drops
below a healthy comparable at the draft — E1 objective, spec category 5.
"""
from __future__ import annotations

from .base import Factor, FactorContext, MULTIPLIER

# status (lower-cased) → season availability multiplier. Identity for anything
# meaning "available"; a mild default for a present-but-unrecognised tag (a listed
# injury still signals some risk, but stay conservative to avoid false negatives).
_DISCOUNT: dict[str, float] = {
    "questionable": 0.97, "q": 0.97,
    "doubtful": 0.90, "d": 0.90,
    "out": 0.85, "o": 0.85,
    "na": 0.85, "inactive": 0.85,
    "cov": 0.90, "covid": 0.90,
    "suspended": 0.70, "sus": 0.70,
    "pup": 0.60, "nfi": 0.60,
    "ir": 0.55, "injured_reserve": 0.55, "dnr": 0.55,
}
# tags that mean "available" — explicit identity so they never shave value.
_HEALTHY = frozenset({
    "", "active", "act", "a", "healthy", "probable", "p", "full", "cleared",
})
_UNKNOWN_TAG_DISCOUNT = 0.97  # present-but-unrecognised designation → mild caution


class InjuryFactor(Factor):
    kind = MULTIPLIER
    positions = None  # any position; DST/K carry no injury_status → identity anyway

    def compute(self, ctx: FactorContext) -> float:
        s = (ctx.injury_status or "").strip().lower()
        if not s or s in _HEALTHY:
            return 1.0
        return _DISCOUNT.get(s, _UNKNOWN_TAG_DISCOUNT)
