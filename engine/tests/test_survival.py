"""Tests for E2-survival — injury/availability hazard → P(available) + redistribution.

Fast + deterministic: the discrete-time hazard is scipy logistic regression on person-period
data (no NUTS, no lifelines). Covers the hazard fit recovering signal, the time-varying
recurrence covariate, the injury-report/suspension overrides, the P(available) multiply into
projections, the KNOWN starter-out redistribution case, the degrade path, and the E7
no-regression / ablation gates (over cheap predictors — no NUTS in the harness).
"""
from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from blitz_engine.backtest import HELPS, ablation, baseline_predictor, no_regression, points_of
from blitz_engine.projection.families import ScoringWeights
from blitz_engine.projection.inference import Projection
from blitz_engine.survival import (
    STATUS_P,
    AvailabilityModel,
    DiscreteTimeHazard,
    apply_availability,
    redistribute_shares,
    scale_quantiles,
)

Predictor = Callable[[pd.DataFrame, pd.DataFrame], np.ndarray]


# ── synthetic data ─────────────────────────────────────────────────────────────
def make_injury_history(seed: int = 0) -> pd.DataFrame:
    """Sequential per-player-week `out` events drawn from a KNOWN hazard so the fit can
    recover it. True logit rises with age, workload, and — the recurrence term — a recent
    out, generated week-by-week so `recent_injury` is genuinely time-varying."""
    rng = np.random.default_rng(seed)
    rows = []
    for pid in range(60):
        pos = "RB" if pid % 2 else "WR"
        age = float(rng.uniform(22, 33))
        workload = float(rng.uniform(6, 26))
        recent = 0.0
        for season in (2022, 2023):
            for wk in range(1, 15):
                logit = (
                    -3.0
                    + 0.12 * (age - 27.0)
                    + 0.06 * (workload - 16.0)
                    + 2.0 * recent  # recurrence: a recent out raises this week's hazard
                )
                out = int(rng.random() < 1.0 / (1.0 + np.exp(-logit)))
                rows.append({
                    "player_id": f"p{pid}", "position": pos, "season": season,
                    "week": wk, "age": age, "opportunities": workload, "out": out,
                })
                recent = 1.0 if out else recent * 0.5  # decaying recent-injury state
    return pd.DataFrame(rows)


def make_value_frame() -> pd.DataFrame:
    """Multi-season points frame for the E7 harness; OUT players score 0 in their test week."""
    rows = []
    for season in (2021, 2022, 2023):
        for week in (1, 2, 3):
            for pid, pos, base in [
                ("wr1", "WR", 90.0), ("wr2", "WR", 70.0), ("wr3", "WR", 50.0),
                ("rb1", "RB", 80.0), ("rb2", "RB", 60.0), ("rb3", "RB", 40.0),
            ]:
                # wr3 + rb3 are ruled OUT in the later (test) seasons: real points 0
                out = season >= 2022 and pid in {"wr3", "rb3"}
                rows.append({
                    "player_id": pid, "position": pos, "team": "AAA",
                    "season": season, "week": week, "team_plays": 65.0,
                    "opportunities": 0.0 if out else 15.0,
                    "yards": 0.0 if out else base, "tds": 0.0 if out else 0.5,
                    "status": "OUT" if out else "ACTIVE",
                })
    return pd.DataFrame(rows)


def make_projection() -> Projection:
    """A hand-built Projection (no NUTS) with a two-team share table for redistribution."""
    quantiles = pd.DataFrame({
        "player_id": ["s", "b1", "b2", "u1"],
        "week": [1, 1, 1, 1],
        "mean": [12.0, 6.0, 2.0, 8.0],
        "floor": [8.0, 4.0, 1.0, 5.0],
        "ceiling": [18.0, 9.0, 4.0, 12.0],
    })
    shares = pd.DataFrame({
        "player_id": ["s", "b1", "b2", "u1"],
        "team": ["T", "T", "T", "U"],
        "share": [0.6, 0.3, 0.1, 1.0],
        "dirichlet_alpha": [6.0, 3.0, 1.0, 5.0],
    })
    empty = pd.DataFrame()
    return Projection(
        quantiles=quantiles, shares=shares, opportunity=empty, efficiency=empty,
        convergence=None,  # type: ignore[arg-type]
    )


# ── hazard model ────────────────────────────────────────────────────────────────
def test_hazard_fits_and_recovers_covariate_signal() -> None:
    haz = DiscreteTimeHazard().fit(make_injury_history())
    assert haz.fitted
    # an older, high-workload profile carries more hazard than a young, low-workload one
    old_heavy = pd.DataFrame({
        "player_id": ["x"], "position": ["RB"], "week": [1],
        "age": [32.0], "opportunities": [25.0], "out": [0],
    })
    young_light = pd.DataFrame({
        "player_id": ["y"], "position": ["RB"], "week": [1],
        "age": [23.0], "opportunities": [7.0], "out": [0],
    })
    assert haz.predict_hazard(old_heavy)[0] > haz.predict_hazard(young_light)[0]


