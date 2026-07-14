"""Value surface + value fixes for the interim engine (v4 wave 2).

The deep equity ValueEngine lands later (E4-value-equity); until then the engine rides
on the SHIPPED pipeline value (`pipeline/models/value_engine.py`). This package is the
seam:

    * `interim`    — a thin hook that adapts the pipeline's value OUTPUT into the engine's
                     ranked `InterimValue` surface (reuse, never reimplement value).
    * `fa_penalty` — the truly-free-agent bug fix: detect players with no team AND no
                     draft/role news, sink them below the whole visible board, keep them
                     VISIBLE (not removed). Non-FA rows are untouched.
"""
from __future__ import annotations

from blitz_engine.value.fa_penalty import (
    FA_PENALTY_FACTOR,
    FA_SINK_MARGIN,
    FAStatus,
    apply_fa_penalty,
    is_truly_free_agent,
)
from blitz_engine.value.interim import (
    InterimValue,
    interim_surface,
    load_pipeline_value_engine,
)

__all__ = [
    "InterimValue",
    "interim_surface",
    "load_pipeline_value_engine",
    "FAStatus",
    "is_truly_free_agent",
    "apply_fa_penalty",
    "FA_PENALTY_FACTOR",
    "FA_SINK_MARGIN",
]
