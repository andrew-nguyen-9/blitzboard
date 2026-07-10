"""Projection-factor framework (F3).

Auto-discovered, one-per-file adjustments to a player's projection. See
``docs/modeling/FACTOR_CONTRACT.md`` for the full contract.
"""
from .base import DELTA, MULTIPLIER, Factor, FactorContext
from .loader import default_factors, discover_factors
from .reference import ReferenceFactor

__all__ = [
    "Factor",
    "FactorContext",
    "MULTIPLIER",
    "DELTA",
    "discover_factors",
    "default_factors",
    "ReferenceFactor",
]
