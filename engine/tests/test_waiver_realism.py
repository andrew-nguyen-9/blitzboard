"""C02 — evaluator realism acceptance: bounded point-in-time proactive waivers,
transaction costs, contested shared pool, K/DST streaming, emergency/upside
distinction, playoff/championship proxies, determinism, and the live leak guard.

Synthetic pools with `InjuryDynamics.healthy()` and forced availability make each
behavior exact; the corpus-scale properties stay in `test_league_sim.py`.
"""
from __future__ import annotations

import numpy as np
import pytest

from blitz_engine.backtest.harness import LeakageError
from blitz_engine.lineup.feasibility import InjuryDynamics
from blitz_engine.simulation import season_eval as se

WEEKS = 4


def _mk(pid: str, pos: str, ppw: float, *, bye: int = 0, proj: float | None = None,
        weekly: tuple[float, ...] | None = None) -> se.SeasonPlayer:
    pts = weekly if weekly is not None else tuple([float(ppw)] * WEEKS)
    return se.SeasonPlayer(
        player_id=pid, position=pos, nfl_team="AAA", bye_week=bye,
        points_if_plays=pts, projection=float(proj if proj is not None else ppw * WEEKS),
        depth_rank=1,
    )


def _row(bench: int = 2) -> dict:
    return {"id": "synthetic", "teams": 2, "bench_slots": bench,
            "starting_slots": {"QB": 1, "RB": 1, "K": 1}}


def _pool_and_rosters() -> tuple[list[se.SeasonPlayer], list[list[se.SeasonPlayer]]]:
    a = [_mk("a_qb", "QB", 20), _mk("a_rb", "RB", 15), _mk("a_k", "K", 5),
         _mk("a_bench", "RB", 2.9)]
    b = [_mk("b_qb", "QB", 18), _mk("b_rb", "RB", 14), _mk("b_k", "K", 6),
         _mk("b_bench", "RB", 3.0)]
    free = [_mk("f_rb", "RB", 12), _mk("f_k", "K", 10)]
    return [*a, *b, *free], [a, b]


