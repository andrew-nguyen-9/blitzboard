"""
Projector — emits projections as DISTRIBUTIONS (D5/D6).

Monte Carlo (P7) needs floor/ceiling/stdev, so every Projector returns a full
distribution. The shipping projector is an ENSEMBLE of three independent signals
whose disagreement seeds the variance:

  • HeuristicProjector  — prior-season ppg × age curve × shrinkage to positional mean
  • RegressionProjector — linear model fit on consecutive-season pairs (numpy)
  • ConsensusProjector  — piggyback others' ordering (FFC ADP) × historical magnitudes

Each projector reads a shared HistoryStore (built once from player_stats_history)
and the LeagueRules (so points are computed under THIS league's scoring).
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from .scoring import score_stats, POSITION_FLOOR

PROJECTED_GAMES = 16  # account for injury/rest vs the 17-game slate


# ── shared data context ─────────────────────────────────────────────────────
@dataclass
class SeasonLine:
    season: int
    points: float          # under league scoring
    games: int
    age: int | None
    position: str | None
    stats: dict


class HistoryStore:
    """player_id → [SeasonLine] (sorted ascending by season)."""

    def __init__(self, rules):
        self.rules = rules
        self._by_player: dict[str, list[SeasonLine]] = {}

    def add(self, player_id: str, season: int, stats: dict, games: int,
            age: int | None, position: str | None) -> None:
        line = SeasonLine(
            season=season,
            points=score_stats(stats, self.rules.scoring),
            games=max(int(games or 0), 0),
            age=age,
            position=position,
            stats=stats,
        )
        self._by_player.setdefault(player_id, []).append(line)

    def finalize(self) -> "HistoryStore":
        for lines in self._by_player.values():
            lines.sort(key=lambda x: x.season)
        return self

    def lines(self, player_id: str) -> list[SeasonLine]:
        return self._by_player.get(player_id, [])

    def positional_ppg(self, position: str) -> float:
        """Mean points-per-game across all season lines at a position (for shrinkage)."""
        vals = [
            l.points / l.games
            for ls in self._by_player.values()
            for l in ls
            if l.position == position and l.games > 0
        ]
        return sum(vals) / len(vals) if vals else 0.0

    def all_player_ids(self) -> list[str]:
        return list(self._by_player.keys())


@dataclass
class Projection:
    player_id: str
    season: int
    source: str            # 'heuristic'|'regression'|'consensus'|'ensemble'
    mean: float
    floor: float
    ceiling: float
    stdev: float
    week: int | None = None
    by_stat: dict = field(default_factory=dict)
    predictability: float | None = None   # ρ∈[0,1] (SCORING.md §1) — set by the orchestrator


# Age-curve peak + per-year falloff by position (multiplier vs prior season).
_AGE_CURVE = {
    "RB": (25, 0.93), "WR": (27, 0.96), "TE": (28, 0.97), "QB": (30, 0.985),
}


def _age_multiplier(position: str | None, age: int | None) -> float:
    if not position or age is None or position not in _AGE_CURVE:
        return 1.0
    peak, falloff = _AGE_CURVE[position]
    if age <= peak:
        return 1.0
    return falloff ** (age - peak)


class Projector(ABC):
    source = "abstract"

    def __init__(self, store: HistoryStore, rules, target_season: int):
        self.store = store
        self.rules = rules
        self.target_season = target_season

    @abstractmethod
    def project(self, player: dict) -> Projection | None: ...

    def _stdev_default(self, position: str | None, mean: float) -> float:
        # positional variance as a fraction of mean (RBs riskier than QBs)
        frac = {"RB": 0.42, "WR": 0.38, "TE": 0.40, "QB": 0.28}.get(position or "", 0.40)
        return max(mean * frac, 1.0)


# ── 1. heuristic ────────────────────────────────────────────────────────────
class HeuristicProjector(Projector):
    source = "heuristic"

    def project(self, player):
        pid, pos = player["id"], player.get("position")
        lines = self.store.lines(pid)
        if not lines:
            mean = POSITION_FLOOR.get(pos, 80.0) * 0.6  # unproven discount
            return self._mk(pid, pos, mean, self._stdev_default(pos, mean) * 1.3)

        last = lines[-1]
        ppg = last.points / last.games if last.games else 0.0
        # shrink toward positional mean by sample size (games)
        pos_ppg = self.store.positional_ppg(pos) if pos else 0.0
        w = last.games / (last.games + 6)  # 6-game prior weight
        ppg_adj = w * ppg + (1 - w) * pos_ppg
        age_mult = _age_multiplier(pos, (last.age + 1) if last.age else None)
        mean = ppg_adj * PROJECTED_GAMES * age_mult

        # stdev from season-to-season variance when we have >=2 seasons
        if len(lines) >= 2:
            seas = [l.points for l in lines[-3:]]
            mu = sum(seas) / len(seas)
            var = sum((x - mu) ** 2 for x in seas) / len(seas)
            stdev = max(math.sqrt(var), self._stdev_default(pos, mean) * 0.6)
        else:
            stdev = self._stdev_default(pos, mean)
        return self._mk(pid, pos, mean, stdev)

    def _mk(self, pid, pos, mean, stdev):
        mean = max(mean, 0.0)
        return Projection(
            player_id=pid, season=self.target_season, source=self.source,
            mean=round(mean, 2), stdev=round(stdev, 2),
            floor=round(mean - 1.28 * stdev, 2), ceiling=round(mean + 1.28 * stdev, 2),
        )


# ── 2. regression (numpy linear model on consecutive-season pairs) ──────────
class RegressionProjector(Projector):
    source = "regression"
    _POS = ("QB", "RB", "WR", "TE")

    def __init__(self, store, rules, target_season):
        super().__init__(store, rules, target_season)
        self._coef = None
        self._resid_std = None
        self._fit()

    def _features(self, line: SeasonLine):
        ppg = line.points / line.games if line.games else 0.0
        onehot = [1.0 if line.position == p else 0.0 for p in self._POS]
        return [1.0, line.points, ppg, float(line.games), float(line.age or 25)] + onehot

    def _fit(self):
        try:
            import numpy as np
        except Exception:
            return
        X, y = [], []
        for pid in self.store.all_player_ids():
            ls = self.store.lines(pid)
            for a, b in zip(ls, ls[1:]):
                if b.season == a.season + 1:
                    X.append(self._features(a))
                    y.append(b.points)
        if len(X) < 20:
            return
        X, y = np.asarray(X), np.asarray(y)
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        self._coef = coef
        self._resid_std = float(np.std(y - X @ coef)) or None

    def project(self, player):
        if self._coef is None:
            return None  # not enough data → ensemble drops this signal
        import numpy as np
        pid, pos = player["id"], player.get("position")
        lines = self.store.lines(pid)
        if not lines:
            return None
        feat = self._features(lines[-1])
        # bump age by one season for the projection
        feat[4] += 1
        mean = float(np.asarray(feat) @ self._coef)
        stdev = self._resid_std or self._stdev_default(pos, mean)
        mean = max(mean, 0.0)
        return Projection(
            player_id=pid, season=self.target_season, source=self.source,
            mean=round(mean, 2), stdev=round(stdev, 2),
            floor=round(mean - 1.28 * stdev, 2), ceiling=round(mean + 1.28 * stdev, 2),
        )


# ── 3. consensus (FFC ADP ordering × historical positional magnitudes) ──────
class ConsensusProjector(Projector):
    """Piggyback others' rankings (D6). Uses Fantasy Football Calculator ADP
    (free, no key) for the *ordering*, and historical points-by-positional-rank
    for the *magnitude*. Superflex note: pass fmt='2qb' when available.

    Network-failure-safe: if ADP can't be fetched, project() returns None and the
    ensemble simply blends the other two signals.
    """

    source = "consensus"

    def __init__(self, store, rules, target_season, teams: int = 12, fmt: str = "half-ppr"):
        super().__init__(store, rules, target_season)
        self.teams, self.fmt = teams, fmt
        self._adp_by_name: dict[str, dict] = {}
        self._pos_rank_points: dict[str, list[float]] = {}
        self._load()

    def _load(self):
        # historical points sorted desc per position → magnitude by positional rank
        from collections import defaultdict
        from .adp import fetch_ffc_adp
        buckets: dict[str, list[float]] = defaultdict(list)
        for pid in self.store.all_player_ids():
            ls = self.store.lines(pid)
            if ls:
                buckets[ls[-1].position or "?"].append(ls[-1].points)
        for pos, vals in buckets.items():
            self._pos_rank_points[pos] = sorted(vals, reverse=True)
        # shared, cached FFC ADP fetch (graceful on failure)
        self._adp_by_name = fetch_ffc_adp(self.teams, self.fmt, self.target_season)

    def project(self, player):
        if not self._adp_by_name:
            return None
        pos = player.get("position")
        entry = self._adp_by_name.get((player.get("full_name") or "").lower())
        if not entry or pos not in self._pos_rank_points:
            return None
        # positional rank from ADP ordering within position
        same_pos = sorted(
            [e for e in self._adp_by_name.values() if e.get("position") == pos],
            key=lambda e: e.get("adp", 999),
        )
        try:
            prank = same_pos.index(entry)
        except ValueError:
            return None
        curve = self._pos_rank_points[pos]
        mean = curve[prank] if prank < len(curve) else (curve[-1] if curve else 0.0)
        stdev = self._stdev_default(pos, mean)
        return Projection(
            player_id=player["id"], season=self.target_season, source=self.source,
            mean=round(mean, 2), stdev=round(stdev, 2),
            floor=round(mean - 1.28 * stdev, 2), ceiling=round(mean + 1.28 * stdev, 2),
        )


# ── the shipping projector: ensemble of the above ───────────────────────────
class EnsembleProjector(Projector):
    source = "ensemble"

    def __init__(self, projectors: list[tuple[Projector, float]]):
        self.projectors = projectors  # [(projector, weight)]

    def project(self, player):
        subs: list[tuple[Projection, float]] = []
        for proj, w in self.projectors:
            try:
                p = proj.project(player)
            except NotImplementedError:
                continue
            if p:
                subs.append((p, w))
        if not subs:
            return None
        wsum = sum(w for _, w in subs)
        mean = sum(p.mean * w for p, w in subs) / wsum
        within = sum((p.stdev ** 2) * w for p, w in subs) / wsum
        between = sum(((p.mean - mean) ** 2) * w for p, w in subs) / wsum
        stdev = math.sqrt(within + between)
        return Projection(
            player_id=player["id"], season=subs[0][0].season, source=self.source,
            mean=round(mean, 2), stdev=round(stdev, 2),
            floor=round(mean - 1.28 * stdev, 2), ceiling=round(mean + 1.28 * stdev, 2),
            by_stat={"inputs": {p.source: p.mean for p, _ in subs}},
        )
