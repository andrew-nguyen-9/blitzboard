"""Proper-scoring + ranking metrics for the walk-forward backtest (spec E7 "Metrics").

Point error (MAE/RMSE) rewards a model for being close on average but says nothing about
whether its *uncertainty* is honest or whether it gets the *order* of players right — the two
things a fantasy war room actually acts on. This module adds:

* **Proper scoring** — `crps_gaussian` / `crps_ensemble` (continuous ranked probability score)
  and `log_loss` (binary). Proper scores are minimised only by the true distribution, so a
  sharp-but-wrong forecast is penalised harder than a calibrated wide one (overconfidence hurts).
* **Ranking** — `spearman` rank-correlation of predicted vs realised points and `top_n_hit_rate`
  (fraction of the true top-N players the model also ranks in its top-N).

All closed-form / sample-based over scipy+numpy — no new dependency (sklearn is absent).
"""
from __future__ import annotations

import numpy as np
from scipy.stats import norm, spearmanr

__all__ = [
    "crps_ensemble",
    "crps_gaussian",
    "log_loss",
    "spearman",
    "top_n_hit_rate",
]


def crps_gaussian(
    y: np.ndarray, mu: np.ndarray, sigma: np.ndarray
) -> float:
    """Mean CRPS of a Gaussian forecast `N(mu, sigma)` against observations `y` (lower better).

    Closed form (Gneiting & Raftery 2007): for standardised `z = (y-mu)/sigma`,
    `CRPS = sigma * [ z*(2Φ(z)-1) + 2φ(z) - 1/√π ]`. A too-narrow `sigma` on a wrong `mu`
    blows the `z*(2Φ(z)-1)` term up, so overconfidence is penalised — the proper-scoring point.
    """
    y = np.asarray(y, dtype=float)
    mu = np.asarray(mu, dtype=float)
    sigma = np.clip(np.asarray(sigma, dtype=float), 1e-9, None)
    z = (y - mu) / sigma
    crps = sigma * (z * (2.0 * norm.cdf(z) - 1.0) + 2.0 * norm.pdf(z) - 1.0 / np.sqrt(np.pi))
    return float(np.mean(crps))


def crps_ensemble(y: np.ndarray, samples: np.ndarray) -> float:
    """Mean sample-CRPS of an ensemble forecast against observations `y` (lower better).

    `samples` is `(n_obs, n_draws)` posterior/ensemble draws. Uses the energy form
    `E|X-y| - ½E|X-X'|`; the second term is the mean absolute pairwise gap, so a collapsed
    (overconfident) ensemble loses its spread credit and scores worse than an honest one.
    """
    y = np.asarray(y, dtype=float)
    s = np.atleast_2d(np.asarray(samples, dtype=float))
    if s.shape[0] != y.shape[0]:  # allow (n_draws,) for a single observation
        s = s.reshape(y.shape[0], -1)
    term1 = np.abs(s - y[:, None]).mean(axis=1)
    term2 = np.abs(s[:, :, None] - s[:, None, :]).mean(axis=(1, 2))
    return float(np.mean(term1 - 0.5 * term2))


def log_loss(y: np.ndarray, p: np.ndarray, *, eps: float = 1e-12) -> float:
    """Mean binary log-loss (cross-entropy) of probabilities `p` against labels `y` (lower better).

    `-mean[ y·ln p + (1-y)·ln(1-p) ]`, clipped to stay finite. A confident wrong probability
    (p→1 when y=0) drives the loss up without bound, so overconfidence is punished.
    """
    y = np.asarray(y, dtype=float)
    p = np.clip(np.asarray(p, dtype=float), eps, 1.0 - eps)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def spearman(pred: np.ndarray, actual: np.ndarray) -> float:
    """Spearman rank-correlation of predicted vs realised points (1 = perfect order).

    Returns `nan` when either side has no rank variation (fewer than 2 points, or all-tied) —
    correlation is undefined there rather than silently 0.
    """
    pred = np.asarray(pred, dtype=float)
    actual = np.asarray(actual, dtype=float)
    if pred.size < 2:
        return float("nan")
    rho = spearmanr(pred, actual).correlation
    return float(rho)


def top_n_hit_rate(pred: np.ndarray, actual: np.ndarray, n: int) -> float:
    """Fraction of the true top-`n` players (by realised points) that `pred` also ranks top-`n`.

    1.0 = the model's top-`n` set is exactly the realised top-`n` set; 0.0 = no overlap. `n`
    is capped at the number of observations. Returns `nan` for an empty frame or `n <= 0`.
    """
    pred = np.asarray(pred, dtype=float)
    actual = np.asarray(actual, dtype=float)
    k = min(n, pred.size)
    if k <= 0:
        return float("nan")
    true_top = set(np.argsort(actual)[-k:].tolist())
    pred_top = set(np.argsort(pred)[-k:].tolist())
    return len(true_top & pred_top) / k
