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


# ── C02A: preregistered decision-rule corrections (waiver-realism-v1) ─────────


def test_cross_position_flex_substitution_direct() -> None:
    # A started FLEX RB at 2 ppw is the lowest opportunity cost in the free TE's role
    # space (both FLEX-eligible); nominal positions differ and the swap must still fire.
    positions = ["QB", "RB", "RB", "TE"]
    proj = np.array([20.0, 12.0, 2.0, 10.0])
    swap = se._best_upgrade(
        squad=[0, 1, 2], free=[3], positions=positions, proj=proj,
        known_out=np.zeros(4, dtype=bool), margin=0.15,
        slots={"QB": 1, "RB": 1, "FLEX": 1},
    )
    assert swap == (2, 3)


def test_cross_position_flex_substitution_end_to_end(certain: None) -> None:
    a = [_mk("a_qb", "QB", 20), _mk("a_rb", "RB", 15), _mk("a_wr", "WR", 12),
         _mk("a_bench", "RB", 2)]
    b = [_mk("b_qb", "QB", 18), _mk("b_rb", "RB", 14), _mk("b_wr", "WR", 11),
         _mk("b_bench", "RB", 9)]
    pool = [*a, *b, _mk("f_te", "TE", 10)]
    row = {"id": "flex-sub", "teams": 2, "bench_slots": 1,
           "starting_slots": {"QB": 1, "RB": 1, "WR": 1, "FLEX": 1}}
    res = se.evaluate_rosters(pool, [a, b], row, config=_cfg())
    # seat 0's 2-ppw bench RB is the league's lowest FLEX-space nonstarter; the free TE
    # replaces it across nominal positions (b_bench at 9 fails b's own margin gate)
    assert res.upside_adds[0] >= 1
    assert res.emergency_adds.sum() == 0


def test_infeasible_position_never_claims(certain: None) -> None:
    # No lineup slot can ever use an RB in a QB-only league: the add is infeasible no
    # matter how large its projection edge is.
    a = [_mk("a_qb", "QB", 20), _mk("a_rb", "RB", 2)]
    b = [_mk("b_qb", "QB", 18), _mk("b_rb", "RB", 2)]
    pool = [*a, *b, _mk("f_rb", "RB", 30)]
    row = {"id": "no-slot", "teams": 2, "bench_slots": 1, "starting_slots": {"QB": 1}}
    res = se.evaluate_rosters(pool, [a, b], row, config=_cfg(upgrade_margin=0.0))
    assert res.waiver_adds.sum() == 0


def test_transaction_cost_boundary_semantics() -> None:
    # gain = (10 − 5) ppw × weeks_left 3 = 15 points of expected remaining-horizon
    # improvement. Just-below cost executes; equal and just-above must not (strict '>').
    positions = ["RB", "RB"]
    proj = np.array([5.0, 10.0])
    kw = dict(squad=[0], free=[1], positions=positions, proj=proj,
              known_out=np.zeros(2, dtype=bool), margin=0.0,
              slots={"RB": 1}, weeks_left=3)
    assert se._best_upgrade(**kw, cost=14.9) == (0, 1)
    assert se._best_upgrade(**kw, cost=15.0) is None
    assert se._best_upgrade(**kw, cost=15.1) is None


def test_emergency_claim_is_also_cost_gated(certain: None) -> None:
    # An unfillable RB slot would normally force a claim; a cost above the hole's
    # remaining-horizon value vetoes it.
    a = [_mk("a_qb", "QB", 20), _mk("a_rb", "RB", 15, bye=2), _mk("a_k", "K", 5)]
    b = [_mk("b_qb", "QB", 18), _mk("b_rb", "RB", 14), _mk("b_k", "K", 6)]
    pool = [*a, *b, _mk("f_rb", "RB", 1)]
    cheap = se.evaluate_rosters(pool, [a, b], _row(bench=0),
                                config=_cfg(proactive_moves_per_week=0))
    veto = se.evaluate_rosters(pool, [a, b], _row(bench=0),
                               config=_cfg(proactive_moves_per_week=0, waiver_cost=10_000.0))
    assert cheap.emergency_adds[0] >= 1
    assert veto.waiver_adds.sum() == 0


