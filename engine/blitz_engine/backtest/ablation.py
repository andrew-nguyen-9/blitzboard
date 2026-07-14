"""The two APIs every model unit's DoD calls: `ablation(...)` and `no_regression(...)`.

`ablation` proves a component earns its place: it walk-forwards the model **with** and
**without** the component over identical folds, then runs a paired, dependency-free
sign-flip permutation test on the per-observation error differences. Verdict:

    helps    — removing it significantly *worsens* error   (component adds signal)
    hurts    — removing it significantly *improves* error   (component is harmful)
    neutral  — no significant effect                        (provably neutral / dead)

`no_regression` is the release gate: a candidate predictor must not be meaningfully worse
than a reference (default = the shrink-to-mean baseline, or a prior version's predictor).
Both return rich results that are also truthy/`bool()`-able so a DoD can `assert` them.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from blitz_engine.backtest.harness import Split, walk_forward, walk_forward_splits
from blitz_engine.backtest.predictors import baseline_predictor

if TYPE_CHECKING:
    from blitz_engine.backtest.harness import Predictor

__all__ = [
    "HELPS",
    "HURTS",
    "NEUTRAL",
    "AblationResult",
    "RegressionResult",
    "ablation",
    "no_regression",
    "paired_permutation_p",
]

HELPS = "helps"
NEUTRAL = "neutral"
HURTS = "hurts"


def paired_permutation_p(diff: np.ndarray, *, n_perm: int = 2000, seed: int = 0) -> float:
    """Two-sided sign-flip permutation p-value for the mean of paired differences.

    Under H0 (component has no effect) each pair's sign is exchangeable, so we compare the
    observed mean |diff| against the null of random sign flips. Dependency-free (no scipy).
    Returns 1.0 when every difference is zero (a truly dead component).
    """
    d = np.asarray(diff, dtype=float)
    d = d[d != 0.0]
    if d.size == 0:
        return 1.0
    observed = abs(float(d.mean()))
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1.0, 1.0], size=(n_perm, d.size))
    null = np.abs((signs * d).mean(axis=1))
    return float((null >= observed).mean())


@dataclass
class AblationResult:
    """Verdict on whether a component pulls its weight, with effect size + significance."""

    component: str
    mae_with: float
    mae_without: float
    p_value: float
    verdict: str
    n_obs: int

    @property
    def delta(self) -> float:
        """MAE improvement attributable to the component (without − with); >0 ⇒ it helps."""
        return self.mae_without - self.mae_with

    @property
    def significant(self) -> bool:
        return self.verdict != NEUTRAL

    def __bool__(self) -> bool:
        """Truthy iff the component is not harmful (helps or is neutral)."""
        return self.verdict != HURTS


def ablation(
    component: str,
    *,
    full: Predictor,
    ablated: Predictor,
    frame: pd.DataFrame,
    scoring: dict | None = None,
    time_col: str = "season",
    min_train_periods: int = 1,
    alpha: float = 0.05,
    seed: int = 0,
) -> AblationResult:
    """Does `component` help? Compare `full` vs `ablated` on identical walk-forward folds.

    `full` = model with the component wired in; `ablated` = the same model with it removed
    (neutralised). Folds are built once and shared so the two error vectors are paired
    row-for-row. Significance is `alpha` on the sign-flip permutation test.
    """
    folds: list[Split] = walk_forward_splits(
        frame, time_col=time_col, min_train_periods=min_train_periods
    )
    rep_full = walk_forward(frame, full, scoring=scoring, splits=folds)
    rep_abl = walk_forward(frame, ablated, scoring=scoring, splits=folds)
    if rep_full.errors.shape != rep_abl.errors.shape:
        raise ValueError("full and ablated runs produced misaligned error vectors")

    diff = rep_abl.errors - rep_full.errors  # >0 where removing the component hurt accuracy
    p = paired_permutation_p(diff, seed=seed)
    mean_diff = float(diff.mean()) if diff.size else 0.0
    if p >= alpha or mean_diff == 0.0:
        verdict = NEUTRAL
    elif mean_diff > 0:
        verdict = HELPS
    else:
        verdict = HURTS
    return AblationResult(
        component=component,
        mae_with=rep_full.mae,
        mae_without=rep_abl.mae,
        p_value=p,
        verdict=verdict,
        n_obs=int(diff.size),
    )


@dataclass
class RegressionResult:
    """Whether a candidate holds the line against a reference (baseline or prior version)."""

    candidate_mae: float
    reference_mae: float
    tolerance: float
    p_value: float
    n_obs: int

    @property
    def passed(self) -> bool:
        """True iff the candidate is within `tolerance` of the reference (not a regression)."""
        return self.candidate_mae <= self.reference_mae * (1.0 + self.tolerance)

    def __bool__(self) -> bool:
        return self.passed


def no_regression(
    candidate: Predictor,
    *,
    frame: pd.DataFrame,
    reference: Predictor | None = None,
    scoring: dict | None = None,
    time_col: str = "season",
    min_train_periods: int = 1,
    tolerance: float = 0.02,
    seed: int = 0,
) -> RegressionResult:
    """Release gate: `bool(no_regression(model, frame=...))` — False iff `model` regressed.

    Runs `candidate` and `reference` (default = shrink-to-mean baseline) over the same folds
    and checks the candidate's MAE is within `tolerance` of the reference. A model whose
    accuracy has regressed trips `.passed`/`bool()` to False.
    """
    ref = reference if reference is not None else baseline_predictor(scoring)
    folds = walk_forward_splits(frame, time_col=time_col, min_train_periods=min_train_periods)
    cand_rep = walk_forward(frame, candidate, scoring=scoring, splits=folds)
    ref_rep = walk_forward(frame, ref, scoring=scoring, splits=folds)
    p = paired_permutation_p(cand_rep.errors - ref_rep.errors, seed=seed)
    return RegressionResult(
        candidate_mae=cand_rep.mae,
        reference_mae=ref_rep.mae,
        tolerance=tolerance,
        p_value=p,
        n_obs=int(cand_rep.errors.size),
    )
