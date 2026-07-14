"""Full 12-team league season simulation (E3) — playoffs + championship equity + SOS.

Turns E1's per-player marginals and E3-mc-core's correlated draws into **league**
intelligence: it plays every roster through its actual schedule for tens of thousands of
Monte-Carlo seasons, seeds a playoff bracket, and reduces the whole thing to per-roster
``P(make playoffs)`` / ``P(win league)`` plus a distributional strength-of-schedule.

Design (docs/design/v4-engine-architecture.md §"M1"): **reuse mc-core's streaming — never
re-materialise.** One correlated within-week draw is the primitive (`sample_correlated`);
weeks are independent, so a season is ``total_weeks`` such draws. Seasons stream in batches
and collapse to integer counters (playoff / bye / final / championship) plus running
opponent-score moments; peak memory is one batch of draws
(``batch × total_weeks × players × float32``), independent of the season count — mc-core's
memory contract, carried up to the league.

`ponytail:` win-counting, seeding and the bracket are numpy fancy-indexing over the batch;
the season loop is a loop, not a framework, and the bracket lives in `playoffs.py`.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt
import pandas as pd

from blitz_engine.simulation.correlation import (
    CorrelationSpec,
    build_correlation,
    cholesky_factor,
)
from blitz_engine.simulation.mc import sample_correlated
from blitz_engine.simulation.playoffs import build_bracket

__all__ = [
    "LeagueConfig",
    "LeagueResult",
    "Roster",
    "simulate_league",
]

# Bytes touched per draw-cell across the transient batch arrays (draws, bye-masked copy,
# the reshape into team scores) — used only to estimate peak and pick a safe batch.
_BYTES_PER_CELL = 3 * 4
_KEY_SCALE = 1.0e7  # standings key = wins * scale + points_for (points_for << scale)


@dataclass(frozen=True)
class Roster:
    """One fantasy team: an id and the ``player_id``s it starts every week.

    Starters are summed to the roster's weekly score. Players absent from the marginals
    contribute zero (degrade-neutral). Bye handling (a starter on their NFL bye scoring
    zero that week) is driven by the optional ``byes`` map passed to `simulate_league`.
    """

    id: str
    starters: tuple[str, ...]


@dataclass(frozen=True)
class LeagueConfig:
    """Knobs for one league sim. ``n_seasons`` is the adaptive-scale dial."""

    n_seasons: int = 20_000
    playoff_teams: int = 6
    seed: int = 20240813
    batch_seasons: int = 2_000
    memory_budget_bytes: int = 12 * 1024**3  # under the 16 GB machine budget
    min_batch: int = 100  # smallest season-batch before suggesting a cloud-burst
    sos_risk_lambda: float = 0.5  # nonlinear SOS risk-adjust: mean + lambda * std
    tie_on_points: bool = True  # standings tiebreak by season points-for
    playoff_week_weight: float = 1.0  # value weight on playoff-week scoring (1.0 = neutral)


_DEFAULT_SPEC = CorrelationSpec()
_DEFAULT_CONFIG = LeagueConfig()


@dataclass(frozen=True)
class LeagueResult:
    """Per-roster season outcomes + the distributional strength-of-schedule."""

    standings: pd.DataFrame  # +p_playoffs/p_bye/p_final/p_champion/avg_wins/pf/weighted_value
    sos: pd.DataFrame  # roster_id + opp_mean/opp_std/sos/sos_z (+ latent_sos if supplied)
    n_seasons: int
    batch_seasons: int  # the (possibly degraded) batch actually streamed
    peak_bytes: int  # estimated peak resident bytes of the streaming reduction
    cloud_burst_suggested: bool
    within_budget: bool = field(default=True)

    def p_playoffs(self) -> pd.Series:
        """``roster_id -> P(make playoffs)``."""
        return self.standings.set_index("roster_id")["p_playoffs"]

    def p_champion(self) -> pd.Series:
        """``roster_id -> P(win league)`` — the base for E4 championship equity."""
        return self.standings.set_index("roster_id")["p_champion"]

    def strength_of_schedule(self) -> pd.DataFrame:
        """The distributional SOS table (opponent-score moments + nonlinear risk-adjust)."""
        return self.sos


def _plan_batch(
    total_weeks: int, p: int, cfg: LeagueConfig
) -> tuple[int, int, bool]:
    """Pick a season-batch that fits the budget; return (batch, peak_bytes, cloud_burst)."""
    per_season = total_weeks * p * _BYTES_PER_CELL
    room = cfg.memory_budget_bytes
    want = min(cfg.batch_seasons, cfg.n_seasons)
    feasible = int(room // max(per_season, 1))
    batch = max(cfg.min_batch, min(want, feasible))
    peak = batch * per_season
    suggested = feasible < cfg.min_batch or batch < want
    return batch, peak, suggested


def _align_universe(
    marginals: pd.DataFrame, players: pd.DataFrame, rosters: Sequence[Roster]
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Player universe = starters present in BOTH marginals and players meta, in order."""
    marg = marginals.copy()
    marg["player_id"] = marg["player_id"].astype(str)
    meta = players.copy()
    meta["player_id"] = meta["player_id"].astype(str)
    wanted: list[str] = []
    seen: set[str] = set()
    for r in rosters:
        for pid in r.starters:
            pid = str(pid)
            if pid not in seen:
                seen.add(pid)
                wanted.append(pid)
    df = (
        meta.merge(marg[["player_id", "mean", "stdev"]], on="player_id", how="inner")
        .set_index("player_id")
        .reindex([w for w in wanted if w in set(meta["player_id"]) & set(marg["player_id"])])
        .reset_index()
    )
    if df.empty:
        raise ValueError("no rostered players found in both `marginals` and `players`")
    index = {pid: i for i, pid in enumerate(df["player_id"])}
    return df, index


