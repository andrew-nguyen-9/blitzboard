"""`blitz_engine.calibration` — the model-ops foundation every model unit's DoD leans on.

Model-ops is foundation-tier (v4-engine-architecture §"Model-ops is foundation"): a
projection may only publish if its stated uncertainty is honest. This package turns E1's
posterior-predictive `Projection.quantiles` (`mean`, `stdev`, `p1…p99`) into a verdict.

Public surface:

    calibrated(quantiles, realized)      the DoD probe — truthy iff calibrated, carries all
                                         metrics. `assert calibrated(proj.quantiles, y)`.
    publish_gate(quantiles, realized)    HARD gate — RAISES MiscalibrationError to block a
                                         miscalibrated (overconfident) forecast from publish.
    weekly_recalibration(quantiles, y)   gentle damped auto-recal hook (before/after report).

    CalibrationMetrics / CalibrationReport   calibration · discrimination · sharpness tracked
                                             SEPARATELY, plus CRPS + log-loss proper scores.
    IsotonicRecalibrator / BetaRecalibrator  post-hoc recal (`fit_recalibrator`) — bends a
                                             forecast until stated 70% = observed 70%.

Metric fns (`calibration_error`, `crps_gaussian`, `log_loss_gaussian`, `spearman`,
`top_n_hit_rate`, `reliability_curve`, …) are re-exported for the Model Lab (E8) and
ensemble (E6). E3/E6/E8 + every model unit read this — see E7-calibration.done.md.
"""
from __future__ import annotations

from blitz_engine.calibration.gate import (
    CAL_ERROR_MAX,
    CalibrationMetrics,
    CalibrationReport,
    MiscalibrationError,
    WeeklyRecalibration,
    calibrated,
    check_calibration,
    compute_metrics,
    publish_gate,
    weekly_recalibration,
)
from blitz_engine.calibration.metrics import (
    ReliabilityCurve,
    calibration_error,
    crps_gaussian,
    discrimination,
    log_loss_gaussian,
    pit_values,
    reliability_curve,
    sharpness,
    spearman,
    top_n_hit_rate,
)
from blitz_engine.calibration.recal import (
    QUANTILE_LEVELS,
    BetaRecalibrator,
    IsotonicRecalibrator,
    Recalibrator,
    fit_recalibrator,
)

__all__ = [
    "CAL_ERROR_MAX",
    "QUANTILE_LEVELS",
    "BetaRecalibrator",
    "CalibrationMetrics",
    "CalibrationReport",
    "IsotonicRecalibrator",
    "MiscalibrationError",
    "Recalibrator",
    "ReliabilityCurve",
    "WeeklyRecalibration",
    "calibrated",
    "calibration_error",
    "check_calibration",
    "compute_metrics",
    "crps_gaussian",
    "discrimination",
    "fit_recalibrator",
    "log_loss_gaussian",
    "pit_values",
    "publish_gate",
    "reliability_curve",
    "sharpness",
    "spearman",
    "top_n_hit_rate",
    "weekly_recalibration",
]
