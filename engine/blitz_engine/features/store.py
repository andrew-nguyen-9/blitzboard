"""`FeatureStore` — the one-call orchestrator wiring discovery → screening → importance.

Given a tidy player-week frame, a set of base columns and a projection target, `build`
runs the whole E6 feature pipeline and hands back: the discovered `FeatureSet`, the MI
screen, the dynamic per-season `FeatureImportance` accessor (what E6-graph / E6-ensemble
read), and an `ImportanceFactorHook` ready to inject back into the E1 core. `drift_monitor`
snapshots the discovered features as a reference for later slices.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from blitz_engine.features.discovery import FeatureSet, discover_features
from blitz_engine.features.drift import DriftMonitor
from blitz_engine.features.screening import (
    FeatureImportance,
    ImportanceFactorHook,
    ScreenResult,
    compute_importance,
    screen_features,
)

__all__ = ["FeatureStore"]


@dataclass
class FeatureStore:
    """The assembled feature layer over one frame: features + screen + importance + hook."""

    features: FeatureSet
    screen: ScreenResult
    importance: FeatureImportance
    factor_hook: ImportanceFactorHook

    @property
    def selected(self) -> list[str]:
        """MI-ranked selected feature names — the model input set."""
        return self.screen.selected

    @classmethod
    def build(
        cls,
        frame: pd.DataFrame,
        *,
        base_cols: list[str],
        target_col: str,
        season_col: str = "season",
        interactions: bool = True,
        min_entropy: float = 1e-3,
        top_k: int | None = None,
        gain: float = 0.15,
    ) -> FeatureStore:
        """Run discovery → screening → per-season importance → factor bridge on `frame`.

        `target_col` is the value features are screened against (e.g. fantasy points or
        opportunities). Importance is computed per `season_col` when present, else over one
        synthetic season. The returned `factor_hook` is built from the *selected* features so
        it feeds only the screened signal back into the core.
        """
        features = discover_features(frame, base_cols, interactions=interactions)
        target = pd.to_numeric(frame[target_col], errors="coerce").fillna(0.0).to_numpy(dtype=float)

        screen = screen_features(
            features, target, bins=None, min_entropy=min_entropy, top_k=top_k
        )
        seasons = (
            frame[season_col].to_numpy() if season_col in frame.columns else None
        )
        importance = compute_importance(
            features, target, seasons=seasons, features_subset=screen.selected
        )
        hook = ImportanceFactorHook.from_features(
            features, importance, gain=gain, selected=screen.selected or None
        )
        return cls(features=features, screen=screen, importance=importance, factor_hook=hook)

    def drift_monitor(self, *, bins: int = 20, threshold: float = 0.1) -> DriftMonitor:
        """A `DriftMonitor` referenced on this store's (selected) features."""
        selected = self.features.select(self.selected) if self.selected else self.features
        return DriftMonitor.from_features(selected, bins=bins, threshold=threshold)

    def importance_weights(self) -> dict[str, float]:
        """Normalised aggregate importances over the selected features (convex weights)."""
        return self.importance.weights(self.selected or None)
