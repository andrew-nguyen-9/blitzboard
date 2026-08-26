from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from blitz_engine.intelligence.model import (
    MODE_BUDGETS,
    compare_models,
    expected_points,
    score_predictions,
    validate_forecast_frame,
)


def _forecasts(candidate_shift: float = 0.0) -> pd.DataFrame:
    rows = []
    actuals = {"QB": [20.0, 10.0], "RB": [14.0, 6.0]}
    for position, actual_values in actuals.items():
        for config in ("canonical-ppr", "superflex-half"):
            for model in ("existing", "independent"):
                for index, actual in enumerate(actual_values):
                    conditional = actual + (candidate_shift if model == "independent" else 1.0)
                    rows.append({
                        "model": model, "model_version": "1", "as_of_utc": "2026-08-25Z",
                        "player_id": f"{position}-{index}", "position": position,
                        "league_config_id": config, "horizon": "weekly", "week": 1,
                        "availability_p": 1.0, "conditional_mean": conditional,
                        "conditional_stdev": 2.0, "p10": conditional - 3,
                        "p50": conditional, "p90": conditional + 3,
                        "actual_points": actual,
                    })
    return pd.DataFrame(rows)


def test_shared_schema_separates_availability_from_conditional_points() -> None:
    frame = _forecasts().iloc[:1].copy()
    frame["availability_p"] = 0.5
    validate_forecast_frame(frame)
    assert expected_points(frame).iloc[0] == frame["conditional_mean"].iloc[0] / 2


def test_daily_and_deep_budgets_are_local_and_bounded() -> None:
    assert MODE_BUDGETS["daily"].max_runtime_minutes <= 10
    assert MODE_BUDGETS["daily"].max_memory_gb <= 8
    assert MODE_BUDGETS["deep"].max_trials > MODE_BUDGETS["daily"].max_trials


def test_multi_metric_gate_promotes_clean_candidate_across_groups() -> None:
    report = compare_models(_forecasts(candidate_shift=0.0), candidate_model="independent",
                            reference_model="existing")
    assert report.promoted
    assert {group.group for group in report.groups} == {
        "position=QB", "position=RB", "league_config_id=canonical-ppr",
        "league_config_id=superflex-half",
    }


def test_multi_metric_gate_blocks_position_regression() -> None:
    frame = _forecasts(candidate_shift=0.0)
    mask = (frame["model"] == "independent") & (frame["position"] == "RB")
    frame.loc[mask, ["conditional_mean", "p10", "p50", "p90"]] += 5
    report = compare_models(frame, candidate_model="independent", reference_model="existing")
    assert not report.promoted
    failed = next(group for group in report.groups if group.group == "position=RB")
    assert "mae_regression" in failed.reasons


def test_metrics_include_accuracy_rank_calibration_and_decision_utility() -> None:
    metric = score_predictions(
        np.array([1.0, 3.0, 2.0]), np.array([1.0, 2.0, 3.0]),
        np.array([0.0, 1.0, 1.0]), np.array([2.0, 4.0, 4.0]), top_k=1,
    )
    assert metric.mae == pytest.approx(2 / 3)
    assert metric.rmse > metric.mae
    assert 0 <= metric.interval_coverage <= 1
    assert 0 <= metric.decision_utility <= 1


@pytest.mark.parametrize("mutation", ["availability", "quantiles", "duplicate", "ros_week"])
def test_schema_rejects_invalid_forecasts(mutation: str) -> None:
    frame = _forecasts().iloc[:1].copy()
    if mutation == "availability":
        frame["availability_p"] = 1.1
    elif mutation == "quantiles":
        frame["p10"], frame["p90"] = 30.0, 1.0
    elif mutation == "duplicate":
        frame = pd.concat([frame, frame], ignore_index=True)
    else:
        frame["horizon"] = "ros"
    with pytest.raises(ValueError):
        validate_forecast_frame(frame)

