"""Tests for E1-talent — true-talent dynamics plugged into E1-core's talent-prior seam.

Fast + deterministic: closed-form GP / Kalman / Viterbi, no NUTS. Covers the seam contract
(shape + alignment + degrade-neutral), the regime/aging/rookie accessors E2 reads, the
CFBD-absent degrade path, and a minimal ablation-or-neutral fixture (the talent layer moves
priors in the *right* direction and is provably neutral for unknown players).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from blitz_engine.projection import HierarchicalProjector, ModelData
from blitz_engine.projection.priors import TalentPrior, TalentPriorHook
from blitz_engine.projection.talent import (
    REGIMES,
    AgingCurves,
    RookiePriors,
    TalentModel,
    fit_career_arc,
    label_regime,
    learn_lengthscale,
)


def make_history(seed: int = 0) -> pd.DataFrame:
    """Synthetic multi-season careers: stars high, scrubs low, one clear riser + decliner."""
    rng = np.random.default_rng(seed)
    rows = []
    # base talent level per player (log-usage scale), by position
    roster = {
        "WR": {"star": 1.2, "scrub": -0.9, "riser": None, "decliner": None},
        "RB": {"vetA": 0.3, "vetB": -0.2},
    }
    for pos, players in roster.items():
        for name, base in players.items():
            pid = f"{pos}_{name}"
            for season in range(2018, 2024):
                t = float(season - 2018)
                if name == "riser":
                    level = -1.0 + 0.45 * t  # climbing every year
                elif name == "decliner":
                    level = 1.0 - 0.45 * t
                else:
                    level = base
                for wk in range(1, 9):
                    rows.append({
                        "player_id": pid, "position": pos,
                        "t": t + wk / 22.0, "age": 22.0 + t,
                        "value": level + rng.normal(0, 0.15),
                    })
    return pd.DataFrame(rows)


def make_current_frame() -> pd.DataFrame:
    """A current-week frame whose player universe overlaps history + one unknown player."""
    ids = ["WR_star", "WR_scrub", "RB_vetA", "UNKNOWN_1"]
    pos = ["WR", "WR", "RB", "WR"]
    return pd.DataFrame({
        "player_id": ids, "position": pos, "team": ["A", "A", "B", "B"],
        "week": [9, 9, 9, 9], "team_plays": [65.0] * 4,
        "opportunities": [8, 3, 6, 4], "yards": [80.0, 25.0, 40.0, 30.0], "tds": [1, 0, 0, 0],
    })


# ── the seam contract ──────────────────────────────────────────────────────────
def test_talentmodel_satisfies_hook_protocol():
    model = TalentModel.fit(make_history(), default_scale=1.0)
    assert isinstance(model, TalentPriorHook)  # runtime_checkable structural check


def test_hook_shape_alignment_and_neutral_unknown():
    model = TalentModel.fit(make_history(), default_scale=1.0)
    ids = ["WR_star", "UNKNOWN_1", "WR_scrub"]
    tp = model(ids, "opportunity", 1.0)
    assert isinstance(tp, TalentPrior)
    assert tp.loc.shape == (3,) and tp.scale.shape == (3,)
    # unknown player is exactly neutral: loc 0, default scale
    assert tp.loc[1] == pytest.approx(0.0)
    assert tp.scale[1] == pytest.approx(1.0)
    # a star ranks strictly above a scrub in talent loc
    assert tp.loc[0] > tp.loc[2]


def test_non_opportunity_stage_is_neutral():
    model = TalentModel.fit(make_history(), default_scale=1.0)
    tp = model(["WR_star", "WR_scrub"], "efficiency", 0.4)
    assert np.allclose(tp.loc, 0.0)
    assert np.allclose(tp.scale, 0.4)


def test_resolves_through_projector_seam():
    """The real E1-core path: projector._resolve_seams calls the hook and aligns arrays."""
    model = TalentModel.fit(make_history(), default_scale=1.0)
    data = ModelData.from_frame(make_current_frame())
    proj = HierarchicalProjector(talent_prior=model)
    seams = proj._resolve_seams(data)
    assert seams.talent_loc is not None and seams.talent_scale is not None
    assert np.asarray(seams.talent_loc).shape == (data.n_players,)
    # the unknown player's slot stays neutral (loc 0), so the hook can't worsen his fit
    star_i = data.player_ids.index("WR_star")
    unk_i = data.player_ids.index("UNKNOWN_1")
    assert float(np.asarray(seams.talent_loc)[unk_i]) == pytest.approx(0.0)
    assert float(np.asarray(seams.talent_loc)[star_i]) > 0.0


# ── ablation-or-neutral: the talent layer moves priors the RIGHT way ─────────────
def test_talent_direction_matches_truth_and_neutral_default():
    """Minimal ablation fixture (E7 harness not landed): the layer is directional where it
    has signal and provably neutral where it doesn't — so it improves or does no harm."""
    model = TalentModel.fit(make_history(), default_scale=1.0)
    tp = model(["WR_star", "WR_scrub", "RB_vetA"], "opportunity", 1.0)
    # star's prior is boosted above the positional mean, scrub's pulled below → captures truth
    assert tp.loc[0] > 0.1 > -0.1 > tp.loc[1]
    # a fully-unknown roster resolves to the exact neutral base prior (ablation = base engine)
    neutral = model(["X", "Y"], "opportunity", 1.0)
    assert np.allclose(neutral.loc, 0.0) and np.allclose(neutral.scale, 1.0)


