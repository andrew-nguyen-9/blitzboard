"""External-data adapters (F2). One free source per module; auto-discovered.

See `base.py` for the contract and `docs/architecture/DATA_SOURCES.md` for how to
add one. Import surface is intentionally tiny: the framework, not the sources."""
from __future__ import annotations

from adapters.base import Adapter, discover, run_all

__all__ = ["Adapter", "discover", "run_all"]
