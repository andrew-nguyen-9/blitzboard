"""`blitz_engine.projection` — the hierarchical Bayesian projection core (E1).

The generative heart every downstream model hangs on. Public surface:

    HierarchicalProjector   fit → convergence-gate → posterior-predict per player-week
    ModelData               the tidy player-week input contract (`from_frame`/`from_store`)
    Projection              the output: quantiles + shares + opportunity/efficiency layers
    projection_model        the raw NumPyro model (for the Lab / custom inference)
    walk_forward_compare    the minimal no-regression backtest

Extension seams (E1-talent / E1-factors / E1-latents plug in here — see each protocol):
    TalentPriorHook   per-player talent prior (loc/scale)        [priors.py]
    FactorHook        bounded multiplicative opportunity factor  [model.py]
    LatentHook        additive latent injection                  [model.py]

Convergence + families are re-exported for the shared vocabulary the ensemble/feature
units reuse (`FAMILIES`, `ScoringWeights`, `ConvergenceReport`).
"""
from __future__ import annotations

from blitz_engine.projection.convergence import (
    ConvergenceError,
    ConvergenceReport,
    check,
    gate,
)
from blitz_engine.projection.families import FAMILIES, ScoringWeights
from blitz_engine.projection.inference import (
    BacktestResult,
    HierarchicalProjector,
    Projection,
    walk_forward_compare,
)
from blitz_engine.projection.model import (
    FACTOR_BOUNDS,
    FactorContext,
    FactorHook,
    LatentContribution,
    LatentHook,
    ModelData,
    Seams,
    projection_model,
)
from blitz_engine.projection.priors import (
    GroupPrior,
    PriorSet,
    TalentPrior,
    TalentPriorHook,
    default_priors,
)

__all__ = [
    "FACTOR_BOUNDS",
    "FAMILIES",
    "BacktestResult",
    "ConvergenceError",
    "ConvergenceReport",
    "FactorContext",
    "FactorHook",
    "GroupPrior",
    "HierarchicalProjector",
    "LatentContribution",
    "LatentHook",
    "ModelData",
    "PriorSet",
    "Projection",
    "ScoringWeights",
    "Seams",
    "TalentPrior",
    "TalentPriorHook",
    "check",
    "default_priors",
    "gate",
    "projection_model",
    "walk_forward_compare",
]
