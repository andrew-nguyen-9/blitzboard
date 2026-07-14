"""Tests for E1-latents — optional, degrade-neutral latent team/matchup/chemistry structures.

Fast + deterministic: no NUTS. We assert the seam contract on the resolved arrays (aligned to
the player universe, bounded, degrade to 0), the four latents' directions, the chemistry
ablation gate (fires on a real pairing signal, DROPS on noise), and the whole-model degrade
path (thin data / disabled ⇒ all-zero contribution ⇒ a strict no-op on the base projection).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from blitz_engine.projection import HierarchicalProjector, LatentContribution, ModelData
from blitz_engine.projection.latents import (
    ChemistryLatent,
    EcosystemLatent,
    LatentModel,
    OLineLatent,
    ResolveContext,
    clip_latent,
    grouped_shrunk_effect,
    opponent_adjust,
)
from blitz_engine.projection.model import LatentHook

_TEAMS = ("DEN", "BUF", "MIN")
_OPPS = ("BAD", "TUF", "AVG")  # BAD = generous defense, TUF = stingy
_POS_BASE = {"QB": np.log(7.0), "RB": np.log(4.5), "WR": np.log(9.0), "TE": np.log(8.0)}
_OPP_EFF = {"BAD": 0.5, "TUF": -0.5, "AVG": 0.0}
_ECO = {"DEN": 0.0, "BUF": 0.3, "MIN": 0.0}  # BUF best ecosystem
_OLINE_RB = {"DEN": 0.4, "BUF": 0.0, "MIN": -0.3}  # DEN best O-line, MIN worst
_TOUCH = {"QB": 30, "RB": 15, "WR": 8, "TE": 6}


def _roster(team: str) -> list[tuple[str, str]]:
    return [(f"{team}_qb", "QB"), (f"{team}_rb", "RB"),
            (f"{team}_wr", "WR"), (f"{team}_te", "TE")]


def _history() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows = []
    for team in _TEAMS:
        for opp in _OPPS:
            for _ in range(4):
                for pid, pos in _roster(team):
                    log_ypo = _POS_BASE[pos] + _OPP_EFF[opp] + _ECO[team]
                    if pos == "RB":
                        log_ypo += _OLINE_RB[team]
                    log_ypo += rng.normal(0, 0.04)
                    touch = _TOUCH[pos]
                    rows.append({
                        "player_id": pid, "position": pos, "team": team, "opponent": opp,
                        "passer_id": f"{team}_qb", "opportunities": touch,
                        "yards": touch * np.exp(log_ypo), "tds": 1,
                    })
    return pd.DataFrame(rows)


def _current() -> ModelData:
    rows = [
        {"player_id": pid, "position": pos, "team": team, "week": 1,
         "team_plays": 65.0, "opportunities": 10.0, "yards": 60.0, "tds": 0.0}
        for team in _TEAMS for pid, pos in _roster(team)
    ]
    return ModelData.from_frame(pd.DataFrame(rows))


# ── shrinkage helpers ───────────────────────────────────────────────────────────
def test_grouped_shrunk_effect_shrinks_thin_groups_and_clips():
    keys = ["a"] * 20 + ["b"]  # 'a' seen 20×, 'b' once
    resid = np.array([1.0] * 20 + [1.0])
    eff = grouped_shrunk_effect(keys, resid, k=6.0, bound=0.5)
    assert eff["a"] > eff["b"]              # more data ⇒ less shrinkage
    assert eff["b"] == pytest.approx(1.0 / (1 + 6.0))  # single obs shrinks hard toward 0
    assert all(abs(v) <= 0.5 for v in eff.values())     # clip respected


def test_opponent_adjust_removes_offense_strength():
    # two offenses, one strong (+1) one weak (−1); after adjustment the residual is offense-free
    vals = np.array([2.0, 2.0, 0.0, 0.0])
    offense = ["strong", "strong", "weak", "weak"]
    resid = opponent_adjust(vals, offense, k=0.0)
    assert np.allclose(resid[:2], resid[2:])  # both offenses reduced to the same residual


def test_clip_latent_bounds():
    assert clip_latent(5.0, 0.3) == 0.3
    assert clip_latent(-5.0, 0.3) == -0.3


# ── degrade-neutral: empty / thin history ⇒ disabled, all-zero contribution ──────
def test_empty_history_is_disabled_and_neutral():
    m = LatentModel.fit(pd.DataFrame(columns=["player_id", "position", "team",
                                              "opportunities", "yards"]))
    assert not m.enabled
    c = m(_current())
    assert np.allclose(np.asarray(c.opportunity), 0.0)
    assert np.allclose(np.asarray(c.efficiency), 0.0)


def test_thin_history_degrades_to_neutral():
    thin = _history().head(3)  # below the min-rows floor
    m = LatentModel.fit(thin)
    assert not m.enabled


def test_missing_required_column_raises():
    with pytest.raises(ValueError, match="missing columns"):
        LatentModel.fit(pd.DataFrame({"player_id": ["x"], "position": ["WR"]}))


# ── hook protocol + seam shape ──────────────────────────────────────────────────
def test_model_satisfies_latent_hook_protocol():
    m = LatentModel.fit(_history(), matchups={"DEN": "BAD"})
    assert isinstance(m, LatentHook)
    c = m(_current())
    assert isinstance(c, LatentContribution)
    n = _current().n_players
    assert np.asarray(c.opportunity).shape == (n,)
    assert np.asarray(c.efficiency).shape == (n,)


# ── defense latent: opponent-adjusted, feeds efficiency + within-team share shift ─
def test_defense_generous_vs_stingy_direction():
    m = LatentModel.fit(_history())
    ds = m.defense_strength()
    assert ds[("BAD", "WR")] > 0 > ds[("TUF", "WR")]  # generous > 0 > stingy


def test_defense_efficiency_reflects_matchup():
    # DEN faces the generous BAD, BUF faces the stingy TUF
    m = LatentModel.fit(_history(), matchups={"DEN": "BAD", "BUF": "TUF", "MIN": "AVG"})
    c = m(_current())
    ids = _current().player_ids
    eff = {pid: float(e) for pid, e in zip(ids, np.asarray(c.efficiency), strict=True)}
    assert eff["DEN_wr"] > eff["BUF_wr"]  # generous matchup lifts efficiency vs stingy


def test_defense_opportunity_is_within_team_differential():
    # a pure team-constant opportunity latent cancels in the Dirichlet share, so the defense
    # opportunity contribution must sum to ~0 within each team (only the differential survives)
    m = LatentModel.fit(_history(), matchups={"DEN": "BAD", "BUF": "TUF", "MIN": "AVG"})
    data = _current()
    opp = np.asarray(m(data).opportunity)
    teams = np.asarray([data.teams[i] for i in data.team_of_player])
    for t in np.unique(teams):
        assert abs(float(opp[teams == t].sum())) < 1e-5


# ── O-line latent: RB rush efficiency full, pass floor a fraction ────────────────
def test_oline_direction_and_position_weighting():
    m = LatentModel.fit(_history())
    ol = m.oline()
    assert ol["DEN"] > ol["MIN"]  # DEN best O-line, MIN worst
    # RB gets the full effect, pass-catchers a fraction of it (same sign)
    ctx = ResolveContext(
        player_ids=["rb", "wr"], positions=["RB", "WR"], teams=["DEN", "DEN"],
    )
    _, eff = OLineLatent({"DEN": 0.2}).contribution(ctx)
    assert eff[0] == pytest.approx(0.2)          # RB rush efficiency = full
    assert 0.0 < eff[1] < eff[0]                  # WR pass floor = fraction


# ── ecosystem latent: rising-tide efficiency ────────────────────────────────────
def test_ecosystem_direction():
    m = LatentModel.fit(_history())
    eco = m.ecosystem()
    assert eco["BUF"] > eco["DEN"] and eco["BUF"] > eco["MIN"]  # BUF best ecosystem
    ctx = ResolveContext(player_ids=["a"], positions=["WR"], teams=["BUF"])
    _, eff = EcosystemLatent({"BUF": 0.15}).contribution(ctx)
    assert eff[0] == pytest.approx(0.15)


# ── chemistry latent: HARD-regularised + ablation-gated ──────────────────────────
def _chem_history(*, real: bool) -> tuple:
    rng = np.random.default_rng(0)
    rows = []
    for _ in range(8):  # R1 caught by QA
        rows.append(("QA", "R1", "WR", np.log(9) + (0.5 if real else 0.0) + rng.normal(0, 0.05)))
    for _ in range(8):  # R1 also caught by QB — real ⇒ much worse (chemistry with QA)
        rows.append(("QB", "R1", "WR", np.log(9) + (-0.5 if real else 0.0) + rng.normal(0, 0.05)))
    for r, q in (("R2", "QC"), ("R3", "QD")):  # single-QB receivers = noise
        for _ in range(6):
            rows.append((q, r, "TE", np.log(8) + rng.normal(0, 0.3)))
    psr, rcv, pos, ly = zip(*rows, strict=True)
    return (np.array(psr), np.array(rcv), np.array(pos), np.array(ly))


def test_chemistry_fires_on_real_pairing_signal():
    chem = ChemistryLatent.fit(*_chem_history(real=True))
    assert chem.significant
    assert chem.pair[("QA", "R1")] > 0 > chem.pair[("QB", "R1")]


def test_chemistry_drops_when_signal_is_noise():
    chem = ChemistryLatent.fit(*_chem_history(real=False))
    assert not chem.significant
    assert chem.pair == {}
    # a dropped chemistry latent contributes exactly nothing
    ctx = ResolveContext(
        player_ids=["R1"], positions=["WR"], teams=["DEN"],
        qb_of_team={"DEN": "QA"},
    )
    _, eff = chem.contribution(ctx)
    assert np.allclose(eff, 0.0)


def test_chemistry_needs_passer_column():
    m = LatentModel.fit(_history().drop(columns=["passer_id"]))
    assert not m.chemistry_significant
    assert m.chemistry() == {}


# ── whole-model degrade + safety bounds ─────────────────────────────────────────
def test_missing_matchups_degrades_defense_but_keeps_others():
    m = LatentModel.fit(_history())  # no matchups ⇒ no opponent to face
    assert m.enabled
    c = m(_current())
    # defense (needs an opponent) is neutral, but ecosystem/oline still move efficiency
    assert np.abs(np.asarray(c.efficiency)).max() > 0.0


def test_composed_contribution_respects_global_bounds():
    m = LatentModel.fit(_history(), matchups={"DEN": "BAD", "BUF": "TUF", "MIN": "AVG"})
    c = m(_current())
    assert np.abs(np.asarray(c.opportunity)).max() <= 0.4 + 1e-6
    assert np.abs(np.asarray(c.efficiency)).max() <= 0.5 + 1e-6


def test_unknown_players_degrade_to_zero():
    m = LatentModel.fit(_history(), matchups={"DEN": "BAD"})
    unknown = ModelData.from_frame(pd.DataFrame([{
        "player_id": "ghost", "position": "WR", "team": "ZZZ", "week": 1,
        "team_plays": 60.0, "opportunities": 8.0, "yards": 50.0, "tds": 0.0,
    }]))
    c = m(unknown)
    assert np.allclose(np.asarray(c.efficiency), 0.0)
    assert np.allclose(np.asarray(c.opportunity), 0.0)


# ── projector seam integration ──────────────────────────────────────────────────
def test_projector_resolves_latent_seam_within_bounds():
    data = _current()
    m = LatentModel.fit(_history(), matchups={"DEN": "BAD", "BUF": "TUF", "MIN": "AVG"})
    proj = HierarchicalProjector(latent=m)
    seams = proj._resolve_seams(data)
    lat_opp = np.asarray(seams.latent_opp)
    lat_eff = np.asarray(seams.latent_eff)
    assert lat_opp.shape == (data.n_players,) and lat_eff.shape == (data.n_players,)
    assert np.isfinite(lat_opp).all() and np.isfinite(lat_eff).all()
    assert np.abs(lat_eff).max() > 0.0  # the latent actually moved efficiency
    assert np.abs(lat_eff).max() <= 0.5 + 1e-6


def test_projector_with_disabled_latent_is_neutral_seam():
    data = _current()
    disabled = LatentModel.fit(pd.DataFrame(columns=["player_id", "position", "team",
                                                     "opportunities", "yards"]))
    proj = HierarchicalProjector(latent=disabled)
    seams = proj._resolve_seams(data)
    assert float(np.abs(np.asarray(seams.latent_opp)).max()) == 0.0
    assert float(np.abs(np.asarray(seams.latent_eff)).max()) == 0.0
