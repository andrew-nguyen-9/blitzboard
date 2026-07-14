"""Walk-forward harness — the strict temporal engine every model unit's DoD runs through.

Generalises `projection.walk_forward_compare` (the minimal E1 hook) into a reusable
walk-forward runner over 2014–2025 (or any time column). The unit of work is a
**predictor** — `Callable[[train_df, test_df], np.ndarray]` returning fantasy points per
test row — so leakage detection, ablation significance, stress and benchmark logic are all
testable against cheap synthetic predictors, and the real engine is just one predictor
(see `predictors.py`).

Leakage is caught structurally: a strict temporal split requires **every** train time to be
< the held-out time. `detect_leakage` raises if that invariant is violated, so a mis-built
split can never silently train on the future.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from blitz_engine.projection.families import ScoringWeights

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    #: A model under test: (train rows, test rows) → predicted fantasy points per test row.
    Predictor = Callable[[pd.DataFrame, pd.DataFrame], np.ndarray]

__all__ = [
    "LeakageError",
    "Split",
    "WalkForwardReport",
    "detect_leakage",
    "points_of",
    "walk_forward",
    "walk_forward_splits",
]


class LeakageError(ValueError):
    """Raised when a split would let the model see data at or after the held-out time."""


def points_of(df: pd.DataFrame, weights: ScoringWeights) -> np.ndarray:
    """Fantasy points per row from skill yards + TDs (mirrors the projector's scoring)."""
    return np.asarray(
        weights.points(yards=df["yards"].to_numpy(), tds=df["tds"].to_numpy()), dtype=float
    )


@dataclass(frozen=True)
class Split:
    """One walk-forward fold: everything strictly before `time`, held out at `time`."""

    time: int
    train: pd.DataFrame
    test: pd.DataFrame


def detect_leakage(train: pd.DataFrame, test: pd.DataFrame, *, time_col: str) -> None:
    """Assert a strict temporal boundary between `train` and `test`.

    No-op on either side empty. Raises `LeakageError` if any train time is >= the earliest
    test time — the one bug a temporal backtest must never ship.
    """
    if len(train) == 0 or len(test) == 0:
        return
    train_max = float(pd.to_numeric(train[time_col]).max())
    test_min = float(pd.to_numeric(test[time_col]).min())
    if train_max >= test_min:
        raise LeakageError(
            f"leakage on {time_col!r}: train reaches {train_max} but test starts {test_min}"
        )


def walk_forward_splits(
    frame: pd.DataFrame,
    *,
    time_col: str = "season",
    min_train_periods: int = 1,
    common_players_only: bool = True,
) -> list[Split]:
    """Expanding-window folds: for each distinct time t, train on `< t`, test on `== t`.

    Skips the first `min_train_periods` times (no history to train on). Restricts each test
    fold to players also seen in train (`common_players_only`) so held-out error is defined.
    Every fold is leakage-checked before it is returned.
    """
    times = sorted(pd.to_numeric(frame[time_col]).unique())
    splits: list[Split] = []
    for i, t in enumerate(times):
        if i < min_train_periods:
            continue
        tnum = pd.to_numeric(frame[time_col])
        train = frame[tnum < t]
        test = frame[tnum == t]
        if common_players_only:
            common = set(train["player_id"].astype(str)) & set(test["player_id"].astype(str))
            test = test[test["player_id"].astype(str).isin(common)]
        if len(test) == 0:
            continue
        detect_leakage(train, test, time_col=time_col)
        splits.append(Split(time=int(t), train=train.copy(), test=test.copy()))
    return splits


@dataclass
class WalkForwardReport:
    """Aggregate + per-fold error of one predictor over a walk-forward run.

    `errors` is the concatenation of per-observation absolute errors across folds, in fold
    order — the paired vector ablation/significance compares between two runs.
    """

    per_split: dict[int, float]
    errors: np.ndarray
    n_obs: int
    keys: list[tuple[int, str]] = field(default_factory=list)

    @property
    def mae(self) -> float:
        return float(self.errors.mean()) if self.errors.size else float("nan")

    @property
    def rmse(self) -> float:
        return float(np.sqrt((self.errors**2).mean())) if self.errors.size else float("nan")


def walk_forward(
    frame: pd.DataFrame,
    predictor: Predictor,
    *,
    scoring: dict | None = None,
    time_col: str = "season",
    min_train_periods: int = 1,
    splits: Iterable[Split] | None = None,
) -> WalkForwardReport:
    """Run `predictor` across every walk-forward fold and score it against actuals.

    Pass pre-built `splits` to reuse the exact same folds across predictors (so two runs'
    `errors` vectors align row-for-row — the precondition for a *paired* ablation test).
    """
    weights = ScoringWeights.from_scoring(scoring or {})
    folds = (
        list(splits)
        if splits is not None
        else walk_forward_splits(
            frame, time_col=time_col, min_train_periods=min_train_periods
        )
    )
    per_split: dict[int, float] = {}
    chunks: list[np.ndarray] = []
    keys: list[tuple[int, str]] = []
    for sp in folds:
        actual = points_of(sp.test, weights)
        pred = np.asarray(predictor(sp.train, sp.test), dtype=float)
        if pred.shape != actual.shape:
            raise ValueError(
                f"predictor returned {pred.shape}, expected {actual.shape} at time {sp.time}"
            )
        err = np.abs(pred - actual)
        per_split[sp.time] = float(err.mean()) if err.size else float("nan")
        chunks.append(err)
        keys.extend((sp.time, str(p)) for p in sp.test["player_id"].astype(str))
    errors = np.concatenate(chunks) if chunks else np.asarray([], dtype=float)
    return WalkForwardReport(
        per_split=per_split, errors=errors, n_obs=int(errors.size), keys=keys
    )
