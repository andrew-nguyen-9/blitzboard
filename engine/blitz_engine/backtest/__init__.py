"""`blitz_engine.backtest` — the model-ops foundation every model unit's DoD runs through.

Generalises E1's minimal `walk_forward_compare` into the full walk-forward / ablation /
stress / drift / benchmark harness. The two headline APIs a model unit calls to prove its
component earns its place and its version hasn't regressed:

    from blitz_engine.backtest import ablation, no_regression

    verdict = ablation("vegas_factor", full=with_it, ablated=without_it, frame=hist,
                       scoring=scoring)          # -> helps | neutral | hurts + p-value
    assert no_regression(candidate, frame=hist, scoring=scoring)   # release gate

Everything is expressed over **predictors** (`(train_df, test_df) -> points`), so the real
`HierarchicalProjector` is just one predictor (`engine_predictor`) and the whole harness is
testable without running NUTS. The benchmark board (`BenchmarkBoard`) is a JSONL ledger under
the store root, keyed to the registry version tuple.
"""
from __future__ import annotations

from blitz_engine.backtest.ablation import (
    HELPS,
    HURTS,
    NEUTRAL,
    AblationResult,
    RegressionResult,
    ablation,
    no_regression,
    paired_permutation_p,
)
from blitz_engine.backtest.benchmark import BenchmarkBoard, BenchmarkEntry
from blitz_engine.backtest.drift import (
    DriftAlarm,
    population_stability_index,
    scan_drift,
)
from blitz_engine.backtest.harness import (
    LeakageError,
    Split,
    WalkForwardReport,
    detect_leakage,
    points_of,
    walk_forward,
    walk_forward_splits,
)
from blitz_engine.backtest.metrics import (
    crps_ensemble,
    crps_gaussian,
    log_loss,
    spearman,
    top_n_hit_rate,
)
from blitz_engine.backtest.predictors import (
    baseline_predictor,
    engine_predictor,
    fantasypros_predictor,
)
from blitz_engine.backtest.stress import (
    STRESS_SCENARIOS,
    StressResult,
    all_injury_week,
    outlier_season,
    run_stress,
    weather_disaster,
)

__all__ = [
    "HELPS",
    "HURTS",
    "NEUTRAL",
    "STRESS_SCENARIOS",
    "AblationResult",
    "BenchmarkBoard",
    "BenchmarkEntry",
    "DriftAlarm",
    "LeakageError",
    "RegressionResult",
    "Split",
    "StressResult",
    "WalkForwardReport",
    "ablation",
    "all_injury_week",
    "baseline_predictor",
    "crps_ensemble",
    "crps_gaussian",
    "detect_leakage",
    "engine_predictor",
    "fantasypros_predictor",
    "log_loss",
    "no_regression",
    "outlier_season",
    "paired_permutation_p",
    "points_of",
    "population_stability_index",
    "run_stress",
    "scan_drift",
    "spearman",
    "top_n_hit_rate",
    "walk_forward",
    "walk_forward_splits",
    "weather_disaster",
]
