"""Tests for E3-league-sim — the full 12-team season sim, playoff bracket + SOS.

Fast + deterministic (numpy RNG, streamed). Covers: the fixed seeding bracket (byes +
higher-score-advances), the season sim's playoff/championship accounting (exactly
``playoff_teams`` make the playoffs each season, championship mass sums to 1), monotonicity
(a stronger roster wins the league more often), the streaming memory bound (peak independent
of season count), the distributional SOS accessor, the bye-week interaction, and the E7
`calibrated` gate on the shared correlated sampler.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from blitz_engine.calibration import calibrated
from blitz_engine.simulation import (
    LeagueConfig,
    Roster,
    build_bracket,
    sample_correlated,
    simulate_league,
)
from blitz_engine.simulation.correlation import build_correlation, cholesky_factor

_POS_CYCLE = ("QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DST")
_STARTER_POS = ("QB", "RB", "RB", "WR", "WR", "TE", "WR", "K", "DST")


# ── fixtures ─────────────────────────────────────────────────────────────────────
def round_robin(ids: list[str]) -> list[list[tuple[str, str]]]:
    """Circle-method single round-robin (n-1 weeks) for an even number of teams."""
    arr = list(ids)
    n = len(arr)
    weeks = []
    for _ in range(n - 1):
        weeks.append([(arr[i], arr[n - 1 - i]) for i in range(n // 2)])
        arr = [arr[0], arr[-1], *arr[1:-1]]
    return weeks


def make_league(
    n_teams: int = 12, seed: int = 0
) -> tuple[pd.DataFrame, pd.DataFrame, list[Roster], list[list[tuple[str, str]]]]:
    """12 rosters of 9 starters; team strength rises with team index (monotone ladder)."""
    rng = np.random.default_rng(seed)
    rows, rosters = [], []
    for t in range(n_teams):
        starters = []
        for k, pos in enumerate(_STARTER_POS):
            pid = f"T{t}_P{k}"
            base = 8.0 + 1.2 * t + rng.uniform(-0.5, 0.5)  # strength ladder in t
            rows.append({
                "player_id": pid, "position": pos, "team": f"NFL{t}",
                "mean": base, "stdev": max(base * 0.5, 3.0),
            })
            starters.append(pid)
        rosters.append(Roster(id=f"team{t}", starters=tuple(starters)))
    df = pd.DataFrame(rows)
    marginals = df[["player_id", "mean", "stdev"]].copy()
    players = df[["player_id", "position", "team"]].copy()
    schedule = round_robin([r.id for r in rosters])
    return marginals, players, rosters, schedule


# ── playoff bracket (unit) ───────────────────────────────────────────────────────
def test_bracket_shape_byes() -> None:
    b = build_bracket(6)
    assert b.n_rounds == 3
    assert b.n_byes == 2  # 8-slot bracket, top 2 seeds bye
    assert build_bracket(4).n_byes == 0
    assert build_bracket(8).n_rounds == 3


def test_bracket_top_seed_wins_when_dominant() -> None:
    # Seed 0 always scores highest in every round -> always champion.
    b = build_bracket(6)
    scores = np.tile(np.arange(6, 0, -1, dtype=float), (5, 3, 1))  # seed 0 = 6 (best)
    champ, (fa, fb) = b.resolve(scores)
    assert (champ == 0).all()
    assert set(np.unique(np.concatenate([fa, fb]))) <= {0, 1}  # the two bye seeds reach final


def test_bracket_tie_breaks_to_better_seed() -> None:
    b = build_bracket(4)
    scores = np.ones((3, 2, 4), dtype=float)  # every seed ties every round
    champ, _ = b.resolve(scores)
    assert (champ == 0).all()  # ties advance the better (lower-index) seed


# ── league season sim ────────────────────────────────────────────────────────────
def test_playoff_and_championship_accounting() -> None:
    marg, players, rosters, sched = make_league()
    res = simulate_league(
        marg, players, rosters, sched, config=LeagueConfig(n_seasons=3_000, playoff_teams=6)
    )
    st = res.standings
    assert len(st) == 12
    # exactly 6 rosters make the playoffs each season
    assert abs(st["p_playoffs"].sum() - 6.0) < 1e-9
    # exactly one champion per season
    assert abs(st["p_champion"].sum() - 1.0) < 1e-9
    # two bye teams, two finalists per season
    assert abs(st["p_bye"].sum() - 2.0) < 1e-9
    assert abs(st["p_final"].sum() - 2.0) < 1e-9
    assert (st["p_champion"] <= st["p_final"] + 1e-9).all()
    assert (st["p_final"] <= st["p_playoffs"] + 1e-9).all()


def test_stronger_roster_wins_more() -> None:
    marg, players, rosters, sched = make_league()
    res = simulate_league(
        marg, players, rosters, sched, config=LeagueConfig(n_seasons=4_000)
    )
    p_champ = res.p_champion()
    # the top-strength roster (team11) should out-champion the weakest (team0)
    assert p_champ["team11"] > p_champ["team0"]
    assert p_champ["team11"] == p_champ.max()
    assert res.p_playoffs()["team11"] > res.p_playoffs()["team0"]


def test_memory_bounded_peak_independent_of_seasons() -> None:
    marg, players, rosters, sched = make_league()
    small = simulate_league(marg, players, rosters, sched,
                            config=LeagueConfig(n_seasons=1_000, batch_seasons=500))
    big = simulate_league(marg, players, rosters, sched,
                          config=LeagueConfig(n_seasons=8_000, batch_seasons=500))
    assert small.peak_bytes == big.peak_bytes  # peak set by batch, not season count
    assert small.within_budget and big.within_budget
    assert not small.cloud_burst_suggested


def test_tiny_budget_degrades_batch_and_flags_burst() -> None:
    marg, players, rosters, sched = make_league()
    res = simulate_league(
        marg, players, rosters, sched,
        config=LeagueConfig(n_seasons=600, batch_seasons=600, min_batch=50,
                            memory_budget_bytes=200_000),
    )
    assert res.batch_seasons < 600  # degraded to fit the tiny budget
    assert res.cloud_burst_suggested


# ── distributional SOS ───────────────────────────────────────────────────────────
def test_sos_distributional_accessor() -> None:
    marg, players, rosters, sched = make_league()
    res = simulate_league(marg, players, rosters, sched,
                          config=LeagueConfig(n_seasons=2_000))
    sos = res.strength_of_schedule()
    assert set(sos["roster_id"]) == {r.id for r in rosters}
    assert {"opp_mean", "opp_std", "sos", "sos_z"} <= set(sos.columns)
    assert abs(sos["sos_z"].mean()) < 1e-6  # z-scored across the league
    assert (sos["opp_std"] > 0).all()  # opponents vary -> a real distribution


def test_latent_sos_hook_optional() -> None:
    marg, players, rosters, sched = make_league()
    difficulty = pd.Series({pid: 0.3 for pid in marg["player_id"]})
    res = simulate_league(marg, players, rosters, sched,
                          config=LeagueConfig(n_seasons=800), difficulty=difficulty)
    assert "latent_sos" in res.sos.columns
    # log-mean-exp of a constant 0.3 == 0.3
    assert np.allclose(res.sos["latent_sos"].to_numpy(), 0.3, atol=1e-6)


# ── bye-week interaction ─────────────────────────────────────────────────────────
def test_bye_week_zeroes_starter_and_cuts_points() -> None:
    marg, players, rosters, sched = make_league()
    cfg = LeagueConfig(n_seasons=1_500)
    base = simulate_league(marg, players, rosters, sched, config=cfg)
    # put every one of team5's starters on bye in regular week 0
    byes = {pid: 0 for pid in rosters[5].starters}
    hurt = simulate_league(marg, players, rosters, sched, config=cfg, byes=byes)
    b_pts = base.standings.set_index("roster_id").loc["team5", "avg_points"]
    h_pts = hurt.standings.set_index("roster_id").loc["team5", "avg_points"]
    assert h_pts < b_pts  # lost a full week of starters


# ── playoff-week value weighting (default-neutral knob) ──────────────────────────
def test_playoff_week_weight_amplifies_playoff_value_and_composes_with_bye() -> None:
    marg, players, rosters, sched = make_league()  # team11 = strongest -> peaks in playoffs
    n_reg = len(sched)  # regular weeks; playoff weeks are indices n_reg..n_reg+n_rounds-1
    neutral = simulate_league(
        marg, players, rosters, sched,
        config=LeagueConfig(n_seasons=2_000, playoff_week_weight=1.0),
    )
    heavy = simulate_league(
        marg, players, rosters, sched,
        config=LeagueConfig(n_seasons=2_000, playoff_week_weight=3.0),
    )
    nv = neutral.standings.set_index("roster_id")["weighted_value"]
    hv = heavy.standings.set_index("roster_id")["weighted_value"]
    # weighting playoff weeks (>1.0) strictly lifts value — positive playoff-week scoring
    assert (hv > nv + 1e-6).all()
    # and amplifies the strong roster's playoff-week edge over the weak one
    assert (hv["team11"] - hv["team0"]) > (nv["team11"] - nv["team0"]) + 1e-6

    # compose with a bye landing in a playoff week: the starter zeroes that week, then the
    # weight applies to the remaining (non-bye) playoff-week production -> a larger drop
    # under the heavier weight.
    byes = {pid: n_reg for pid in rosters[11].starters}  # first playoff week
    heavy_bye = simulate_league(
        marg, players, rosters, sched,
        config=LeagueConfig(n_seasons=2_000, playoff_week_weight=3.0), byes=byes,
    )
    neutral_bye = simulate_league(
        marg, players, rosters, sched,
        config=LeagueConfig(n_seasons=2_000, playoff_week_weight=1.0), byes=byes,
    )
    hb = heavy_bye.standings.set_index("roster_id")["weighted_value"]
    nb = neutral_bye.standings.set_index("roster_id")["weighted_value"]
    drop_heavy = hv["team11"] - hb["team11"]
    drop_neutral = nv["team11"] - nb["team11"]
    assert drop_heavy > drop_neutral + 1e-6  # weight scales the zeroed playoff-week loss


# ── E7 calibration on the shared correlated sampler ──────────────────────────────
def test_league_sampler_calibrated() -> None:
    # The league sim draws player-weeks through mc-core's `sample_correlated`; a realised
    # draw from the sim's own marginals must pass the E7 `calibrated` gate.
    rng = np.random.default_rng(11)
    p = 800
    mean = rng.uniform(4.0, 30.0, p)
    sd = rng.uniform(3.0, 9.0, p)
    ids = [f"p{i}" for i in range(p)]
    meta = pd.DataFrame({"player_id": ids, "position": "WR", "team": "AAA"})
    chol = cholesky_factor(build_correlation(meta))
    realized = sample_correlated(mean, sd, chol, 1, rng)[0]
    q = pd.DataFrame({"player_id": ids, "mean": mean, "stdev": sd})
    assert calibrated(q, realized)


# ── E5: the imperfect-information season evaluator (THE eval fix) ─────────────────
# These are the acceptance tests for the metric every later v5 fit is scored against.
# See `blitz_engine/simulation/season_eval.py` for what the metric means.
import pytest  # noqa: E402

from blitz_engine.backtest.ablation import paired_permutation_p  # noqa: E402
from blitz_engine.backtest.harness import LeakageError  # noqa: E402
from blitz_engine.simulation import season_eval as se  # noqa: E402
from blitz_engine.testing import corpus, matrix  # noqa: E402

_ROW = "t12-1qb-half-te0.5-b8-ir0"  # 12-team, 8 bench — enough bench for insurance to exist
_YEAR = corpus.GOLDEN_SEASON


@pytest.fixture(scope="module")
def eval_pool() -> list[se.SeasonPlayer]:
    return se.build_players(_YEAR, _ROW)


def test_same_seed_reproduces_the_season_exactly(eval_pool: list[se.SeasonPlayer]) -> None:
    # One seed drives draft seats, injury paths, availability draws and waiver order.
    row = matrix.by_id(_ROW)
    cfg = se.EvalConfig(n_seasons=2, seed=se.SEASON_EVAL_SEED)
    a = se.evaluate_season(_YEAR, row, config=cfg, players=eval_pool)
    b = se.evaluate_season(_YEAR, row, config=cfg, players=eval_pool)
    assert np.array_equal(a.per_season, b.per_season)  # bit-identical, not merely close
    assert a.seat_policy == b.seat_policy
    other = se.evaluate_season(
        _YEAR, row, config=se.EvalConfig(n_seasons=2, seed=se.SEASON_EVAL_SEED + 1),
        players=eval_pool,
    )
    assert not np.array_equal(a.per_season, other.per_season)  # the seed is load-bearing


def test_leaked_lineup_decision_trips_the_guard(eval_pool: list[se.SeasonPlayer]) -> None:
    # Lineups are time-honest MECHANICALLY: a decision frame that contains the week being
    # decided must raise, not silently inflate the score.
    row = matrix.by_id(_ROW)
    cfg = se.EvalConfig(n_seasons=1)
    rosters, seats = se.draft_league(eval_pool, row, seed=cfg.seed)
    se.evaluate_rosters(eval_pool, rosters, row, seat_policy=seats, config=cfg)  # clean run
    with pytest.raises(LeakageError):
        se.evaluate_rosters(
            eval_pool, rosters, row, seat_policy=seats, config=cfg, leak={"week": 5}
        )


def test_mixed_policy_h2h_is_non_degenerate(eval_pool: list[se.SeasonPlayer]) -> None:
    # The retired harness ran all 12 seats on ONE policy, so H2H was 50% by construction.
    # With a documented policy mix the strongest policy must beat 50% across seeds.
    row = matrix.by_id(_ROW)
    by_policy: dict[str, list[float]] = {p: [] for p in se.policy_names()}
    for k in range(4):
        res = se.evaluate_season(
            _YEAR, row, config=se.EvalConfig(n_seasons=2, seed=se.SEASON_EVAL_SEED + 97 * k),
            players=eval_pool,
        )
        for pol, rate in zip(res.seat_policy, res.h2h_win_rate, strict=True):
            by_policy[pol].append(float(rate))
    means = {p: float(np.mean(v)) for p, v in by_policy.items()}
    best = max(means, key=lambda p: means[p])
    assert means[best] > 0.52, means  # not 50% by construction any more
    diffs = np.asarray(by_policy[best]) - 0.5
    assert paired_permutation_p(diffs, seed=3) < 0.05, (means, diffs.mean())
    assert len(set(np.round(list(means.values()), 4))) == len(means)  # policies are distinct


def test_bench_insurance_moves_the_new_metric_and_not_hindsight(
    eval_pool: list[se.SeasonPlayer],
) -> None:
    # THE acceptance test. Two arms draft identical starters from the same board and the same
    # talent band; only the BENCH differs (cover vs deliberately non-covering). The
    # imperfect-information metric must see it. The retired perfect-hindsight metric must not.
    row = matrix.by_id(_ROW)
    cfg = se.EvalConfig(n_seasons=12)
    arms, hind, drafts = {}, {}, {}
    for cover in (True, False):
        rosters, seats = se.draft_league(
            eval_pool, row, seed=cfg.seed, pick_fn=se.bench_cover_pick_fn(cover)
        )
        drafts[cover] = rosters
        arms[cover] = se.evaluate_rosters(
            eval_pool, rosters, row, seat_policy=seats, config=cfg
        )
        hind[cover] = se.hindsight_points(eval_pool, rosters, row)
    starters = sum(int(n) for n in row["starting_slots"].values())
    # the arms really are matched on starters — the ablation is a pure BENCH ablation
    assert [p.player_id for p in drafts[True][0][:starters]] == [
        p.player_id for p in drafts[False][0][:starters]
    ]

    new_delta = arms[True].metric - arms[False].metric
    new_p = paired_permutation_p((arms[True].per_season - arms[False].per_season).ravel(), seed=1)
    hind_delta = float((hind[True] - hind[False]).mean())
    hind_p = paired_permutation_p(hind[True] - hind[False], seed=1)

    assert new_delta > 0.0, new_delta
    assert new_p < 0.05, (new_delta, new_p)  # the new metric MOVES — the eval is fixed
    assert hind_p >= 0.05, (hind_delta, hind_p)  # the old metric is blind to bench insurance
    # and the bench actually did its job: fewer starting slots lost to a hole
    assert arms[True].starts_lost.mean() < arms[False].starts_lost.mean()


@pytest.mark.parametrize("row", matrix.smoke(), ids=lambda r: r["id"])
def test_smoke_matrix_row_evaluates(row: dict) -> None:
    # Cost discipline (v5-architecture §3): the DoD path runs `matrix.smoke()` (16 rows) at one
    # sampled season each; `matrix.all()` (432 rows) sits behind BLITZ_EVAL_FULL=1.
    res = se.evaluate_season(_YEAR, row, config=se.EvalConfig(n_seasons=1))
    assert res.started_points.shape == (row["teams"],)
    assert np.all(res.started_points > 0.0)
    assert abs(float(res.h2h_win_rate.mean()) - 0.5) < 1e-9  # H2H is zero-sum by construction
    assert res.per_season.dtype == np.float64


@pytest.mark.skipif(not se.full_sweep_enabled(), reason="set BLITZ_EVAL_FULL=1 for the full sweep")
def test_full_matrix_sweep() -> None:
    for row in matrix.all():
        res = se.evaluate_season(_YEAR, row, config=se.EvalConfig(n_seasons=1))
        assert np.all(res.started_points > 0.0), row["id"]


def test_uncertainty_is_read_from_the_fitted_models_not_hardcoded(
    eval_pool: list[se.SeasonPlayer],
) -> None:
    # No availability or injury number lives in this module: both arrive through the public
    # interfaces, and e3's fixture must still say the event is CLINICAL injury (otherwise
    # multiplying it by e2a's availability would double-count one signal).
    from blitz_engine.lineup.feasibility import InjuryDynamics

    dyn = InjuryDynamics.load()
    assert "clinical" in dyn.event.lower()
    row = matrix.by_id(_ROW)
    real = se.evaluate_season(_YEAR, row, config=se.EvalConfig(n_seasons=3), players=eval_pool)
    healthy = se.evaluate_season(
        _YEAR, row,
        config=se.EvalConfig(n_seasons=3, injury=InjuryDynamics.healthy()),
        players=eval_pool,
    )
    assert healthy.metric > real.metric  # turning e3's model off is visible in the metric
    assert healthy.starts_lost.mean() < real.starts_lost.mean()
