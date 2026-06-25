"""
Reliability / calibration of projection distributions (v2.2.3.2 / SCORING.md
"Validation"). A distribution is well-calibrated if realized outcomes land inside
its predicted percentiles at the right rate — the check that the Monte Carlo
boom/bust ranges (and especially the volatile K/DEF ones) are honest, not just wide.

Method: the Probability Integral Transform. For a Normal forecast N(μ,σ), the PIT of
a realized value r is Φ((r−μ)/σ). A perfectly-calibrated forecaster yields PIT values
that are Uniform(0,1); systematic over/under-confidence shows up as PIT mass piling
toward the middle / the extremes. Calibration error is the Kolmogorov–Smirnov distance
between the empirical PIT distribution and the uniform — 0 is perfect.

Pure Python (math only) so the check stays numpy-optional like the rest of the layer.
"""
from __future__ import annotations

import math

_SQRT2 = math.sqrt(2.0)


def _norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / _SQRT2))


def pit_values(means, stdevs, realized) -> list[float]:
    """Probability Integral Transform of each realized outcome under its Normal
    forecast: Φ((r−μ)/σ). Degenerate σ≤0 maps to 0.5 (no information)."""
    out: list[float] = []
    for mu, sd, r in zip(means, stdevs, realized):
        out.append(0.5 if sd is None or sd <= 0 else _norm_cdf((r - mu) / sd))
    return out


def calibration_error(pit: list[float]) -> float:
    """Kolmogorov–Smirnov distance of the PIT sample from Uniform(0,1): the largest
    gap between the empirical CDF and the diagonal. 0 = perfectly calibrated."""
    n = len(pit)
    if n == 0:
        return 0.0
    ordered = sorted(pit)
    worst = 0.0
    for i, p in enumerate(ordered):
        worst = max(worst, abs((i + 1) / n - p), abs(p - i / n))
    return worst


def reliability_table(pit: list[float], bins: int = 10) -> list[tuple[float, float, float]]:
    """Partition [0,1] into `bins` equal slices and report the fraction of PIT values
    in each → the reliability diagram. Every fraction ≈ 1/bins means well-calibrated.
    Returns (lo, hi, observed_fraction) per bin; fractions sum to 1."""
    n = len(pit)
    counts = [0] * bins
    for p in pit:
        idx = min(int(p * bins), bins - 1)  # p==1.0 lands in the last bin
        counts[idx] += 1
    return [(i / bins, (i + 1) / bins, (counts[i] / n if n else 0.0)) for i in range(bins)]
