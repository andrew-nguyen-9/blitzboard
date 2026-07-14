"""Shared plumbing for the bounded, degrade-neutral opportunity factors (E1-factors).

Each factor is a *small pure fn* mapping the core's player universe to a per-player raw
multiplier (identity ``1.0``), returned as an ``(n_players,)`` array. The projector clamps
every factor to ``FACTOR_BOUNDS`` and applies it on log-opportunity (∏ factors), so a factor
only ever *reshapes* volume and can never blow a fit up. Degrade-neutral is the whole
contract: a factor that knows nothing about a player (no context row) returns ``1.0`` — the
context-free player is projected by the plain hierarchy.

`ponytail:` there is deliberately NO factor framework beyond E1-core's ``FactorHook`` — this
module is only the three helpers every factor shares (team/position lookups + a clamp + a
per-player array builder), not a base class.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Callable

    from blitz_engine.projection.model import ModelData


def clamp(x: float, lo: float, hi: float) -> float:
    """Scalar clamp (each factor keeps its own gentle band inside ``FACTOR_BOUNDS``)."""
    return max(lo, min(hi, x))


def player_teams(data: ModelData) -> list[str]:
    """Canonical team code per player (aligned to ``data.player_ids``)."""
    return [data.teams[i] for i in np.asarray(data.team_of_player)]


def player_positions(data: ModelData) -> list[str]:
    """Position per player (aligned to ``data.player_ids``)."""
    return [data.positions[i] for i in np.asarray(data.pos_of_player)]


def by_player(data: ModelData, fn: Callable[[str, str, str], float]) -> np.ndarray:
    """Build the ``(P,)`` raw-multiplier array from a per-player ``fn(position, team, pid)``.

    ``fn`` returns a raw multiplier (identity ``1.0``); any player it cannot score should be
    left at ``1.0`` by the caller returning ``1.0`` — that is the degrade-neutral default.
    """
    teams = player_teams(data)
    positions = player_positions(data)
    out = np.ones(data.n_players, dtype=np.float64)
    for i, (pos, team, pid) in enumerate(zip(positions, teams, data.player_ids, strict=True)):
        out[i] = fn(pos, team, pid)
    return out
