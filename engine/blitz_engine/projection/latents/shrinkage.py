"""Empirical-Bayes shrinkage + safety clip — the regularization every latent shares.

A latent team/matchup effect is a *group mean of residuals* over thin data, so the honest
estimate is the group mean pulled toward 0 by how little we've seen it. Under a Normal(0, τ)
hierarchical prior with per-observation noise σ², the posterior mean of a group with `n`
observations and sample mean `m` is exactly ``m · n / (n + k)`` with ``k = σ²/τ²`` — i.e.
Stein / partial-pooling shrinkage. That single closed form is the whole regularizer (no
optimizer, no sklearn): a large `k` = a *hard* prior (thin-data latents like chemistry), a
small `k` = a loose one.

`ponytail:` the shrinkage prior does the regularization; there is no framework here beyond
the closed-form posterior mean + one final hard clip that guarantees a latent can never blow
a projection up (mirrors the factor-seam `FACTOR_BOUNDS` guarantee on the efficiency side).
"""
from __future__ import annotations

from collections.abc import Hashable, Sequence

import numpy as np

__all__ = [
    "clip_latent",
    "grouped_shrunk_effect",
    "opponent_adjust",
]


def clip_latent(x: float, bound: float) -> float:
    """Hard clamp a single log-scale latent to ``[-bound, +bound]`` (the safety guard)."""
    return float(np.clip(x, -bound, bound))


def grouped_shrunk_effect[K: Hashable](
    keys: Sequence[K],
    resid: np.ndarray,
    *,
    k: float,
    bound: float,
) -> dict[K, float]:
    """Empirical-Bayes shrunk, clipped mean residual per group key.

    For each distinct `key`, the mean of its residuals is shrunk toward 0 by ``n/(n+k)``
    (the Normal-Normal posterior mean) and clamped to ``±bound``. Groups seen rarely shrink
    hard toward the neutral 0; a large `k` makes the whole latent conservative. Returns only
    keys with data — a key absent from the map degrades to 0 (neutral) at lookup time.
    """
    resid = np.asarray(resid, dtype=np.float64).ravel()
    sums: dict[K, float] = {}
    counts: dict[K, int] = {}
    for key, r in zip(keys, resid, strict=True):
        if not np.isfinite(r):
            continue
        sums[key] = sums.get(key, 0.0) + float(r)
        counts[key] = counts.get(key, 0) + 1
    out: dict[K, float] = {}
    for key, s in sums.items():
        n = counts[key]
        mean = s / n
        out[key] = clip_latent(mean * n / (n + k), bound)
    return out


def opponent_adjust(
    values: np.ndarray,
    offense_keys: Sequence[Hashable],
    *,
    k: float,
) -> np.ndarray:
    """Remove the offense's own strength from `values`, returning opponent-facing residuals.

    A raw "yards allowed" number confounds *the defense faced* with *the offense that
    produced it*. One pass of shrunk offense de-meaning (subtract each row's offense effect,
    itself an empirical-Bayes group mean) leaves a residual attributable to the matchup — the
    minimal identifiable opponent adjustment (a one-iteration additive two-way decomposition,
    the same idea as Massey/SRS ratings without the linear solve).
    """
    values = np.asarray(values, dtype=np.float64).ravel()
    if values.size == 0:
        return values
    league = float(np.nanmean(values))
    off_effect = grouped_shrunk_effect(
        offense_keys, values - league, k=k, bound=np.inf
    )
    adj = np.array([off_effect.get(key, 0.0) for key in offense_keys], dtype=np.float64)
    return values - league - adj