def _starter_matrix(
    rosters: Sequence[Roster], index: Mapping[str, int], p: int
) -> npt.NDArray[np.float32]:
    """0/1 ``(n_teams x P)`` matrix: which players each roster starts every week."""
    w = np.zeros((len(rosters), p), dtype=np.float32)
    for t, r in enumerate(rosters):
        for pid in r.starters:
            j = index.get(str(pid))
            if j is not None:
                w[t, j] = 1.0
    return w


def _bye_mask(
    byes: Mapping[str, int] | None, index: Mapping[str, int], total_weeks: int, p: int
) -> npt.NDArray[np.float32] | None:
    """``(total_weeks x P)`` 1/0 availability mask (0 where a player is on their NFL bye)."""
    if not byes:
        return None
    mask = np.ones((total_weeks, p), dtype=np.float32)
    for pid, wk in byes.items():
        j = index.get(str(pid))
        if j is not None and 0 <= int(wk) < total_weeks:
            mask[int(wk), j] = 0.0
    return mask


def simulate_league(
    marginals: pd.DataFrame,
    players: pd.DataFrame,
    rosters: Sequence[Roster],
    schedule: Sequence[Sequence[tuple[str, str]]],
    *,
    corr: pd.DataFrame | None = None,
    spec: CorrelationSpec = _DEFAULT_SPEC,
    config: LeagueConfig = _DEFAULT_CONFIG,
    byes: Mapping[str, int] | None = None,
    difficulty: pd.Series | Mapping[str, float] | None = None,
) -> LeagueResult:
    """Monte-Carlo a full league season → per-roster playoff / championship odds + SOS.

    ``marginals``: ``player_id``, ``mean``, ``stdev`` (from ``Projection.quantiles``).
    ``players``:   ``player_id``, ``position``, ``team`` (+ optional ``opponent``) — the
                   correlation universe, exactly as mc-core's `simulate` consumes.
    ``rosters``:   the fantasy teams (each an id + its weekly starters).
    ``schedule``:  the **regular season** — a sequence of weeks, each a sequence of
                   ``(home_roster_id, away_roster_id)`` matchups. Playoff weeks are the
                   bracket's rounds, simulated after the regular season.
    ``byes``:      optional ``player_id -> week index`` (0-based over regular+playoff weeks)
                   NFL bye map — a bye starter scores zero that week (bye-week interaction).
    ``difficulty``: optional ``player_id -> matchup-difficulty`` (e.g. E1-latents
                   ``defense_strength``); adds a nonlinear latent-defense SOS column,
                   degrade-neutral when omitted.

    Streams ``config.n_seasons`` seasons in memory-bounded batches (mc-core's streaming),
    accumulating integer counters + opponent-score moments only.
    """
    df, index = _align_universe(marginals, players, rosters)
    pid = df["player_id"].to_numpy(dtype=object)
    p = len(pid)
    mean = df["mean"].to_numpy(dtype=np.float64)
    sd = np.clip(df["stdev"].to_numpy(dtype=np.float64), 1e-9, None)

    if corr is None:
        corr = build_correlation(df, spec)
    else:
        corr = corr.loc[list(pid), list(pid)]
    chol = cholesky_factor(corr)

    team_ids = [r.id for r in rosters]
    n_teams = len(rosters)
    w_mat = _starter_matrix(rosters, index, p)

    bracket = build_bracket(config.playoff_teams)
    n_reg = len(schedule)
    total_weeks = n_reg + bracket.n_rounds
    if n_teams < config.playoff_teams:
        raise ValueError("playoff_teams exceeds the number of rosters")

    # Flatten the regular-season schedule into parallel matchup arrays.
    tid_ix = {t: i for i, t in enumerate(team_ids)}
    wk_list, home_list, away_list = [], [], []
    for wk, week in enumerate(schedule):
        for home, away in week:
            wk_list.append(wk)
            home_list.append(tid_ix[home])
            away_list.append(tid_ix[away])
    mw = np.asarray(wk_list, dtype=np.int64)
    mh = np.asarray(home_list, dtype=np.int64)
    ma = np.asarray(away_list, dtype=np.int64)

    bye_mask = _bye_mask(byes, index, total_weeks, p)
    batch, peak, burst = _plan_batch(total_weeks, p, config)
    rng = np.random.default_rng(config.seed)

    # ── streaming counters ────────────────────────────────────────────────
    playoff_ct = np.zeros(n_teams, dtype=np.int64)
    bye_ct = np.zeros(n_teams, dtype=np.int64)
    final_ct = np.zeros(n_teams, dtype=np.int64)
    champ_ct = np.zeros(n_teams, dtype=np.int64)
    wins_sum = np.zeros(n_teams, dtype=np.float64)
    pf_sum = np.zeros(n_teams, dtype=np.float64)
    playoff_pf_sum = np.zeros(n_teams, dtype=np.float64)  # own scoring in playoff weeks only
    opp_sum = np.zeros(n_teams, dtype=np.float64)
    opp_sq = np.zeros(n_teams, dtype=np.float64)

    done = 0
    while done < config.n_seasons:
        b = min(batch, config.n_seasons - done)
        draws = sample_correlated(mean, sd, chol, b * total_weeks, rng)  # (b*W, P) f32
        if bye_mask is not None:
            draws = draws.reshape(b, total_weeks, p) * bye_mask[None]
            flat = draws.reshape(b * total_weeks, p)
        else:
            flat = draws
        # team scores: (b*W, P) @ (P, n_teams) -> (b, W, n_teams)
        scores = (flat @ w_mat.T).reshape(b, total_weeks, n_teams)

        reg = scores[:, :n_reg, :]
        rows = np.arange(b)[:, None]
        hs = scores[:, mw, mh]  # (b, M)
        as_ = scores[:, mw, ma]
        h_win = (hs > as_).astype(np.float64) + 0.5 * (hs == as_)
        a_win = (as_ > hs).astype(np.float64) + 0.5 * (hs == as_)
        np.add.at(wins_sum, mh[None, :].repeat(b, 0), h_win)
        np.add.at(wins_sum, ma[None, :].repeat(b, 0), a_win)
        pf_sum += reg.sum(axis=(0, 1))
        playoff_pf_sum += scores[:, n_reg:, :].sum(axis=(0, 1))  # value-weight seam
        # opponent-score moments (each team faces one opponent per regular week)
        np.add.at(opp_sum, mh[None, :].repeat(b, 0), as_)
        np.add.at(opp_sum, ma[None, :].repeat(b, 0), hs)
        np.add.at(opp_sq, mh[None, :].repeat(b, 0), as_ * as_)
        np.add.at(opp_sq, ma[None, :].repeat(b, 0), hs * hs)

        # season standings key + seeding (descending)
        season_wins = np.zeros((b, n_teams), dtype=np.float64)
        np.add.at(season_wins, (rows, mh[None, :]), h_win)
        np.add.at(season_wins, (rows, ma[None, :]), a_win)
        season_pf = reg.sum(axis=1)  # (b, n_teams)
        key = season_wins * _KEY_SCALE + (season_pf if config.tie_on_points else 0.0)
        seed_team = np.argsort(-key, axis=1, kind="stable")  # (b, n_teams), [:,0]=best
        top = seed_team[:, : config.playoff_teams]
        np.add.at(playoff_ct, top.reshape(-1), 1)
        if bracket.n_byes:
            np.add.at(bye_ct, seed_team[:, : bracket.n_byes].reshape(-1), 1)

        # playoff rounds: gather each seed's score in each round's week
        seed_scores = np.empty((b, bracket.n_rounds, config.playoff_teams), dtype=np.float64)
        for r in range(bracket.n_rounds):
            wk_scores = scores[:, n_reg + r, :]  # (b, n_teams)
            seed_scores[:, r, :] = np.take_along_axis(wk_scores, top, axis=1)
        champ_seed, (fa_seed, fb_seed) = bracket.resolve(seed_scores)
        champ_team = np.take_along_axis(top, champ_seed[:, None], axis=1)[:, 0]
        np.add.at(champ_ct, champ_team, 1)
        for f in (fa_seed, fb_seed):
            np.add.at(final_ct, np.take_along_axis(top, f[:, None], axis=1)[:, 0], 1)

        done += b

    inv = 1.0 / config.n_seasons
    # Full-season roster value with the playoff-week weighting knob (1.0 = neutral: the
    # plain regular+playoff points total; >1.0 amplifies playoff-week starter production).
    weighted_value = (pf_sum + config.playoff_week_weight * playoff_pf_sum) * inv
    reg_obs = config.n_seasons * n_reg  # opponents faced per team over all seasons
    opp_mean = opp_sum / reg_obs
    opp_var = np.clip(opp_sq / reg_obs - opp_mean**2, 0.0, None)
    opp_std = np.sqrt(opp_var)
    sos = opp_mean + config.sos_risk_lambda * opp_std  # nonlinear risk-adjusted SOS
    sos_z = (sos - sos.mean()) / (sos.std() + 1e-12)

    standings = pd.DataFrame(
        {
            "roster_id": team_ids,
            "p_playoffs": playoff_ct * inv,
            "p_bye": bye_ct * inv,
            "p_final": final_ct * inv,
            "p_champion": champ_ct * inv,
            "avg_wins": wins_sum * inv,
            "avg_points": pf_sum * inv,
            "weighted_value": weighted_value,
        }
    ).sort_values("p_champion", ascending=False, ignore_index=True)

    sos_df = pd.DataFrame(
        {
            "roster_id": team_ids,
            "opp_mean": opp_mean,
            "opp_std": opp_std,
            "sos": sos,
            "sos_z": sos_z,
        }
    )
    if difficulty is not None:
        sos_df["latent_sos"] = _latent_sos(rosters, difficulty)
    sos_df = sos_df.sort_values("sos", ascending=False, ignore_index=True)

    return LeagueResult(
        standings=standings,
        sos=sos_df,
        n_seasons=config.n_seasons,
        batch_seasons=batch,
        peak_bytes=peak,
        cloud_burst_suggested=burst,
        within_budget=peak <= config.memory_budget_bytes,
    )


def _latent_sos(
    rosters: Sequence[Roster], difficulty: pd.Series | Mapping[str, float]
) -> npt.NDArray[np.float64]:
    """Nonlinear latent-defense SOS: log-mean-exp of each roster's starter difficulties.

    The E1-latents seam — pass its ``defense_strength``-derived per-player matchup
    difficulty and each roster's schedule strength surfaces as a soft-max-weighted (hence
    nonlinear, tail-sensitive) aggregate. Degrade-neutral: unknown players contribute 0.
    """
    s = pd.Series(difficulty, dtype=float) if not isinstance(difficulty, pd.Series) else difficulty
    s.index = s.index.astype(str)
    out = np.zeros(len(rosters), dtype=np.float64)
    for t, r in enumerate(rosters):
        vals = np.array([float(s.get(str(pid), 0.0)) for pid in r.starters], dtype=np.float64)
        if vals.size:
            out[t] = float(np.log(np.mean(np.exp(vals))))  # log-mean-exp (nonlinear)
    return out
