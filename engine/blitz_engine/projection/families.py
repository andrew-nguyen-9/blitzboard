"""Prescriptive per-stat likelihood families + fantasy-points composition.

Each fantasy stat has a *natural* generative family (brief §"Prescriptive per-stat
families"). Modelling counts as Poisson/NegBin, non-negative yards as Gamma, rates as
Beta and usage shares as Dirichlet respects the support and mean–variance shape of each
quantity — far better calibrated than one Gaussian for everything.

    TD / INT        → Poisson                (rare integer events)
    receptions/tgts → NegativeBinomial2      (over-dispersed counts; mean-parameterised)
    yards           → Gamma                  (non-negative, right-skewed)
    catch% / comp%  → Beta                   (a rate in (0, 1))
    target/rush share → Dirichlet            (a simplex over a team's players)

`FAMILIES` is the single lookup every downstream unit (E6-features/ensemble) shares, so
nobody re-guesses "what distribution does this stat want". The families here are *pure*
NumPyro distribution factories — the hierarchical linear predictors that feed their
parameters live in `model.py`.

Fantasy points are a *linear* function of the raw stats (that is exactly what
`pipeline/models/scoring.py::score_stats` computes), so composition is one dot product;
`ScoringWeights.from_scoring` reads the very same league `scoring` JSONB the cron uses,
keeping the engine and the free pipeline scoring-identical.

`ponytail:` no per-family classes — NumPyro already provides the distributions; a dict of
thin factories is the whole abstraction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpyro.distributions as dist

if TYPE_CHECKING:
    from collections.abc import Callable

    import jax

    Array = jax.Array

__all__ = [
    "FAMILIES",
    "ScoringWeights",
    "beta_family",
    "dirichlet_family",
    "gamma_family",
    "negbin_family",
    "poisson_family",
]


# -- family factories (mean-parameterised where NumPyro allows it) --------------
def poisson_family(rate: Array) -> dist.Distribution:
    """Count of rare events (TD, INT). `rate` = expected count (already ≥ 0)."""
    return dist.Poisson(rate)


def negbin_family(mean: Array, concentration: Array) -> dist.Distribution:
    """Over-dispersed count (receptions, targets). Mean-parameterised NegBin;
    `concentration` → ∞ recovers Poisson, small values inflate the variance."""
    return dist.NegativeBinomial2(mean, concentration)


def gamma_family(mean: Array, concentration: Array) -> dist.Distribution:
    """Non-negative right-skewed magnitude (yards). Parameterised by its `mean` so the
    linear predictor targets the mean directly (rate = concentration / mean)."""
    return dist.Gamma(concentration=concentration, rate=concentration / mean)


def beta_family(mean: Array, concentration: Array) -> dist.Distribution:
    """A rate in (0, 1) (catch%, completion%). Mean/concentration parameterisation:
    a = mean·conc, b = (1-mean)·conc."""
    return dist.Beta(mean * concentration, (1.0 - mean) * concentration)


def dirichlet_family(concentration: Array) -> dist.Distribution:
    """Usage share over a team's players (target/rush share). `concentration` is the
    per-player Dirichlet α; its normalisation is the expected share. Zeroing a player's
    α (injury) auto-redistributes mass to the rest — the accessor E2 rebuilds from."""
    return dist.Dirichlet(concentration)


#: Prescriptive family per stat name — the shared contract (E6 extends, never re-guesses).
FAMILIES: dict[str, Callable[..., dist.Distribution]] = {
    "td": poisson_family,
    "interception": poisson_family,
    "receptions": negbin_family,
    "targets": negbin_family,
    "carries": negbin_family,
    "opportunities": negbin_family,
    "yards": gamma_family,
    "catch_rate": beta_family,
    "completion_pct": beta_family,
    "share": dirichlet_family,
}


# -- fantasy-points composition (linear; mirrors pipeline scoring.score_stats) --
@dataclass(frozen=True)
class ScoringWeights:
    """Linear fantasy weights pulled from a league `scoring` JSONB.

    Fantasy points are linear in the raw stats, so posterior-predictive points are a
    single weighted sum of sampled stat draws — no per-draw Python loop. The keys mirror
    `pipeline/models/scoring.py` so the engine and the free cron never diverge on scoring.
    """

    pass_yd: float = 0.04
    pass_td: float = 4.0
    interception: float = -2.0
    rush_yd: float = 0.1
    rush_td: float = 6.0
    rec: float = 0.5
    rec_yd: float = 0.1
    rec_td: float = 6.0
    fumble_lost: float = -2.0

    @classmethod
    def from_scoring(cls, scoring: dict) -> ScoringWeights:
        """Build from the same JSONB structure `score_stats` consumes (missing → default)."""
        p = scoring.get("passing", {})
        r = scoring.get("rushing", {})
        rec = scoring.get("receiving", {})
        misc = scoring.get("misc", {})
        return cls(
            pass_yd=p.get("pt_per_yd", 0.04),
            pass_td=p.get("td", 4.0),
            interception=p.get("int", -2.0),
            rush_yd=r.get("pt_per_yd", 0.1),
            rush_td=r.get("td", 6.0),
            rec=rec.get("ppr", 0.5),
            rec_yd=rec.get("pt_per_yd", 0.1),
            rec_td=rec.get("td", 6.0),
            fumble_lost=misc.get("fumble_lost", -2.0),
        )

    def points(
        self,
        *,
        yards: Array | float = 0.0,
        tds: Array | float = 0.0,
        receptions: Array | float = 0.0,
        pass_yards: Array | float = 0.0,
        pass_tds: Array | float = 0.0,
        interceptions: Array | float = 0.0,
        fumbles_lost: Array | float = 0.0,
    ) -> Array:
        """Vectorised fantasy points for skill stats (yards/tds/rec = the modelled core).

        `yards`/`tds` are treated as receiving-or-rushing skill yards/TDs (the two-stage
        core models a player's own yardage+scores); passing terms are optional for QBs.
        Broadcasts over any draw/player-week array shape.
        """
        pts = (
            yards * self.rec_yd
            + tds * self.rec_td
            + receptions * self.rec
            + pass_yards * self.pass_yd
            + pass_tds * self.pass_td
            + interceptions * self.interception
            + fumbles_lost * self.fumble_lost
        )
        return pts  # type: ignore[return-value]
