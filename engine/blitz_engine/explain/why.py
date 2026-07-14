"""Per-projection "why" — exact Shapley attribution + posterior-contribution readout.

E1-core emits a *distribution* per player-week and reads the two generative stages back
apart: `Projection.opportunity` (volume) and `Projection.efficiency`
(yards-per-touch + TD rate). This module turns those numbers into an **additive, plain-
language "why"**: how much of a player's projected points comes from usage vs efficiency
vs scoring, measured against a neutral replacement baseline.

The attribution is a game-theoretic **Shapley value** over three features
(``volume``, ``efficiency``, ``scoring``). With only three features every coalition is
enumerated exactly, so the values satisfy the *efficiency axiom* on the nose — the three
contributions sum to ``value(player) − value(baseline)`` — and are fully **deterministic**
(no sampling, no seed). Exact enumeration IS the SHAP value; the `shap` library is one
approximate implementation of the same quantity, unnecessary for three features (and kept
out of the critical path — see `ponytail:` below).

`ponytail:` the whole explainer is one pure value function + one exact-Shapley loop over
`itertools.combinations` — no `shap`/`numba` dependency, no surrogate model, and the
attribution is exact rather than sampled. The value function reuses the *same*
`ScoringWeights.points` the projector publishes with, so the "why" can never drift from the
number it explains.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from math import factorial
from typing import TYPE_CHECKING

import pandas as pd

from blitz_engine.projection.families import ScoringWeights

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from blitz_engine.projection.inference import Projection

__all__ = [
    "FEATURES",
    "ProjectionWhy",
    "WhyFeature",
    "explain",
    "shapley_contributions",
    "why_frame",
]

#: The three decomposable drivers of a skill projection (machine key → plain label).
#: `volume` = expected touches (`mu_opportunity`), `efficiency` = yards per touch,
#: `scoring` = per-touch TD rate. Every projected point traces to some mix of these.
FEATURES: tuple[tuple[str, str], ...] = (
    ("volume", "usage / volume"),
    ("efficiency", "yards per touch"),
    ("scoring", "touchdown rate"),
)
_KEYS = [k for k, _ in FEATURES]
_LABELS = dict(FEATURES)


@dataclass(frozen=True)
class WhyFeature:
    """One driver's contribution to a projection, in fantasy points.

    `value`/`baseline` are the player's and the replacement's raw feature levels;
    `contribution` is this feature's exact Shapley share of `projected − baseline` points
    (positive = lifts the projection above replacement, negative = drags it down).
    """

    name: str
    label: str
    value: float
    baseline: float
    contribution: float


@dataclass(frozen=True)
class ProjectionWhy:
    """The full "why" for one player-week: headline number + additive driver breakdown.

    `features` is sorted by absolute contribution (biggest driver first), so
    `features[0]` is always the dominant reason. `reconstructed` = `baseline` +
    Σ`contribution` (the deterministic-mean the decomposition is exact for); `projected`
    is the published posterior-predictive mean it explains (the two agree up to the
    posterior Jensen gap).
    """

    player_id: str
    week: int
    projected: float
    baseline: float
    features: tuple[WhyFeature, ...]

    @property
    def reconstructed(self) -> float:
        return self.baseline + sum(f.contribution for f in self.features)

    def top(self, n: int = 2) -> tuple[WhyFeature, ...]:
        """The `n` biggest drivers (by absolute contribution)."""
        return self.features[:n]


# ── the value function + exact Shapley ────────────────────────────────────────
def _points(feat: Mapping[str, float], w: ScoringWeights) -> float:
    """Deterministic mean fantasy points from a feature bundle (reuses publish scoring).

    Mean points = points(yards = volume·efficiency, tds = volume·scoring) — the same
    linear composition the projector applies to its posterior draws.
    """
    vol = feat["volume"]
    return float(w.points(yards=vol * feat["efficiency"], tds=vol * feat["scoring"]))


def shapley_contributions(
    player: Mapping[str, float], baseline: Mapping[str, float], w: ScoringWeights
) -> dict[str, float]:
    """Exact Shapley value of each feature for `_points`, vs the `baseline` bundle.

    Enumerates all coalitions (2³) so the result is exact and deterministic and satisfies
    Σ contributions == `_points(player) − _points(baseline)`.
    """
    n = len(_KEYS)
    out = {k: 0.0 for k in _KEYS}
    for k in _KEYS:
        others = [j for j in _KEYS if j != k]
        for r in range(len(others) + 1):
            for combo in itertools.combinations(others, r):
                weight = factorial(len(combo)) * factorial(n - len(combo) - 1) / factorial(n)
                without = {j: (player[j] if j in combo else baseline[j]) for j in _KEYS}
                with_k = {**without, k: player[k]}
                out[k] += weight * (_points(with_k, w) - _points(without, w))
    return out


# ── projection → why ──────────────────────────────────────────────────────────
def _feature_frame(projection: Projection) -> pd.DataFrame:
    """Join the opportunity + efficiency layers into one feature row per player-week."""
    opp = projection.opportunity.rename(columns={"mu_opportunity": "volume"})
    eff = projection.efficiency.rename(
        columns={"yards_per_opp": "efficiency", "td_rate": "scoring"}
    )
    feat = opp.merge(eff, on=["player_id", "week"], how="inner")
    mean = projection.quantiles[["player_id", "week", "mean"]]
    return feat.merge(mean, on=["player_id", "week"], how="left")


def explain(
    projection: Projection,
    *,
    weights: ScoringWeights | None = None,
    baseline: Mapping[str, float] | None = None,
) -> list[ProjectionWhy]:
    """Decompose every projected player-week into its driver contributions.

    `baseline` is the replacement-level feature bundle to attribute against; default is the
    slate-wide mean of each feature (a "league-average touch"). Returns one `ProjectionWhy`
    per row, each with an exact, deterministic Shapley breakdown. Empty projection → `[]`.
    """
    w = weights or ScoringWeights()
    feat = _feature_frame(projection)
    if feat.empty:
        return []
    base = (
        dict(baseline)
        if baseline is not None
        else {k: float(feat[k].mean()) for k in _KEYS}
    )
    base_pts = _points(base, w)

    out: list[ProjectionWhy] = []
    for row in feat.itertuples(index=False):
        vals = {k: float(getattr(row, k)) for k in _KEYS}
        contrib = shapley_contributions(vals, base, w)
        features = tuple(
            sorted(
                (
                    WhyFeature(k, _LABELS[k], vals[k], base[k], contrib[k])
                    for k in _KEYS
                ),
                key=lambda f: abs(f.contribution),
                reverse=True,
            )
        )
        mean = getattr(row, "mean", None)
        projected = float(mean) if mean is not None and pd.notna(mean) else _points(vals, w)
        out.append(
            ProjectionWhy(
                player_id=str(row.player_id),
                week=int(row.week),
                projected=projected,
                baseline=base_pts,
                features=features,
            )
        )
    return out


def why_frame(whys: Sequence[ProjectionWhy]) -> pd.DataFrame:
    """Flatten explanations to a snapshot-friendly table (one column per driver).

    Columns: player_id, week, projected, baseline, why_<feature> (points), plus the raw
    feature level why_<feature>_value. Stable column order regardless of driver ranking.
    """
    rows = []
    for wy in whys:
        by_name = {f.name: f for f in wy.features}
        row: dict[str, object] = {
            "player_id": wy.player_id,
            "week": wy.week,
            "projected": wy.projected,
            "baseline": wy.baseline,
        }
        for k in _KEYS:
            f = by_name[k]
            row[f"why_{k}"] = f.contribution
            row[f"why_{k}_value"] = f.value
        rows.append(row)
    return pd.DataFrame(rows)