def _breakout_fixture(weeks: int, breakout_ppw: float):
    def mk(pid: str, pos: str, ppw: float, *, proj: float | None = None) -> se.SeasonPlayer:
        return se.SeasonPlayer(
            player_id=pid, position=pos, nfl_team="AAA", bye_week=0,
            points_if_plays=tuple([float(ppw)] * weeks),
            projection=float(proj if proj is not None else ppw * weeks), depth_rank=1,
        )

    a = [mk("a_qb", "QB", 20), mk("a_rb", "RB", 8), mk("a_bench", "RB", 6)]
    b = [mk("b_qb", "QB", 18), mk("b_rb", "RB", 7), mk("b_bench", "RB", 5)]
    # the breakout: preseason prior of 1 ppw — BELOW every incumbent — with high
    # realized weeks that only point-in-time observation can surface
    br = mk("f_break", "RB", breakout_ppw, proj=1.0 * weeks)
    row = {"id": "breakout", "teams": 2, "bench_slots": 1,
           "starting_slots": {"QB": 1, "RB": 1}}
    return [*a, *b, br], [a, b], row


def test_in_season_breakout_is_acquired_from_a_low_prior(certain: None) -> None:
    pool, rosters, row = _breakout_fixture(weeks=6, breakout_ppw=30.0)
    res = se.evaluate_rosters(pool, rosters, row, config=_cfg())
    assert res.upside_adds.sum() >= 1  # observations made the low prior actionable

    # trajectory proof 1: with only the preseason prior visible (single waiver window,
    # decided before any observation of the breakout reaches the forecast), no claim
    short_pool, short_rosters, short_row = _breakout_fixture(weeks=2, breakout_ppw=30.0)
    short = se.evaluate_rosters(short_pool, short_rosters, short_row, config=_cfg())
    assert short.upside_adds.sum() == 0

    # trajectory proof 2: the no-breakout control (same prior, mediocre weeks) never claims
    ctl_pool, ctl_rosters, ctl_row = _breakout_fixture(weeks=6, breakout_ppw=1.0)
    ctl = se.evaluate_rosters(ctl_pool, ctl_rosters, ctl_row, config=_cfg())
    assert ctl.upside_adds.sum() == 0


# ── C02A supplement: one shared weekly move budget (waiver-realism-v2) ────────


def _budget_fixture(rb_bye: int):
    # Seat 0 can face BOTH an emergency (RB bye hole — its only backup is a QB) and an
    # attractive upside upgrade (free K 10 over started K 5) in the same waiver window.
    a = [_mk("a_qb", "QB", 20), _mk("a_rb", "RB", 15, bye=rb_bye), _mk("a_k", "K", 5),
         _mk("a_bench", "QB", 3)]
    b = [_mk("b_qb", "QB", 18), _mk("b_rb", "RB", 14), _mk("b_k", "K", 9),
         _mk("b_bench", "RB", 8)]
    pool = [*a, *b, _mk("f_rb", "RB", 12), _mk("f_k", "K", 10)]
    return pool, [a, b]


def test_emergency_consumes_the_shared_weekly_budget(certain: None) -> None:
    pool, rosters = _budget_fixture(rb_bye=2)
    res = se.evaluate_rosters(pool, rosters, _row(bench=1),
                              config=_cfg(n_seasons=1))
    # week-1 window (weeks=4 → 3 windows): seat 0's emergency RB claim consumes the
    # entire default budget of 1, so its same-week K upgrade must NOT execute; the
    # remaining windows have no emergency, so the K stream lands later. Weekly totals
    # can therefore never exceed the budget:
    per_week_max = res.n_seasons * (WEEKS - 1)  # 3 windows × budget 1
    assert res.waiver_adds[0] * res.n_seasons <= per_week_max
    assert res.emergency_adds[0] >= 1
    assert np.allclose(res.waiver_adds, res.emergency_adds + res.upside_adds)


