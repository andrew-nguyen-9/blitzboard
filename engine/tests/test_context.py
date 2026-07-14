"""Tests for E1-sentiment-vegas: the context seams over E1-core.

Fast + deterministic — no NUTS. The hooks are exercised through the projector's
`_resolve_seams` (cheap) plus direct unit checks: sentiment nudge is bounded and widens
variance; the Vegas mapping is a *fitted nonlinear* curve that degrades to neutral without
`ODDS_API_KEY`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from blitz_engine.projection import FACTOR_BOUNDS, HierarchicalProjector, ModelData
from blitz_engine.projection.context import (
    GameScriptMapping,
    SentimentPrior,
    SentimentSignal,
    VegasGameScriptFactor,
    aggregate_signals,
    resolve_scorer,
    score_and_aggregate,
    team_lines_from_odds,
)
from blitz_engine.projection.priors import TalentPrior

SCORING = {
    "receiving": {"pt_per_yd": 0.1, "ppr": 0.5, "td": 6},
    "rushing": {"pt_per_yd": 0.1, "td": 6},
}


def _data() -> ModelData:
    rows = []
    for t in range(2):
        for p in range(3):
            rows.append({
                "player_id": f"T{t}_P{p}", "position": ["WR", "RB", "TE"][p], "team": f"T{t}",
                "week": 1, "team_plays": 65.0, "opportunities": 8, "yards": 60.0, "tds": 0,
            })
    return ModelData.from_frame(pd.DataFrame(rows))


# ── sentiment: bounded nudge + variance widener ────────────────────────────────
def test_sentiment_nudge_is_bounded():
    data = _data()
    sig = {"T0_P0": SentimentSignal(sentiment=1.0, n=100)}  # max positive, high confidence
    hook = SentimentPrior(sig, nudge_gain=2.0, max_nudge=0.5)  # gain would overshoot
    tp = hook(data.player_ids, "opportunity", 1.0)
    assert tp.loc[0] == pytest.approx(0.5)  # clipped to max_nudge
    assert tp.loc[1] == 0.0  # unknown player → neutral


def test_sentiment_nudge_sign_and_confidence():
    data = _data()
    sig = {
        "T0_P0": SentimentSignal(sentiment=0.8, n=100),   # confident positive
        "T0_P1": SentimentSignal(sentiment=-0.8, n=100),  # confident negative
        "T0_P2": SentimentSignal(sentiment=0.8, n=1),     # thin → shrunk
    }
    tp = SentimentPrior(sig, nudge_gain=0.4, confidence_at=3)(data.player_ids, "opportunity", 1.0)
    assert tp.loc[0] > 0 and tp.loc[1] < 0
    assert abs(tp.loc[2]) < abs(tp.loc[0])  # low-volume signal moves the mean less


def test_sentiment_variance_widener():
    data = _data()
    sig = {
        "T0_P0": SentimentSignal(sentiment=-0.5, n=10, injury_flag=True),  # widens
        "T0_P1": SentimentSignal(sentiment=0.3, n=10, disagreement=0.0),   # no widen
    }
    hook = SentimentPrior(sig, widen_gain=0.5, injury_penalty=0.75)
    tp = hook(data.player_ids, "opportunity", 0.8)
    assert tp.scale[0] == pytest.approx(0.8 * 1.375)  # 1 + 0.5*0.75
    assert tp.scale[1] == pytest.approx(0.8)          # neutral scale
    assert tp.scale[2] == pytest.approx(0.8)          # unknown → default


def test_sentiment_composes_over_base_hook():
    data = _data()

    def base(pids, stage, default_scale):
        loc = np.zeros(len(pids))
        loc[0] = 1.5  # a talent-model prior underneath
        return TalentPrior(loc=loc, scale=np.full(len(pids), default_scale))

    sig = {"T0_P0": SentimentSignal(sentiment=0.5, n=100)}
    tp = SentimentPrior(sig, base=base)(data.player_ids, "opportunity", 1.0)
    assert tp.loc[0] > 1.5  # base preserved + sentiment nudge stacked on top


def test_aggregate_signals_disagreement():
    rows = [
        {"player_ids": ["A"], "sentiment": 0.9, "opportunity_flag": True},
        {"player_ids": ["A"], "sentiment": -0.9, "injury_flag": True},
    ]
    sigs = aggregate_signals(rows)
    assert sigs["A"].n == 2
    assert sigs["A"].sentiment == pytest.approx(0.0)
    assert sigs["A"].disagreement > 0
    assert sigs["A"].injury_flag and sigs["A"].opportunity_flag


def test_scorer_fallback_scores_injury_negative():
    """resolve_scorer degrades to VADER (transformers absent) and still reads injury news."""
    scorer = resolve_scorer()
    assert scorer.name in {"vader", "transformer"}
    sigs = score_and_aggregate(
        [("Star RB ruled out with a torn ACL, expected to miss the season", ["A"])], scorer
    )
    assert sigs["A"].sentiment < 0 and sigs["A"].injury_flag


# ── vegas: learned nonlinear mapping + key-gated degrade ───────────────────────
def test_mapping_neutral_is_identity():
    assert GameScriptMapping.neutral().predict(-7.0, 48.0) == 1.0


def test_mapping_fit_is_nonlinear_not_raw_spread():
    rng = np.random.default_rng(0)
    spreads = rng.uniform(-14, 14, 400)
    totals = rng.uniform(38, 52, 400)
    # true log-multiplier has a genuine spread² curvature (a raw-spread map cannot fit it)
    log_mult = 0.01 * (totals - 44) - 0.015 * spreads + 0.0015 * spreads**2
    m = GameScriptMapping.fit(spreads, totals, log_mult, ridge=1e-3)
    lo, mid, hi = (np.log(m.predict(s, 44.0)) for s in (-14.0, 0.0, 14.0))
    curvature = lo - 2 * mid + hi
    assert curvature > 0.1  # second difference ≠ 0 ⇒ nonlinear, not affine in spread
    assert m.predict(-14.0, 44.0) != pytest.approx(m.predict(14.0, 44.0))


def test_mapping_predict_is_bounded():
    m = GameScriptMapping(coef=np.array([5.0, 0.0, 0.0, 0.0, 0.0, 0.0]))  # huge intercept
    assert m.predict(0.0, 44.0) == pytest.approx(FACTOR_BOUNDS[1])  # clipped to 2.0×


def test_team_lines_from_odds_signs_spreads():
    rows = [{"home_team": "T0", "away_team": "T1", "home_spread": -6.5, "total": 47.0}]
    lines = team_lines_from_odds(rows)
    assert lines["T0"] == (-6.5, 47.0)  # home favored
    assert lines["T1"] == (6.5, 47.0)   # away underdog, shared total


def test_vegas_factor_degrades_without_key():
    data = _data()
    ctx_factor = VegasGameScriptFactor(
        team_lines={"T0": (-7.0, 50.0)},
        mapping=GameScriptMapping.fit([-7, 7], [50, 44], [0.2, -0.1], ridge=1e-3),
        enabled=False,  # ODDS_API_KEY absent
    )
    from blitz_engine.projection.model import FactorContext

    out = ctx_factor(FactorContext(data=data, context={}))
    assert np.array_equal(out, np.ones(data.n_players))  # neutral: mapping off


def test_vegas_factor_active_is_neutral_for_unknown_teams():
    data = _data()
    mapping = GameScriptMapping.fit(
        [-10, -3, 3, 10], [52, 45, 45, 40], [0.25, 0.05, -0.05, -0.2], ridge=1e-3
    )
    factor = VegasGameScriptFactor(
        team_lines={"T0": (-10.0, 52.0)}, mapping=mapping, enabled=True  # only T0 has a line
    )
    from blitz_engine.projection.model import FactorContext

    out = factor(FactorContext(data=data, context={}))
    t0 = [i for i, ti in enumerate(data.team_of_player) if data.teams[ti] == "T0"]
    t1 = [i for i, ti in enumerate(data.team_of_player) if data.teams[ti] == "T1"]
    assert all(out[i] != 1.0 for i in t0)          # T0 line applied
    assert all(out[i] == 1.0 for i in t1)          # T1 unknown → neutral


def test_context_hooks_plug_into_projector_seams():
    """Both context signals resolve through the core's DI seams, bounded + composable."""
    data = _data()
    sig = {"T0_P0": SentimentSignal(sentiment=1.0, n=100, injury_flag=True)}
    mapping = GameScriptMapping.fit([-8, 8], [50, 42], [0.3, -0.15], ridge=1e-3)
    factor = VegasGameScriptFactor(team_lines={"T0": (-8.0, 50.0)}, mapping=mapping, enabled=True)
    proj = HierarchicalProjector(
        scoring=SCORING, talent_prior=SentimentPrior(sig), factors=[factor]
    )
    seams = proj._resolve_seams(data)
    # talent loc nudged for the sentiment player; scale widened by the injury flag
    assert float(np.asarray(seams.talent_loc)[0]) > 0
    assert float(np.asarray(seams.talent_scale)[0]) > float(np.asarray(seams.talent_scale)[1])
    # factor log-multiplier stays inside the core's clamp
    logf = np.abs(np.asarray(seams.factor_log_opp))
    assert float(logf.max()) <= np.log(FACTOR_BOUNDS[1]) + 1e-6
    assert float(logf.max()) > 0  # T0 line actually moved something
