"""The stacked ensemble — a BMA-weighted convex blend of member forecasts.

Stacking here is a *convex combination* of the members' predictive distributions, with the
combination weights learned from out-of-sample skill (`bma.bma_weights`) rather than a
meta-learner (`ponytail:` — the brief's "weighted average by OOS skill, no meta-learner zoo").
The blend is a Gaussian mixture, so the ensemble carries an honest predictive stdev too:

    mean = Σ wₖ μₖ
    var  = Σ wₖ (σₖ² + μₖ²) − mean²        (law of total variance over the mixture)

which feeds `calibration.calibrated()` via `quantiles()`. The ensemble is itself an E7
`Predictor` (`as_predictor()`), so `walk_forward` / `no_regression` / `ablation` score the
whole stack exactly as they score a single model — the DoD proves the blend beats every member
on the same folds.

Weights are recomputed per fold from that fold's *train* frame only (leakage-safe) and cached
by frame identity so `weights(train)` + `predict(train, test)` cost one BMA pass.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from scipy import stats

from blitz_engine.calibration import QUANTILE_LEVELS
from blitz_engine.ensemble.bma import bma_weights
from blitz_engine.ensemble.members import EnsembleMember, MemberPrediction

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from blitz_engine.ensemble.members import FloatArray

__all__ = ["StackedEnsemble", "ensemble_predictor", "quantiles_frame"]


def quantiles_frame(pred: MemberPrediction) -> pd.DataFrame:
    """A `Projection.quantiles`-shaped frame (mean/stdev/p1…p99) for `calibration.calibrated()`."""
    mu = np.asarray(pred.mean, dtype=np.float64)
    sd = np.clip(np.asarray(pred.stdev, dtype=np.float64), 1e-9, None)
    data: dict[str, FloatArray] = {"mean": mu, "stdev": sd}
    for col, tau in QUANTILE_LEVELS.items():
        data[col] = stats.norm.ppf(tau, loc=mu, scale=sd)
    return pd.DataFrame(data)


@dataclass
class StackedEnsemble:
    """A BMA-weighted blend of `members` — the release candidate the DoD scores.

    `fixed_weights` pins the blend (skip the OOS pass); otherwise weights are learned per train
    frame via `bma_weights`. `temperature` tempers the BMA softmax (see `bma`).
    """

    members: Sequence[EnsembleMember]
    scoring: dict | None = None
    temperature: float = 1.0
    time_col: str = "season"
    min_train_periods: int = 1
    fixed_weights: dict[str, float] | None = None
    _cache: dict[int, dict[str, float]] = field(default_factory=dict, init=False, repr=False)

    def weights(self, train: pd.DataFrame) -> dict[str, float]:
        """BMA weights for this train frame (Σ=1), cached by frame identity."""
        if self.fixed_weights is not None:
            return dict(self.fixed_weights)
        key = id(train)
        if key not in self._cache:
            self._cache[key] = bma_weights(
                list(self.members),
                train,
                scoring=self.scoring,
                time_col=self.time_col,
                min_train_periods=self.min_train_periods,
                temperature=self.temperature,
            )
        return self._cache[key]

    def predict(self, train: pd.DataFrame, test: pd.DataFrame) -> MemberPrediction:
        """The mixture forecast: weighted mean + total-variance stdev over the members."""
        w = self.weights(train)
        preds = {m.name: m.predict(train, test) for m in self.members}
        n = len(test)
        mu = np.zeros(n)
        second = np.zeros(n)  # E[X²] of the mixture = Σ wₖ (σₖ² + μₖ²)
        for name, weight in w.items():
            p = preds[name]
            mu = mu + weight * p.mean
            second = second + weight * (p.stdev**2 + p.mean**2)
        var = np.clip(second - mu**2, 1e-9, None)
        return MemberPrediction(mean=np.asarray(mu, dtype=np.float64), stdev=np.sqrt(var))

    def as_predictor(self) -> Callable[[pd.DataFrame, pd.DataFrame], FloatArray]:
        """The mean-only E7 `Predictor` view of the whole stack."""
        def predict(train: pd.DataFrame, test: pd.DataFrame) -> FloatArray:
            return self.predict(train, test).mean

        return predict

    def quantiles(self, train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
        """Ensemble forecast as a `calibrated()`-ready quantiles frame."""
        return quantiles_frame(self.predict(train, test))


def ensemble_predictor(
    members: Sequence[EnsembleMember],
    *,
    scoring: dict | None = None,
    temperature: float = 1.0,
    time_col: str = "season",
    min_train_periods: int = 1,
    fixed_weights: dict[str, float] | None = None,
) -> Callable[[pd.DataFrame, pd.DataFrame], FloatArray]:
    """Convenience: a mean-only E7 `Predictor` for a BMA-weighted stack of `members`."""
    return StackedEnsemble(
        members=members,
        scoring=scoring,
        temperature=temperature,
        time_col=time_col,
        min_train_periods=min_train_periods,
        fixed_weights=fixed_weights,
    ).as_predictor()
