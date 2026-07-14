"""Tests for the E1-core hierarchical projection core.

Kept fast: NUTS runs on a tiny synthetic league with short chains. The hard-gate
correctness is proven deterministically on hand-crafted sample dicts (no reliance on
sampler stochasticity), plus a real degenerate fit that the gate must block.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from blitz_engine.projection import (
    FACTOR_BOUNDS,
    FAMILIES,
    ConvergenceError,
    HierarchicalProjector,
    ModelData,
    ScoringWeights,
    check,
    gate,
    walk_forward_compare,
)
from blitz_engine.projection.model import clamp_factor

# half-PPR-ish scoring for the tests
SCORING = {
    "receiving": {"pt_per_yd": 0.1, "ppr": 0.5, "td": 6},
    "rushing": {"pt_per_yd": 0.1, "td": 6},
}


def make_frame(seed: int = 0, weeks: int = 12, teams: int = 3, per_team: int = 5) -> pd.DataFrame:
    """Synthetic player-week league: per-player usage share + efficiency + TD rate,
    with meaningful per-week team-play variation so the structural engine has real signal."""
    rng = np.random.default_rng(seed)
    cycle = ["WR", "WR", "RB", "TE", "RB"]
    rows = []
    for t in range(teams):
        appeal = rng.normal(0.0, 0.6, per_team)
        share = np.exp(appeal)
        share /= share.sum()
        ypo = np.exp(rng.normal(1.9, 0.25, per_team))
        tdr = rng.uniform(0.02, 0.08, per_team)
        pids = [f"T{t}_P{p}" for p in range(per_team)]
        poss = [cycle[p % len(cycle)] for p in range(per_team)]
        for wk in range(1, weeks + 1):
            plays = max(float(rng.normal(65, 12)), 40.0)
            for p in range(per_team):
                opp = int(rng.poisson(plays * share[p]))
                yards = float(rng.gamma(6.0, (opp * ypo[p]) / 6.0)) if opp > 0 else 0.0
                tds = int(rng.poisson(opp * tdr[p]))
                rows.append({
                    "player_id": pids[p], "position": poss[p], "team": f"T{t}",
                    "week": wk, "team_plays": plays, "opportunities": opp,
                    "yards": yards, "tds": tds,
                })
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def fitted():
    frame = make_frame(seed=1)
    data = ModelData.from_frame(frame)
    proj = HierarchicalProjector(scoring=SCORING)
    report = proj.fit(data, num_warmup=400, num_samples=400, num_chains=2, enforce_gate=False)
    return proj, data, report


# ── families / scoring ────────────────────────────────────────────────────────
def test_scoring_weights_linear():
    w = ScoringWeights.from_scoring(SCORING)
    # 100 rec yards + 1 TD + 5 rec = 10 + 6 + 2.5
    assert w.points(yards=100.0, tds=1.0, receptions=5.0) == pytest.approx(18.5)
    # vectorised broadcast
    out = np.asarray(w.points(yards=np.array([10.0, 20.0]), tds=np.array([0.0, 1.0])))
    assert out.shape == (2,)


def test_families_registry_covers_every_stat_class():
    for stat in ("td", "receptions", "yards", "catch_rate", "share"):
        assert stat in FAMILIES
    d = FAMILIES["yards"](mean=np.array([10.0]), concentration=np.array([5.0]))
    assert float(d.mean[0]) == pytest.approx(10.0, rel=1e-4)


# ── convergence gate (deterministic) ──────────────────────────────────────────
def _good_samples() -> dict:
    rng = np.random.default_rng(0)
    return {"x": rng.normal(0, 1, size=(4, 500))}  # 4 chains agree


def _bad_samples() -> dict:
    # two chains with very different means → split-R-hat ≫ 1.01
    a = np.random.default_rng(1).normal(-5, 0.1, size=(1, 500))
    b = np.random.default_rng(2).normal(5, 0.1, size=(1, 500))
    return {"x": np.concatenate([a, b], axis=0)}


def test_gate_passes_converged():
    rep = gate(_good_samples())
    assert rep.passed and rep.rhat_max < 1.01


def test_gate_blocks_high_rhat():
    with pytest.raises(ConvergenceError):
        gate(_bad_samples())


def test_gate_blocks_divergences():
    with pytest.raises(ConvergenceError):
        gate(_good_samples(), n_divergences=1)


def test_check_reports_without_raising():
    rep = check(_bad_samples())
    assert not rep.passed and rep.rhat_max > 1.01


def test_real_degenerate_fit_is_blocked():
    """A real, under-sampled fit must trip the hard gate (ESS/R-hat)."""
    data = ModelData.from_frame(make_frame(seed=3, weeks=4))
    proj = HierarchicalProjector(scoring=SCORING)
    with pytest.raises(ConvergenceError):
        proj.fit(data, num_warmup=1, num_samples=4, num_chains=2, enforce_gate=True)


# ── fit + predict outputs ─────────────────────────────────────────────────────
def test_predict_shapes_and_ordering(fitted):
    proj, data, _ = fitted
    out = proj.predict(data)
    q = out.quantiles
    assert len(q) == data.n_obs
    # floor ≤ median ≤ ceiling, tails outside
    assert (q["p1"] <= q["floor"] + 1e-6).all()
    assert (q["floor"] <= q["p50"] + 1e-6).all()
    assert (q["p50"] <= q["ceiling"] + 1e-6).all()
    assert (q["ceiling"] <= q["p99"] + 1e-6).all()
    # uncertainty split is non-negative and totals sensibly
    assert (q["epistemic_sd"] >= 0).all() and (q["aleatoric_sd"] >= 0).all()
    assert (q["stdev"] >= 0).all()


def test_dirichlet_share_accessor(fitted):
    proj, data, _ = fitted
    out = proj.predict(data)
    shares = out.shares
    assert set(shares["player_id"]) == set(data.player_ids)
    # shares within each team sum to ~1, alphas strictly positive
    for _, grp in shares.groupby("team"):
        assert grp["share"].sum() == pytest.approx(1.0, abs=1e-4)
    assert (shares["dirichlet_alpha"] > 0).all()


def test_injury_redistribution_from_alpha(fitted):
    """E2 contract: zeroing an injured player's α renormalises the rest of his team."""
    proj, data, _ = fitted
    shares = proj.predict(data).shares
    team0 = shares[shares["team"] == "T0"].copy()
    alpha = team0["dirichlet_alpha"].to_numpy().copy()
    alpha[0] = 0.0  # injure player 0
    redistributed = alpha / alpha.sum()
    assert redistributed[0] == 0.0
    assert redistributed.sum() == pytest.approx(1.0)
    # a surviving teammate's share strictly grows
    assert redistributed[1] > team0["share"].to_numpy()[1]


