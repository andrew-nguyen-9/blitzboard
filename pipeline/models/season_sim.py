"""
SeasonSimulator — season-long Monte Carlo of fantasy-point distributions (v3 Epic 12.2).

NET-NEW model, distinct from value_engine.MonteCarloEngine (which samples ONE season
total per player from a projection mean/σ to PRICE the board). This one models the three
things that actually shape a full season for a single player:

  • injury / availability  — games_played ~ Binomial(games_slate, 1 − injury_rate)
  • usage                  — per-game mean points (ppg_mean)
  • week-to-week variance  — per-game σ (ppg_stdev)

→ a per-player season-total distribution → floor / ceiling / boom-bust.

Math: a season total is the sum of `g` played games, each ~Normal(μ, σ). The sum of g
iid normals is Normal(g·μ, √g·σ), so we sample games first, then draw the season total in
closed form instead of μ·σ over 17×N per-game draws — same distribution, a fraction of the
work (ponytail: closed-form sum-of-normals). Totals are clipped at 0 (no negative seasons).

Validated out-of-sample vs actual 2015-2025 in backtest/models_backtest.py.

  python tests/test_season_sim.py   # plain-assert self-check
"""
from __future__ import annotations

from dataclasses import dataclass

GAMES_SLATE = 17  # full NFL regular season

# Per-GAME probability a player misses the game (availability = 1 − this). Position
# priors from historical games-missed rates; RBs take the most contact, team D/ST never
# "miss". ponytail: priors, not per-player medicine — pass injury_rate to override when a
# real availability signal exists (depth-chart / IR feed).
INJURY_RATE = {"RB": 0.11, "WR": 0.075, "TE": 0.085, "QB": 0.06, "K": 0.02, "DST": 0.0}
DEFAULT_INJURY_RATE = 0.08

BOOM_MULT = 1.25  # season > 1.25× its own median = "boom"
BUST_MULT = 0.75  # season < 0.75× its own median = "bust"


@dataclass
class SimInput:
    player_id: str
    position: str
    ppg_mean: float          # per-game fantasy points (usage)
    ppg_stdev: float         # per-game σ (week-to-week variance)
    injury_rate: float | None = None   # per-game miss prob; None → positional prior


@dataclass
class SeasonOutcome:
    player_id: str
    position: str
    proj_mean: float         # E[season points]
    floor: float             # P10 season total
    p50: float               # median season total
    ceiling: float           # P90 season total
    boom_bust: float         # ceiling − floor (absolute spread)
    boom_pct: float          # P(season > BOOM_MULT × median)
    bust_pct: float          # P(season < BUST_MULT × median)
    games_exp: float         # expected games played


def injury_rate_for(position: str, override: float | None) -> float:
    if override is not None:
        return max(0.0, min(1.0, override))
    return INJURY_RATE.get(position, DEFAULT_INJURY_RATE)


def from_per_game(player_id: str, position: str, ppg_mean: float, ppg_stdev: float,
                  injury_rate: float | None = None) -> SimInput:
    return SimInput(player_id, position, max(0.0, ppg_mean), max(0.0, ppg_stdev), injury_rate)


def from_projection(proj, position: str, games_slate: int = GAMES_SLATE) -> SimInput:
    """Build a per-game input from a season-level Projection (mean/stdev are season totals).
    season σ ≈ √g·ppg_σ ⇒ ppg_σ = season_σ/√g."""
    g = max(1, games_slate)
    return SimInput(proj.player_id, position, max(0.0, proj.mean / g),
                    max(0.0, proj.stdev / (g ** 0.5)), getattr(proj, "injury_rate", None))


class SeasonSimulator:
    def __init__(self, n_sims: int = 10_000, games_slate: int = GAMES_SLATE, seed: int | None = None):
        self.n_sims = n_sims
        self.games_slate = games_slate
        self.seed = seed

    def simulate(self, players: list[SimInput]) -> list[SeasonOutcome]:
        import numpy as np

        if not players:
            return []
        rng = np.random.default_rng(self.seed)
        mu = np.array([p.ppg_mean for p in players], dtype=float)
        sig = np.array([p.ppg_stdev for p in players], dtype=float)
        avail = np.array([1.0 - injury_rate_for(p.position, p.injury_rate) for p in players],
                         dtype=float)

        n = len(players)
        # games_played per sim per player (injury). shape (n_sims, n)
        games = rng.binomial(self.games_slate, avail, size=(self.n_sims, n)).astype(float)
        # closed-form sum of `games` iid Normal(μ,σ): Normal(games·μ, √games·σ), clip ≥ 0.
        totals = np.clip(rng.normal(games * mu, np.sqrt(games) * sig), 0.0, None)

        p10 = np.percentile(totals, 10, axis=0)
        p50 = np.percentile(totals, 50, axis=0)
        p90 = np.percentile(totals, 90, axis=0)
        med = np.where(p50 > 0, p50, 1e-9)
        boom = (totals > BOOM_MULT * med).mean(axis=0)
        bust = (totals < BUST_MULT * med).mean(axis=0)
        mean = totals.mean(axis=0)
        games_exp = games.mean(axis=0)

        return [
            SeasonOutcome(
                player_id=p.player_id, position=p.position,
                proj_mean=round(float(mean[i]), 2), floor=round(float(p10[i]), 2),
                p50=round(float(p50[i]), 2), ceiling=round(float(p90[i]), 2),
                boom_bust=round(float(p90[i] - p10[i]), 2),
                boom_pct=round(float(boom[i]), 4), bust_pct=round(float(bust[i]), 4),
                games_exp=round(float(games_exp[i]), 2),
            )
            for i, p in enumerate(players)
        ]
