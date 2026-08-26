"""Comparison contract for existing and independent weekly/ROS forecasts.

Training remains in ``blitz_engine.ensemble``. This module provides the shared output schema,
daily/deep local budgets, and the multi-metric shadow-to-promotion gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

ModelMode = Literal["daily", "deep"]
REQUIRED_COLUMNS = frozenset({
    "model", "model_version", "as_of_utc", "player_id", "position", "league_config_id",
    "horizon", "week", "availability_p", "conditional_mean", "conditional_stdev",
    "p10", "p50", "p90",
})


@dataclass(frozen=True)
class LocalBudget:
    max_runtime_minutes: int
    max_memory_gb: int
    max_trials: int


MODE_BUDGETS = {
    "daily": LocalBudget(max_runtime_minutes=10, max_memory_gb=8, max_trials=12),
    "deep": LocalBudget(max_runtime_minutes=480, max_memory_gb=12, max_trials=200),
}


@dataclass(frozen=True)
class MetricSet:
    mae: float
    rmse: float
    rank_correlation: float
    interval_coverage: float
    calibration_error: float
    decision_utility: float


@dataclass(frozen=True)
class GroupGate:
    group: str
    candidate: MetricSet
    reference: MetricSet
    passed: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PromotionReport:
    promoted: bool
    groups: tuple[GroupGate, ...]
    candidate_model: str
    reference_model: str


def validate_forecast_frame(frame: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"forecast schema missing columns: {missing}")
    if frame.empty:
        raise ValueError("forecast frame cannot be empty")
    if frame[list(REQUIRED_COLUMNS - {"week"})].isna().any().any():
        raise ValueError("forecast required columns cannot be null (week may be null for ROS)")
    if not frame["horizon"].isin(["weekly", "ros"]).all():
        raise ValueError("horizon must be weekly or ros")
    weekly = frame["horizon"] == "weekly"
    if frame.loc[weekly, "week"].isna().any() or frame.loc[~weekly, "week"].notna().any():
        raise ValueError("week is required only for weekly forecasts")
    if not frame["availability_p"].between(0, 1).all():
        raise ValueError("availability_p must be between zero and one")
    if (frame["conditional_stdev"] <= 0).any():
        raise ValueError("conditional_stdev must be positive")
    if not ((frame["p10"] <= frame["p50"]) & (frame["p50"] <= frame["p90"])).all():
        raise ValueError("forecast quantiles must be ordered")
    keys = ["model", "model_version", "as_of_utc", "player_id", "league_config_id",
            "horizon", "week"]
    if frame.duplicated(keys).any():
        raise ValueError("forecast frame contains duplicate model/player/horizon rows")


def expected_points(frame: pd.DataFrame) -> pd.Series:
    """Unconditional points; availability remains separately inspectable in the frame."""
    validate_forecast_frame(frame)
    return frame["availability_p"] * frame["conditional_mean"]


def _rank_correlation(predicted: np.ndarray, actual: np.ndarray) -> float:
    pred_rank = pd.Series(predicted).rank(method="average").to_numpy()
    actual_rank = pd.Series(actual).rank(method="average").to_numpy()
    if np.std(pred_rank) == 0 or np.std(actual_rank) == 0:
        return 0.0
    return float(np.corrcoef(pred_rank, actual_rank)[0, 1])


def score_predictions(
    predicted: np.ndarray,
    actual: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    *,
    target_coverage: float = 0.8,
    top_k: int = 12,
) -> MetricSet:
    arrays = [np.asarray(value, dtype=float) for value in (predicted, actual, lower, upper)]
    pred, truth, lo, hi = arrays
    if not len(pred) or any(len(value) != len(pred) for value in arrays):
        raise ValueError("metric arrays must be non-empty and aligned")
    if not all(np.isfinite(value).all() for value in arrays):
        raise ValueError("metric arrays must be finite")
    error = pred - truth
    coverage = float(np.mean((truth >= lo) & (truth <= hi)))
    k = min(top_k, len(pred))
    selected = np.argsort(pred)[-k:]
    oracle = np.argsort(truth)[-k:]
    denominator = max(float(truth[oracle].sum()), 1e-9)
    return MetricSet(
        mae=float(np.mean(np.abs(error))),
        rmse=float(np.sqrt(np.mean(error**2))),
        rank_correlation=_rank_correlation(pred, truth),
        interval_coverage=coverage,
        calibration_error=abs(coverage - target_coverage),
        decision_utility=float(truth[selected].sum() / denominator),
    )


def _gate(candidate: MetricSet, reference: MetricSet, tolerance: float) -> tuple[str, ...]:
    reasons: list[str] = []
    if candidate.mae > reference.mae + tolerance:
        reasons.append("mae_regression")
    if candidate.rmse > reference.rmse + tolerance:
        reasons.append("rmse_regression")
    if candidate.rank_correlation + tolerance < reference.rank_correlation:
        reasons.append("rank_regression")
    if candidate.calibration_error > reference.calibration_error + tolerance:
        reasons.append("calibration_regression")
    if candidate.decision_utility + tolerance < reference.decision_utility:
        reasons.append("decision_utility_regression")
    return tuple(reasons)


def compare_models(
    frame: pd.DataFrame,
    *,
    candidate_model: str,
    reference_model: str,
    actual_col: str = "actual_points",
    tolerance: float = 0.0,
) -> PromotionReport:
    validate_forecast_frame(frame)
    if actual_col not in frame or frame[actual_col].isna().any():
        raise ValueError("actual_points are required for promotion evaluation")
    groups: list[GroupGate] = []
    dimensions = ["position", "league_config_id"]
    for dimension in dimensions:
        for value in sorted(frame[dimension].unique()):
            subset = frame[frame[dimension] == value]
            scores = {}
            for model in (candidate_model, reference_model):
                rows = subset[subset["model"] == model]
                if rows.empty:
                    raise ValueError(f"missing {model} rows for {dimension}={value}")
                scores[model] = score_predictions(
                    expected_points(rows).to_numpy(), rows[actual_col].to_numpy(),
                    rows["p10"].to_numpy(), rows["p90"].to_numpy(),
                )
            reasons = _gate(scores[candidate_model], scores[reference_model], tolerance)
            groups.append(GroupGate(f"{dimension}={value}", scores[candidate_model],
                                    scores[reference_model], not reasons, reasons))
    return PromotionReport(
        promoted=all(group.passed for group in groups),
        groups=tuple(groups),
        candidate_model=candidate_model,
        reference_model=reference_model,
    )