def test_budget_boundary_emergency_blocks_same_week_upside(certain: None) -> None:
    # Single waiver window (weeks=2): the emergency claim must win the one allowance
    # and the upside K upgrade must be blocked entirely.
    def mk2(pid, pos, ppw, bye=0):
        return se.SeasonPlayer(player_id=pid, position=pos, nfl_team="AAA", bye_week=bye,
                               points_if_plays=(float(ppw),) * 2, projection=ppw * 2.0,
                               depth_rank=1)
    a = [mk2("a_qb", "QB", 20), mk2("a_rb", "RB", 15, bye=2), mk2("a_k", "K", 5),
         mk2("a_bench", "QB", 3), mk2("a_bench2", "WR", 2)]
    b = [mk2("b_qb", "QB", 18), mk2("b_rb", "RB", 14), mk2("b_k", "K", 9),
         mk2("b_bench", "RB", 8), mk2("b_bench2", "WR", 6)]
    pool = [*a, *b, mk2("f_rb", "RB", 12), mk2("f_k", "K", 10)]
    res = se.evaluate_rosters(pool, [a, b], _row(bench=2), config=_cfg(n_seasons=1))
    assert res.emergency_adds[0] == 1  # the hole was patched…
    assert res.upside_adds[0] == 0  # …and the same-week upgrade was budget-blocked

    # control: no bye → no emergency → the same window executes the upside K upgrade
    a2 = [mk2("a_qb", "QB", 20), mk2("a_rb", "RB", 15), mk2("a_k", "K", 5),
          mk2("a_bench", "QB", 3), mk2("a_bench2", "WR", 2)]
    pool2 = [*a2, *b, mk2("f_rb", "RB", 12), mk2("f_k", "K", 10)]
    ctl = se.evaluate_rosters(pool2, [a2, b], _row(bench=2), config=_cfg(n_seasons=1))
    assert ctl.emergency_adds[0] == 0
    assert ctl.upside_adds[0] >= 1

    # a weekly budget of 2 permits both claim kinds in the same window
    both = se.evaluate_rosters(pool, [a, b], _row(bench=2),
                               config=_cfg(n_seasons=1, waiver_moves_per_week=2))
    assert both.emergency_adds[0] == 1
    assert both.upside_adds[0] >= 1


# ── C02B: laptop-2 production equivalents (waiver-realism-v3/v4) ──────────────


def test_dead_bench_body_dropped_for_cross_role_upgrade(certain: None) -> None:
    # Production equivalent of the laptop-2 case: a configuration-ineligible bench WR
    # (no WR slot exists in this row) is the roster-wide lowest nonstarter and is
    # dropped for a legal RB add — no shared role space required.
    positions = ["RB", "WR", "RB"]
    proj = np.array([100.0, 1.0, 20.0])
    swap = se._best_upgrade(squad=[0, 1], free=[2], positions=positions, proj=proj,
                            known_out=np.zeros(3, dtype=bool), margin=0.15,
                            slots={"RB": 1})
    assert swap == (1, 2)

    # end-to-end: only seat 0's dead WR clears the margin gate, so exactly that seat
    # executes the cross-role swap
    a = [_mk("a_rb", "RB", 25), _mk("a_wr", "WR", 1)]
    b = [_mk("b_rb", "RB", 24), _mk("b_wr", "WR", 11)]
    pool = [*a, *b, _mk("f_rb", "RB", 12)]
    row = {"id": "dead-body", "teams": 2, "bench_slots": 1, "starting_slots": {"RB": 1}}
    res = se.evaluate_rosters(pool, [a, b], row, config=_cfg())
    assert res.upside_adds.tolist() == [1.0, 0.0]


def test_combined_weekly_cap_production_equivalent(certain: None) -> None:
    # Production equivalent of the laptop-2 weekly-cap case, via the public config:
    # defaults (1, 1) permit ONE total claim per team-week even when an emergency and
    # an upside opportunity coexist; the budget formula is max(emergency, proactive).
    positions = ["RB", "K", "RB", "K"]
    projections = np.array([10.0, 1.0, 8.0, 10.0])
    squads = [[0, 1]]
    free = [2, 3]
    emergency, upside = se._run_waivers(
        squads, free, np.zeros(1), {"RB": 1, "K": 1}, positions, projections,
        known_out=np.array([True, False, False, False]), limit=1, cap=2,
        proactive_limit=1, upgrade_margin=0.15, moves_left=np.array([10]),
    )
    assert (emergency + upside).tolist() == [1.0]
    assert emergency.tolist() == [1.0]  # the emergency won the shared allowance
