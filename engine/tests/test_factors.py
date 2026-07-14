"""Tests for E1-factors — bounded, degrade-neutral multiplicative opportunity factors.

Fast + deterministic: no NUTS. We assert the seam contract directly on the factor arrays
(FACTOR_BOUNDS respected, context-free ⇒ every factor 1.0) and on the projector's seam
resolution (neutral context ⇒ zero log-multiplier). H2H is proven to DROP itself when its
signal fails the ablation-significance test and to fire when it passes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from blitz_engine.projection import (
    FACTOR_BOUNDS,
    FactorContext,
    FactorHook,
    HierarchicalProjector,
    ModelData,
)
from blitz_engine.projection.factors import (
    AltitudeDomeFactor,
    CoachingTendencyFactor,
    PaceFactor,
    PassRateFactor,
    SituationalFactor,
    TeamH2HFactor,
    WeatherFactor,
    default_factors,
)
from blitz_engine.projection.factors.ablation import is_significant

# one player per (team, position) is enough to exercise every branch
_ROWS = [
    ("den_qb", "QB", "DEN"), ("den_rb", "RB", "DEN"), ("den_wr", "WR", "DEN"),
    ("min_te", "TE", "MIN"), ("min_wr", "WR", "MIN"),
    ("buf_qb", "QB", "BUF"), ("buf_rb", "RB", "BUF"), ("buf_wr", "WR", "BUF"),
]


def _data() -> ModelData:
    rows = []
    for pid, pos, team in _ROWS:
        rows.append({
            "player_id": pid, "position": pos, "team": team, "week": 1,
            "team_plays": 65.0, "opportunities": 10.0, "yards": 60.0, "tds": 0.0,
        })
    return ModelData.from_frame(pd.DataFrame(rows))


def _ctx(**context: object) -> FactorContext:
    return FactorContext(data=_data(), context=dict(context))


ALL_FACTORS = [
    WeatherFactor(), AltitudeDomeFactor(), PaceFactor(), PassRateFactor(),
    CoachingTendencyFactor(), SituationalFactor(), TeamH2HFactor(),
]


# ── degrade-neutral: a context-free player ⇒ every factor = 1.0 ─────────────────
@pytest.mark.parametrize("factor", ALL_FACTORS, ids=lambda f: f.name)
def test_context_free_is_identity(factor):
    ctx = _ctx()
    out = np.asarray(factor(ctx))
    assert out.shape == (ctx.data.n_players,)
    assert np.allclose(out, 1.0), f"{factor.name} is not degrade-neutral with no context"


def test_every_factor_satisfies_the_hook_protocol():
    for f in ALL_FACTORS:
        assert isinstance(f, FactorHook)
        assert isinstance(f.name, str) and f.name


def test_default_factors_all_neutral_without_context():
    ctx = _ctx()
    for f in default_factors():
        assert np.allclose(np.asarray(f(ctx)), 1.0)


# ── each factor stays inside FACTOR_BOUNDS even on extreme context ──────────────
def test_all_factors_respect_bounds_on_extreme_context():
    lo, hi = FACTOR_BOUNDS
    ctx = _ctx(
        weather={"BUF": {"temp_f": -30, "wind_mph": 60, "precip": True, "horizon_days": 1}},
        venue_team={"DEN": "DEN", "MIN": "MIN"},
        team_pace={"BUF": 90.0, "DEN": 30.0},
        pass_rate={"BUF": 0.95, "DEN": 0.20},
        coaching={"BUF": {"pass_bias": 0.5}, "DEN": {"pass_bias": -0.5}},
        game_situation={"BUF": {"home": False, "travel_miles": 9000, "rest_days": 3,
                                "short_week": True}},
    )
    for f in default_factors():
        out = np.asarray(f(ctx))
        assert (out >= lo).all() and (out <= hi).all()


# ── weather: passing suppressed / rushing boosted + horizon shrink ─────────────
def test_weather_direction_and_horizon_shrink():
    bad = {"temp_f": 10, "wind_mph": 30, "precip": True}
    near = np.asarray(WeatherFactor()(_ctx(weather={"BUF": {**bad, "horizon_days": 1}})))
    far = np.asarray(WeatherFactor()(_ctx(weather={"BUF": {**bad, "horizon_days": 20}})))
    data = _data()
    idx = {pid: i for i, pid in enumerate(data.player_ids)}
    # QB/WR passing suppressed (<1), RB game-script boosted (>1) near the game
    assert near[idx["buf_qb"]] < 1.0 and near[idx["buf_wr"]] < 1.0
    assert near[idx["buf_rb"]] > 1.0
    # far-out forecast is shrunk toward climatology → deviation strictly smaller
    assert abs(far[idx["buf_qb"]] - 1.0) < abs(near[idx["buf_qb"]] - 1.0)
    # indoor game is weather-neutral
    dome = np.asarray(WeatherFactor()(_ctx(weather={"BUF": {**bad, "indoor": True}})))
    assert np.allclose(dome, 1.0)


def test_altitude_and_dome():
    out = np.asarray(AltitudeDomeFactor()(_ctx(venue_team={"DEN": "DEN", "MIN": "MIN"})))
    data = _data()
    idx = {pid: i for i, pid in enumerate(data.player_ids)}
    assert out[idx["den_wr"]] > 1.0  # altitude lifts skill volume
    assert out[idx["min_wr"]] > 1.0  # dome passing bump
    assert out[idx["buf_wr"]] == 1.0  # no venue → identity


def test_pace_and_pass_rate_direction():
    d = _data()
    idx = {pid: i for i, pid in enumerate(d.player_ids)}
    pace = np.asarray(PaceFactor()(_ctx(team_pace={"BUF": 75.0, "DEN": 55.0})))
    assert pace[idx["buf_wr"]] > 1.0 and pace[idx["den_wr"]] < 1.0
    pr = np.asarray(PassRateFactor()(_ctx(pass_rate={"BUF": 0.68})))
    assert pr[idx["buf_wr"]] > 1.0 and pr[idx["buf_rb"]] < 1.0  # WR up, RB down


def test_coaching_softens_on_regime_change():
    d = _data()
    idx = {pid: i for i, pid in enumerate(d.player_ids)}
    stable = np.asarray(CoachingTendencyFactor()(_ctx(coaching={"BUF": {"pass_bias": 0.2}})))
    fresh = np.asarray(CoachingTendencyFactor()(
        _ctx(coaching={"BUF": {"pass_bias": 0.2, "new_regime": True}})))
    # both lift the WR, but a new regime is pulled toward neutral (smaller deviation)
    assert stable[idx["buf_wr"]] > fresh[idx["buf_wr"]] > 1.0


def test_situational_home_and_fatigue():
    d = _data()
    idx = {pid: i for i, pid in enumerate(d.player_ids)}
    out = np.asarray(SituationalFactor()(_ctx(game_situation={
        "BUF": {"home": True},
        "DEN": {"home": False, "short_week": True, "rest_days": 3, "travel_miles": 2500},
    })))
    assert out[idx["buf_qb"]] > 1.0  # home boost
    assert out[idx["den_qb"]] < 1.0  # short week + travel + low rest → fatigue


# ── H2H: gated by ablation significance ────────────────────────────────────────
def test_ablation_significance_gate():
    rng = np.random.default_rng(0)
    signal = np.linspace(0, 1, 24)
    assert is_significant(signal, signal * 2 + rng.normal(0, 0.05, 24))  # tight linear
    assert not is_significant(signal, np.tile([0.0, 1.0], 12))  # no monotone relation
    assert not is_significant(None, None)  # missing evidence
    assert not is_significant([1, 2], [1, 2])  # too small to test


def test_h2h_drops_when_signal_is_noise():
    sig = np.linspace(0, 1, 24)
    ctx = _ctx(
        h2h={"BUF": 0.9, "DEN": 0.1},
        h2h_ablation={"signal": sig, "outcome": np.tile([0.0, 1.0], 12)},  # no relation
    )
    assert np.allclose(np.asarray(TeamH2HFactor()(ctx)), 1.0)


def test_h2h_fires_when_signal_is_significant():
    sig = np.linspace(0, 1, 24)
    d = _data()
    idx = {pid: i for i, pid in enumerate(d.player_ids)}
    ctx = _ctx(
        h2h={"BUF": 0.9, "DEN": 0.1},
        h2h_ablation={"signal": sig, "outcome": sig * 3 + 0.5},  # perfectly informative
    )
    out = np.asarray(TeamH2HFactor()(ctx))
    assert out[idx["buf_wr"]] > 1.0  # soft matchup → boost
    assert out[idx["den_wr"]] < 1.0  # tough matchup → discount
    assert (out >= FACTOR_BOUNDS[0]).all() and (out <= FACTOR_BOUNDS[1]).all()


def test_h2h_neutral_without_ablation_evidence():
    ctx = _ctx(h2h={"BUF": 0.9})  # no h2h_ablation key at all
    assert np.allclose(np.asarray(TeamH2HFactor()(ctx)), 1.0)


# ── projector seam integration ─────────────────────────────────────────────────
def test_projector_resolves_neutral_context_to_zero_log():
    data = _data()
    proj = HierarchicalProjector(factors=list(default_factors()))
    seams = proj._resolve_seams(data, context={})
    assert float(np.abs(np.asarray(seams.factor_log_opp)).max()) == 0.0


def test_projector_resolves_real_context_within_bounds():
    data = _data()
    proj = HierarchicalProjector(factors=list(default_factors()))
    seams = proj._resolve_seams(data, context={
        "team_pace": {"BUF": 75.0}, "pass_rate": {"BUF": 0.68},
        "venue_team": {"DEN": "DEN"},
    })
    log_mult = np.asarray(seams.factor_log_opp)
    assert np.abs(log_mult).max() > 0.0  # context actually moved something
    # composed multiplier stays inside the seam clamp
    mult = np.exp(log_mult)
    assert (mult >= FACTOR_BOUNDS[0]).all() and (mult <= FACTOR_BOUNDS[1]).all()
