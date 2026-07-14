"""Tests for E3-mc-core — the correlated Monte-Carlo simulation core.

Fast + deterministic (numpy RNG, no NUTS). Covers: the correlation matrix (factor/rule
signs + PSD validity), the Gaussian-copula sampler recovering a planted QB↔WR stack
correlation, the *streaming* reduction being memory-bounded (peak independent of run count
+ auto-degrade / cloud-burst), the per-player outputs (finish tiers / boom / bust / ADP),
projection-preservation via the E7 `no_regression` gate, and E7 `calibrated` on the sim's
marginals. Also the snapshot hand-off (corr_matrix + mc_probs populated + round-tripped).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from blitz_engine.backtest import baseline_predictor, no_regression, points_of
from blitz_engine.calibration import calibrated
from blitz_engine.projection.families import ScoringWeights
from blitz_engine.projection.inference import Projection
from blitz_engine.simulation import (
    SimConfig,
    build_correlation,
    cholesky_factor,
    nearest_psd_correlation,
    sample_correlated,
    simulate,
    simulate_projection,
    to_snapshot,
)
from blitz_engine.snapshot import Snapshot


# ── fixtures ────────────────────────────────────────────────────────────────────
def make_slate(seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A structured one-week slate: 4 games, each team QB/RB/WR×2/TE + DST, with opponents."""
    rng = np.random.default_rng(seed)
    rows = []
    for g in range(4):
        a, b = f"A{g}", f"B{g}"
        for team, opp in ((a, b), (b, a)):
            for pos, n in (("QB", 1), ("RB", 1), ("WR", 2), ("TE", 1), ("DST", 1)):
                for k in range(n):
                    base = {"QB": 300, "RB": 200, "WR": 170, "TE": 110, "DST": 90}[pos]
                    rows.append({
                        "player_id": f"{team}_{pos}{k}",
                        "position": pos, "team": team, "opponent": opp,
                        "mean": base * float(rng.uniform(0.6, 1.4)),
                    })
    players = pd.DataFrame(rows)
    players["stdev"] = np.maximum(players["mean"] * 0.35, 3.0)
    marginals = players[["player_id", "mean", "stdev"]].copy()
    meta = players[["player_id", "position", "team", "opponent"]].copy()
    return marginals, meta


# ── correlation structure ───────────────────────────────────────────────────────
def test_correlation_signs_and_validity() -> None:
    players = pd.DataFrame({
        "player_id": ["qA", "wA", "rA", "qB", "dA"],
        "position": ["QB", "WR", "RB", "QB", "DST"],
        "team": ["A", "A", "A", "B", "A"],
        "opponent": ["B", "B", "B", "A", "B"],
    })
    c = build_correlation(players)
    # QB stacks its WR positively; the RB (pass-vs-run) goes the other way.
    assert c.loc["qA", "wA"] > 0.15
    assert c.loc["qA", "rA"] < 0.0
    # game-stack: opposing QBs positively correlated (shootout).
    assert c.loc["qA", "qB"] > 0.0
    # DST vs the opposing offense: negative (script).
    assert c.loc["dA", "qB"] < 0.0
    # valid correlation matrix: symmetric, unit diagonal, PSD.
    m = c.to_numpy()
    assert np.allclose(m, m.T)
    assert np.allclose(np.diag(m), 1.0)
    assert np.linalg.eigvalsh(m).min() > -1e-8


def test_nearest_psd_fixes_indefinite() -> None:
    bad = np.array([[1.0, 0.9, -0.9], [0.9, 1.0, 0.9], [-0.9, 0.9, 1.0]])
    fixed = nearest_psd_correlation(bad)
    assert np.linalg.eigvalsh(fixed).min() >= -1e-10
    assert np.allclose(np.diag(fixed), 1.0)


def test_degrade_neutral_unknown_position_is_independent() -> None:
    # An unknown position and a player with no opponent → zero off-diagonal, still valid.
    players = pd.DataFrame({
        "player_id": ["qA", "xA"],
        "position": ["QB", "LS"],  # LS not a modelled position
        "team": ["A", "A"],
    })
    c = build_correlation(players)
    assert abs(c.loc["qA", "xA"]) < 1e-9
    assert np.linalg.eigvalsh(c.to_numpy()).min() > -1e-8


