"""Adversarial stress scenarios — does the model degrade gracefully off-distribution?

Each scenario is a pure `frame -> frame` transform of the held-out world; `run_stress`
applies it, walk-forwards the predictor over the mutated frame, and asserts the output is
finite (no NaN/inf blow-up). The set covers the failure modes a fantasy engine actually
meets: a decimated week (mass injuries), a scoring collapse (weather), and an extreme season
(outliers). A stress result is `bad` if the model produced non-finite projections.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from blitz_engine.backtest.harness import walk_forward

if TYPE_CHECKING:
    from collections.abc import Callable

    from blitz_engine.backtest.harness import Predictor

__all__ = [
    "STRESS_SCENARIOS",
    "StressResult",
    "all_injury_week",
    "outlier_season",
    "run_stress",
    "weather_disaster",
]


def all_injury_week(
    frame: pd.DataFrame, *, time_col: str = "season", fraction: float = 0.5, seed: int = 0
) -> pd.DataFrame:
    """Zero out opportunities/yards/TDs for a random `fraction` of players in the last time
    period — a mass-injury week where much of the usable field vanishes."""
    out = frame.copy()
    last = pd.to_numeric(out[time_col]).max()
    rng = np.random.default_rng(seed)
    players = out.loc[pd.to_numeric(out[time_col]) == last, "player_id"].astype(str).unique()
    injured = set(rng.choice(players, size=max(1, int(len(players) * fraction)), replace=False))
    mask = (pd.to_numeric(out[time_col]) == last) & out["player_id"].astype(str).isin(injured)
    out.loc[mask, ["opportunities", "yards", "tds"]] = 0.0
    return out


def weather_disaster(frame: pd.DataFrame, *, factor: float = 0.4) -> pd.DataFrame:
    """A league-wide scoring collapse (blizzards/hurricanes): slash yards and TDs to
    `factor` of nominal, leaving opportunity structure intact."""
    out = frame.copy()
    out["yards"] = out["yards"] * factor
    out["tds"] = out["tds"] * factor
    return out


def outlier_season(
    frame: pd.DataFrame, *, time_col: str = "season", multiplier: float = 4.0
) -> pd.DataFrame:
    """Blow up the most recent period into a fat-tailed outlier (a freak historic season)
    by scaling its yards/TDs — probes tail robustness."""
    out = frame.copy()
    last = pd.to_numeric(out[time_col]).max()
    mask = pd.to_numeric(out[time_col]) == last
    out.loc[mask, "yards"] = out.loc[mask, "yards"] * multiplier
    out.loc[mask, "tds"] = out.loc[mask, "tds"] * multiplier
    return out


#: Named adversarial transforms the harness sweeps by default.
STRESS_SCENARIOS: dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
    "all_injury_week": all_injury_week,
    "weather_disaster": weather_disaster,
    "outlier_season": outlier_season,
}


@dataclass
class StressResult:
    """Outcome of one scenario: its MAE and whether projections stayed finite."""

    scenario: str
    mae: float
    finite: bool

    @property
    def bad(self) -> bool:
        return not self.finite


def run_stress(
    predictor: Predictor,
    frame: pd.DataFrame,
    *,
    scoring: dict | None = None,
    time_col: str = "season",
    min_train_periods: int = 1,
    scenarios: dict[str, Callable[[pd.DataFrame], pd.DataFrame]] | None = None,
) -> dict[str, StressResult]:
    """Sweep every scenario: mutate the frame, walk-forward, and record MAE + finiteness."""
    todo = scenarios if scenarios is not None else STRESS_SCENARIOS
    results: dict[str, StressResult] = {}
    for name, transform in todo.items():
        mutated = transform(frame)
        rep = walk_forward(
            mutated,
            predictor,
            scoring=scoring,
            time_col=time_col,
            min_train_periods=min_train_periods,
        )
        finite = bool(rep.errors.size) and bool(np.isfinite(rep.errors).all())
        results[name] = StressResult(scenario=name, mae=rep.mae, finite=finite)
    return results
