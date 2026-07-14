"""2014+ PBP + advanced-stats ingest into the ParquetStore (E0-ingest).

Public API:
    from blitz_engine.data.ingest import ingest_all, ingest_source, SOURCES
    from blitz_engine.data.ingest import upsert_parquet, stamp, to_float32

`ingest_all(store, range(2014, 2026))` fills the store idempotently; the validation
gate (`blitz_engine.data.validation`) must pass before any model reads it.
"""
from __future__ import annotations

from blitz_engine.data.ingest.nflverse import (
    FIRST_SEASON,
    SOURCE_NAME,
    SOURCES,
    SOURCES_BY_TABLE,
    IngestResult,
    SourceSpec,
    ingest_all,
    ingest_source,
    plan_seasons,
)
from blitz_engine.data.ingest.provenance import (
    INGESTED_AT_COL,
    PROVENANCE_COLS,
    SOURCE_COL,
    stamp,
    to_float32,
    utc_now_iso,
)
from blitz_engine.data.ingest.upsert import upsert_parquet

__all__ = [
    "FIRST_SEASON",
    "INGESTED_AT_COL",
    "PROVENANCE_COLS",
    "SOURCE_COL",
    "SOURCE_NAME",
    "SOURCES",
    "SOURCES_BY_TABLE",
    "IngestResult",
    "SourceSpec",
    "ingest_all",
    "ingest_source",
    "plan_seasons",
    "stamp",
    "to_float32",
    "upsert_parquet",
    "utc_now_iso",
]
