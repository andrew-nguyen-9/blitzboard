"""Tests for E6-ensemble — stacked BMA blend, member roster, and market benchmark.

Most tests use cheap deterministic synthetic members (pure `(train, test) -> MemberPrediction`
functions, no NUTS) so the stacking / BMA / market machinery is exercised instantly; two
smoke tests run the real `gbm_member` (LightGBM absent → numpy GBRT fallback) and `nn_member`
(torch MLP) on a tiny frame to prove the wiring holds. The headline DoD checks live here:
BMA weights sum to 1, the blend beats every single member out-of-sample, it is calibratable
via E7, it clears `no_regression`, and it beats the market line.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from blitz_engine.backtest import (
    no_regression,
    points_of,
    walk_forward,
    walk_forward_splits,
)
from blitz_engine.calibration import calibrated, weekly_recalibration
from blitz_engine.ensemble import (
    CallableMember,
    MarketBenchmark,
    MemberPrediction,
    StackedEnsemble,
    bma_weights,
    gbm_member,
    market_edge,
    nn_member,
    quantiles_frame,
)
from blitz_engine.ensemble.members import _crc_u01
from blitz_engine.projection.families import ScoringWeights

SCORING = {
    "receiving": {"pt_per_yd": 0.1, "ppr": 0.5, "td": 6},
    "rushing": {"pt_per_yd": 0.1, "td": 6},
}
WEIGHTS = ScoringWeights.from_scoring(SCORING)


def make_seasons(seasons=None, weeks=3, teams=6, per_team=6, seed=0) -> pd.DataFrame:
    """Multi-season synthetic league; player identities + talent persist across seasons."""
    seasons = range(2014, 2020) if seasons is None else seasons
    rng = np.random.default_rng(seed)
    cycle = ["WR", "WR", "RB", "TE", "WR", "RB"]
    talent = {}
    rows = []
    for t in range(teams):
        for p in range(per_team):
            talent[(t, p)] = (
                np.exp(rng.normal(0.0, 0.5)),
                np.exp(rng.normal(1.9, 0.2)),
                rng.uniform(0.02, 0.08),
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


def gaussian_member(name: str, sigma: float, salt: int) -> CallableMember:
    """A calibrated member: mean = actual + deterministic Gaussian(0, σ), reported stdev = σ.

    Pure in (train, test) — the same rows always yield the same forecast — so the ensemble and
    a standalone evaluation see identical draws (deterministic comparison). Distinct `salt`
    values decorrelate members, which is exactly what lets averaging reduce error.
    """

    def fn(train: pd.DataFrame, test: pd.DataFrame) -> MemberPrediction:
        y = np.asarray(points_of(test, WEIGHTS), dtype=np.float64)
        u = np.array([
            _crc_u01(f"{p}:{t}:{salt}")
            for p, t in zip(test["player_id"], test["season"], strict=True)
        ])
        eps = stats.norm.ppf(np.clip(u, 1e-4, 1 - 1e-4)) * sigma
        return MemberPrediction(mean=y + eps, stdev=np.full(len(test), sigma))

    return CallableMember(name, fn)


def market_projections(frame: pd.DataFrame, *, bias: float, noise_salt: int) -> pd.DataFrame:
    """A per-(player, season) consensus line: actual points + a systematic bias (weak market)."""
    d = frame.copy()
    d["_pts"] = points_of(d, WEIGHTS)
    agg = d.groupby(["player_id", "season"])["_pts"].mean().reset_index()
    jitter = np.array([
        _crc_u01(f"{p}:{s}:{noise_salt}")
        for p, s in zip(agg["player_id"], agg["season"], strict=True)
    ])
    agg["proj_points"] = agg["_pts"] + bias + (jitter - 0.5) * 2 * bias
    return agg[["player_id", "season", "proj_points"]]


# ── BMA weights: sum to 1, ordered by skill ───────────────────────────────────
def test_bma_weights_sum_to_one(frame):
    members = [gaussian_member("a", 6.0, 1), gaussian_member("b", 6.0, 2)]
    w = bma_weights(members, frame, scoring=SCORING)
    assert set(w) == {"a", "b"}
    assert sum(w.values()) == pytest.approx(1.0)
    assert all(v >= 0 for v in w.values())


def test_bma_favours_the_more_skilful_member(frame):
    sharp = gaussian_member("sharp", 3.0, 10)   # low noise, higher OOS log-score
    fuzzy = gaussian_member("fuzzy", 20.0, 11)   # high noise
    w = bma_weights([sharp, fuzzy], frame, scoring=SCORING)
    assert w["sharp"] > w["fuzzy"]
    assert sum(w.values()) == pytest.approx(1.0)


# ── the blend beats any single member out-of-sample (block-release core) ───────
def test_ensemble_beats_any_single_member(frame):
    members = [
        gaussian_member("a", 8.0, 1),
        gaussian_member("b", 8.0, 2),
        gaussian_member("c", 8.0, 3),
    ]
    ens = StackedEnsemble(members=members, scoring=SCORING)
    folds = walk_forward_splits(frame, time_col="season")
    ens_mae = walk_forward(frame, ens.as_predictor(), scoring=SCORING, splits=folds).mae
    member_maes = [
        walk_forward(frame, m.as_predictor(), scoring=SCORING, splits=folds).mae for m in members
    ]
    assert ens_mae < min(member_maes)  # decorrelated members → averaging wins


# ── calibration (E7): the mixture is calibratable ─────────────────────────────
def _pool_oos(ens: StackedEnsemble, frame: pd.DataFrame):
    """Pool the ensemble's held-out forecasts across all folds (large-n calibration sample)."""
    folds = walk_forward_splits(frame, time_col="season")
    mu, sd, y = [], [], []
    for sp in folds:
        pred = ens.predict(sp.train, sp.test)
        mu.append(pred.mean)
        sd.append(pred.stdev)
        y.append(np.asarray(points_of(sp.test, WEIGHTS), dtype=np.float64))
    q = quantiles_frame(MemberPrediction(np.concatenate(mu), np.concatenate(sd)))
    return q, np.concatenate(y)