def test_riser_has_positive_momentum_decliner_negative():
    model = TalentModel.fit(make_history())
    rise = model.player("WR_riser")
    fall = model.player("WR_decliner")
    assert rise is not None and fall is not None
    assert rise.arc.momentum >= fall.arc.momentum
    assert rise.regime.slope > 0 > fall.regime.slope


# ── regime labels (E2 hazard inputs) ─────────────────────────────────────────────
def test_regime_labels_exposed_and_valid():
    model = TalentModel.fit(make_history())
    labels = model.regimes()
    assert labels and set(labels.values()) <= set(REGIMES)
    feat = model.regime("WR_star")
    assert feat is not None and feat.label in REGIMES
    assert np.isfinite(feat.slope) and feat.volatility >= 0


def test_label_regime_direct_breakout_and_hurt():
    breakout = label_regime(np.array([-1.0, -0.3, 0.4, 1.1, 1.8]))
    assert breakout.label == "breakout" and breakout.slope > 0
    hurt = label_regime(np.array([1.0, 0.9, 1.0, -0.2, -1.9]))
    assert hurt.label in ("hurt", "decline")
    assert label_regime(np.array([0.5])).label == "steady"  # too short → neutral


# ── aging curve accessor ─────────────────────────────────────────────────────────
def test_aging_curve_peak_and_bounded_adjustment():
    model = TalentModel.fit(make_history())
    peak = model.aging.peak_age("RB")
    assert 20.0 <= peak <= 34.0
    # adjustment is 0 at peak, non-positive elsewhere, and bounded
    assert model.aging_adjustment("RB", peak) == pytest.approx(0.0, abs=1e-6)
    assert -0.6 <= model.aging_adjustment("RB", peak + 6) <= 0.0
    # unknown position / missing age → neutral
    assert model.aging_adjustment("ZZ", 25.0) == 0.0
    assert model.aging_adjustment("RB", None) == 0.0


def test_aging_curves_fit_directly_concave():
    pos = np.array(["RB"] * 12)
    age = np.array([21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32], dtype=float)
    val = -((age - 26.0) ** 2) * 0.05 + 2.0  # concave, peak at 26
    curves = AgingCurves.fit(pos, age, val)
    assert 24.0 <= curves.peak_age("RB") <= 28.0


# ── rookie prior + CFBD-absent degrade path ──────────────────────────────────────
def test_rookie_prior_degrades_without_cfbd():
    """No draft/CFBD frame ⇒ rookie prior falls back to archetype + wide scale, no crash."""
    rk = RookiePriors(draft=None, archetype_loc={"WR": 0.0}, default_scale=1.0)
    assert rk.college_available is False
    prior = rk.get("SOME_ROOKIE", "WR")
    assert prior.college_used is False
    assert prior.scale > 1.0  # widened (high epistemic) rookie prior
    assert -1.5 <= prior.loc <= 1.5


def test_rookie_draft_capital_and_cfbd_present():
    draft = pd.DataFrame({
        "player_id": ["R_top", "R_late"], "position": ["WR", "RB"],
        "draft_overall": [3, 220], "ras": [9.5, 4.0],
    })
    rk = RookiePriors(draft=draft, archetype_loc={"WR": 0.0, "RB": 0.0}, default_scale=1.0)
    assert rk.college_available is True
    top = rk.get("R_top", "WR")
    late = rk.get("R_late", "RB")
    # earlier pick + higher RAS ⇒ strictly higher rookie loc
    assert top.loc > late.loc
    assert top.college_used is True and top.draft_overall == 3.0


def test_model_fit_degrades_when_draft_lacks_cfbd_columns():
    """A draft frame with no `ras` column ⇒ college layer skipped (CFBD-absent path)."""
    draft = pd.DataFrame({"player_id": ["R1"], "position": ["WR"], "draft_overall": [10]})
    model = TalentModel.fit(make_history(), draft=draft, default_scale=1.0)
    assert model.college_available is False
    rp = model.rookie_prior("R1", "WR")
    assert rp.college_used is False and rp.draft_overall == 10.0


# ── dynamics primitives ──────────────────────────────────────────────────────────
def test_career_arc_tracks_level_and_degrades_empty():
    t = np.linspace(0.0, 5.0, 30)
    high = fit_career_arc(t, np.full(30, 1.5), lengthscale=2.0)
    low = fit_career_arc(t, np.full(30, -1.5), lengthscale=2.0)
    assert high.level > low.level and high.n_obs == 30
    empty = fit_career_arc(np.array([]), np.array([]), lengthscale=2.0)
    assert empty.n_obs == 0 and empty.level == 0.0


def test_learn_lengthscale_returns_grid_value():
    rng = np.random.default_rng(0)
    series = [(np.arange(6.0), rng.normal(0, 1, 6)) for _ in range(4)]
    ls = learn_lengthscale(series)
    assert ls in (0.5, 1.0, 2.0, 4.0, 8.0)


def test_empty_history_is_fully_neutral():
    model = TalentModel.fit(pd.DataFrame(columns=["player_id", "position", "t", "value"]))
    tp = model(["a", "b"], "opportunity", 1.0)
    assert np.allclose(tp.loc, 0.0) and np.allclose(tp.scale, 1.0)
