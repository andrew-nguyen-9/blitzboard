"""Tests for the E6 projection explainability layer.

Fast and sampler-free: the "why" attribution and narrative are *pure functions of the
projection numbers*, so we build a tiny hand-made `Projection` (no NUTS) and assert the
Shapley additivity axiom, the driver ranking, and — the headline E6 contract — that the
war-room brief is byte-for-byte deterministic with no AI call.
"""
from __future__ import annotations

import pandas as pd

from blitz_engine.explain import (
    explain,
    render_why,
    shapley_contributions,
    war_room_brief,
    why_frame,
    why_report,
)
from blitz_engine.explain.why import _points  # exact-mean value fn under test
from blitz_engine.projection.convergence import ConvergenceReport
from blitz_engine.projection.families import ScoringWeights
from blitz_engine.projection.inference import Projection

SCORING = ScoringWeights.from_scoring(
    {"receiving": {"pt_per_yd": 0.1, "ppr": 0.5, "td": 6}, "rushing": {"pt_per_yd": 0.1, "td": 6}}
)


def _projection() -> Projection:
    """A 3-player fixture with a clear volume king, an efficiency king, and a replacement."""
    players = ["star_vol", "star_eff", "repl"]
    week = [1, 1, 1]
    # star_vol: many touches, avg efficiency; star_eff: few touches, elite ypo; repl: low both
    vols, ypos, tdrs = [22.0, 12.0, 8.0], [7.0, 15.0, 6.0], [0.05, 0.09, 0.03]
    opp = pd.DataFrame({"player_id": players, "week": week, "mu_opportunity": vols})
    eff = pd.DataFrame({
        "player_id": players, "week": week, "yards_per_opp": ypos, "td_rate": tdrs,
    })
    # mean = deterministic composition so `projected` and `reconstructed` line up in the test
    mean = [_points({"volume": v, "efficiency": y, "scoring": t}, SCORING)
            for v, y, t in zip(vols, ypos, tdrs, strict=True)]
    quantiles = pd.DataFrame({"player_id": players, "week": week, "mean": mean})
    shares = pd.DataFrame({"player_id": players, "team": ["A", "A", "B"], "share": [0.5, 0.2, 0.4]})
    report = ConvergenceReport(passed=True, rhat_max=1.0, ess_min=200.0, n_divergences=0)
    return Projection(
        quantiles=quantiles, shares=shares, opportunity=opp, efficiency=eff, convergence=report
    )


def test_shapley_additivity_exact():
    """The three driver contributions sum EXACTLY to value(player) − value(baseline)."""
    player = {"volume": 20.0, "efficiency": 8.0, "scoring": 0.06}
    base = {"volume": 10.0, "efficiency": 6.0, "scoring": 0.03}
    contrib = shapley_contributions(player, base, SCORING)
    assert set(contrib) == {"volume", "efficiency", "scoring"}
    total = _points(player, SCORING) - _points(base, SCORING)
    assert sum(contrib.values()) == total  # exact float identity (enumerated coalitions)


def test_shapley_is_deterministic():
    player = {"volume": 20.0, "efficiency": 8.0, "scoring": 0.06}
    base = {"volume": 10.0, "efficiency": 6.0, "scoring": 0.03}
    a = shapley_contributions(player, base, SCORING)
    b = shapley_contributions(player, base, SCORING)
    assert a == b


def test_explain_ranks_dominant_driver():
    whys = {w.player_id: w for w in explain(_projection(), weights=SCORING)}
    assert set(whys) == {"star_vol", "star_eff", "repl"}
    # volume king's top driver is volume; efficiency king's top driver is efficiency
    assert whys["star_vol"].features[0].name == "volume"
    assert whys["star_vol"].features[0].contribution > 0
    assert whys["star_eff"].features[0].name == "efficiency"
    # additivity holds through the dataclass too
    w = whys["star_vol"]
    assert abs(w.reconstructed - w.projected) < 1e-6


def test_why_frame_columns_stable():
    frame = why_frame(explain(_projection(), weights=SCORING))
    for k in ("volume", "efficiency", "scoring"):
        assert f"why_{k}" in frame.columns and f"why_{k}_value" in frame.columns
    assert {"player_id", "week", "projected", "baseline"} <= set(frame.columns)
    assert len(frame) == 3


def test_render_why_is_plain_language_and_deterministic():
    whys = explain(_projection(), weights=SCORING)
    star = next(w for w in whys if w.player_id == "star_vol")
    text = render_why(star)
    assert text == render_why(star)  # pure
    assert "Projects" in text and "pts" in text and "usage / volume" in text


def test_war_room_brief_deterministic_no_ai():
    """Headline E6 contract: same projection ⇒ byte-identical brief, generated from numbers."""
    whys = explain(_projection(), weights=SCORING)
    first = war_room_brief(whys)
    second = war_room_brief(whys)
    assert first == second
    # ranked by projected desc → the efficiency king (24.5 pts) leads the board
    assert first["summary"].startswith("star_eff")
    assert "star_vol" in first["body"] and "star_eff" in first["body"] and "repl" in first["body"]


def test_war_room_brief_degrades_on_empty():
    brief = war_room_brief([])
    assert "No projections" in brief["summary"]
    assert isinstance(brief["body"], str) and brief["body"].strip()


def test_why_report_shape_and_determinism():
    proj = _projection()
    kw = {"weights": SCORING, "season": 2025, "week": 1, "generated_at": "2025-09-10T00:00:00Z"}
    rep = why_report(proj, **kw)
    assert why_report(proj, **kw) == rep  # deterministic: same input ⇒ same artifact
    assert rep["season"] == 2025 and rep["week"] == 1
    players = rep["players"]
    assert [p["player_id"] for p in players][0] == "star_eff"  # top of the board first
    p0 = players[0]
    assert set(p0["contributions"]) == {"volume", "efficiency", "scoring"}
    assert "text" in p0 and "brief" in rep and set(rep["brief"]) == {"summary", "body"}
