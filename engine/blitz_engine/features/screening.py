"""MI / entropy feature screening, dynamic per-season importance, and the E1 factor bridge.

Screening ranks candidate features by their **mutual information** with the projection
target and drops near-constant (low-entropy) noise. Importance is computed *per season* so
it can drift across years (a feature that mattered in 2022 may not in 2024) — the accessor
exposes both the per-season table and a season-aggregated view. `ImportanceFactorHook`
turns those importances into a bounded per-player opportunity multiplier that plugs into the
E1 `FactorHook` seam, degrade-neutral for any player it has no signal on.

`ponytail:` MI and entropy are histogram estimators over numpy/scipy — no sklearn
dependency (it is not in the engine env). A 2-D histogram gives the joint, its marginals
give the product, and MI is the KL of joint against product; `scipy.stats.entropy` supplies
the log-sum. That is ~15 lines and needs zero new deps.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.stats import entropy as _scipy_entropy

from blitz_engine.features.discovery import FeatureSet

__all__ = [
    "ScreenResult",
    "FeatureImportance",
    "ImportanceFactorHook",
    "mutual_information",
    "feature_entropy",
    "screen_features",
    "compute_importance",
]


def _n_bins(n: int) -> int:
    """Freedman-lite bin count: ~√n, clamped to a sane [4, 32] range."""
    return int(min(max(int(np.sqrt(max(n, 1))), 4), 32))


def mutual_information(x: np.ndarray, y: np.ndarray, *, bins: int | None = None) -> float:
    """Histogram estimate of MI(x; y) in nats (≥ 0).

    Bins both variables, forms the joint ``p_xy`` and marginals, and sums
    ``p_xy · log(p_xy / (p_x·p_y))`` over occupied cells. Independent variables → ~0;
    a deterministic relation → high. Constant inputs return 0.
    """
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    b = bins or _n_bins(x.size)
    if np.ptp(x) == 0 or np.ptp(y) == 0:
        return 0.0
    c_xy, _, _ = np.histogram2d(x, y, bins=b)
    total = c_xy.sum()
    if total == 0:
        return 0.0
    p_xy = c_xy / total
    p_x = p_xy.sum(axis=1, keepdims=True)
    p_y = p_xy.sum(axis=0, keepdims=True)
    outer = p_x @ p_y
    nz = p_xy > 0
    mi = float(np.sum(p_xy[nz] * np.log(p_xy[nz] / outer[nz])))
    return max(mi, 0.0)


def feature_entropy(x: np.ndarray, *, bins: int | None = None) -> float:
    """Shannon entropy (nats) of a binned feature — the low-entropy screen's statistic.

    A near-constant feature carries almost no information (entropy → 0) and is dropped
    before ranking; a well-spread feature keeps high entropy.
    """
    x = np.asarray(x, dtype=float).ravel()
    if np.ptp(x) == 0:
        return 0.0
    counts, _ = np.histogram(x, bins=bins or _n_bins(x.size))
    counts = counts[counts > 0]
    return float(_scipy_entropy(counts))


@dataclass(frozen=True)
class ScreenResult:
    """The screen verdict: MI-ranked survivors, plus what was dropped as low-entropy."""

    ranked: list[tuple[str, float]]  # (feature, MI) descending, entropy-survivors only
    dropped: list[str]  # features dropped by the entropy floor
    bins: int

    @property
    def selected(self) -> list[str]:
        """Feature names in descending MI order (the models' input set)."""
        return [name for name, _ in self.ranked]

    def scores(self) -> dict[str, float]:
        """``feature → MI`` map for the survivors."""
        return dict(self.ranked)


def screen_features(
    features: FeatureSet,
    target: np.ndarray,
    *,
    bins: int | None = None,
    min_entropy: float = 1e-3,
    top_k: int | None = None,
) -> ScreenResult:
    """Drop low-entropy features, then rank the rest by MI with `target`.

    `min_entropy` is the near-constant floor (default drops only truly degenerate columns);
    `top_k` optionally keeps just the strongest survivors. Returns a `ScreenResult` whose
    `.selected` is the ranked feature list the importance accessor and models consume.
    """
    target = np.asarray(target, dtype=float).ravel()
    b = bins or _n_bins(features.n_rows)
    scored: list[tuple[str, float]] = []
    dropped: list[str] = []
    for name in features.names:
        col = features.column(name)
        if feature_entropy(col, bins=b) < min_entropy:
            dropped.append(name)
            continue
        scored.append((name, mutual_information(col, target, bins=b)))
    scored.sort(key=lambda kv: kv[1], reverse=True)
    if top_k is not None:
        scored = scored[:top_k]
    return ScreenResult(ranked=scored, dropped=dropped, bins=b)


@dataclass(frozen=True)
class FeatureImportance:
    """Dynamic per-season feature importance — the accessor E6-graph / E6-ensemble read.

    `per_season` maps a season label to its ``feature → MI`` table; importance is
    recomputed each season so it can drift. `importance(feature, season=None)` returns the
    season value or the cross-season mean; `weights()` normalises the aggregate to sum 1 for
    use as model input weights.
    """

    per_season: dict[int, dict[str, float]]
    _aggregate: dict[str, float] = field(default_factory=dict)

    def seasons(self) -> list[int]:
        return sorted(self.per_season)

    def importance(self, feature: str, season: int | None = None) -> float:
        """Importance of `feature` in `season` (or the season-aggregated mean)."""
        if season is not None:
            return self.per_season.get(season, {}).get(feature, 0.0)
        return self._aggregate.get(feature, 0.0)

    def ranked(self, season: int | None = None) -> list[tuple[str, float]]:
        """Features ranked by importance descending (aggregate, or one season)."""
        table = self.per_season[season] if season is not None else self._aggregate
        return sorted(table.items(), key=lambda kv: kv[1], reverse=True)

    def weights(self, features: list[str] | None = None) -> dict[str, float]:
        """Aggregate importances (optionally restricted to `features`) normalised to sum 1.

        All-zero importances degrade to uniform weights so a downstream consumer always
        gets a valid convex combination.
        """
        keys = features if features is not None else list(self._aggregate)
        vals = np.array([max(self._aggregate.get(k, 0.0), 0.0) for k in keys], dtype=float)
        total = vals.sum()
        if total <= 0:
            vals = np.ones(len(keys)) if keys else vals
            total = vals.sum() or 1.0
        return {k: float(v / total) for k, v in zip(keys, vals, strict=True)}


def compute_importance(
    features: FeatureSet,
    target: np.ndarray,
    *,
    seasons: np.ndarray | None = None,
    bins: int | None = None,
    features_subset: list[str] | None = None,
) -> FeatureImportance:
    """Per-season MI importance for each feature, plus a cross-season aggregate.

    Rows are grouped by `seasons` (or a single synthetic season 0 when absent); within each
    group every feature's MI with `target` is scored. The aggregate is the mean across
    seasons — importance that *shifts* year to year is visible in `per_season`, while
    `_aggregate` gives a stable default for consumers that want one number.
    """
    target = np.asarray(target, dtype=float).ravel()
    names = features_subset if features_subset is not None else features.names
    if seasons is None:
        seasons = np.zeros(features.n_rows, dtype=int)
    seasons = np.asarray(seasons).ravel()

    per_season: dict[int, dict[str, float]] = {}
    for s in np.unique(seasons):
        mask = seasons == s
        b = bins or _n_bins(int(mask.sum()))
        per_season[int(s)] = {
            n: mutual_information(features.column(n)[mask], target[mask], bins=b) for n in names
        }
    aggregate = {
        n: float(np.mean([tbl.get(n, 0.0) for tbl in per_season.values()])) for n in names
    }
    return FeatureImportance(per_season=per_season, _aggregate=aggregate)


@dataclass
class ImportanceFactorHook:
    """Feed selected features + importances back into E1 as a bounded opportunity factor.

    Implements the E1 `FactorHook` protocol: `__call__(ctx)` returns a per-player raw
    multiplier ``(n_players,)`` that the projector clamps to `FACTOR_BOUNDS` and applies on
    the log-opportunity scale. Each player's multiplier is ``exp(gain · z)`` where ``z`` is
    the importance-weighted, standardized aggregate of their selected features. DEGRADE-
    NEUTRAL: a player with no computed score (unknown to the store) gets ``z = 0 ⇒ ×1.0`` —
    so wiring this hook can never make the base fit worse (E1's core safety invariant).
    """

    name: str
    player_scores: dict[str, float]
    gain: float = 0.15

    def __call__(self, ctx: object) -> np.ndarray:  # ctx: FactorContext (duck-typed)
        pids = ctx.data.player_ids  # type: ignore[attr-defined]
        return np.array(
            [np.exp(self.gain * self.player_scores.get(str(p), 0.0)) for p in pids], dtype=float
        )

    @classmethod
    def from_features(
        cls,
        features: FeatureSet,
        importance: FeatureImportance,
        *,
        name: str = "feature_importance",
        gain: float = 0.15,
        player_col: str = "player_id",
        selected: list[str] | None = None,
    ) -> ImportanceFactorHook:
        """Build a hook by aggregating selected features to per-player importance scores.

        Each selected feature is averaged per player, the importance weights combine them
        into one score per player, and scores are z-scored across players so `gain` is a
        stable, unit-free knob. Requires `player_col` in the feature index.
        """
        weights = importance.weights(selected)
        idx = features.index.reset_index(drop=True)
        if player_col not in idx.columns:
            raise ValueError(f"feature index has no {player_col!r} column")
        pid = idx[player_col].astype(str).to_numpy()
        players = list(dict.fromkeys(pid))
        score = np.zeros(len(players), dtype=float)
        pos = {p: i for i, p in enumerate(players)}
        row_pos = np.array([pos[p] for p in pid])
        for feat, w in weights.items():
            col = features.column(feat)
            # per-player mean of this feature
            summed = np.zeros(len(players))
            np.add.at(summed, row_pos, col)
            counts = np.bincount(row_pos, minlength=len(players)).astype(float)
            per_player = summed / np.where(counts > 0, counts, 1.0)
            score += w * per_player
        sd = score.std()
        z = (score - score.mean()) / (sd if sd > 0 else 1.0)
        return cls(name=name, player_scores=dict(zip(players, z.tolist(), strict=True)), gain=gain)
