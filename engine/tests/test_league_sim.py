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
