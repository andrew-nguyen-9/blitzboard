"""New free engine data sources (v4 E0-sources).

Four degrade-safe adapters feeding the engine `ParquetStore`, each ONE small module
sharing `base.EngineSource` (no per-source framework):

    nflverse_advanced  keyless   NGS / snaps / depth charts / routes-air-yards
    vegas_odds         ODDS_API_KEY   betting lines (reuses pipeline OddsAdapter)
    combine_draft      CFBD_API_KEY   combine athleticism + draft capital
    coaching_roles     keyless   coaching staff + contracts / roles

`run_all(store)` runs every source degrade-safe and reports which keys were present
without failing (cf. `pipeline/selftest.py`).
"""
from __future__ import annotations

from blitz_engine.data.sources.base import EngineSource, SourceResult
from blitz_engine.data.sources.coaching_roles import CoachingRolesSource
from blitz_engine.data.sources.combine_draft import CombineDraftSource
from blitz_engine.data.sources.nflverse_advanced import NflverseAdvancedSource
from blitz_engine.data.sources.vegas_odds import VegasOddsSource

__all__ = [
    "SOURCES",
    "CoachingRolesSource",
    "CombineDraftSource",
    "EngineSource",
    "NflverseAdvancedSource",
    "SourceResult",
    "VegasOddsSource",
    "sources",
    "run_all",
]

# The registry: adding a source = adding a class here (no central switch).
SOURCES: tuple[type[EngineSource], ...] = (
    NflverseAdvancedSource,
    VegasOddsSource,
    CombineDraftSource,
    CoachingRolesSource,
)


def sources() -> list[EngineSource]:
    """Instantiate every registered engine source."""
    return [cls() for cls in SOURCES]


def run_all(store: object) -> list[SourceResult]:
    """Run every source degrade-safe against `store`; return one result each.

    Never raises for a missing key/source — unavailable sources report
    ``available=False`` with 0 rows, and the rest still run.
    """
    return [s.run(store) for s in sources()]  # type: ignore[arg-type]
