"""Interim value hook — adapt the SHIPPED pipeline value into the engine's board surface.

`ponytail:` the pipeline's `models/value_engine.py` already computes shaped draft value
(VORP / Monte-Carlo). We do NOT recompute it here; we only *adapt its output* into the
one small shape the engine's fixes operate on — a ranked list of `InterimValue`. When the
deep equity engine (E4-value-equity) lands it swaps under this same surface, so every
consumer (the FA penalty, later the roster solver) is written against `InterimValue`, not
against whichever engine happens to be producing value today.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import ModuleType
from typing import Protocol, runtime_checkable


@runtime_checkable
class _HasValue(Protocol):
    """Structural type for any pipeline value row (e.g. `PlayerValue`)."""

    player_id: str
    value: float


@dataclass
class InterimValue:
    """One ranked entry on the interim board — the surface every value fix rides on."""

    player_id: str
    value: float           # board value (pre-penalty); higher ranks better
    rank: int              # 1-based board rank by `value` (1 == best)
    pos: str | None = None


def load_pipeline_value_engine() -> ModuleType:
    """Import the shipped `pipeline/models/value_engine.py` (reuse, don't reimplement).

    `pipeline/` has no packaging metadata, so — exactly like `pipeline_bridge` does for
    the adapters — we put its root on `sys.path` on demand and import the module. Callers
    that already hold computed `PlayerValue`s never need this; it exists so the engine can
    *drive* the pipeline engine when it has to.
    """
    import sys

    from blitz_engine.pipeline_bridge import pipeline_root

    root = str(pipeline_root())
    if root not in sys.path:
        sys.path.insert(0, root)
    from models import value_engine  # pipeline/models/value_engine.py

    return value_engine


def interim_surface(
    values: Iterable[_HasValue],
    positions: Mapping[str, str] | None = None,
) -> list[InterimValue]:
    """Adapt pipeline value output into a ranked `InterimValue` board.

    `values` is any iterable of objects exposing `.player_id` and `.value` (the pipeline's
    `PlayerValue` qualifies as-is). Rows are sorted best-first and 1-based ranked. `pos` is
    filled from `positions` when provided (the pipeline `PlayerValue` carries no position).
    """
    pos_map = positions or {}
    surface = [
        InterimValue(
            player_id=v.player_id, value=float(v.value), rank=0, pos=pos_map.get(v.player_id)
        )
        for v in values
    ]
    surface.sort(key=lambda iv: iv.value, reverse=True)
    for i, iv in enumerate(surface, 1):
        iv.rank = i
    return surface