def test_single_calibrated_member_ensemble_is_calibrated(frame):
    """A calibrated member, blended alone, stays calibrated end-to-end through `quantiles()`."""
    ens = StackedEnsemble(members=[gaussian_member("solo", 7.0, 42)], scoring=SCORING)
    q, y = _pool_oos(ens, frame)
    assert calibrated(q, y)  # KS(PIT, uniform) within the E7 gate over the pooled fold rows


def test_blend_underconfidence_is_fixed_by_e7_recalibration(frame):
    """Averaging independent calibrated members is under-confident; E7 recal sharpens it back."""
    members = [gaussian_member(n, 7.0, s) for n, s in [("a", 1), ("b", 2), ("c", 3)]]
    ens = StackedEnsemble(members=members, scoring=SCORING)
    q, y = _pool_oos(ens, frame)
    wk = weekly_recalibration(q, y, method="beta", gentle=1.0)
    assert wk.improved  # damped recal lowered the calibration error
    assert wk.after.metrics.calibration_error <= wk.before.metrics.calibration_error


# ── release gate + market edge ────────────────────────────────────────────────
def test_ensemble_clears_no_regression(frame):
    members = [gaussian_member("a", 6.0, 1), gaussian_member("b", 6.0, 2)]
    ens = StackedEnsemble(members=members, scoring=SCORING)
    assert no_regression(ens.as_predictor(), frame=frame, scoring=SCORING)


def test_market_benchmark_member_and_edge(frame):
    proj = market_projections(frame, bias=12.0, noise_salt=99)  # a biased, weak market line
    market = MarketBenchmark(proj)
    members = [gaussian_member("a", 6.0, 1), gaussian_member("b", 6.0, 2), market.member()]
    ens = StackedEnsemble(members=members, scoring=SCORING)

    edge = market.edge_of(ens.as_predictor(), frame, scoring=SCORING)
    assert edge.beats_market and edge  # we learn an edge over the consensus
    assert edge.edge == pytest.approx(edge.market_mae - edge.ensemble_mae)

    # the market is also a plain benchmark predictor
    direct = market_edge(ens.as_predictor(), market.predictor(), frame, scoring=SCORING)
    assert direct.market_mae == pytest.approx(edge.market_mae)


# ── real members run (LightGBM absent → numpy GBRT; torch MLP) ─────────────────
def _one_split(frame):
    return walk_forward_splits(frame, time_col="season")[-1]


def test_gbm_member_runs_and_is_finite(frame):
    sp = _one_split(frame)
    pred = gbm_member(SCORING).predict(sp.train, sp.test)
    assert pred.mean.shape == (len(sp.test),)
    assert np.isfinite(pred.mean).all() and np.isfinite(pred.stdev).all()
    assert (pred.stdev > 0).all()


def test_nn_member_runs_and_is_finite(frame):
    sp = _one_split(frame)
    pred = nn_member(SCORING, epochs=60).predict(sp.train, sp.test)
    assert pred.mean.shape == (len(sp.test),)
    assert np.isfinite(pred.mean).all() and np.isfinite(pred.stdev).all()


def test_real_member_roster_bma_weights_sum_to_one(frame):
    proj = market_projections(frame, bias=3.0, noise_salt=7)
    members = [gbm_member(SCORING), nn_member(SCORING, epochs=60), MarketBenchmark(proj).member()]
    w = bma_weights(members, frame, scoring=SCORING)
    assert set(w) == {"gbm", "nn", "market"}
    assert sum(w.values()) == pytest.approx(1.0)
