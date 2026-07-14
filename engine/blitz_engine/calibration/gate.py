"""The publish gate + the `calibrated()` API every model unit's DoD calls.

Model-ops is foundation-tier: a projection is only allowed to publish if its stated
uncertainty is honest. This module turns the metrics (`metrics.py`) and recalibration
(`recal.py`) into the two things downstream units actually import:

  * `calibrated(quantiles, realized) -> CalibrationReport` — the DoD probe. The report is
    truthy iff calibration passes (`bool(report)`), and always carries the full metric
    bundle, so a unit test reads `assert calibrated(q, y)` and a log reads `report.summary()`.
  * `publish_gate(quantiles, realized)` — the HARD gate: it RAISES `MiscalibrationError`
    when the forecast is miscalibrated, so an overconfident model can never reach a
    snapshot. Mirrors the convergence `gate` / `ConvergenceError` pattern E1 established
    (report-to-inspect vs raise-to-block).

Only **calibration** blocks — a sharp, well-ranking, *overconfident* model is precisely the
dangerous one, and sharpness/discrimination are reported alongside for inspection, never
gated on. `weekly_recalibration` is the gentle auto-recal hook: it learns the week's
calibration map and applies a *damped* correction, nudging toward calibrated without
chasing one week of noise.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

from blitz_engine.calibration.metrics import (
    calibration_error,
    crps_gaussian,
    discrimination,
    log_loss_gaussian,
    pit_values,
    reliability_curve,
    sharpness,
    top_n_hit_rate,
)
from blitz_engine.calibration.recal import Recalibrator, fit_recalibrator

if TYPE_CHECKING:
    import pandas as pd

    from blitz_engine.calibration.metrics import ReliabilityCurve

__all__ = [
    "CAL_ERROR_MAX",
    "CalibrationMetrics",
    "CalibrationReport",
    "MiscalibrationError",
    "WeeklyRecalibration",
    "calibrated",
    "check_calibration",
    "compute_metrics",
    "publish_gate",
    "weekly_recalibration",
]

# Hard gate default: max KS distance of the PIT from uniform before publish is blocked.
# ~1.36/√n is the 95% band, so 0.10 clears sampling noise for the hundreds of player-weeks
# a real snapshot carries while still catching systemic over/under-confidence.
CAL_ERROR_MAX = 0.10
# Rows ranked for the top-N discrimination metric (top fantasy tier).
TOP_N = 12


class MiscalibrationError(RuntimeError):
    """Raised by `publish_gate` when a forecast fails the hard calibration criterion."""


@dataclass(frozen=True)
class CalibrationMetrics:
    """The three orthogonal axes + proper scores — reported together, never collapsed."""

    n: int
    calibration_error: float  # KS(PIT, uniform) — the gated axis
    log_loss: float           # mean NLL — overconfidence penalty
    crps: float               # mean CRPS
    sharpness: float          # mean predictive stdev (NOT gated)
    discrimination: float     # Spearman ρ of mean vs realized (NOT gated)
    top_n_hit_rate: float     # top-N ranking overlap (NOT gated)
    reliability: ReliabilityCurve

    def summary(self) -> str:
        return (
            f"cal_err={self.calibration_error:.3f} log_loss={self.log_loss:.3f} "
            f"crps={self.crps:.3f} sharpness={self.sharpness:.3f} "
            f"discrimination={self.discrimination:.3f} top{TOP_N}={self.top_n_hit_rate:.2f} "
            f"(n={self.n})"
        )


@dataclass(frozen=True)
class CalibrationReport:
    """Publish verdict + the full metric bundle. Truthy iff calibration passes."""

    passed: bool
    metrics: CalibrationMetrics
    threshold: float
    reason: str = ""

    def __bool__(self) -> bool:
        return self.passed

    def summary(self) -> str:
        verdict = "PASS" if self.passed else "BLOCK"
        tail = f" — {self.reason}" if self.reason else ""
        return f"[{verdict}] {self.metrics.summary()}{tail}"


def _extract(
    quantiles: pd.DataFrame, realized: npt.ArrayLike
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Pull (mean, stdev, realized) aligned arrays from the `Projection.quantiles` frame.

    `realized` is aligned row-for-row to `quantiles` (the caller joins on player_id/week).
    """
    mu = quantiles["mean"].to_numpy(dtype=np.float64)
    sd = quantiles["stdev"].to_numpy(dtype=np.float64)
    y = np.asarray(realized, dtype=np.float64)
    if y.shape != mu.shape:
        raise ValueError(f"realized shape {y.shape} != quantiles rows {mu.shape}")
    return mu, sd, y


