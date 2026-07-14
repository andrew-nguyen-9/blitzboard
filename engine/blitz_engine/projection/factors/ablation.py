"""Ablation-significance gate — the "drop it if it's noise" guard for weak factors.

The brief gates the Team-H2H factor on *ablation significance*: only let the signal move a
projection if it demonstrably explains the outcome better than chance; otherwise drop it to
neutral. Rather than pull in SciPy for a t-test, we run a dependency-free **permutation
test** on the signal↔outcome correlation — deterministic under a fixed seed, exact for the
small fixtures a weekly factor sees.

`ponytail:` a permutation test is ~10 lines of NumPy and needs no special functions; it is
also the honest null ("shuffle the labels") for a small, possibly-nonlinear signal.
"""
from __future__ import annotations

import numpy as np


def _abs_corr(x: np.ndarray, y: np.ndarray) -> float:
    sx, sy = x.std(), y.std()
    if sx == 0.0 or sy == 0.0:
        return 0.0
    return float(abs(np.corrcoef(x, y)[0, 1]))


def is_significant(
    signal: object,
    outcome: object,
    alpha: float = 0.05,
    *,
    n_perm: int = 2000,
    seed: int = 0,
) -> bool:
    """True iff ``signal`` correlates with ``outcome`` beyond chance at level ``alpha``.

    Permutation null: shuffle ``outcome`` ``n_perm`` times and count how often the shuffled
    ``|corr|`` meets or beats the observed one; that fraction is the p-value. Degrades to
    ``False`` (⇒ the gated factor drops to neutral) whenever the evidence is missing,
    mismatched, or too small to test — the conservative, degrade-neutral default.
    """
    if signal is None or outcome is None:
        return False
    x = np.asarray(signal, dtype=np.float64).ravel()
    y = np.asarray(outcome, dtype=np.float64).ravel()
    if x.shape != y.shape or x.size < 4:
        return False

    observed = _abs_corr(x, y)
    if observed == 0.0:
        return False
    rng = np.random.default_rng(seed)
    perm = y.copy()
    hits = 0
    for _ in range(n_perm):
        rng.shuffle(perm)
        if _abs_corr(x, perm) >= observed:
            hits += 1
    p_value = (hits + 1) / (n_perm + 1)  # +1 = the observed permutation (unbiased)
    return p_value <= alpha
