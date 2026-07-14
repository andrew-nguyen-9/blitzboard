"""Concrete predictors the harness scores — the real engine, the reference baseline, FP.

Each is a `(train_df, test_df) -> np.ndarray` closure (see `harness.Predictor`). The engine
predictor wraps the E1 `HierarchicalProjector`: fit on the train universe, posterior-predict
the held-out rows, return the mean projected points aligned to `test_df`. Backtests are
diagnostic, so the hard convergence gate is off here (`enforce_gate=False`) — publishing
keeps it on.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from blitz_engine.backtest.harness import points_of
from blitz_engine.projection import HierarchicalProjector, ModelData
from blitz_engine.projection.families import ScoringWeights

if TYPE_CHECKING:
    from collections.abc import Callable

    from blitz_engine.backtest.harness import Predictor

__all__ = ["baseline_predictor", "engine_predictor", "fantasypros_predictor"]


def baseline_predictor(scoring: dict | None = None) -> Predictor:
    """Shrink-to-positional-mean — the interim pipeline projector's behaviour, the reference
    every hierarchical model must beat (or match). Predicts each test player his position's
    mean train points."""
    weights = ScoringWeights.from_scoring(scoring or {})

    def predict(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
        tr = train.copy()
        tr["_pts"] = points_of(tr, weights)
        pos_mean = tr.groupby(tr["position"].astype(str))["_pts"].mean()
        overall = float(tr["_pts"].mean())
        return np.array(
            [float(pos_mean.get(p, overall)) for p in test["position"].astype(str)]
        )

    return predict


def engine_predictor(
    scoring: dict | None = None,
    *,
    factory: Callable[[], HierarchicalProjector] | None = None,
    **fit_kw: object,
) -> Predictor:
    """The hierarchical projection core as a predictor. `factory` lets a model unit inject a
    projector wired with its component (factor/latent/talent seam) — the with/without pair
    an ablation compares."""

    def predict(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
        proj = factory() if factory is not None else HierarchicalProjector(scoring=scoring)
        train_data = ModelData.from_frame(train)
        kw = dict(fit_kw)
        kw.setdefault("enforce_gate", False)
        proj.fit(train_data, **kw)  # type: ignore[arg-type]
        out = proj.predict(ModelData.from_frame(train, obs_df=test))
        pred_by_pid = out.quantiles.groupby("player_id")["mean"].mean()
        overall = float(out.quantiles["mean"].mean())
        return np.array(
            [float(pred_by_pid.get(p, overall)) for p in test["player_id"].astype(str)]
        )

    return predict


def fantasypros_predictor(
    projections: pd.DataFrame,
    *,
    time_col: str = "season",
    points_col: str = "proj_points",
) -> Predictor:
    """An external-projection predictor (e.g. FantasyPros consensus) for the benchmark board.

    `projections` carries `player_id`, the time column, and `points_col`. Looks up each test
    row's projected points; unknown player-times fall back to the column mean.
    """
    proj = projections.copy()
    proj["player_id"] = proj["player_id"].astype(str)
    overall = float(proj[points_col].mean()) if len(proj) else 0.0
    lookup: dict[tuple[str, int], float] = {
        (str(r["player_id"]), int(r[time_col])): float(r[points_col])
        for _, r in proj.iterrows()
    }

    def predict(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
        return np.array(
            [
                lookup.get((str(pid), int(t)), overall)
                for pid, t in zip(
                    test["player_id"].astype(str), test[time_col], strict=False
                )
            ]
        )

    return predict
