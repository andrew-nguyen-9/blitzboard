"""Feature-drift alarms — catch a feature's distribution moving out from under the model.

Uses the Population Stability Index (PSI): bin a reference window on its own quantiles, then
compare the current window's mass per bin. PSI > `threshold` (industry rule of thumb 0.2)
raises the alarm. Dependency-free; the same alarm covers input features and residuals.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

__all__ = ["DriftAlarm", "population_stability_index", "scan_drift"]


def population_stability_index(
    reference: np.ndarray, current: np.ndarray, *, bins: int = 10
) -> float:
    """PSI of `current` vs `reference`, binned on the reference's quantiles.

    0 ≈ identical, ~0.1 small shift, >0.2 material shift. Open outer edges so out-of-range
    current values still land in the extreme bins; a small floor avoids log(0).
    """
    ref = np.asarray(reference, dtype=float)
    cur = np.asarray(current, dtype=float)
    if ref.size == 0 or cur.size == 0:
        return 0.0
    edges = np.quantile(ref, np.linspace(0.0, 1.0, bins + 1))
    edges = np.unique(edges)
    if edges.size < 2:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    r = np.histogram(ref, edges)[0] / ref.size
    c = np.histogram(cur, edges)[0] / cur.size
    eps = 1e-6
    r = np.clip(r, eps, None)
    c = np.clip(c, eps, None)
    return float(np.sum((c - r) * np.log(c / r)))


@dataclass
class DriftAlarm:
    """Per-feature drift verdict."""

    feature: str
    psi: float
    threshold: float

    @property
    def drifted(self) -> bool:
        return self.psi > self.threshold


def scan_drift(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    *,
    features: list[str],
    threshold: float = 0.2,
    bins: int = 10,
) -> dict[str, DriftAlarm]:
    """PSI-scan each feature between a reference and current frame; return per-feature alarms."""
    alarms: dict[str, DriftAlarm] = {}
    for feat in features:
        psi = population_stability_index(
            reference[feat].to_numpy(dtype=float),
            current[feat].to_numpy(dtype=float),
            bins=bins,
        )
        alarms[feat] = DriftAlarm(feature=feat, psi=psi, threshold=threshold)
    return alarms