@pytest.fixture()
def certain(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove availability randomness so every behavior below is exact."""
    monkeypatch.setattr(se, "_availability", lambda players: np.ones(len(players)))


def _cfg(**kw) -> se.EvalConfig:
    base = dict(n_seasons=1, injury=InjuryDynamics.healthy())
    base.update(kw)
    return se.EvalConfig(**base)


def test_stale_bench_upgrade_is_an_upside_claim(certain: None) -> None:
    pool, rosters = _pool_and_rosters()
    res = se.evaluate_rosters(pool, rosters, _row(), config=_cfg())
    assert res.upside_adds.sum() > 0  # a 12-ppw free RB over a ~3-ppw bench body
    assert res.emergency_adds.sum() == 0  # nobody ever had an unfillable slot
    assert np.allclose(res.waiver_adds, res.emergency_adds + res.upside_adds)


def test_upgrade_margin_bounds_churn(certain: None) -> None:
    pool, rosters = _pool_and_rosters()
    free = [p for p in pool if p.player_id.startswith("f_")]
    thin = [p if p.player_id != "f_rb" else _mk("f_rb", "RB", 3.1) for p in pool
            if p.player_id != "f_k"]
    res = se.evaluate_rosters(thin, rosters, _row(), config=_cfg())
    assert res.upside_adds.sum() == 0  # 3.1 does not clear 3.0 × 1.15
    assert len(free) == 2  # (guard: the fixture actually had both free agents)


def test_contested_pool_goes_to_the_worse_record(certain: None) -> None:
    pool, rosters = _pool_and_rosters()
    pool = [p for p in pool if p.player_id != "f_k"]  # exactly one contested prize
    res = se.evaluate_rosters(pool, rosters, _row(), config=_cfg())
    # Team B trails after week 1 (38 < 40), so B claims f_rb first; the body B drops
    # (3.0 ppw) does not clear team A's own margin — one add, to the worse seat.
    assert res.upside_adds.tolist() == [0.0, 1.0]


def test_kdst_streams_through_the_same_upgrade_rule(certain: None) -> None:
    pool, rosters = _pool_and_rosters()
    on = se.evaluate_rosters(pool, rosters, _row(), config=_cfg())
    off = se.evaluate_rosters(pool, rosters, _row(), config=_cfg(proactive_moves_per_week=0))
    # the 10-ppw free K replaces a started 5/6-ppw K (started bodies are replaceable —
    # that IS streaming), so realism-on strictly outscores realism-off
    assert on.metric > off.metric
    assert on.upside_adds.sum() >= 2  # both seats upgraded (RB and/or K)
    assert off.upside_adds.sum() == 0


def test_transaction_cost_is_charged_per_claim(certain: None) -> None:
    pool, rosters = _pool_and_rosters()
    free_run = se.evaluate_rosters(pool, rosters, _row(), config=_cfg(waiver_cost=0.0))
    costed = se.evaluate_rosters(pool, rosters, _row(), config=_cfg(waiver_cost=5.0))
    assert np.allclose(free_run.waiver_adds, costed.waiver_adds)  # same claims, same seed
    expected = 5.0 * costed.waiver_adds * costed.n_seasons
    assert np.allclose(free_run.per_season[0] - costed.per_season[0], expected)


def test_season_moves_cap_is_a_hard_bound(certain: None) -> None:
    pool, rosters = _pool_and_rosters()
    none = se.evaluate_rosters(pool, rosters, _row(), config=_cfg(season_moves_cap=0))
    assert none.waiver_adds.sum() == 0
    one = se.evaluate_rosters(pool, rosters, _row(), config=_cfg(season_moves_cap=1))
    assert (one.waiver_adds * one.n_seasons <= 1.0 + 1e-12).all()


def test_emergency_and_upside_are_distinct_counters(certain: None) -> None:
    # An unfillable RB slot (bye, no backup, no proactive moves) is an EMERGENCY claim.
    a = [_mk("a_qb", "QB", 20), _mk("a_rb", "RB", 15, bye=2), _mk("a_k", "K", 5)]
    b = [_mk("b_qb", "QB", 18), _mk("b_rb", "RB", 14), _mk("b_k", "K", 6)]
    pool = [*a, *b, _mk("f_rb", "RB", 1)]
    res = se.evaluate_rosters(pool, [a, b], _row(bench=0),
                              config=_cfg(proactive_moves_per_week=0))
    assert res.emergency_adds[0] >= 1  # seat 0 patched the bye hole
    assert res.upside_adds.sum() == 0


def test_realism_path_is_seed_deterministic() -> None:
    pool, rosters = _pool_and_rosters()  # REAL availability model — randomness present
    cfg = _cfg(n_seasons=3, waiver_cost=2.0)
    a = se.evaluate_rosters(pool, rosters, _row(), config=cfg)
    b = se.evaluate_rosters(pool, rosters, _row(), config=cfg)
    for f in ("per_season", "per_season_h2h", "per_season_playoff", "per_season_champ",
              "emergency_adds", "upside_adds", "waiver_adds", "playoff_rate", "champ_rate"):
        assert np.array_equal(getattr(a, f), getattr(b, f)), f
    reseeded = _cfg(n_seasons=3, waiver_cost=2.0, seed=se.SEASON_EVAL_SEED + 1)
    other = se.evaluate_rosters(pool, rosters, _row(), config=reseeded)
    assert not np.array_equal(a.per_season, other.per_season)


def test_playoff_and_championship_proxies(certain: None) -> None:
    pool, rosters = _pool_and_rosters()
    cfg = _cfg(n_seasons=2, playoff_slots=1)
    res = se.evaluate_rosters(pool, rosters, _row(), config=cfg)
    assert res.per_season_playoff.shape == (2, 2)
    assert set(np.unique(res.per_season_playoff)) <= {0.0, 1.0}
    assert (res.per_season_playoff.sum(axis=1) == 1).all()  # exactly `playoff_slots` seats
    assert (res.per_season_champ.sum(axis=1) == 1).all()  # exactly one champion proxy
    assert (res.per_season_champ <= res.per_season_playoff).all()  # champ ⊆ playoff field
    assert np.allclose(res.playoff_rate, res.per_season_playoff.mean(axis=0))
    assert np.allclose(res.h2h_win_rate, res.per_season_h2h.mean(axis=0))


def test_paired_ci_shapes_and_ordering(certain: None) -> None:
    pool, rosters = _pool_and_rosters()
    a = se.evaluate_rosters(pool, rosters, _row(), config=_cfg(n_seasons=4))
    off = _cfg(n_seasons=4, proactive_moves_per_week=0)
    b = se.evaluate_rosters(pool, rosters, _row(), config=off)
    for f in ("per_season", "per_season_h2h", "per_season_playoff", "per_season_champ"):
        ci = se.paired_ci(a, b, seats=[0, 1], field=f)
        assert set(ci) == {"mean", "lo", "hi", "n"}
        assert ci["lo"] <= ci["mean"] <= ci["hi"]
        assert ci["n"] == 4.0
    pts = se.paired_ci(a, b, seats=[0, 1])
    assert pts["mean"] > 0  # realism-on strictly outscores realism-off here


def test_leak_guard_stays_live_under_realism(certain: None) -> None:
    pool, rosters = _pool_and_rosters()
    se.evaluate_rosters(pool, rosters, _row(), config=_cfg())  # clean
    with pytest.raises(LeakageError):
        se.evaluate_rosters(pool, rosters, _row(), config=_cfg(), leak={"week": 2})