# ── the Gaussian-copula sampler recovers a planted stack correlation ─────────────
def test_qb_wr_stack_correlation_recovered() -> None:
    corr = np.array([[1.0, 0.6], [0.6, 1.0]])
    chol = cholesky_factor(corr)
    rng = np.random.default_rng(1)
    draws = sample_correlated(
        np.array([18.0, 14.0]), np.array([6.0, 5.0]), chol, 80_000, rng
    )
    recovered = float(np.corrcoef(draws.T)[0, 1])
    # positive stack variance recovered (mild attenuation from the zero-clip is fine).
    assert 0.45 < recovered < 0.72


# ── per-player outputs ───────────────────────────────────────────────────────────
def test_outputs_shape_and_probabilities() -> None:
    marg, meta = make_slate()
    adp = {pid: i % 12 + 1 for i, pid in enumerate(meta["player_id"])}
    res = simulate(marg, meta, config=SimConfig(n_runs=20_000, batch_size=5_000), adp=adp)
    out = res.outputs
    assert len(out) == len(marg)
    prob_cols = ["top3", "top5", "top10", "top12", "bust_pct", "boom_pct", "beats_adp"]
    for col in prob_cols:
        v = out[col].to_numpy()
        assert np.all((v >= -1e-9) & (v <= 1 + 1e-9))
    # finish tiers are nested: P(top3) ≤ P(top5) ≤ P(top10) ≤ P(top12).
    assert (out["top3"] <= out["top5"] + 1e-9).all()
    assert (out["top5"] <= out["top10"] + 1e-9).all()
    assert (out["top10"] <= out["top12"] + 1e-9).all()
    # median ± 95 % ordered.
    assert (out["p2_5"] <= out["median"] + 1e-9).all()
    assert (out["median"] <= out["p97_5"] + 1e-9).all()


def test_projection_preserving_mean() -> None:
    # The sim adds distributional signal without moving the point estimate.
    marg, meta = make_slate()
    res = simulate(marg, meta, config=SimConfig(n_runs=10_000))
    got = res.outputs.set_index("player_id")["mean"]
    want = marg.set_index("player_id")["mean"]
    assert np.allclose(got.loc[want.index].to_numpy(), want.to_numpy())


# ── memory-bounded streaming reduction ───────────────────────────────────────────
def test_streaming_peak_independent_of_run_count() -> None:
    from blitz_engine.simulation.mc import _plan_batch

    marg, meta = make_slate()
    cfg_small = SimConfig(n_runs=10_000, batch_size=5_000)
    cfg_large = SimConfig(n_runs=1_000_000, batch_size=5_000)
    small = simulate(marg, meta, config=cfg_small)
    # 100× the runs, same batch: the estimated peak is a function of batch+P only, so it is
    # identical — proof the reduction streams and never materialises n_runs × P.
    b1, p1, _ = _plan_batch(len(marg), cfg_small)
    b2, p2, _ = _plan_batch(len(marg), cfg_large)
    assert (b1, p1) == (b2, p2)
    assert small.within_budget


def test_scaled_run_stays_bounded_and_completes() -> None:
    # A genuinely scaled run (500k draws) must complete and stay within the budget.
    marg, meta = make_slate()
    res = simulate(marg, meta, config=SimConfig(n_runs=500_000, batch_size=10_000))
    assert res.n_runs == 500_000
    assert res.within_budget
    # peak is one batch + the P×P factor — kilobytes-to-megabytes, never 500k×P.
    naive = 500_000 * len(marg) * 4
    assert res.peak_bytes < naive


def test_tiny_budget_degrades_batch_and_flags_cloud_burst() -> None:
    marg, meta = make_slate()
    # A budget too small for the requested batch forces a degrade + cloud-burst suggestion.
    tiny = SimConfig(n_runs=50_000, batch_size=40_000, min_batch=500,
                     memory_budget_bytes=100_000)
    res = simulate(marg, meta, config=tiny)
    assert res.batch_size < 40_000
    assert res.cloud_burst_suggested


