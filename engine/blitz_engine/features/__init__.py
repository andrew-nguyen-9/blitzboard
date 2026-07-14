"""`blitz_engine.features` — the E6 automated feature layer over the E1 projection core.

Public surface (three jobs the brief names — discovery, importance, drift):

    discover_features / FeatureSet      base columns + bounded nonlinear interactions
    screen_features / ScreenResult      MI ranking behind a low-entropy screen
    compute_importance / FeatureImportance   dynamic PER-SEASON importance accessor
                                             (E6-graph / E6-ensemble read this)
    DriftMonitor / DriftReport          KL / JS distribution-drift alarms (item VIII)
    ImportanceFactorHook                feed selected features back into the E1 FactorHook seam
    FeatureStore                        one-call orchestrator over all of the above

Estimators are numpy/scipy histogram MI + JS divergence (`ponytail:` no sklearn — it is not
in the engine env; scipy already is). Every consumer-facing accessor degrades to a safe
neutral (uniform weights / ×1.0 factor) so a missing signal never harms the base fit.
"""
from __future__ import annotations

from blitz_engine.features.discovery import (
    INTERACTION_SEP,
    FeatureSet,
    discover_features,
)
from blitz_engine.features.drift import (
    DriftMonitor,
    DriftReport,
    js_divergence,
    kl_divergence,
)
from blitz_engine.features.screening import (
    FeatureImportance,
    ImportanceFactorHook,
    ScreenResult,
    compute_importance,
    feature_entropy,
    mutual_information,
    screen_features,
)
from blitz_engine.features.store import FeatureStore

__all__ = [
    "INTERACTION_SEP",
    "DriftMonitor",
    "DriftReport",
    "FeatureImportance",
    "FeatureSet",
    "FeatureStore",
    "ImportanceFactorHook",
    "ScreenResult",
    "compute_importance",
    "discover_features",
    "feature_entropy",
    "js_divergence",
    "kl_divergence",
    "mutual_information",
    "screen_features",
]
