"""Post-hoc recalibration — bend a miscalibrated forecast until "stated 70% = observed 70%".

The reliability curve (`metrics.reliability_curve`) exposes the calibration map
`C(u) = P(PIT ≤ u)` — the coverage actually observed when the model *claims* coverage `u`.
A calibrated model has `C = identity`; a real one bows off it. Recalibration learns `C`
from a holdout and composes it onto the forecast so the corrected PIT is uniform
(Kuleshov et al. 2018, "Accurate Uncertainties for Deep Learning Using Calibrated
Regression"):

  * transform an old PIT: `pit' = C(pit)`  — which is ~Uniform by construction, so the
    reliability curve straightens (the "recal improves reliability" DoD check);
  * emit a calibrated `τ`-coverage quantile: raw prob `u = C⁻¹(τ)`, value `Φ⁻¹(u; μ,σ)` —
    which is how `recalibrate_quantiles` rewrites the publishable `p1…p99` columns.

Two learners, one interface (`_forward = C`, `_inverse = C⁻¹`):
  * **isotonic** — non-parametric PAVA fit (`scipy.optimize.isotonic_regression`); makes no
    shape assumption, best when enough holdout rows are available.
  * **beta** — a 2-parameter Beta-CDF map; smooth and stable on small holdouts, the safer
    default for a single week of games.

`ponytail:` scipy supplies both the PAVA solver and the Beta CDF/PPF — no hand-rolled
calibrator, no sklearn dependency (not in the engine venv).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt
from scipy import stats
from scipy.optimize import isotonic_regression

from blitz_engine.calibration.metrics import pit_values

if TYPE_CHECKING:
    import pandas as pd

__all__ = [
    "QUANTILE_LEVELS",
    "BetaRecalibrator",
    "IsotonicRecalibrator",
    "Recalibrator",
    "fit_recalibrator",
]

FloatArray = npt.NDArray[np.float64]

# Publishable quantile columns → the nominal lower-tail coverage each claims (mirrors
# HierarchicalProjector.predict: tails=(.01,.99), floor_ceiling=(.10,.90)).
QUANTILE_LEVELS: dict[str, float] = {
    "p1": 0.01, "floor": 0.10, "p50": 0.50, "ceiling": 0.90, "p99": 0.99,
}


class Recalibrator:
    """Base for a monotone calibration map `C:[0,1]→[0,1]` fitted from a holdout's PIT.

    Subclasses implement `_fit(pit)` and the paired monotone `_forward`/`_inverse`. The
    shared surface is what callers use: `transform_pit` (straighten an old PIT) and
    `recalibrate_quantiles` (rewrite the publish columns), with a `strength` knob the weekly
    hook dials down for a gentle nudge.
    """

    def __init__(self) -> None:
        self._fitted = False

    # -- to be provided by subclasses -------------------------------------------------
    def _fit(self, pit: FloatArray) -> None:
        raise NotImplementedError

    def _forward(self, u: FloatArray) -> FloatArray:
        raise NotImplementedError

    def _inverse(self, c: FloatArray) -> FloatArray:
        raise NotImplementedError

    # -- shared surface ---------------------------------------------------------------
    def fit(
        self, mean: npt.ArrayLike, stdev: npt.ArrayLike, realized: npt.ArrayLike
    ) -> Recalibrator:
        """Learn the calibration map from a holdout of (forecast mean/stdev, realized)."""
        self._fit(pit_values(mean, stdev, realized))
        self._fitted = True
        return self

    def _check(self) -> None:
        if not self._fitted:
            raise RuntimeError("call fit() before using the recalibrator")

    def transform_pit(self, pit: npt.ArrayLike, strength: float = 1.0) -> FloatArray:
        """Map raw PIT values through `C` (→ ~uniform). `strength<1` blends toward identity."""
        self._check()
        u = np.clip(np.asarray(pit, dtype=np.float64), 0.0, 1.0)
        return _blend(u, self._forward(u), strength)

    def recalibrate_quantiles(
        self,
        quantiles: pd.DataFrame,
        *,
        levels: dict[str, float] | None = None,
        strength: float = 1.0,
    ) -> pd.DataFrame:
        """Rewrite the `p1…p99` columns as calibrated quantiles of Gaussian(mean, stdev).

        For each level `τ`, the calibrated value is `Φ⁻¹(C⁻¹(τ); μ,σ)`. `strength` in [0,1]
        blends the raw prob toward the nominal `τ` — the weekly hook's gentleness dial.
        """
        self._check()
        levels = levels or QUANTILE_LEVELS
        df = quantiles.copy()
        mu = df["mean"].to_numpy(dtype=np.float64)
        sd = np.clip(df["stdev"].to_numpy(dtype=np.float64), 1e-9, None)
        for col, tau in levels.items():
            if col not in df.columns:
                continue
            u = _blend(np.full(mu.shape, tau), self._inverse(np.full(mu.shape, tau)), strength)
            df[col] = stats.norm.ppf(np.clip(u, 1e-6, 1 - 1e-6), loc=mu, scale=sd)
        return df


def _blend(identity: FloatArray, mapped: FloatArray, strength: float) -> FloatArray:
    s = float(np.clip(strength, 0.0, 1.0))
    return (1.0 - s) * identity + s * mapped


class IsotonicRecalibrator(Recalibrator):
    """Non-parametric calibration map: a monotone PAVA fit of the empirical CDF of the PIT."""

    def _fit(self, pit: FloatArray) -> None:
        p = np.sort(pit)
        n = p.size
        if n == 0:
            self._x = np.array([0.0, 1.0])
            self._c = np.array([0.0, 1.0])
            return
        # C(p_(i)) ≈ empirical CDF; PAVA keeps it monotone against sampling noise.
        ecdf = (np.arange(1, n + 1)) / n
        y = np.asarray(isotonic_regression(ecdf).x, dtype=np.float64)
        # pin the endpoints so the map spans the full unit square
        self._x = np.concatenate(([0.0], p, [1.0]))
        self._c = np.clip(np.concatenate(([0.0], y, [1.0])), 0.0, 1.0)

    def _forward(self, u: FloatArray) -> FloatArray:
        return np.interp(u, self._x, self._c)

    def _inverse(self, c: FloatArray) -> FloatArray:
        # invert a monotone step map: interp with strictly-increasing knots on the c-axis
        x, cc = _strictly_increasing(self._c, self._x)
        return np.interp(c, x, cc)


class BetaRecalibrator(Recalibrator):
    """Smooth 2-parameter calibration map `C(u) = Beta(a,b).cdf(u)` — stable on small holdouts."""

    def _fit(self, pit: FloatArray) -> None:
        p = np.clip(pit, 1e-6, 1 - 1e-6)
        if p.size < 2:
            self._a, self._b = 1.0, 1.0  # identity
            return
        a, b, _, _ = stats.beta.fit(p, floc=0.0, fscale=1.0)
        self._a, self._b = float(a), float(b)

    def _forward(self, u: FloatArray) -> FloatArray:
        return np.asarray(stats.beta.cdf(u, self._a, self._b), dtype=np.float64)

    def _inverse(self, c: FloatArray) -> FloatArray:
        return np.asarray(stats.beta.ppf(c, self._a, self._b), dtype=np.float64)


def _strictly_increasing(x: FloatArray, y: FloatArray) -> tuple[FloatArray, FloatArray]:
    """Nudge a monotone-non-decreasing `x` to strictly increasing so `np.interp` can invert it."""
    xs = np.maximum.accumulate(x + np.arange(x.size) * 1e-12)
    return xs, y


def fit_recalibrator(
    mean: npt.ArrayLike,
    stdev: npt.ArrayLike,
    realized: npt.ArrayLike,
    *,
    method: str = "isotonic",
) -> Recalibrator:
    """Fit and return a recalibrator by name — `"isotonic"` (default) or `"beta"`."""
    cls = {"isotonic": IsotonicRecalibrator, "beta": BetaRecalibrator}.get(method)
    if cls is None:
        raise ValueError(f"unknown recal method {method!r} (expected 'isotonic' or 'beta')")
    return cls().fit(mean, stdev, realized)
