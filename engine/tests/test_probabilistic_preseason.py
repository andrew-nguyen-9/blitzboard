from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from blitz_engine.backtest.probabilistic_preseason import (
    add_rolling_uncertainty,
    build_player_seasons,
    component_forecasts,
    point_forecasts,
    run_component_archive,
    score_component_forecasts,
    score_forecasts,
    weighted_interval_score,
)


def _weekly() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    players = {
        2018: {"qb": ("QB", [10.0, 10.0]), "rb": ("RB", [5.0, 5.0])},
        2019: {"qb": ("QB", [12.0]), "rb": ("RB", [6.0, 6.0])},
        2020: {"qb": ("QB", [14.0, 14.0]), "rb": ("RB", [7.0, 7.0])},
        2021: {"qb": ("QB", [16.0, 16.0]), "rb": ("RB", [8.0, 8.0])},
    }
    for season, entries in players.items():
        for player_id, (position, points) in entries.items():
            for week, value in enumerate(points, start=1):
                rows.append(
                    {
                        "season": season,
                        "week": week,
                        "season_type": "REG",
                        "player_id": player_id,
                        "position": position,
                        "fantasy_points": value,
                        "fantasy_points_ppr": value + (1.0 if position == "RB" else 0.0),
                    }
                )
    return pd.DataFrame(rows)


def test_build_player_seasons_scores_half_ppr_and_drops_postseason() -> None:
    weekly = _weekly()
    weekly.loc[len(weekly)] = {
        "season": 2021,
        "week": 19,
        "season_type": "POST",
        "player_id": "qb",
        "position": "QB",
        "fantasy_points": 1000.0,
        "fantasy_points_ppr": 1000.0,
    }
    out = build_player_seasons(weekly, scoring="half")
    rb = out[(out.season == 2021) & (out.player_id == "rb")].iloc[0]
    qb = out[(out.season == 2021) & (out.player_id == "qb")].iloc[0]
    assert rb.points == pytest.approx(17.0)
    assert qb.points == pytest.approx(32.0)
    assert qb.games == 2


def test_availability_preserving_forecast_differs_from_per_game_proxy() -> None:
    table = build_player_seasons(_weekly(), scoring="std")
    out = point_forecasts(table, methods=("game_rate", "prior_total"), start_season=2019)
    qb_2019 = out[(out.season == 2019) & (out.player_id == "qb")].set_index("method")
    assert qb_2019.loc["game_rate", "mean"] == pytest.approx(160.0)
    assert qb_2019.loc["prior_total", "mean"] == pytest.approx(20.0)


def test_shrinkage_stays_between_prior_total_and_position_anchor() -> None:
    weekly = _weekly()
    extra = weekly[(weekly.season == 2018) & (weekly.player_id == "qb")].copy()
    extra["player_id"] = "qb2"
    extra["fantasy_points"] = 30.0
    extra["fantasy_points_ppr"] = 30.0
    weekly = pd.concat([weekly, extra], ignore_index=True)
    table = build_player_seasons(weekly, scoring="std")
    out = point_forecasts(table, methods=("prior_total", "pooled_total"), start_season=2019)
    qb = out[(out.season == 2019) & (out.player_id == "qb")].set_index("method")
    assert qb.loc["prior_total", "mean"] < qb.loc["pooled_total", "mean"] < 40.0


def test_forecast_for_a_fold_is_unchanged_when_future_outcomes_mutate() -> None:
    table = build_player_seasons(_weekly(), scoring="std")
    first = point_forecasts(table, methods=("recency_total",), start_season=2019)
    mutated = table.copy()
    mutated.loc[mutated.season >= 2020, "points"] = 99999.0
    second = point_forecasts(mutated, methods=("recency_total",), start_season=2019)
    cols = ["season", "player_id", "method", "mean"]
    pd.testing.assert_frame_equal(
        first[first.season == 2019][cols].reset_index(drop=True),
        second[second.season == 2019][cols].reset_index(drop=True),
    )


def test_rolling_uncertainty_uses_only_prior_residuals_and_orders_intervals() -> None:
    table = build_player_seasons(_weekly(), scoring="std")
    points = point_forecasts(table, methods=("prior_total",), start_season=2019)
    first = add_rolling_uncertainty(points, min_residuals=1)
    changed = points.copy()
    changed.loc[changed.season >= 2021, "actual"] = 50000.0
    second = add_rolling_uncertainty(changed, min_residuals=1)
    a = first[first.season == 2020].reset_index(drop=True)
    b = second[second.season == 2020].reset_index(drop=True)
    pd.testing.assert_series_equal(a.stdev, b.stdev)
    assert (first[["p10", "p25", "p50", "p75", "p90"]].diff(axis=1).iloc[:, 1:] >= 0).all().all()