def compute_metrics(quantiles: pd.DataFrame, realized: npt.ArrayLike) -> CalibrationMetrics:
    """All three axes + proper scores for a forecast against its realized outcomes."""
    mu, sd, y = _extract(quantiles, realized)
    pit = pit_values(mu, sd, y)
    return CalibrationMetrics(
        n=int(mu.size),
        calibration_error=calibration_error(pit),
        log_loss=log_loss_gaussian(mu, sd, y),
        crps=float(crps_gaussian(mu, sd, y).mean()) if mu.size else 0.0,
        sharpness=sharpness(sd),
        discrimination=discrimination(mu, y),
        top_n_hit_rate=top_n_hit_rate(mu, y, TOP_N),
        reliability=reliability_curve(pit),
    )


def check_calibration(
    quantiles: pd.DataFrame,
    realized: npt.ArrayLike,
    *,
    max_calibration_error: float = CAL_ERROR_MAX,
) -> CalibrationReport:
    """Non-raising calibration verdict — for the Lab, logs, and the `calibrated()` probe."""
    metrics = compute_metrics(quantiles, realized)
    passed = metrics.calibration_error <= max_calibration_error
    reason = (
        ""
        if passed
        else f"calibration_error {metrics.calibration_error:.3f} > {max_calibration_error:.3f}"
    )
    return CalibrationReport(
        passed=passed, metrics=metrics, threshold=max_calibration_error, reason=reason
    )


def calibrated(
    quantiles: pd.DataFrame,
    realized: npt.ArrayLike,
    *,
    max_calibration_error: float = CAL_ERROR_MAX,
) -> CalibrationReport:
    """The DoD API model units call: `assert calibrated(projection.quantiles, realized)`.

    Returns a truthy-iff-calibrated `CalibrationReport` carrying every metric — "bool +
    metrics" in one object. Alias of `check_calibration`, named for how DoDs read.
    """
    return check_calibration(quantiles, realized, max_calibration_error=max_calibration_error)


def publish_gate(
    quantiles: pd.DataFrame,
    realized: npt.ArrayLike,
    *,
    max_calibration_error: float = CAL_ERROR_MAX,
) -> CalibrationReport:
    """HARD gate: RAISE `MiscalibrationError` on a miscalibrated forecast (blocks publish).

    Returns the passing report on success (so callers can log the metrics).
    """
    report = check_calibration(quantiles, realized, max_calibration_error=max_calibration_error)
    if not report.passed:
        raise MiscalibrationError("Calibration gate BLOCKED publish — " + report.summary())
    return report


@dataclass(frozen=True)
class WeeklyRecalibration:
    """Result of the gentle weekly auto-recal hook: the corrected frame + before/after."""

    quantiles: pd.DataFrame
    recalibrator: Recalibrator
    before: CalibrationReport
    after: CalibrationReport

    @property
    def improved(self) -> bool:
        """True iff the damped correction lowered the calibration error."""
        return self.after.metrics.calibration_error <= self.before.metrics.calibration_error


def weekly_recalibration(
    quantiles: pd.DataFrame,
    realized: npt.ArrayLike,
    *,
    method: str = "beta",
    gentle: float = 0.35,
    max_calibration_error: float = CAL_ERROR_MAX,
) -> WeeklyRecalibration:
    """Gentle weekly auto-recal: learn the week's map, apply a *damped* correction.

    `gentle` in [0,1] blends the correction toward identity so one noisy week can't yank the
    published intervals around — a slow drift toward calibration, not a jerk. Returns the
    recalibrated `quantiles` frame plus before/after reports for the audit log. `beta` is the
    default learner (smooth, stable on a single week).
    """
    before = check_calibration(quantiles, realized, max_calibration_error=max_calibration_error)
    mu, sd, y = _extract(quantiles, realized)
    recal = fit_recalibrator(mu, sd, y, method=method)
    corrected = recal.recalibrate_quantiles(quantiles, strength=gentle)
    # Recal fixes interval coverage, not the mean/stdev summary, so the honest "after"
    # calibration error is the KS of the *recalibrated* PIT — what the corrected quantiles
    # actually deliver. Other axes carry over unchanged.
    after_pit = recal.transform_pit(pit_values(mu, sd, y), strength=gentle)
    after_err = float(calibration_error(after_pit))
    after = CalibrationReport(
        passed=after_err <= max_calibration_error,
        metrics=replace(before.metrics, calibration_error=after_err),
        threshold=max_calibration_error,
    )
    return WeeklyRecalibration(quantiles=corrected, recalibrator=recal, before=before, after=after)
