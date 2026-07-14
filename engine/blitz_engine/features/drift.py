"""Distribution-drift monitoring (item VIII): KL / Jensen-Shannon divergence + alarms.

A `DriftMonitor` snapshots a *reference* `FeatureSet` (e.g. the training season) as fixed-
edge histograms; `check(current)` re-bins each feature of a new slice on the SAME edges and
scores its Jensen-Shannon divergence from the reference. JS is symmetric and bounded to
``[0, 1]`` (log base 2), so a single `threshold` gives a clean per-feature alarm — the
signal E6 raises when the incoming data has shifted out from under a fitted model.

`ponytail:` KL is `scipy.stats.entropy(p, q)`; JS is the two-term average against the
mixture — a handful of lines, no dependency beyond scipy (already in the engine env).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import entropy as _scipy_entropy

from blitz_engine.features.discovery import FeatureSet

__all__ = ["DriftReport", "DriftMonitor", "kl_divergence", "js_divergence"]

_EPS = 1e-12


def _normalize(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, dtype=float) + _EPS
    return p / p.sum()


def kl_divergence(p: np.ndarray, q: np.ndarray) -> float:
    """KL(p ‖ q) in bits, over two (unnormalised) histograms — asymmetric."""
    return float(_scipy_entropy(_normalize(p), _normalize(q), base=2))


def js_divergence(p: np.ndarray, q: np.ndarray) -> float:
    """Jensen-Shannon divergence in bits ∈ [0, 1]: symmetric, always finite.

    ``JS = ½·KL(p‖m) + ½·KL(q‖m)`` with ``m = ½(p+q)``. 0 = identical distributions,
    1 = disjoint support.
    """
    p, q = _normalize(p), _normalize(q)
    m = 0.5 * (p + q)
    return float(0.5 * _scipy_entropy(p, m, base=2) + 0.5 * _scipy_entropy(q, m, base=2))


@dataclass(frozen=True)
class DriftReport:
    """Per-feature JS divergence of a current slice vs the reference, with alarm logic."""

    per_feature: dict[str, float]
    threshold: float

    @property
    def alarms(self) -> list[str]:
        """Features whose divergence exceeds the threshold (drift detected)."""
        return [f for f, d in self.per_feature.items() if d > self.threshold]

    @property
    def alarm(self) -> bool:
        """True iff any feature drifted past the threshold."""
        return bool(self.alarms)

    @property
    def max_divergence(self) -> float:
        return max(self.per_feature.values(), default=0.0)


@dataclass
class DriftMonitor:
    """Reference-vs-current drift detector over a `FeatureSet`'s columns.

    Build from a reference set with `from_features`; call `check(current)` per new slice.
    Bin edges are frozen from the reference so both distributions are strictly comparable
    (current values outside the reference range fall into the edge bins — itself a drift
    signal). Only features present in BOTH sets are scored.
    """

    threshold: float
    bins: int
    _edges: dict[str, np.ndarray]
    _ref_hist: dict[str, np.ndarray]

    @classmethod
    def from_features(
        cls, reference: FeatureSet, *, bins: int = 20, threshold: float = 0.1
    ) -> DriftMonitor:
        edges: dict[str, np.ndarray] = {}
        ref_hist: dict[str, np.ndarray] = {}
        for name in reference.names:
            col = reference.column(name)
            lo, hi = float(np.min(col)), float(np.max(col))
            if lo == hi:  # constant reference: nudge to a unit window so bins are valid
                lo, hi = lo - 0.5, hi + 0.5
            e = np.linspace(lo, hi, bins + 1)
            edges[name] = e
            ref_hist[name] = np.histogram(col, bins=e)[0]
        return cls(threshold=threshold, bins=bins, _edges=edges, _ref_hist=ref_hist)

    def check(self, current: FeatureSet) -> DriftReport:
        """Score JS divergence of each shared feature vs the reference; flag alarms."""
        per: dict[str, float] = {}
        current_names = set(current.names)
        for name, edges in self._edges.items():
            if name not in current_names:
                continue
            cur = np.histogram(current.column(name), bins=edges)[0]
            per[name] = js_divergence(self._ref_hist[name], cur)
        return DriftReport(per_feature=per, threshold=self.threshold)
