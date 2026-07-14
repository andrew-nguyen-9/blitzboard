"""BlitzBoard heavy local quant engine (`blitz_engine`).

Two-tier seam (see docs/design/v4-engine-architecture.md): this package is the LOCAL,
JAX/NumPyro/DuckDB-heavy tier that produces versioned draft snapshots. The `pipeline/`
package stays the free GitHub-Actions cron and must never import JAX/torch.

Public foundation surface (E0-scaffold — every v4 unit builds on this):
    config    -> EngineConfig, load_config   (M1/16GB knobs, single source of truth)
    store     -> ParquetStore                (DuckDB + mmap Parquet data-access seam)
    snapshot  -> Snapshot, SCHEMA_VERSION     (versioned hand-off bundle)
    registry  -> ModelRegistry, RunRecord     (reproducible run records)
"""
from __future__ import annotations

from blitz_engine.config import EngineConfig, load_config
from blitz_engine.registry import ModelRegistry, RunRecord
from blitz_engine.snapshot import SCHEMA_VERSION, Snapshot
from blitz_engine.store import ParquetStore

__all__ = [
    "SCHEMA_VERSION",
    "EngineConfig",
    "ModelRegistry",
    "ParquetStore",
    "RunRecord",
    "Snapshot",
    "load_config",
]

__version__ = "0.1.0"
