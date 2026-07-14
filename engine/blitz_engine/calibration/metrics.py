"""Calibration / discrimination / sharpness + proper scoring — tracked SEPARATELY.

A predictive distribution can be wrong in three orthogonal ways, and the brief
(§"Track calibration / discrimination / sharpness separately") insists we never collapse
them into one number:

  * **Calibration** — are the stated probabilities honest? A claimed 70% interval should
    contain the truth 70% of the time. Measured on the *Probability Integral Transform*:
    for forecast F the PIT of a realized `y` is `F(y)`, which is Uniform(0,1) iff the
    forecaster is calibrated. `calibration_error` is the Kolmogorov–Smirnov distance of the
    PIT sample from that uniform (0 = perfect). This is the only axis the publish gate
    blocks on — a sharp, discriminating, *overconfident* model is dangerous.
  * **Discrimination** — does the forecaster rank players correctly regardless of
    calibration? Spearman rank-correlation between predicted mean and realized outcome.
  * **Sharpness** — how concentrated are the predictions (mean predictive stdev)? Sharper
    is better *subject to* calibration; sharpness alone rewards reckless overconfidence.

Proper scoring rules reward calibration AND sharpness jointly and cannot be gamed:
  * **CRPS** — closed-form for a Gaussian forecast; the "MAE of distributions".
  * **log-loss** (negative log predictive density) — savagely penalises overconfidence
    (a tiny σ that misses blows up), which is exactly the failure mode we fear.

Everything is vectorised numpy over the `Projection.quantiles` columns (`mean`, `stdev`).
The forecast is summarised as Gaussian(mean, stdev) — the honest summary of a posterior
predictive whose full quantiles E1 already exposes; recalibration (see `recal.py`) fixes
the residual non-Gaussianity that the reliability curve reveals.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from scipy import stats

__all__ = [
    "ReliabilityCurve",
    "calibration_error",
    "crps_gaussian",
    "discrimination",
    "log_loss_gaussian",
    "pit_values",
    "reliability_curve",
    "sharpness",
    "spearman",
    "top_n_hit_rate",
]

FloatArray = npt.NDArray[np.float64]
_INV_SQRT_PI = 1.0 / math.sqrt(math.pi)


def _f(a: npt.ArrayLike) -> FloatArray:
    return np.asarray(a, dtype=np.float64)


def pit_values(mean: npt.ArrayLike, stdev: npt.ArrayLike, realized: npt.ArrayLike) -> FloatArray:
    """Probability Integral Transform under a Gaussian forecast: `Φ((y−μ)/σ)`.

    Uniform(0,1) iff calibrated. Degenerate `σ≤0` carries no information → 0.5.
    """
    mu, sd, y = _f(mean), _f(stdev), _f(realized)
    out = np.full(mu.shape, 0.5)
    ok = sd > 0
    out[ok] = stats.norm.cdf((y[ok] - mu[ok]) / sd[ok])
    return out


def calibration_error(pit: npt.ArrayLike) -> float:
    """Kolmogorov–Smirnov distance of the PIT sample from Uniform(0,1) — 0 = perfect.

    The largest gap between the empirical CDF of the PIT values and the diagonal. This is
    the single scalar the publish gate blocks on.
    """
    p = np.sort(_f(pit))
    n = p.size
    if n == 0:
        return 0.0
    i = np.arange(1, n + 1)
    return float(np.maximum(i / n - p, p - (i - 1) / n).max())


@dataclass(frozen=True)
class ReliabilityCurve:
    """A reliability diagram: nominal cumulative coverage vs observed frequency.

    `expected[k]` is a claimed lower-tail probability; `observed[k]` is the fraction of PIT
    values ≤ it. A calibrated forecaster lies on the diagonal (`observed == expected`); mass
    bowing above ⇒ under-confident, below ⇒ over-confident. This is the curve `recal.py`
    straightens.
    """

    expected: FloatArray
    observed: FloatArray

    @property
    def max_gap(self) -> float:
        """Worst |observed − expected| — a bin-based cousin of `calibration_error`."""
        return float(np.abs(self.observed - self.expected).max()) if self.expected.size else 0.0


def reliability_curve(pit: npt.ArrayLike, n_bins: int = 10) -> ReliabilityCurve:
    """Empirical CDF of the PIT sampled on an even grid — the plottable reliability diagram."""
    p = _f(pit)
    expected = np.linspace(0.0, 1.0, n_bins + 1)
    observed = (
        np.array([float(np.mean(p <= e)) for e in expected]) if p.size else np.zeros_like(expected)
    )
    return ReliabilityCurve(expected=expected, observed=observed)


def sharpness(stdev: npt.ArrayLike) -> float:
    """Mean predictive standard deviation — lower is sharper (only virtuous if calibrated)."""
    sd = _f(stdev)
    return float(sd.mean()) if sd.size else 0.0


def discrimination(mean: npt.ArrayLike, realized: npt.ArrayLike) -> float:
    """Spearman rank-correlation of predicted mean vs realized — the ranking skill axis."""
    return spearman(mean, realized)


def spearman(pred: npt.ArrayLike, realized: npt.ArrayLike) -> float:
    """Spearman ρ (rank correlation); 0.0 when undefined (n<2 or a constant vector)."""
    a, b = _f(pred), _f(realized)
    if a.size < 2:
        return 0.0
    rho = stats.spearmanr(a, b).statistic
    return 0.0 if not np.isfinite(rho) else float(rho)


def top_n_hit_rate(pred: npt.ArrayLike, realized: npt.ArrayLike, n: int) -> float:
    """Fraction of the truly top-`n` outcomes captured by the predicted top-`n` (ranking)."""
    a, b = _f(pred), _f(realized)
    n = min(n, a.size)
    if n <= 0:
        return 0.0
    pred_top = set(np.argsort(a)[-n:].tolist())
    real_top = set(np.argsort(b)[-n:].tolist())
    return len(pred_top & real_top) / n


def crps_gaussian(mean: npt.ArrayLike, stdev: npt.ArrayLike, realized: npt.ArrayLike) -> FloatArray:
    """Closed-form CRPS of a Gaussian forecast per row (the "MAE of distributions").

    `CRPS(N(μ,σ), y) = σ · [ ω(2Φ(ω)−1) + 2φ(ω) − 1/√π ]` with `ω=(y−μ)/σ`. Proper: it is
    minimised only by the true distribution, rewarding calibration and sharpness together.
    Degenerate `σ≤0` collapses to the absolute error `|y−μ|`.
    """
    mu, sd, y = _f(mean), _f(stdev), _f(realized)
    out = np.abs(y - mu)
    ok = sd > 0
    w = (y[ok] - mu[ok]) / sd[ok]
    out[ok] = sd[ok] * (w * (2 * stats.norm.cdf(w) - 1) + 2 * stats.norm.pdf(w) - _INV_SQRT_PI)
    return out


def log_loss_gaussian(mean: npt.ArrayLike, stdev: npt.ArrayLike, realized: npt.ArrayLike) -> float:
    """Mean negative log predictive density under Gaussian(μ,σ) — punishes overconfidence.

    `−log φ((y−μ)/σ)/σ = ½log(2πσ²) + (y−μ)²/(2σ²)`. A confident-but-wrong forecast (small
    σ, large residual) explodes the second term — the whole point of tracking it.
    """
    mu, sd, y = _f(mean), _f(stdev), _f(realized)
    sd = np.clip(sd, 1e-9, None)
    nll = 0.5 * np.log(2 * np.pi * sd**2) + (y - mu) ** 2 / (2 * sd**2)
    return float(nll.mean()) if nll.size else 0.0
