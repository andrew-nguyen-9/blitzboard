"""Frozen statistics for the C05 promotion protocol.

The CI construction is the one preregistered in promotion-v3.json `ci_method`: per-season draws
within a seat are averaged first (seats are the independent unit — pseudo-replicating the season
draws would shrink the interval dishonestly), then a deterministic seeded percentile bootstrap over
seats gives the CI95. Everything here is a pure function of its inputs — two runs on the same data
are byte-identical.
"""
from __future__ import annotations

import zlib

import numpy as np

__all__ = ["boot_seed", "paired_ci95", "seat_deltas", "slice_no_regression"]


def seat_deltas(candidate_per_season: np.ndarray, control_per_season: np.ndarray) -> np.ndarray:
    """Per-seat mean paired delta from two `(n_seasons, teams)` matched matrices (cand − ctrl)."""
    a = np.asarray(candidate_per_season, dtype=float)
    b = np.asarray(control_per_season, dtype=float)
    if a.shape != b.shape or a.ndim != 2:
        raise ValueError(f"paired matrices misaligned: {a.shape} vs {b.shape}")
    return (a - b).mean(axis=0)


def boot_seed(base_seeds: list[int] | tuple[int, ...], slice_key: str) -> int:
    """The preregistered bootstrap seed: `(sum(base_seeds) + crc32(slice_key)) % 2**32`."""
    return int((sum(int(s) for s in base_seeds) + zlib.crc32(slice_key.encode())) % 2**32)


def paired_ci95(
    deltas: np.ndarray, *, n_boot: int = 10_000, seed: int = 0
) -> tuple[float, float, float]:
    """`(mean, lo, hi)`: seat-resampled percentile bootstrap CI95 of the mean paired delta.

    Deterministic in `seed`. One seat degenerates to a point interval; an empty sample is the
    caller's problem (zero evidence is an explicit gate outcome, not a statistic).
    """
    d = np.asarray(deltas, dtype=float)
    if d.size == 0:
        raise ValueError("empty delta sample — zero evidence is a gate outcome, not a CI")
    mean = float(d.mean())
    if d.size == 1:
        return mean, mean, mean
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, d.size, size=(n_boot, d.size))
    boots = d[idx].mean(axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return mean, float(lo), float(hi)


def slice_no_regression(deltas: np.ndarray, *, tolerance: float = 0.0) -> bool:
    """The zero-tolerance slice gate: mean paired delta must be >= −tolerance.

    Same semantics as `backtest.ablation.RegressionResult.passed` transposed from errors (lower
    better) to points (higher better): with tolerance 0.0 the candidate may not average below the
    control on the slice at all.
    """
    d = np.asarray(deltas, dtype=float)
    if d.size == 0:
        return False  # absent evidence never passes a mandatory slice
    return bool(d.mean() >= -float(tolerance))
