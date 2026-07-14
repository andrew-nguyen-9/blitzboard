"""Bayesian Model Averaging weights — blend members by out-of-sample predictive skill.

The stack's weights are learned, not guessed: each member is walk-forwarded over the training
history (leakage-safe, reusing the E7 folds), its pooled OOS forecast scored by the **log
predictive density** (the proper score `calibration.log_loss_gaussian` computes), and the
members softmax-weighted by that score. This is *pseudo-BMA* — the model-averaging weight of a
member is proportional to `exp(elpd_k)`, its expected log pointwise predictive density
(Yao et al. 2018), estimated here on held-out folds rather than by an intractable marginal
likelihood.

Two guarantees the DoD leans on:
  * weights are a softmax → **sum to 1** by construction (a convex combination);
  * a member that predicts badly OOS earns an exponentially small weight, so a weak learner
    can never drag the blend below the good members — the ensemble tracks its best members.

`temperature` tempers the softmax: →0 collapses to the single best member (winner-take-all
BMA), large values flatten toward a uniform average. Default 1.0 uses the per-observation mean
log-score, which blends diverse members instead of collapsing onto one.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from blitz_engine.backtest import points_of, walk_forward_splits
from blitz_engine.calibration import log_loss_gaussian
from blitz_engine.projection.families import ScoringWeights

if TYPE_CHECKING:
    import pandas as pd

    from blitz_engine.backtest.harness import Split
    from blitz_engine.ensemble.members import EnsembleMember

__all__ = ["bma_skill", "bma_weights", "softmax_weights"]


def softmax_weights(scores: dict[str, float], *, temperature: float = 1.0) -> dict[str, float]:
    """Softmax a score map into weights that sum to 1 (non-finite scores → weight 0)."""
    names = list(scores)
    if not names:
        return {}
    vals = np.array([scores[n] for n in names], dtype=np.float64)
    finite = np.isfinite(vals)
    if not finite.any():
        return {n: 1.0 / len(names) for n in names}
    t = max(float(temperature), 1e-6)
    z = np.where(finite, vals, -np.inf) / t
    z = z - z[finite].max()
    e = np.where(np.isfinite(z), np.exp(z), 0.0)
    w = e / e.sum()
    return {n: float(wi) for n, wi in zip(names, w, strict=False)}


def bma_skill(
    members: list[EnsembleMember],
    frame: pd.DataFrame,
    *,
    scoring: dict | None = None,
    time_col: str = "season",
    min_train_periods: int = 1,
    splits: list[Split] | None = None,
) -> dict[str, float]:
    """Per-member OOS expected log predictive density (elpd; higher = more skilful).

    Runs every member over the same walk-forward folds, pools its held-out Gaussian forecasts,
    and returns the mean log-score. `-inf` for a member that produced no held-out rows.
    """
    weights = ScoringWeights.from_scoring(scoring or {})
    folds = splits or walk_forward_splits(
        frame, time_col=time_col, min_train_periods=min_train_periods
    )
    pooled: dict[str, list[tuple[np.ndarray, np.ndarray, np.ndarray]]] = {
        m.name: [] for m in members
    }
    for sp in folds:
        y = np.asarray(points_of(sp.test, weights), dtype=np.float64)
        for m in members:
            pred = m.predict(sp.train, sp.test)
            pooled[m.name].append((pred.mean, pred.stdev, y))
    scores: dict[str, float] = {}
    for name, chunks in pooled.items():
        if not chunks:
            scores[name] = -np.inf
            continue
        mu = np.concatenate([c[0] for c in chunks])
        sd = np.concatenate([c[1] for c in chunks])
        yy = np.concatenate([c[2] for c in chunks])
        # log_loss_gaussian is the *negative* log density; negate → elpd (higher is better).
        scores[name] = -log_loss_gaussian(mu, sd, yy)
    return scores


def bma_weights(
    members: list[EnsembleMember],
    frame: pd.DataFrame,
    *,
    scoring: dict | None = None,
    time_col: str = "season",
    min_train_periods: int = 1,
    temperature: float = 1.0,
    splits: list[Split] | None = None,
) -> dict[str, float]:
    """BMA weights over `members` from their OOS log-score on `frame` — a convex blend (Σ=1)."""
    scores = bma_skill(
        members,
        frame,
        scoring=scoring,
        time_col=time_col,
        min_train_periods=min_train_periods,
        splits=splits,
    )
    return softmax_weights(scores, temperature=temperature)