def test_layers_separately_accessible(fitted):
    proj, data, _ = fitted
    out = proj.predict(data)
    assert (out.opportunity["mu_opportunity"] >= 0).all()
    assert (out.efficiency["yards_per_opp"] > 0).all()
    assert ((out.efficiency["td_rate"] > 0) & (out.efficiency["td_rate"] < 1)).all()


def test_draws_persist_to_store(fitted, tmp_path):
    from blitz_engine.store import ParquetStore

    proj, data, _ = fitted
    with ParquetStore.open(tmp_path) as store:
        out = proj.predict(data, store=store)
        assert out.draws_path is not None and out.draws_path.exists()
        assert "projection_draws" in store.tables()


# ── extension seams ───────────────────────────────────────────────────────────
def test_factor_hook_bounded_and_neutral(fitted):
    proj, data, _ = fitted

    class NeutralFactor:
        name = "neutral"

        def __call__(self, ctx):
            return np.ones(ctx.data.n_players)

    # neutral factor changes nothing structurally (log-multiplier is 0)
    seams = HierarchicalProjector(scoring=SCORING, factors=[NeutralFactor()])._resolve_seams(data)
    assert float(np.abs(np.asarray(seams.factor_log_opp)).max()) == 0.0
    # clamp respects bounds: a 10× request is capped at the upper bound
    capped = float(np.exp(clamp_factor(np.array(10.0), FACTOR_BOUNDS)))
    assert capped == pytest.approx(FACTOR_BOUNDS[1])


def test_talent_prior_hook_shifts_prior(fitted):
    from blitz_engine.projection.priors import TalentPrior

    proj, data, _ = fitted

    def hook(player_ids, stage, default_scale):
        loc = np.zeros(len(player_ids))
        loc[0] = 1.5  # boost one player's talent
        return TalentPrior(loc=loc, scale=np.full(len(player_ids), default_scale))

    seams = HierarchicalProjector(scoring=SCORING, talent_prior=hook)._resolve_seams(data)
    assert float(np.asarray(seams.talent_loc)[0]) == pytest.approx(1.5)


# ── minimal walk-forward no-regression ────────────────────────────────────────
def test_walk_forward_no_regression():
    frame = make_frame(seed=7, weeks=12)
    result = walk_forward_compare(
        frame, scoring=SCORING, num_warmup=300, num_samples=300, num_chains=2
    )
    assert result.n_players > 0
    assert result.no_regression, (
        f"engine MAE {result.engine_mae:.3f} regressed vs baseline {result.baseline_mae:.3f}"
    )
