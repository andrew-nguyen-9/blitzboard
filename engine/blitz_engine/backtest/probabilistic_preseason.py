"""Leakage-safe preseason forecast experiments over archived weekly outcomes.

This is an evaluation seam, not a production projector.  It compares causal preseason
baselines, fits uncertainty from strictly earlier rolling residuals, and emits compact metrics
that can screen a candidate before a blind-draft shadow is allowed to consume it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from blitz_engine.calibration.metrics import calibration_error, crps_gaussian, pit_values

METHODS = ("game_rate", "prior_total", "pooled_total", "recency_total")
COMPONENT_METHODS = ("prior_components", "pooled_components", "recency_components")


def scheduled_games(season: int) -> int:
    """Known preseason regular-season game count (the 17-game schedule began in 2021)."""
    return 17 if int(season) >= 2021 else 16


def build_player_seasons(weekly: pd.DataFrame, *, scoring: str = "half") -> pd.DataFrame:
    """Aggregate nflverse-style weekly rows into player-season outcomes.

    `games` counts stat-bearing rows and is deliberately distinct from `scheduled_games`:
    the difference carries historical availability rather than pretending every player who
    appeared once played a full season.
    """
    if scoring not in {"std", "half", "ppr"}:
        raise ValueError("scoring must be std, half, or ppr")
    required = {
        "season", "week", "season_type", "player_id", "position",
        "fantasy_points", "fantasy_points_ppr",
    }
    missing = required - set(weekly)
    if missing:
        raise ValueError(f"weekly frame missing {sorted(missing)}")
    frame = weekly[weekly["season_type"].eq("REG")].copy()
    frame = frame[frame["position"].isin(["QB", "RB", "WR", "TE"])]
    standard = frame["fantasy_points"].fillna(0).to_numpy(dtype=float)
    ppr = frame["fantasy_points_ppr"].fillna(frame["fantasy_points"]).to_numpy(dtype=float)
    frame["_points"] = {"std": standard, "half": (standard + ppr) / 2, "ppr": ppr}[scoring]
    out = (
        frame.groupby(["season", "player_id", "position"], as_index=False)
        .agg(points=("_points", "sum"), games=("week", "nunique"))
        .sort_values(["season", "player_id"])
        .reset_index(drop=True)
    )
    out["season"] = out["season"].astype(int)
    out["player_id"] = out["player_id"].astype(str)
    out["points"] = out["points"].astype(float)
    out["games"] = out["games"].astype(int)
    return out


def _normalized_total(row: pd.Series, target_season: int) -> float:
    return (
        float(row["points"])
        * scheduled_games(target_season)
        / scheduled_games(int(row["season"]))
    )


def _forecast_mean(
    history: pd.DataFrame,
    *,
    player_id: str,
    position: str,
    target_season: int,
    method: str,
    shrink_games: float,
) -> tuple[float | None, int]:
    player = history[history["player_id"].eq(player_id)].sort_values("season", ascending=False)
    if player.empty:
        return None, 0
    prior_season = target_season - 1
    prior = player[player["season"].eq(prior_season)]
    if prior.empty:
        return None, len(player)
    latest = prior.iloc[0]
    if method == "game_rate":
        return (
            float(latest["points"]) / max(int(latest["games"]), 1)
            * scheduled_games(target_season),
            len(player),
        )
    latest_total = _normalized_total(latest, target_season)
    if method == "prior_total":
        return latest_total, len(player)
    prior_all = history[history["season"].eq(prior_season)]
    anchors = prior_all[prior_all["position"].eq(position)].apply(
        _normalized_total, axis=1, target_season=target_season
    )
    anchor = float(anchors.median()) if len(anchors) else float(
        prior_all.apply(_normalized_total, axis=1, target_season=target_season).median()
    )
    if method == "pooled_total":
        weight = int(latest["games"]) / (int(latest["games"]) + float(shrink_games))
        return weight * latest_total + (1 - weight) * anchor, len(player)
    if method == "recency_total":
        older = player[player["season"].eq(target_season - 2)]
        if older.empty:
            return latest_total, len(player)
        older_total = _normalized_total(older.iloc[0], target_season)
        return 0.7 * latest_total + 0.3 * older_total, len(player)
    raise ValueError(f"unknown method {method!r}; expected one of {METHODS}")


def point_forecasts(
    table: pd.DataFrame,
    *,
    methods: Sequence[str] = METHODS,
    start_season: int | None = None,
    shrink_games: float = 8.0,
) -> pd.DataFrame:
    """Expanding-origin player-season point forecasts using only seasons `< target`."""
    unknown = set(methods) - set(METHODS)
    if unknown:
        raise ValueError(f"unknown methods: {sorted(unknown)}")
    seasons = sorted(int(value) for value in table["season"].unique())
    if len(seasons) < 2:
        raise ValueError("at least two seasons are required")
    first = max(seasons[1], start_season or seasons[1])
    rows: list[dict[str, Any]] = []
    for target_season in [season for season in seasons if season >= first]:
        history = table[table["season"] < target_season]
        if len(history) and int(history["season"].max()) >= target_season:
            raise ValueError("forecast training boundary reaches target season")
        target = table[table["season"].eq(target_season)]
        for record in target.itertuples(index=False):
            for method in methods:
                mean, history_years = _forecast_mean(
                    history,
                    player_id=str(record.player_id),
                    position=str(record.position),
                    target_season=target_season,
                    method=method,
                    shrink_games=shrink_games,
                )
                if mean is None:  # Primary accuracy cohort: returning players with t-1 history.
                    continue
                rows.append(
                    {
                        "season": target_season,
                        "player_id": str(record.player_id),
                        "position": str(record.position),
                        "method": method,
                        "mean": float(max(mean, 0.0)),
                        "actual": float(record.points),
                        "history_years": int(history_years),
                        "train_start": int(history["season"].min()),
                        "train_end": int(history["season"].max()),
                    }
                )
    return pd.DataFrame(rows).sort_values(["season", "player_id", "method"]).reset_index(drop=True)


def _component_mean(
    history: pd.DataFrame,
    *,
    player_id: str,
    position: str,
    target_season: int,
    method: str,
    shrink_games: float,
) -> tuple[float | None, float | None, int]:
    player = history[history["player_id"].eq(player_id)].sort_values("season", ascending=False)
    if player.empty:
        return None, None, 0
    prior_season = target_season - 1
    prior = player[player["season"].eq(prior_season)]
    if prior.empty:
        return None, None, len(player)
    latest = prior.iloc[0]
    latest_games = int(latest["games"])
    latest_rate = float(latest["points"]) / max(latest_games, 1)
    latest_availability = min(latest_games / scheduled_games(prior_season), 1.0)
    conditional_rate = latest_rate
    availability = latest_availability

    if method == "pooled_components":
        prior_all = history[history["season"].eq(prior_season)]
        position_rows = prior_all[prior_all["position"].eq(position)]
        anchor_rows = position_rows if len(position_rows) else prior_all
        rate_anchor = float((anchor_rows["points"] / anchor_rows["games"].clip(lower=1)).median())
        availability_anchor = float(
            (anchor_rows["games"] / scheduled_games(prior_season)).clip(upper=1).median()
        )
        weight = latest_games / (latest_games + float(shrink_games))
        conditional_rate = weight * latest_rate + (1 - weight) * rate_anchor
        availability = weight * latest_availability + (1 - weight) * availability_anchor
    elif method == "recency_components":
        older = player[player["season"].eq(target_season - 2)]
        if not older.empty:
            older_row = older.iloc[0]
            older_games = int(older_row["games"])
            conditional_rate = 0.7 * latest_rate + 0.3 * (
                float(older_row["points"]) / max(older_games, 1)
            )
            availability = 0.7 * latest_availability + 0.3 * min(
                older_games / scheduled_games(target_season - 2), 1.0
            )
    elif method != "prior_components":
        raise ValueError(f"unknown component method {method!r}")

    return (
        max(conditional_rate * scheduled_games(target_season), 0.0),
        float(np.clip(availability, 0.0, 1.0)),
        len(player),
    )


def component_forecasts(
    table: pd.DataFrame,
    *,
    methods: Sequence[str] = COMPONENT_METHODS,
    start_season: int | None = None,
    shrink_games: float = 8.0,
) -> pd.DataFrame:
    """Causal forecasts that keep production-given-appearance separate from availability.

    `conditional_mean` is a full-schedule equivalent from stat-bearing games. `availability_p`
    is an appearance-fraction baseline, not the richer weekly `AvailabilityModel.p_startable`.
    Their product is derived only here at the evaluation boundary.
    """
    unknown = set(methods) - set(COMPONENT_METHODS)
    if unknown:
        raise ValueError(f"unknown component methods: {sorted(unknown)}")
    seasons = sorted(int(value) for value in table["season"].unique())
    if len(seasons) < 2:
        raise ValueError("at least two seasons are required")
    first = max(seasons[1], start_season or seasons[1])
    rows: list[dict[str, Any]] = []
    for target_season in [season for season in seasons if season >= first]:
        history = table[table["season"] < target_season]
        target = table[table["season"].eq(target_season)]
        for record in target.itertuples(index=False):
            actual_games = int(record.games)
            actual_availability = min(actual_games / scheduled_games(target_season), 1.0)
            actual_conditional = (
                float(record.points) / max(actual_games, 1) * scheduled_games(target_season)
            )
            for method in methods:
                conditional, availability, history_years = _component_mean(
                    history,
                    player_id=str(record.player_id),
                    position=str(record.position),
                    target_season=target_season,
                    method=method,
                    shrink_games=shrink_games,
                )
                if conditional is None or availability is None:
                    continue
                rows.append(
                    {
                        "season": target_season,
                        "player_id": str(record.player_id),
                        "position": str(record.position),
                        "method": method,
                        "conditional_mean": conditional,
                        "availability_p": availability,
                        "expected_mean": conditional * availability,
                        "actual_conditional": actual_conditional,
                        "actual_availability": actual_availability,
                        "actual_total": float(record.points),
                        "actual_games": actual_games,
                        "scheduled_games": scheduled_games(target_season),
                        "history_years": int(history_years),
                        "train_start": int(history["season"].min()),
                        "train_end": int(history["season"].max()),
                    }
                )
    return pd.DataFrame(rows).sort_values(["season", "player_id", "method"]).reset_index(drop=True)


def _component_metrics(frame: pd.DataFrame) -> dict[str, float | int]:
    conditional_error = frame["actual_conditional"] - frame["conditional_mean"]
    expected_error = frame["actual_total"] - frame["expected_mean"]
    probability = frame["availability_p"].to_numpy(dtype=float)
    observed = frame["actual_availability"].to_numpy(dtype=float)
    bins = np.clip((probability * 10).astype(int), 0, 9)
    calibration_gap = 0.0
    for index in np.unique(bins):
        mask = bins == index
        calibration_gap += float(mask.mean()) * abs(
            float(probability[mask].mean() - observed[mask].mean())
        )

    def rank(left: pd.Series, right: pd.Series) -> float:
        varied = len(frame) > 1 and left.nunique() > 1 and right.nunique() > 1
        value = stats.spearmanr(left, right).statistic if varied else np.nan
        return round(float(value), 6) if np.isfinite(value) else 0.0

    return {
        "n": len(frame),
        "conditional_mae": round(float(np.mean(np.abs(conditional_error))), 6),
        "conditional_spearman": rank(frame["conditional_mean"], frame["actual_conditional"]),
        "availability_brier": round(
            float(np.mean(observed * (1 - probability) ** 2 + (1 - observed) * probability**2)),
            6,
        ),
        "availability_mae": round(float(np.mean(np.abs(observed - probability))), 6),
        "availability_calibration_gap": round(calibration_gap, 6),
        "expected_mae": round(float(np.mean(np.abs(expected_error))), 6),
        "expected_spearman": rank(frame["expected_mean"], frame["actual_total"]),
    }


def score_component_forecasts(forecasts: pd.DataFrame) -> dict[str, Any]:
    """Score each component and their derived expectation without conflating the targets."""
    models = {
        str(method): _component_metrics(frame)
        for method, frame in forecasts.groupby("method", sort=True)
    }
    by_season = {
        str(method): {
            str(int(season)): _component_metrics(group)
            for season, group in frame.groupby("season", sort=True)
        }
        for method, frame in forecasts.groupby("method", sort=True)
    }
    return {
        "schema_version": 1,
        "authority": "exploratory synthetic development evidence; not promotion evidence",
        "models": models,
        "by_season": by_season,
        "limitations": [
            "A stat-bearing game is an appearance proxy, not an injury or startability label.",
            "Returning-player cohort excludes rookies and players without prior-season history.",
            "No archived point-in-time preseason injury or depth-chart inputs are available.",
        ],
    }


def _scale(residuals: np.ndarray, fallback_mean: float) -> float:
    if residuals.size >= 2:
        value = float(np.std(residuals, ddof=1))
        if np.isfinite(value) and value > 0:
            return value
    return max(abs(float(fallback_mean)) * 0.5, 1.0)


def add_rolling_uncertainty(
    forecasts: pd.DataFrame,
    *,
    kind: str = "position_gaussian",
    min_residuals: int = 20,
) -> pd.DataFrame:
    """Fit each row's uncertainty from same-method residuals in strictly earlier seasons.

    `position_gaussian` uses a position residual scale when sufficiently supported and otherwise
    falls back to the earlier global pool. `global_gaussian` always uses that pool.
    `split_conformal` uses earlier absolute residual quantiles for central 50%/80% intervals.
    """
    if kind not in {"position_gaussian", "global_gaussian", "split_conformal"}:
        raise ValueError("unknown uncertainty kind")
    output: list[pd.DataFrame] = []
    for (method, season), current in forecasts.groupby(["method", "season"], sort=True):
        previous = forecasts[
            (forecasts["method"].eq(method)) & (forecasts["season"] < season)
        ].copy()
        residual = previous["actual"].to_numpy(dtype=float) - previous["mean"].to_numpy(dtype=float)
        current = current.copy()
        values: list[tuple[float, float, float, float, float, int, str]] = []
        for row in current.itertuples(index=False):
            pos = previous[previous["position"].eq(row.position)]
            pos_residual = pos["actual"].to_numpy(dtype=float) - pos["mean"].to_numpy(dtype=float)
            selected = (
                pos_residual
                if kind != "global_gaussian" and len(pos_residual) >= min_residuals
                else residual
            )
            source = "position" if selected is pos_residual else "global"
            sd = _scale(selected, float(row.mean))
            if kind == "split_conformal" and selected.size:
                absolute = np.abs(selected)
                q50 = float(np.quantile(absolute, 0.5, method="higher"))
                q80 = float(np.quantile(absolute, 0.8, method="higher"))
                quantiles = (
                    row.mean - q80,
                    row.mean - q50,
                    row.mean,
                    row.mean + q50,
                    row.mean + q80,
                )
            else:
                quantiles = tuple(
                    float(stats.norm.ppf(q, loc=row.mean, scale=sd))
                    for q in (.1, .25, .5, .75, .9)
                )
            values.append((*quantiles, len(selected), source))
        current[["p10", "p25", "p50", "p75", "p90", "residual_n", "scale_source"]] = values
        current["stdev"] = [
            _scale(
                (
                    previous[previous["position"].eq(row.position)]["actual"].to_numpy(dtype=float)
                    - previous[previous["position"].eq(row.position)]["mean"].to_numpy(dtype=float)
                )
                if kind != "global_gaussian"
                and len(previous[previous["position"].eq(row.position)]) >= min_residuals
                else residual,
                float(row.mean),
            )
            for row in current.itertuples(index=False)
        ]
        current["uncertainty"] = kind
        output.append(current)
    return pd.concat(output, ignore_index=True).sort_values(
        ["season", "player_id", "method"]
    ).reset_index(drop=True)


def weighted_interval_score(
    y: np.ndarray,
    *,
    p10: np.ndarray,
    p25: np.ndarray,
    p50: np.ndarray,
    p75: np.ndarray,
    p90: np.ndarray,
) -> float:
    """Mean WIS using the median and central 50%/80% intervals (lower is better)."""
    arrays = [np.asarray(value, dtype=float) for value in (p10, p25, p50, p75, p90)]
    if any(np.any(left > right) for left, right in zip(arrays, arrays[1:], strict=False)):
        raise ValueError("forecast quantiles must be ordered")
    truth = np.asarray(y, dtype=float)

    def interval_score(lower: np.ndarray, upper: np.ndarray, alpha: float) -> np.ndarray:
        return (
            upper - lower
            + 2 / alpha * (lower - truth) * (truth < lower)
            + 2 / alpha * (truth - upper) * (truth > upper)
        )

    total = (
        0.5 * np.abs(truth - arrays[2])
        + 0.25 * interval_score(arrays[1], arrays[3], 0.5)
        + 0.1 * interval_score(arrays[0], arrays[4], 0.2)
    ) / 2.5
    return float(total.mean())


def _metrics(frame: pd.DataFrame) -> dict[str, float | int]:
    actual = frame["actual"].to_numpy(dtype=float)
    mean = frame["mean"].to_numpy(dtype=float)
    stdev = frame["stdev"].to_numpy(dtype=float)
    error = actual - mean
    varied = len(frame) > 1 and np.ptp(mean) > 0 and np.ptp(actual) > 0
    rho = stats.spearmanr(mean, actual).statistic if varied else np.nan
    return {
        "n": len(frame),
        "mae": round(float(np.mean(np.abs(error))), 6),
        "rmse": round(float(np.sqrt(np.mean(error**2))), 6),
        "spearman": round(float(rho), 6) if np.isfinite(rho) else 0.0,
        "crps": round(float(np.mean(crps_gaussian(mean, stdev, actual))), 6),
        "wis": round(weighted_interval_score(
            actual,
            p10=frame["p10"].to_numpy(), p25=frame["p25"].to_numpy(),
            p50=frame["p50"].to_numpy(), p75=frame["p75"].to_numpy(),
            p90=frame["p90"].to_numpy(),
        ), 6),
        "pit_ks": round(calibration_error(pit_values(mean, stdev, actual)), 6),
        "coverage_50": round(float(np.mean((actual >= frame.p25) & (actual <= frame.p75))), 6),
        "coverage_80": round(float(np.mean((actual >= frame.p10) & (actual <= frame.p90))), 6),
        "width_50": round(float(np.mean(frame.p75 - frame.p25)), 6),
        "width_80": round(float(np.mean(frame.p90 - frame.p10)), 6),
    }


def _cluster_interval(values: dict[int, float], *, seed: int, resamples: int) -> list[float]:
    ordered = np.asarray([values[key] for key in sorted(values)], dtype=float)
    if len(ordered) == 1:
        return [round(float(ordered[0]), 6)] * 2
    rng = np.random.default_rng(seed)
    sampled = ordered[rng.integers(0, len(ordered), size=(resamples, len(ordered)))].mean(axis=1)
    return [round(float(value), 6) for value in np.quantile(sampled, (0.025, 0.975))]


def score_forecasts(
    forecasts: pd.DataFrame,
    *,
    seed: int = 20260829,
    bootstrap_resamples: int = 5000,
) -> dict[str, Any]:
    """Compact deterministic report with aggregate, fold, position, and paired evidence."""
    models: dict[str, Any] = {}
    by_season: dict[str, Any] = {}
    by_position: dict[str, Any] = {}
    for method, frame in forecasts.groupby("method", sort=True):
        models[str(method)] = _metrics(frame)
        by_season[str(method)] = {
            str(int(season)): _metrics(group)
            for season, group in frame.groupby("season", sort=True)
        }
        by_position[str(method)] = {
            str(position): _metrics(group)
            for position, group in frame.groupby("position", sort=True)
        }
    paired: dict[str, Any] = {}
    if "game_rate" in models:
        baseline = forecasts[forecasts["method"].eq("game_rate")]
        for offset, method in enumerate(sorted(set(forecasts.method) - {"game_rate"})):
            candidate = forecasts[forecasts["method"].eq(method)]
            joined = baseline.merge(
                candidate, on=["season", "player_id", "position"], suffixes=("_base", "_candidate")
            )
            effects: dict[str, Any] = {"paired_rows": len(joined)}
            for metric_index, metric in enumerate(("mae", "crps")):
                if metric == "mae":
                    base_loss = np.abs(joined.actual_base - joined.mean_base)
                    cand_loss = np.abs(joined.actual_candidate - joined.mean_candidate)
                else:
                    base_loss = crps_gaussian(
                        joined.mean_base, joined.stdev_base, joined.actual_base
                    )
                    cand_loss = crps_gaussian(
                        joined.mean_candidate, joined.stdev_candidate, joined.actual_candidate
                    )
                fold_delta = {}
                for season in sorted(joined.season.unique()):
                    mask = joined.season == season
                    fold_delta[int(season)] = float(np.mean(cand_loss[mask] - base_loss[mask]))
                effects[f"{metric}_delta"] = round(float(np.mean(cand_loss - base_loss)), 6)
                effects[f"{metric}_delta_ci95"] = _cluster_interval(
                    fold_delta,
                    seed=seed + offset * 17 + metric_index,
                    resamples=bootstrap_resamples,
                )
            paired[method] = effects
    return {
        "schema_version": 1,
        "authority": "exploratory synthetic development evidence; not promotion evidence",
        "seed": seed,
        "models": models,
        "by_season": by_season,
        "by_position": by_position,
        "paired_vs_game_rate": paired,
        "limitations": [
            "Outcome-derived active-player universe; primary rows require prior-season history.",
            "No archived vendor point distributions, rookies, depth charts, or preseason injuries.",
            "All scored seasons are already inspected and cannot serve as promotion confirmation.",
        ],
    }


def load_weekly_archive(directory: Path) -> tuple[pd.DataFrame, dict[str, str]]:
    paths = sorted(directory.glob("weekly_*.pkl"))
    if not paths:
        raise FileNotFoundError(f"no weekly_*.pkl files in {directory}")
    frames, hashes = [], {}
    for path in paths:
        frames.append(pd.read_pickle(path))
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return pd.concat(frames, ignore_index=True), hashes


def run_archive(
    directory: Path,
    *,
    scoring: str = "half",
    uncertainty: str = "position_gaussian",
    start_season: int = 2017,
    seed: int = 20260829,
) -> dict[str, Any]:
    weekly, hashes = load_weekly_archive(directory)
    table = build_player_seasons(weekly, scoring=scoring)
    # Generate the earliest possible folds so the first reported season can calibrate only on
    # earlier forecast errors. Filtering before uncertainty fitting would discard that history.
    points = point_forecasts(table)
    forecasts = add_rolling_uncertainty(points, kind=uncertainty)
    forecasts = forecasts[forecasts["season"] >= start_season].reset_index(drop=True)
    report = score_forecasts(forecasts, seed=seed)
    report["configuration"] = {
        "scoring": scoring,
        "uncertainty": uncertainty,
        "start_season": start_season,
        "seasons": sorted(int(value) for value in table.season.unique()),
        "source_sha256": hashes,
    }
    return report


def run_component_archive(
    directory: Path,
    *,
    scoring: str = "half",
    start_season: int = 2017,
) -> dict[str, Any]:
    """Run the component contract over an archive with source-hash provenance."""
    weekly, hashes = load_weekly_archive(directory)
    table = build_player_seasons(weekly, scoring=scoring)
    forecasts = component_forecasts(table, start_season=start_season)
    report = score_component_forecasts(forecasts)
    report["configuration"] = {
        "scoring": scoring,
        "start_season": start_season,
        "seasons": sorted(int(value) for value in table.season.unique()),
        "component_contract": "expected_mean = conditional_mean * availability_p",
        "availability_target": "regular-season stat-bearing appearance fraction",
        "source_sha256": hashes,
    }
    return report


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weekly-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--scoring", choices=("std", "half", "ppr"), default="half")
    parser.add_argument(
        "--uncertainty",
        choices=("position_gaussian", "global_gaussian", "split_conformal"),
        default="position_gaussian",
    )
    parser.add_argument("--start-season", type=int, default=2017)
    parser.add_argument("--seed", type=int, default=20260829)
    parser.add_argument(
        "--components",
        action="store_true",
        help="score conditional production and availability separately",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = (
        run_component_archive(
            args.weekly_dir,
            scoring=args.scoring,
            start_season=args.start_season,
        )
        if args.components
        else run_archive(
            args.weekly_dir,
            scoring=args.scoring,
            uncertainty=args.uncertainty,
            start_season=args.start_season,
            seed=args.seed,
        )
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