# ── E7 gates: projection-preservation (no_regression) + calibration ──────────────
def _mc_predictor(scoring: dict | None = None):
    weights = ScoringWeights.from_scoring(scoring or {})

    def predict(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
        tr = train.copy()
        tr["_pts"] = points_of(tr, weights)
        pos_mean = tr.groupby(tr["position"].astype(str))["_pts"].mean()
        overall = float(tr["_pts"].mean())
        m = np.array([float(pos_mean.get(p, overall)) for p in test["position"].astype(str)])
        pid = test["player_id"].astype(str).to_numpy()
        marg = pd.DataFrame({"player_id": pid, "mean": m, "stdev": np.maximum(m * 0.3, 1.0)})
        players = pd.DataFrame({"player_id": pid, "position": test["position"].astype(str),
                                "team": "AAA"})
        res = simulate(marg, players, config=SimConfig(n_runs=2_000, batch_size=1_000))
        by = res.outputs.set_index("player_id")["mean"]
        return np.array([float(by.get(p, overall)) for p in pid])

    return predict


def make_points_frame() -> pd.DataFrame:
    rows = []
    for season in (2021, 2022, 2023):
        for pid, pos, base in [("q1", "QB", 300.0), ("r1", "RB", 200.0),
                               ("w1", "WR", 180.0), ("w2", "WR", 150.0), ("t1", "TE", 120.0)]:
            rows.append({"player_id": pid, "position": pos, "team": "AAA", "season": season,
                         "week": 1, "team_plays": 65.0, "opportunities": 15.0,
                         "yards": base, "tds": 1.0})
    return pd.DataFrame(rows)


def test_no_regression_projection_preserving() -> None:
    # The MC layer feeds through the same point estimate as the baseline → never regresses.
    frame = make_points_frame()
    verdict = no_regression(
        _mc_predictor(), frame=frame, reference=baseline_predictor(), tolerance=0.02
    )
    assert bool(verdict)


def test_outputs_calibrated() -> None:
    # Realised outcomes drawn from the sim's own marginals ⇒ E7 `calibrated` passes.
    rng = np.random.default_rng(7)
    p = 800
    mean = rng.uniform(4.0, 30.0, p)
    sd = rng.uniform(3.0, 9.0, p)
    marg = pd.DataFrame({"player_id": [f"p{i}" for i in range(p)], "mean": mean, "stdev": sd})
    meta = pd.DataFrame({"player_id": marg["player_id"], "position": "WR", "team": "AAA"})
    res = simulate(marg, meta, config=SimConfig(n_runs=2_000, batch_size=2_000))
    realized = np.clip(rng.normal(mean, sd), 0.0, None)
    assert calibrated(res.outputs, realized)


# ── snapshot hand-off ────────────────────────────────────────────────────────────
def _hand_projection(marg: pd.DataFrame) -> Projection:
    q = marg.rename(columns={}).copy()
    q["week"] = 1
    empty = pd.DataFrame()
    return Projection(quantiles=q, shares=empty, opportunity=empty, efficiency=empty,
                      convergence=None)  # type: ignore[arg-type]


def test_to_snapshot_populates_corr_and_mc(tmp_path) -> None:
    marg, meta = make_slate()
    proj = _hand_projection(marg)
    res = simulate_projection(proj, meta, config=SimConfig(n_runs=5_000, batch_size=5_000))
    snap = to_snapshot(proj, res)
    assert isinstance(snap, Snapshot)
    assert not snap.corr_matrix.empty
    assert not snap.mc_probs.empty
    assert snap.corr_matrix.shape[0] == len(marg)
    # full round-trip through the versioned bundle.
    snap.write(tmp_path / "snap")
    back = Snapshot.read(tmp_path / "snap")
    assert back.corr_matrix.shape == snap.corr_matrix.shape
    assert list(back.mc_probs.columns) == list(snap.mc_probs.columns)