def test_recurrence_covariate_present_and_raises_hazard() -> None:
    """The time-varying recurrence covariate exists and a recent out lifts current hazard."""
    haz = DiscreteTimeHazard().fit(make_injury_history())
    assert "recent_injury" in haz.feature_names
    assert haz.beta[haz.feature_names.index("recent_injury")] > 0  # recurrence ⇒ +hazard

    # end-to-end: same player, trailing weeks either injured or healthy → higher current hazard
    def trail(outs: list[int]) -> pd.DataFrame:
        return pd.DataFrame({
            "player_id": ["z"] * len(outs), "position": ["WR"] * len(outs),
            "week": list(range(1, len(outs) + 1)), "age": [27.0] * len(outs),
            "opportunities": [15.0] * len(outs), "out": outs,
        })

    injured = haz.predict_hazard(trail([1, 1, 1, 1, 0]))[-1]
    healthy = haz.predict_hazard(trail([0, 0, 0, 0, 0]))[-1]
    assert injured > healthy


# ── availability: report status + suspension + degrade ───────────────────────────
def test_status_and_suspension_override() -> None:
    model = AvailabilityModel()  # unfitted → base neutral 1.0
    frame = pd.DataFrame({
        "player_id": ["a", "b", "c", "d", "e"],
        "status": ["ACTIVE", "OUT", "QUESTIONABLE", "DOUBTFUL", "ACTIVE"],
        "suspended": [False, False, False, False, True],
    })
    p = model.p_available(frame)
    assert p["a"] == 1.0
    assert p["b"] == 0.0  # OUT
    assert p["c"] == STATUS_P["QUESTIONABLE"] == 0.5
    assert p["d"] == STATUS_P["DOUBTFUL"]
    assert p["e"] == 0.0  # suspension wins even over an ACTIVE status


def test_degrade_safe_without_injury_data() -> None:
    """No `out` history ⇒ hazard unfitted; no status/suspended cols ⇒ P(available)=1.0."""
    haz = DiscreteTimeHazard().fit(
        pd.DataFrame({"player_id": ["a", "b"], "position": ["WR", "RB"],
                      "age": [25.0, 26.0], "opportunities": [10.0, 12.0]})
    )
    assert not haz.fitted
    model = AvailabilityModel(hazard=haz)
    frame = pd.DataFrame({"player_id": ["a", "b"], "position": ["WR", "RB"]})
    p = model.p_available(frame)
    assert np.allclose(p.to_numpy(), 1.0)


# ── multiply into projection ─────────────────────────────────────────────────────
def test_scale_quantiles_multiplies_availability() -> None:
    q = make_projection().quantiles
    scaled = scale_quantiles(q, {"s": 0.5, "b1": 0.0})
    assert scaled.loc[scaled.player_id == "s", "mean"].item() == 6.0  # 12 * 0.5
    assert scaled.loc[scaled.player_id == "s", "ceiling"].item() == 9.0
    assert scaled.loc[scaled.player_id == "b1", "mean"].item() == 0.0
    assert scaled.loc[scaled.player_id == "u1", "mean"].item() == 8.0  # absent → unscaled


# ── redistribution: the KNOWN starter-out case ──────────────────────────────────
def test_starter_out_redistributes_share_to_backups() -> None:
    shares = make_projection().shares
    out = redistribute_shares(shares, {"s": 0.0})  # starter fully out
    by_pid = out.set_index("player_id")["share"]
    assert by_pid["s"] == 0.0
    assert by_pid["b1"] > 0.3  # backup share UP (0.3 → 0.75)
    assert by_pid["b2"] > 0.1  # 0.1 → 0.25
    assert np.isclose(by_pid[["s", "b1", "b2"]].sum(), 1.0)  # team still normalised
    assert np.isclose(by_pid["u1"], 1.0)  # other team untouched


def test_partial_availability_sheds_share_continuously() -> None:
    shares = make_projection().shares
    out = redistribute_shares(shares, {"s": 0.5}).set_index("player_id")["share"]
    assert out["s"] < 0.6  # questionable starter sheds part of his usage
    assert out["b1"] > 0.3


def test_apply_availability_scales_and_redistributes() -> None:
    proj = make_projection()
    adjusted = apply_availability(proj, {"s": 0.0})
    # numbers scaled
    assert adjusted.quantiles.set_index("player_id").loc["s", "mean"] == 0.0
    # share redistributed
    assert adjusted.shares.set_index("player_id").loc["b1", "share"] > 0.3
    # input not mutated
    assert proj.shares.set_index("player_id").loc["b1", "share"] == 0.3


# ── E7 harness: no regression + ablation over cheap predictors (no NUTS) ─────────
def _availability_predictor(base: Predictor) -> Predictor:
    """Wrap a base predictor, multiplying in P(available) read off the test frame's status."""
    model = AvailabilityModel()  # unfitted: neutral except explicit report status

    def predict(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
        pts = base(train, test)
        p = model.p_available(test).to_numpy()  # row-aligned to test
        return pts * p

    return predict


def test_no_regression_with_availability() -> None:
    frame = make_value_frame()
    full = _availability_predictor(baseline_predictor())
    assert bool(no_regression(full, frame=frame))  # availability layer holds the line


def test_availability_helps_ablation() -> None:
    frame = make_value_frame()
    full = _availability_predictor(baseline_predictor())
    result = ablation(
        "availability", full=full, ablated=baseline_predictor(), frame=frame,
    )
    assert bool(result)  # not harmful
    assert result.delta >= 0
    assert result.verdict == HELPS  # zeroing OUT players' projections lowers error


def test_scoring_weights_available() -> None:
    # sanity: the harness scoring is the same vocabulary the survival layer scales
    w = ScoringWeights.from_scoring({})
    frame = make_value_frame()
    assert points_of(frame, w).shape[0] == len(frame)
