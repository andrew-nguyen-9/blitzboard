"""E7 — calibration harness: publish gate, recal, proper scoring, metric separation.

The DoD checks the brief spells out:
  * a miscalibrated (overconfident) fixture TRIPS the publish gate,
  * recalibration IMPROVES reliability,
  * CRPS / log-loss compute (and penalise overconfidence).

Fixtures are synthetic Gaussian worlds shaped like `Projection.quantiles` (mean/stdev +
p1…p99), so the tests exercise the exact contract model units feed in — no NUTS run needed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from blitz_engine.calibration import (
    BetaRecalibrator,
    IsotonicRecalibrator,
    MiscalibrationError,
    calibrated,
    calibration_error,
    compute_metrics,
    crps_gaussian,
    fit_recalibrator,
    log_loss_gaussian,
    pit_values,
    publish_gate,
    sharpness,
    spearman,
    top_n_hit_rate,
    weekly_recalibration,
)
from blitz_engine.calibration.recal import QUANTILE_LEVELS


def _quantiles(mean: np.ndarray, stdev: np.ndarray) -> pd.DataFrame:
    """Build a `Projection.quantiles`-shaped frame from Gaussian(mean, stdev) summaries."""
    df = pd.DataFrame(
        {"player_id": [f"p{i}" for i in range(mean.size)], "week": 1, "mean": mean, "stdev": stdev}
    )
    for col, tau in QUANTILE_LEVELS.items():
        df[col] = stats.norm.ppf(tau, loc=mean, scale=stdev)
    return df


def _world(n: int, sigma_scale: float, seed: int = 0):
    """A population whose forecast σ is `sigma_scale`× the σ that actually generated `y`.

    `sigma_scale=1` → calibrated; `<1` → overconfident (intervals too tight).
    """
    rng = np.random.default_rng(seed)
    mean = rng.uniform(60, 320, n)
    true_sigma = mean * rng.uniform(0.20, 0.30, n)
    realized = rng.normal(mean, true_sigma)
    forecast_sigma = true_sigma * sigma_scale
    return _quantiles(mean, forecast_sigma), realized


# ---------------------------------------------------------------------------------------
# publish gate
# ---------------------------------------------------------------------------------------
def test_calibrated_world_passes_the_gate():
    q, y = _world(800, sigma_scale=1.0)
    report = publish_gate(q, y)  # does not raise
    assert report.passed
    assert bool(calibrated(q, y)) is True


def test_overconfident_fixture_trips_the_publish_gate():
    q, y = _world(800, sigma_scale=0.5)  # intervals half as wide as reality
    report = calibrated(q, y)
    assert report.passed is False
    assert bool(report) is False
    with pytest.raises(MiscalibrationError):
        publish_gate(q, y)


def test_underconfident_fixture_also_trips_the_gate():
    q, y = _world(800, sigma_scale=2.0)  # intervals twice too wide
    assert not calibrated(q, y)


# ---------------------------------------------------------------------------------------
# recalibration improves reliability
# ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("method", ["isotonic", "beta"])
def test_recal_improves_reliability(method):
    q, y = _world(1500, sigma_scale=0.5, seed=1)
    mu, sd = q["mean"].to_numpy(), q["stdev"].to_numpy()
    recal = fit_recalibrator(mu, sd, y, method=method)
    before = calibration_error(pit_values(mu, sd, y))
    after = calibration_error(recal.transform_pit(pit_values(mu, sd, y)))
    assert after < before
    assert after < 0.1  # recalibrated PIT is close to uniform


@pytest.mark.parametrize("cls", [IsotonicRecalibrator, BetaRecalibrator])
def test_recal_widens_overconfident_intervals(cls):
    q, y = _world(1500, sigma_scale=0.5, seed=2)
    recal = cls().fit(q["mean"].to_numpy(), q["stdev"].to_numpy(), y)
    fixed = recal.recalibrate_quantiles(q)
    # an overconfident 80% interval [floor, ceiling] must get WIDER after recal
    assert (fixed["ceiling"] - fixed["floor"]).mean() > (q["ceiling"] - q["floor"]).mean()


def test_weekly_recalibration_is_gentle_but_improves():
    q, y = _world(1500, sigma_scale=0.5, seed=3)
    full = fit_recalibrator(q["mean"].to_numpy(), q["stdev"].to_numpy(), y, method="beta")
    week = weekly_recalibration(q, y, gentle=0.35)
    assert week.improved
    assert week.after.metrics.calibration_error < week.before.metrics.calibration_error
    # gentleness: the damped correction moves the ceiling LESS than a full correction would
    full_fixed = full.recalibrate_quantiles(q, strength=1.0)
    damped = (week.quantiles["ceiling"] - q["ceiling"]).abs().mean()
    hard = (full_fixed["ceiling"] - q["ceiling"]).abs().mean()
    assert damped < hard


# ---------------------------------------------------------------------------------------
# proper scoring + metric separation
# ---------------------------------------------------------------------------------------
def test_log_loss_penalises_overconfidence():
    q_cal, y = _world(800, sigma_scale=1.0, seed=4)
    q_over, _ = _world(800, sigma_scale=0.3, seed=4)  # same world, tighter σ
    ll_cal = log_loss_gaussian(q_cal["mean"], q_cal["stdev"], y)
    ll_over = log_loss_gaussian(q_over["mean"], q_over["stdev"], y)
    assert ll_over > ll_cal  # overconfident model scores worse (higher NLL)


def test_crps_is_minimised_near_the_true_sigma():
    q_true, y = _world(800, sigma_scale=1.0, seed=5)
    q_over, _ = _world(800, sigma_scale=0.4, seed=5)
    q_under, _ = _world(800, sigma_scale=3.0, seed=5)
    crps_true = crps_gaussian(q_true["mean"], q_true["stdev"], y).mean()
    crps_over = crps_gaussian(q_over["mean"], q_over["stdev"], y).mean()
    crps_under = crps_gaussian(q_under["mean"], q_under["stdev"], y).mean()
    assert crps_true < crps_over
    assert crps_true < crps_under


def test_axes_are_tracked_separately():
    # An overconfident model can be perfectly SHARP and DISCRIMINATING yet MIScalibrated —
    # the three axes must not move together.
    q, y = _world(800, sigma_scale=0.4, seed=6)
    m = compute_metrics(q, y)
    assert m.discrimination > 0.8          # ranks well (mean ∝ realized)
    assert m.sharpness < sharpness(q["stdev"] * 3)  # sharper than a wide variant
    assert m.calibration_error > 0.1       # yet badly miscalibrated
    assert 0.0 <= m.top_n_hit_rate <= 1.0


def test_spearman_and_top_n_reward_ranking():
    mean = np.arange(20.0)
    realized = mean + np.random.default_rng(7).normal(0, 0.1, 20)  # near-perfect ranking
    assert spearman(mean, realized) > 0.95
    assert top_n_hit_rate(mean, realized, 5) >= 0.8


def test_metrics_summary_is_nonempty_and_shapes_align():
    q, y = _world(50, sigma_scale=1.0, seed=8)
    report = calibrated(q, y)
    assert report.metrics.n == 50
    assert "cal_err" in report.metrics.summary()
    assert report.metrics.reliability.expected.shape == report.metrics.reliability.observed.shape


def test_realized_shape_mismatch_raises():
    q, y = _world(30, sigma_scale=1.0)
    with pytest.raises(ValueError):
        calibrated(q, y[:10])
