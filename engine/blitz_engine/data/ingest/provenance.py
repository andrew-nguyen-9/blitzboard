"""Provenance stamping + the M1 float32 cast — the two per-row transforms every
ingest applies before a table lands in the store.

Provenance is COLUMN-BASED: every ingested table carries `_source` (who produced it)
and `_ingested_at` (UTC ISO timestamp of the ingest run). The validation gate asserts
both are present and non-null, so "source + timestamp per table" is a data invariant,
not a side file that can drift. `ponytail:` two columns beat a metadata table + join.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pyarrow as pa

SOURCE_COL = "_source"
INGESTED_AT_COL = "_ingested_at"
PROVENANCE_COLS = (SOURCE_COL, INGESTED_AT_COL)


def utc_now_iso() -> str:
    """Sortable UTC ISO-8601 timestamp — string order == chronological order, so it
    doubles as the dedup tie-breaker in `upsert_parquet`."""
    return datetime.now(UTC).isoformat()


def to_float32(table: pa.Table, dtype: str = "float32") -> pa.Table:
    """Downcast every float64 column to `dtype` (the M1/16 GB budget). Non-float
    columns are untouched. A no-op when `dtype` is not a narrower float."""
    target = pa.type_for_alias(dtype)
    if not pa.types.is_floating(target):
        return table
    fields = [
        f.with_type(target) if pa.types.is_float64(f.type) else f for f in table.schema
    ]
    return table.cast(pa.schema(fields))


def stamp(table: pa.Table, source: str, at: str | None = None) -> pa.Table:
    """Append/overwrite the provenance columns. Idempotent: re-stamping replaces the
    existing columns rather than duplicating them."""
    at = at or utc_now_iso()
    n = table.num_rows
    for name in PROVENANCE_COLS:
        if name in table.column_names:
            table = table.drop_columns(name)
    table = table.append_column(SOURCE_COL, pa.array([source] * n, pa.string()))
    table = table.append_column(INGESTED_AT_COL, pa.array([at] * n, pa.string()))
    return table
