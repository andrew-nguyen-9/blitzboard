"""Tests for E7-backtest — the walk-forward / ablation / stress / drift / benchmark harness.

The harness is expressed over *predictors*, so most tests use cheap synthetic predictors and
run instantly (no NUTS). One integration test exercises the real `engine_predictor` on a tiny
frame with short chains to prove the projector wiring holds.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from blitz_engine.backtest import (
    HELPS,
    HURTS,
    NEUTRAL,
    BenchmarkBoard,
    LeakageError,
    ablation,
    baseline_predictor,
    detect_leakage,
    engine_predictor,
    fantasypros_predictor,
    no_regression,
    points_of,
    run_stress,
    scan_drift,
    walk_forward,
    walk_forward_splits,
)
from blitz_engine.projection.families import ScoringWeights

SCORING = {
    "receiving": {"pt_per_yd": 0.1, "ppr": 0.5, "td": 6},
    "rushing": {"pt_per_yd": 0.1, "td": 6},
}
WEIGHTS = ScoringWeights.from_scoring(SCORING)


def make_seasons(seasons=None, weeks=3, teams=2, per_team=4, seed=0) -> pd.DataFrame:
    """Multi-season synthetic league; player identities persist across seasons."""
    seasons = range(2014, 2020) if seasons is None else seasons
    rng = np.random.default_rng(seed)
    cycle = ["WR", "WR", "RB", "TE"]
    talent = {}
    rows = []
    for t in range(teams):
        for p in range(per_team):
            talent[(t, p)] = (
                np.exp(rng.normal(0.0, 0.5)),  # usage appeal
                np.exp(rng.normal(1.9, 0.2)),  # yards/opp
                rng.uniform(0.02, 0.08),       # td rate
            )
    for season in seasons:
        for t in range(teams):
            appeals = np.array([talent[(t, p)][0] for p in range(per_team)])
            share = appeals / appeals.sum()
            for wk in range(1, weeks + 1):
                plays = max(float(rng.normal(65, 8)), 45.0)
                for p in range(per_team):
                    _, ypo, tdr = talent[(t, p)]
                    opp = int(rng.poisson(plays * share[p]))
                    yards = float(rng.gamma(6.0, (opp * ypo) / 6.0)) if opp > 0 else 0.0
                    tds = int(rng.poisson(opp * tdr))
                    rows.append({
                        "player_id": f"T{t}_P{p}", "position": cycle[p % len(cycle)],
                        "team": f"T{t}", "season": season, "week": wk, "team_plays": plays,
                        "opportunities": opp, "yards": yards, "tds": tds,
                    })
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def frame() -> pd.DataFrame:
    return make_seasons()


# ── walk-forward split: strict temporal, no leakage ───────────────────────────
def test_walk_forward_splits_have_no_leakage(frame):
    splits = walk_forward_splits(frame, time_col="season")
    assert splits, "expected at least one fold"
    for sp in splits:
        # every training season strictly precedes the held-out season
        assert sp.train["season"].max() < sp.time
        assert (sp.test["season"] == sp.time).all()
        # detect_leakage agrees (does not raise)
        detect_leakage(sp.train, sp.test, time_col="season")


def test_detect_leakage_raises_on_future_train(frame):
    train = frame[frame["season"] <= 2016]
    test = frame[frame["season"] == 2015]  # overlaps the train window → leak
    with pytest.raises(LeakageError):
        detect_leakage(train, test, time_col="season")


# ── ablation: dead component neutral, real component helps ─────────────────────
def _const_predictor(value: float):
    return lambda train, test: np.full(len(test), value)


def _accurate_predictor(noise: float, seed: int):
    """Predicts near-actual points with a controllable noise floor."""
    rng = np.random.default_rng(seed)

    def predict(train, test):
        actual = points_of(test, WEIGHTS)
        return actual + rng.normal(0.0, noise, size=len(test))

    return predict


def test_ablation_flags_dead_component(frame):
    """A dead component leaves predictions identical (with == without) → provably NEUTRAL."""
    same = baseline_predictor(SCORING)  # deterministic: identical output both runs
    res = ablation("dead", full=same, ablated=same, frame=frame, scoring=SCORING)
    assert res.verdict == NEUTRAL
    assert not res.significant
    assert res.p_value == pytest.approx(1.0)


def test_ablation_detects_helpful_component(frame):
    """Removing a component that sharply worsens accuracy is flagged HELPS."""
    full = _accurate_predictor(noise=1.0, seed=2)      # with the component: accurate
    ablated = _accurate_predictor(noise=30.0, seed=3)  # without it: much worse
    res = ablation("real", full=full, ablated=ablated, frame=frame, scoring=SCORING)
    assert res.verdict == HELPS
    assert res.delta > 0 and res.significant


def test_ablation_flags_harmful_component(frame):
    """A component that makes things worse is flagged HURTS (and is not truthy)."""
    full = _accurate_predictor(noise=30.0, seed=4)     # with it: bad
    ablated = _accurate_predictor(noise=1.0, seed=5)   # without it: good
    res = ablation("harmful", full=full, ablated=ablated, frame=frame, scoring=SCORING)
    assert res.verdict == HURTS
    assert not res


# ── no_regression: a regressed model trips false ──────────────────────────────
def test_no_regression_passes_for_strong_model(frame):
    good = _accurate_predictor(noise=1.0, seed=6)
    result = no_regression(good, frame=frame, scoring=SCORING)  # vs shrink-to-mean baseline
    assert result and result.passed


def test_regressed_model_trips_no_regression_false(frame):
    reference = _accurate_predictor(noise=1.0, seed=7)  # strong incumbent
    regressed = _const_predictor(0.0)                   # predicts zero for everyone
    result = no_regression(
        regressed, frame=frame, reference=reference, scoring=SCORING
    )
    assert not result
    assert result.candidate_mae > result.reference_mae


# ── stress scenarios run and stay finite ──────────────────────────────────────
def test_stress_scenarios_run(frame):
    pred = baseline_predictor(SCORING)
    results = run_stress(pred, frame, scoring=SCORING)
    assert set(results) == {"all_injury_week", "weather_disaster", "outlier_season"}
    for res in results.values():
        assert res.finite and not res.bad
        assert np.isfinite(res.mae)


# ── feature-drift alarm ───────────────────────────────────────────────────────
def test_drift_alarm_fires_on_shift(frame):
    ref = frame[frame["season"] <= 2015]
    shifted = frame[frame["season"] <= 2015].copy()
    shifted["yards"] = shifted["yards"] * 3.0 + 200.0  # large distribution shift
    alarms = scan_drift(ref, shifted, features=["yards"])
    assert alarms["yards"].drifted
    # a frame against itself does not drift
    quiet = scan_drift(ref, ref, features=["yards", "opportunities"])
    assert not any(a.drifted for a in quiet.values())


# ── benchmark board keyed to a version tuple ──────────────────────────────────
def test_benchmark_board_records_and_compares(frame, tmp_path):
    board = BenchmarkBoard(tmp_path)
    fp = fantasypros_predictor(
        frame.assign(proj_points=points_of(frame, WEIGHTS) + 5.0)[
            ["player_id", "season", "proj_points"]
        ]
    )
    entry = board.record_run(
        version="abc123def456",
        model=_accurate_predictor(noise=1.0, seed=8),
        frame=frame,
        fantasypros=fp,
        scoring=SCORING,
    )
    assert entry.version == "abc123def456"
    assert entry.beats_fantasypros is True  # accurate model clears the padded FP line
    assert board.latest("abc123def456") is not None
    assert len(board.entries()) == 1


# ── integration: the real hierarchical engine as a predictor ──────────────────
def test_engine_predictor_walk_forward(frame):
    """The real projector, wired through the harness, produces finite held-out error."""
    small = frame[frame["team"] == "T0"].copy()
    pred = engine_predictor(
        scoring=SCORING, num_warmup=150, num_samples=150, num_chains=1
    )
    report = walk_forward(
        small, pred, scoring=SCORING, time_col="season", min_train_periods=4
    )
    assert report.n_obs > 0
    assert np.isfinite(report.mae)
