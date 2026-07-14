"""Tests for E7 proper-scoring + ranking metrics (CRPS / log-loss / Spearman / top-N).

Additive to `test_backtest.py`: each new metric gets one behavioural test, plus a wiring test
proving the walk-forward report and benchmark board surface the ranking metric alongside MAE.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from blitz_engine.backtest import (
    BenchmarkBoard,
    crps_ensemble,
    crps_gaussian,
    log_loss,
    points_of,
    spearman,
    top_n_hit_rate,
    walk_forward,
)

from test_backtest import SCORING, WEIGHTS, make_seasons


# ── proper scoring: CRPS penalises overconfidence ─────────────────────────────
def test_crps_gaussian_penalises_overconfidence():
    """A sharp-but-wrong forecast scores worse than a calibrated wide one (proper scoring)."""
    y = np.array([10.0, 10.0, 10.0])
    overconfident = crps_gaussian(y, mu=np.full(3, 4.0), sigma=np.full(3, 0.3))  # sharp, wrong
    calibrated = crps_gaussian(y, mu=np.full(3, 4.0), sigma=np.full(3, 6.0))     # wide, honest
    assert overconfident > calibrated
    # a perfectly-centred sharp forecast beats the wide one — sharpness is rewarded when right
    correct = crps_gaussian(y, mu=np.full(3, 10.0), sigma=np.full(3, 0.3))
    assert correct < calibrated


def test_crps_ensemble_matches_gaussian_and_rewards_spread():
    """Sample-CRPS ≈ closed-form Gaussian CRPS, and a collapsed ensemble is penalised."""
    rng = np.random.default_rng(0)
    y = np.array([5.0])
    draws = rng.normal(5.0, 2.0, size=(1, 4000))
    approx = crps_ensemble(y, draws)
    closed = crps_gaussian(y, mu=np.array([5.0]), sigma=np.array([2.0]))
    assert approx == pytest.approx(closed, abs=0.1)
    # overconfident (collapsed) ensemble around the wrong value scores worse than honest spread
    collapsed = crps_ensemble(np.array([5.0]), np.full((1, 200), 1.0))
    honest = crps_ensemble(np.array([5.0]), rng.normal(1.0, 5.0, size=(1, 4000)))
    assert collapsed > honest


# ── proper scoring: log-loss finite + correct direction ───────────────────────
def test_log_loss_finite_and_directional():
    y = np.array([1.0, 0.0, 1.0, 0.0])
    confident_right = log_loss(y, np.array([0.99, 0.01, 0.98, 0.02]))
    confident_wrong = log_loss(y, np.array([0.01, 0.99, 0.02, 0.98]))
    assert np.isfinite(confident_right) and np.isfinite(confident_wrong)
    assert confident_right < confident_wrong
    # clipped so an all-wrong certain forecast stays finite rather than +inf
    assert np.isfinite(log_loss(np.array([1.0]), np.array([0.0])))


# ── ranking: Spearman + top-N on a known-ranked fixture ───────────────────────
def test_spearman_and_top_n_on_known_ranking():
    actual = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    monotonic = np.array([10.0, 20.0, 30.0, 40.0, 50.0])  # same order → ρ = 1
    reversed_ = actual[::-1]                                # opposite order → ρ = -1
    assert spearman(monotonic, actual) == pytest.approx(1.0)
    assert spearman(reversed_, actual) == pytest.approx(-1.0)
    # top-2: a prediction that nails the two biggest gets a perfect hit-rate
    pred = np.array([0.0, 0.0, 0.0, 9.0, 10.0])
    assert top_n_hit_rate(pred, actual, 2) == pytest.approx(1.0)
    # a prediction that inverts the ranking misses the true top-2 entirely
    assert top_n_hit_rate(reversed_, actual, 2) == pytest.approx(0.0)
    # degenerate guards: <2 obs → nan spearman, n<=0 → nan hit-rate
    assert np.isnan(spearman(np.array([1.0]), np.array([1.0])))
    assert np.isnan(top_n_hit_rate(pred, actual, 0))


# ── wiring: the walk-forward report + benchmark board surface ranking metrics ──
def _ranked_predictor(noise: float, seed: int):
    rng = np.random.default_rng(seed)

    def predict(train, test):
        return points_of(test, WEIGHTS) + rng.normal(0.0, noise, size=len(test))

    return predict


def test_walk_forward_report_exposes_ranking_metrics():
    frame = make_seasons()
    report = walk_forward(frame, _ranked_predictor(noise=1.0, seed=1), scoring=SCORING)
    assert report.predictions.shape == report.actuals.shape == report.errors.shape
    assert np.isfinite(report.mae) and np.isfinite(report.rmse)  # MAE/RMSE intact
    assert -1.0 <= report.spearman <= 1.0
    assert report.spearman > 0.5  # an accurate model ranks players well
    assert 0.0 <= report.top_n_hit_rate(5) <= 1.0


def test_benchmark_entry_records_spearman(tmp_path):
    frame = make_seasons()
    board = BenchmarkBoard(tmp_path)
    entry = board.record_run(
        version="v0", model=_ranked_predictor(noise=1.0, seed=2), frame=frame, scoring=SCORING
    )
    assert entry.model_spearman is not None and -1.0 <= entry.model_spearman <= 1.0
    # survives the JSONL round-trip
    assert board.latest("v0").model_spearman == pytest.approx(entry.model_spearman)
