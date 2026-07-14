"""Tests for the E6 feature layer — discovery, MI/entropy screening, dynamic per-season
importance, KL/JS drift alarms, and the degrade-neutral E1 factor bridge.

The estimator tests are deterministic on synthetic fixtures (fixed seeds); the single
no-regression test wires the importance factor back into the E1 core through a short NUTS
walk-forward and asserts the seam never makes the base fit worse.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from blitz_engine.features import (
    DriftMonitor,
    FeatureStore,
    ImportanceFactorHook,
    compute_importance,
    discover_features,
    feature_entropy,
    js_divergence,
    kl_divergence,
    mutual_information,
    screen_features,
)
from blitz_engine.projection import FACTOR_BOUNDS, HierarchicalProjector, ModelData
from blitz_engine.projection.model import FactorHook

SCORING = {
    "receiving": {"pt_per_yd": 0.1, "ppr": 0.5, "td": 6},
    "rushing": {"pt_per_yd": 0.1, "td": 6},
}


# ── fixtures ───────────────────────────────────────────────────────────────────
def informative_frame(n: int = 500, seed: int = 0) -> pd.DataFrame:
    """`sig` drives the target; `noise` is independent; `flat` is constant."""
    rng = np.random.default_rng(seed)
    sig = rng.normal(0.0, 1.0, n)
    noise = rng.normal(0.0, 1.0, n)
    target = 2.0 * sig + rng.normal(0.0, 0.3, n)
    return pd.DataFrame({
        "player_id": [f"p{i}" for i in range(n)],
        "sig": sig, "noise": noise, "flat": np.ones(n), "y": target,
    })


def league_frame(seed: int = 1, weeks: int = 12, teams: int = 3, per_team: int = 5) -> pd.DataFrame:
    """Synthetic player-week league (mirrors the E1 projection fixture)."""
    rng = np.random.default_rng(seed)
    cycle = ["WR", "WR", "RB", "TE", "RB"]
    rows = []
    for t in range(teams):
        share = np.exp(rng.normal(0.0, 0.6, per_team))
        share /= share.sum()
        ypo = np.exp(rng.normal(1.9, 0.25, per_team))
        tdr = rng.uniform(0.02, 0.08, per_team)
        for wk in range(1, weeks + 1):
            plays = max(float(rng.normal(65, 12)), 40.0)
            for p in range(per_team):
                opp = int(rng.poisson(plays * share[p]))
                yards = float(rng.gamma(6.0, (opp * ypo[p]) / 6.0)) if opp > 0 else 0.0
                rows.append({
                    "player_id": f"T{t}_P{p}", "position": cycle[p % 5], "team": f"T{t}",
                    "week": wk, "team_plays": plays, "opportunities": opp,
                    "yards": yards, "tds": int(rng.poisson(opp * tdr[p])),
                })
    return pd.DataFrame(rows)


# ── discovery ────────────────────────────────────────────────────────────────
def test_discovery_adds_pairwise_interactions():
    frame = informative_frame(n=100)
    fs = discover_features(frame, ["sig", "noise", "flat"], interactions=True)
    assert fs.n_rows == 100
    # 3 base + C(3,2)=3 interaction features
    assert fs.n_features == 6
    assert "sig x noise" in fs.names
    assert set(fs.index.columns) >= {"player_id"}


def test_discovery_no_interactions_is_just_base():
    fs = discover_features(informative_frame(n=50), ["sig", "noise"], interactions=False)
    assert fs.names == ["sig", "noise"]


# ── MI / entropy screening (DoD: informative ranked above noise) ─────────────
def test_mi_ranks_informative_feature_above_noise():
    frame = informative_frame(n=600, seed=3)
    fs = discover_features(frame, ["sig", "noise"], interactions=False)
    result = screen_features(fs, frame["y"].to_numpy())
    scores = result.scores()
    assert scores["sig"] > scores["noise"]
    assert result.selected[0] == "sig"  # informative feature ranked first


def test_mutual_information_zero_for_constant():
    x = np.ones(200)
    assert mutual_information(x, np.random.default_rng(0).normal(size=200)) == 0.0


def test_entropy_screen_drops_constant_feature():
    frame = informative_frame(n=300)
    fs = discover_features(frame, ["sig", "flat"], interactions=False)
    result = screen_features(fs, frame["y"].to_numpy())
    assert "flat" in result.dropped
    assert feature_entropy(fs.column("flat")) == 0.0
    assert "sig" in result.selected


# ── dynamic per-season importance ─────────────────────────────────────────────
def test_importance_shifts_across_seasons():
    """Feature importance is recomputed per season and can change year to year."""
    rng = np.random.default_rng(5)
    n = 400
    a_sig, a_noise = rng.normal(size=n), rng.normal(size=n)
    b_sig, b_noise = rng.normal(size=n), rng.normal(size=n)
    # season 2022: `sig` drives target; season 2023: `noise` drives it
    frame = pd.DataFrame({
        "player_id": [f"p{i}" for i in range(2 * n)],
        "season": [2022] * n + [2023] * n,
        "sig": np.concatenate([a_sig, b_sig]),
        "noise": np.concatenate([a_noise, b_noise]),
        "y": np.concatenate([2 * a_sig + rng.normal(0, .3, n), 2 * b_noise + rng.normal(0, .3, n)]),
    })
    fs = discover_features(frame, ["sig", "noise"], interactions=False)
    imp = compute_importance(fs, frame["y"].to_numpy(), seasons=frame["season"].to_numpy())
    assert imp.seasons() == [2022, 2023]
    assert imp.importance("sig", 2022) > imp.importance("noise", 2022)
    assert imp.importance("noise", 2023) > imp.importance("sig", 2023)
    # aggregate accessor + convex weights
    w = imp.weights(["sig", "noise"])
    assert pytest.approx(sum(w.values()), abs=1e-9) == 1.0


# ── KL / JS drift (DoD: alarm fires on a shifted fixture) ─────────────────────
def test_js_divergence_bounds():
    p = np.array([1.0, 0.0, 0.0])
    q = np.array([0.0, 0.0, 1.0])
    assert js_divergence(p, p) == pytest.approx(0.0, abs=1e-9)
    assert js_divergence(p, q) == pytest.approx(1.0, abs=1e-6)  # disjoint → 1 bit
    assert kl_divergence(p, p) == pytest.approx(0.0, abs=1e-9)


def test_drift_alarm_fires_on_shifted_fixture():
    rng = np.random.default_rng(7)
    ref = pd.DataFrame({"player_id": range(500), "x": rng.normal(0, 1, 500)})
    shifted = pd.DataFrame({"player_id": range(500), "x": rng.normal(3, 1, 500)})
    stable = pd.DataFrame({"player_id": range(500), "x": rng.normal(0, 1, 500)})

    ref_fs = discover_features(ref, ["x"], interactions=False, standardize=False)
    monitor = DriftMonitor.from_features(ref_fs, threshold=0.1)

    def fs(f: pd.DataFrame):
        return discover_features(f, ["x"], interactions=False, standardize=False)

    shifted_report = monitor.check(fs(shifted))
    stable_report = monitor.check(fs(stable))

    assert shifted_report.alarm and "x" in shifted_report.alarms
    assert shifted_report.max_divergence > stable_report.max_divergence
    assert not stable_report.alarm


# ── FeatureStore orchestrator + E1 factor bridge (degrade-neutral) ───────────
def test_feature_store_builds_full_pipeline():
    frame = league_frame(seed=2, weeks=6)
    store = FeatureStore.build(
        frame, base_cols=["team_plays", "opportunities", "yards"], target_col="yards",
    )
    assert store.selected  # some features survive screening
    assert isinstance(store.factor_hook, FactorHook)  # honours the E1 seam protocol
    weights = store.importance_weights()
    assert pytest.approx(sum(weights.values()), abs=1e-9) == 1.0
    # drift monitor round-trips on its own reference → no drift
    report = store.drift_monitor().check(store.features.select(store.selected))
    assert not report.alarm


def test_factor_hook_is_bounded_and_neutral_for_unknown_players():
    frame = league_frame(seed=2, weeks=6)
    data = ModelData.from_frame(frame)
    store = FeatureStore.build(
        frame, base_cols=["team_plays", "opportunities", "yards"], target_col="yards",
    )
    # resolved into the core, the factor stays inside FACTOR_BOUNDS (log scale)
    seams = HierarchicalProjector(scoring=SCORING, factors=[store.factor_hook])._resolve_seams(data)
    log_mult = np.abs(np.asarray(seams.factor_log_opp))
    assert log_mult.max() <= np.log(FACTOR_BOUNDS[1]) + 1e-6
    # a hook with no scores is exactly neutral (×1.0) for every player
    neutral = ImportanceFactorHook(name="empty", player_scores={})
    from blitz_engine.projection.model import FactorContext
    out = neutral(FactorContext(data=data, context={}))
    assert np.allclose(out, 1.0)


# ── no-regression: the factor seam never worsens the base fit (DoD) ──────────
def test_feature_factor_no_regression():
    """Wiring the importance factor back into the core keeps the walk-forward no-regression
    guarantee (the seam degrades neutral / bounded — E1's core safety invariant)."""
    from blitz_engine.projection import walk_forward_compare

    frame = league_frame(seed=7, weeks=12)
    train = frame[frame["week"] < int(frame["week"].max())]
    store = FeatureStore.build(
        train, base_cols=["team_plays", "opportunities", "yards"], target_col="yards", gain=0.1,
    )
    def make() -> HierarchicalProjector:
        return HierarchicalProjector(scoring=SCORING, factors=[store.factor_hook])

    result = walk_forward_compare(
        frame, scoring=SCORING, num_warmup=300, num_samples=300, num_chains=2,
        projector_factory=make,
    )
    assert result.n_players > 0
    assert result.no_regression, (
        f"feature-factor engine MAE {result.engine_mae:.3f} regressed vs {result.baseline_mae:.3f}"
    )
