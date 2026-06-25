"""
Predictability ρ ∈ [0,1] — how reproducible a player's projection is (SCORING.md §1).

The bug v2.2 fixes: v1 ranks K/DST on a projected point total, treating a volatile
D/ST exactly like a stable WR. Predictability is the per-player signal that lets the
ValueEngine discount unreproducible value toward replacement (`f(ρ)` in VALUE_ENGINE.md).

ρ blends three signals, then SHRINKS toward a positional prior for low-sample players:
  • a positional year-over-year rank-stability prior — K/DST structurally low, the
    top-10 at both positions turns over almost completely year to year;
  • the player's own season-to-season variance (low coefficient of variation → high ρ);
  • the share of points from high-variance sources (TDs, turnovers, returns).

It is **position-agnostic** — it just happens to hit K/DST hardest because the data
(and the prior) say it should. Tuned by the v2.2/v2.4 backtest; nothing here is
hand-set to a target ranking.
"""
from __future__ import annotations

from .projector import HistoryStore, SeasonLine

# Structural year-to-year stability priors, grounded in SCORING.md's research:
# K and D/ST have the lowest predictability of any position; QB the highest. These
# are the fallback when a position has too little history to measure stability, and
# the anchor low-sample players shrink toward.
_STRUCTURAL_PRIOR: dict[str, float] = {
    "QB": 0.75, "RB": 0.55, "WR": 0.58, "TE": 0.52, "K": 0.25, "DST": 0.20,
}
_DEFAULT_PRIOR = 0.45          # unknown position
_SHRINK_TAU = 3.0             # prior weight in seasons: w = n / (n + τ)
_MIN_PAIRS = 6               # consecutive-season pairs needed to trust measured stability


def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def _g(stats: dict, key: str) -> float:
    v = stats.get(key)
    return float(v) if v is not None else 0.0


def td_turnover_share(stats: dict, scoring: dict) -> float:
    """Fraction of a stat line's fantasy points that comes from high-variance
    sources — touchdowns and turnovers (and return/defensive TDs). Yardage and
    receptions are the stable base. Returns 0.0 for an empty/scoreless line."""
    p = scoring.get("passing", {})
    r = scoring.get("rushing", {})
    rec = scoring.get("receiving", {})
    misc = scoring.get("misc", {})
    dst = scoring.get("dst", {})

    td = (
        _g(stats, "passing_tds") * p.get("td", 4)
        + _g(stats, "rushing_tds") * r.get("td", 6)
        + _g(stats, "receiving_tds") * rec.get("td", 6)
        + _g(stats, "def_tds") * dst.get("td_any", 6)
    )
    turnover = (
        abs(_g(stats, "interceptions") * p.get("int", -2))
        + abs(_g(stats, "fumbles_lost") * misc.get("fumble_lost", -2))
    )
    base = (
        abs(_g(stats, "passing_yards") * p.get("pt_per_yd", 0.04))
        + abs(_g(stats, "rushing_yards") * r.get("pt_per_yd", 0.1))
        + abs(_g(stats, "receiving_yards") * rec.get("pt_per_yd", 0.1))
        + abs(_g(stats, "receptions") * rec.get("ppr", 0.5))
    )
    high_var = abs(td) + turnover
    total = high_var + base
    return _clamp01(high_var / total) if total > 0 else 0.0


def _coef_of_variation(points: list[float]) -> float:
    """Season-to-season CV of fantasy points (0 = perfectly stable)."""
    pts = [x for x in points if x is not None]
    if len(pts) < 2:
        return 0.0
    mu = sum(pts) / len(pts)
    if mu <= 0:
        return 0.0
    var = sum((x - mu) ** 2 for x in pts) / len(pts)
    return (var ** 0.5) / mu


def _rank_stability(store: HistoryStore, position: str) -> float | None:
    """Measured YoY rank stability for a position ∈ [0,1] via the average
    rank-correlation of players appearing in consecutive seasons. None if the
    position lacks enough consecutive-season pairs to be trustworthy."""
    # season -> {player_id: points} for this position
    by_season: dict[int, dict[str, float]] = {}
    for pid in store.all_player_ids():
        for line in store.lines(pid):
            if line.position == position and line.games > 0:
                by_season.setdefault(line.season, {})[pid] = line.points

    corrs: list[float] = []
    pairs = 0
    for season in sorted(by_season):
        a, b = by_season.get(season), by_season.get(season + 1)
        if not a or not b:
            continue
        common = [pid for pid in a if pid in b]
        if len(common) < 3:
            continue
        ra = _to_ranks({pid: a[pid] for pid in common})
        rb = _to_ranks({pid: b[pid] for pid in common})
        corrs.append(_pearson([ra[pid] for pid in common], [rb[pid] for pid in common]))
        pairs += len(common)
    if pairs < _MIN_PAIRS or not corrs:
        return None
    # map correlation [-1,1] → stability [0,1]
    return _clamp01((sum(corrs) / len(corrs) + 1) / 2)


def _to_ranks(scores: dict[str, float]) -> dict[str, float]:
    order = sorted(scores, key=lambda pid: scores[pid], reverse=True)
    return {pid: i for i, pid in enumerate(order)}


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return 0.0
    return cov / ((vx * vy) ** 0.5)


class Predictability:
    """Per-player ρ over a shared HistoryStore. Positional priors are computed
    once at construction (cheap), then `score()` is O(seasons) per player."""

    def __init__(self, store: HistoryStore, rules):
        self.store = store
        self.rules = rules
        self.prior: dict[str, float] = {}
        for pos, structural in _STRUCTURAL_PRIOR.items():
            measured = _rank_stability(store, pos)
            # blend measured stability with the structural prior when we trust it
            self.prior[pos] = structural if measured is None else 0.5 * structural + 0.5 * measured

    def _prior_for(self, position: str | None) -> float:
        return self.prior.get(position or "", _DEFAULT_PRIOR)

    def score(self, player_id: str, position: str | None) -> float:
        prior = self._prior_for(position)
        lines: list[SeasonLine] = [l for l in self.store.lines(player_id) if l.games > 0]
        n = len(lines)
        if n == 0:
            return _clamp01(prior)

        # own-signal: reliability from low variance × low TD/turnover dependence
        reliability = 1.0 - _coef_of_variation([l.points for l in lines])
        td_share = sum(td_turnover_share(l.stats, self.rules.scoring) for l in lines) / n
        own_signal = 0.5 * _clamp01(reliability) + 0.5 * (1.0 - td_share)

        # shrink toward the positional prior by sample size
        w = n / (n + _SHRINK_TAU)
        return _clamp01(w * own_signal + (1 - w) * prior)