def test_weighted_interval_score_rewards_sharp_correct_forecast() -> None:
    y = np.array([10.0, 20.0])
    sharp = weighted_interval_score(
        y, p10=np.array([9.0, 19.0]), p25=np.array([9.5, 19.5]),
        p50=y, p75=np.array([10.5, 20.5]), p90=np.array([11.0, 21.0]),
    )
    wide = weighted_interval_score(
        y, p10=np.array([0.0, 10.0]), p25=np.array([5.0, 15.0]),
        p50=y, p75=np.array([15.0, 25.0]), p90=np.array([20.0, 30.0]),
    )
    assert sharp < wide
    with pytest.raises(ValueError, match="ordered"):
        weighted_interval_score(y, p10=y, p25=y, p50=y, p75=y - 1, p90=y)


def test_scoring_is_deterministic_and_reports_coverage() -> None:
    table = build_player_seasons(_weekly(), scoring="std")
    forecasts = add_rolling_uncertainty(
        point_forecasts(table, methods=("game_rate", "prior_total"), start_season=2019),
        min_residuals=1,
    )
    first = score_forecasts(forecasts, seed=7, bootstrap_resamples=100)
    second = score_forecasts(forecasts, seed=7, bootstrap_resamples=100)
    assert first == second
    assert set(first["models"]) == {"game_rate", "prior_total"}
    assert {"coverage_50", "coverage_80", "crps", "wis", "mae"} <= set(
        first["models"]["prior_total"]
    )


def test_component_forecast_keeps_conditional_production_and_availability_separate() -> None:
    table = build_player_seasons(_weekly(), scoring="std")
    out = component_forecasts(table, methods=("prior_components",), start_season=2019)
    qb = out[(out.season == 2019) & (out.player_id == "qb")].iloc[0]
    assert qb.conditional_mean == pytest.approx(160.0)
    assert qb.availability_p == pytest.approx(2 / 16)
    assert qb.expected_mean == pytest.approx(20.0)
    assert qb.actual_conditional * qb.actual_availability == pytest.approx(qb.actual_total)


def test_component_pooling_is_bounded_by_player_and_position_history() -> None:
    weekly = _weekly()
    extra = weekly[(weekly.season == 2018) & (weekly.player_id == "qb")].copy()
    extra["player_id"] = "qb2"
    extra["fantasy_points"] = 30.0
    extra["fantasy_points_ppr"] = 30.0
    weekly = pd.concat([weekly, extra.iloc[:1]], ignore_index=True)
    table = build_player_seasons(weekly, scoring="std")
    out = component_forecasts(
        table,
        methods=("prior_components", "pooled_components"),
        start_season=2019,
    )
    qb = out[(out.season == 2019) & (out.player_id == "qb")].set_index("method")
    assert qb.loc["prior_components", "conditional_mean"] < qb.loc[
        "pooled_components", "conditional_mean"
    ] < 30.0 * 16
    assert 1 / 16 < qb.loc["pooled_components", "availability_p"] < 2 / 16


def test_component_fold_is_unchanged_when_future_outcomes_mutate() -> None:
    table = build_player_seasons(_weekly(), scoring="std")
    first = component_forecasts(table, start_season=2019)
    mutated = table.copy()
    mutated.loc[mutated.season >= 2020, ["points", "games"]] = [99999.0, 16]
    second = component_forecasts(mutated, start_season=2019)
    cols = [
        "season", "player_id", "method", "conditional_mean", "availability_p", "expected_mean"
    ]
    pd.testing.assert_frame_equal(
        first[first.season == 2019][cols].reset_index(drop=True),
        second[second.season == 2019][cols].reset_index(drop=True),
    )


def test_component_scoring_reports_proper_availability_loss_deterministically() -> None:
    table = build_player_seasons(_weekly(), scoring="std")
    forecasts = component_forecasts(table, start_season=2019)
    first = score_component_forecasts(forecasts)
    second = score_component_forecasts(forecasts)
    assert first == second
    assert set(first["models"]) == {
        "pooled_components", "prior_components", "recency_components"
    }
    for model in first["models"].values():
        assert 0 <= model["availability_brier"] <= 1
        assert 0 <= model["availability_mae"] <= 1
        assert 0 <= model["availability_calibration_gap"] <= 1


def test_component_archive_records_source_hashes_and_component_identity(tmp_path) -> None:
    weekly = _weekly()
    for season, frame in weekly.groupby("season"):
        frame.to_pickle(tmp_path / f"weekly_{season}.pkl")
    report = run_component_archive(tmp_path, scoring="std", start_season=2019)
    assert set(report["models"]) == {
        "pooled_components", "prior_components", "recency_components"
    }
    assert report["configuration"]["component_contract"] == (
        "expected_mean = conditional_mean * availability_p"
    )
    assert set(report["configuration"]["source_sha256"]) == {
        "weekly_2018.pkl", "weekly_2019.pkl", "weekly_2020.pkl", "weekly_2021.pkl"
    }
