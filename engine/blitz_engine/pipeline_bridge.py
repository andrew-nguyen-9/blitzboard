"""Import the EXISTING cron adapters without moving or duplicating them.

W1 decision (docs/design/v4-engine-architecture.md §"Shared code seam"): the engine
REUSES `pipeline/adapters/` by import, it does not re-extract them. `pipeline/` has no
packaging metadata (it is a flat module dir run by GitHub Actions), so instead of a
`pip install -e`, we put its root on `sys.path` on demand — a documented import path
costs nothing; a premature `shared/` package would cost a refactor of the working cron.

    from blitz_engine.pipeline_bridge import load_adapters
    discover, Adapter = load_adapters()
    for a in discover():          # every degrade-safe source adapter
        ...

New engine source adapters (E0-sources) subclass this same `Adapter` under
`blitz_engine/data/sources/`, reusing the base degrade contract.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

__all__ = ["load_adapters", "pipeline_root"]


def pipeline_root() -> Path:
    """Absolute path to the repo's `pipeline/` dir (sibling of `engine/`)."""
    return Path(__file__).resolve().parents[2] / "pipeline"


def _ensure_on_path() -> None:
    root = str(pipeline_root())
    if root not in sys.path:
        sys.path.insert(0, root)


def load_adapters() -> tuple[object, type]:
    """Return `(discover, Adapter)` from the existing `pipeline/adapters` package.

    `discover()` instantiates every concrete source adapter; `Adapter` is the base
    class new engine sources subclass. Raises `ImportError` if `pipeline/` is missing.
    """
    _ensure_on_path()
    import adapters  # pipeline/adapters/__init__ (base + one module per source)

    return adapters.discover, adapters.Adapter


def load_common() -> ModuleType:
    """Return the pipeline's `common` module (retry/backoff, upsert, console)."""
    _ensure_on_path()
    import common  # pipeline/common.py

    return common
