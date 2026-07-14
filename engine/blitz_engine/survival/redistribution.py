"""Fold P(available) into a `Projection`: scale the numbers, redistribute the workload.

Two moves, both keyed by the `player_id → P(available)` map the `AvailabilityModel` emits:

1. **Multiply into every projection** (`scale_quantiles`) — the availability-marginal
   expectation ``E[points] = P(available) · E[points | available]``. Applied to the mean and
   every quantile/floor/ceiling column, so a 60 %-available player's whole distribution scales
   to 0.6× (a mixture that plays-or-scores-zero; see gotchas for the zero-inflation nuance).

2. **Redistribute the Dirichlet share to backups** (`redistribute_shares`) — this is the
   pre-box-score workload shift the brief demands. It generalises E1-core's "zero an injured
   player's α and renormalise within team" into a *continuous* reweight: scale each player's
   `dirichlet_alpha` by P(available), then renormalise `share` within team. A starter ruled
   OUT (P=0) drops to α=0 and his usage flows to healthy teammates in proportion to their own
   α; a questionable starter (P=0.5) sheds half his share. Team shares still sum to 1.

`apply_availability` does both and returns a fresh `Projection` (inputs untouched). Every map
lookup defaults to 1.0, so a player absent from the availability map passes through unscaled —
the degrade guarantee end-to-end.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from blitz_engine.projection.inference import Projection

__all__ = [
    "SCALED_COLUMNS",
    "apply_availability",
    "redistribute_shares",
    "scale_quantiles",
]

#: Quantile-frame columns P(available) multiplies into (the whole publishable distribution).
SCALED_COLUMNS = ("mean", "p1", "floor", "p50", "ceiling", "p99", "stdev")


def _lookup(ids: pd.Series, p_available: Mapping[str, float]) -> np.ndarray:
    """Per-row P(available) aligned to `ids`, defaulting missing players to 1.0 (no-op)."""
    return np.array([float(p_available.get(str(pid), 1.0)) for pid in ids], dtype=float)


def scale_quantiles(
    quantiles: pd.DataFrame,
    p_available: Mapping[str, float],
    *,
    player_col: str = "player_id",
    columns: tuple[str, ...] = SCALED_COLUMNS,
) -> pd.DataFrame:
    """Return a copy of `quantiles` with the point/quantile columns scaled by P(available)."""
    out = quantiles.copy()
    mult = _lookup(out[player_col], p_available)
    for col in columns:
        if col in out.columns:
            out[col] = out[col].to_numpy(dtype=float) * mult
    return out


def redistribute_shares(
    shares: pd.DataFrame,
    p_available: Mapping[str, float],
    *,
    player_col: str = "player_id",
    team_col: str = "team",
    alpha_col: str = "dirichlet_alpha",
    share_col: str = "share",
) -> pd.DataFrame:
    """Reweight `dirichlet_alpha` by P(available) and renormalise `share` within team.

    Continuous generalisation of E1-core's injury redistribution: ``α' = α · P(available)``
    then ``share' = α' / Σ_team α'``. Out players (P=0) vacate their share to healthy backups;
    a team whose players are all zeroed keeps a uniform fallback so shares still sum to 1.
    """
    out = shares.copy()
    out[alpha_col] = out[alpha_col].to_numpy(dtype=float) * _lookup(out[player_col], p_available)
    team_sum = out.groupby(team_col)[alpha_col].transform("sum").to_numpy(dtype=float)
    team_size = out.groupby(team_col)[alpha_col].transform("size").to_numpy(dtype=float)
    # zero-sum team (every player unavailable) falls back to uniform so shares still sum to 1
    out[share_col] = np.where(
        team_sum > 0, out[alpha_col].to_numpy(dtype=float) / team_sum, 1.0 / team_size
    )
    return out


def apply_availability(
    projection: Projection,
    p_available: Mapping[str, float],
) -> Projection:
    """Fold P(available) into a `Projection`: scaled quantiles + redistributed shares.

    Returns a new `Projection` (the input is not mutated). Opportunity/efficiency layers and
    the raw-draws path pass through unchanged — availability acts on the publishable numbers
    and the usage split, not the per-opportunity efficiency estimate.
    """
    return replace(
        projection,
        quantiles=scale_quantiles(projection.quantiles, p_available),
        shares=redistribute_shares(projection.shares, p_available),
    )
