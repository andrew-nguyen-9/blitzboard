"""Separate per-position aging curves.

Running backs peak and fall early; receivers and quarterbacks age slowly. A single league
curve smears those apart, so we fit **one curve per position** — a weighted quadratic of
the talent signal on age (ponytail: `np.polyfit` is the whole model; a concave parabola is
the simplest arc that has a peak and two decay wings). The accessor returns an *additive
log-scale* adjustment, normalised so the peak age contributes 0 and every other age is a
non-positive haircut — an over-the-hill RB is nudged down, never a mystery.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["AgingCurves"]

_DEFAULT_PEAK = 27.0  # league-wide fallback peak age when a position lacks data
_MAX_HAIRCUT = 0.6  # cap the aging penalty on the log scale (stays gentle)


@dataclass
class AgingCurves:
    """Per-position age→talent quadratics with a bounded adjustment accessor."""

    coeffs: dict[str, np.ndarray] = field(default_factory=dict)  # position → poly (deg 2)
    peaks: dict[str, float] = field(default_factory=dict)  # position → peak age
    scale: dict[str, float] = field(default_factory=dict)  # position → signal std (normaliser)

    @classmethod
    def fit(cls, position: np.ndarray, age: np.ndarray, value: np.ndarray) -> AgingCurves:
        """Fit a weighted quadratic per position from historical (age, value) points."""
        position = np.asarray(position)
        age = np.asarray(age, dtype=np.float64)
        value = np.asarray(value, dtype=np.float64)
        curves = cls()
        for pos in np.unique(position):
            m = (position == pos) & np.isfinite(age) & np.isfinite(value)
            if m.sum() < 4 or np.ptp(age[m]) < 2:
                continue
            coef = np.polyfit(age[m], value[m], 2)
            curves.coeffs[str(pos)] = coef
            a, b = coef[0], coef[1]
            peak = float(np.clip(-b / (2 * a), 20.0, 34.0)) if a < 0 else _DEFAULT_PEAK
            curves.peaks[str(pos)] = peak
            curves.scale[str(pos)] = float(np.std(value[m])) or 1.0
        return curves

    def peak_age(self, position: str) -> float:
        """The fitted peak age for a position (league fallback if unfit)."""
        return self.peaks.get(position, _DEFAULT_PEAK)

    def adjustment(self, position: str, age: float | None) -> float:
        """Additive log-scale aging adjustment at `age` (0 at the peak, ≤0 elsewhere).

        Unknown position / missing age ⇒ 0.0 (degrade-neutral).
        """
        if age is None or not np.isfinite(age) or position not in self.coeffs:
            return 0.0
        coef = self.coeffs[position]
        here = float(np.polyval(coef, age))
        top = float(np.polyval(coef, self.peaks[position]))
        norm = (here - top) / self.scale[position]  # ≤ 0
        return float(np.clip(norm, -_MAX_HAIRCUT, 0.0))
