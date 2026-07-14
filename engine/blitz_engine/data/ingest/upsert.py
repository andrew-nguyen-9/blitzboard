"""Idempotent, out-of-core upsert into a store Parquet table.

Re-ingesting the same season must NOT duplicate rows (the brief's idempotency key).
DuckDB does the whole job: `UNION ALL BY NAME` the incoming rows onto the existing
Parquet, then `row_number() … QUALIFY = 1` keeps exactly one row per key, newest
`_ingested_at` winning. The dedup streams through DuckDB and is written straight back
to disk with `COPY … TO` — history never lands whole in RAM (the M1/16 GB budget).

`ponytail:` DuckDB is the ETL engine — no hand-rolled merge/dedup loop.
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import duckdb
import pyarrow as pa

from blitz_engine.data.ingest.provenance import INGESTED_AT_COL


def _sql_str(path: Path) -> str:
    """Single-quote a path for inlining into a DuckDB COPY (escape embedded quotes)."""
    return str(path).replace("'", "''")


def upsert_parquet(
    root: str | Path,
    name: str,
    new: pa.Table,
    keys: Sequence[str],
    *,
    ts_col: str = INGESTED_AT_COL,
) -> Path:
    """Merge `new` into the `<name>.parquet` table under `root`, deduped on `keys`.

    First write creates the file. Subsequent writes union the incoming rows with the
    existing Parquet and keep one row per key (latest `ts_col` wins), so re-running an
    ingest is a no-op on unchanged data and an in-place update on changed rows.

    Returns the table's Parquet path. Raises `ValueError` if `keys` is empty (an
    unkeyed upsert can't be idempotent).
    """
    if not keys:
        raise ValueError(f"upsert_parquet({name!r}) needs at least one key column")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    dest = root / f"{name}.parquet"

    con = duckdb.connect()
    try:
        con.register("_new", new)
        if not dest.exists():
            con.execute(f"COPY (SELECT * FROM _new) TO '{_sql_str(dest)}' (FORMAT PARQUET)")
            return dest

        partition = ", ".join(f'"{k}"' for k in keys)
        tmp = dest.with_suffix(".parquet.tmp")
        con.execute(
            f"""
            COPY (
                SELECT * EXCLUDE (_rn) FROM (
                    SELECT *, row_number() OVER (
                        PARTITION BY {partition} ORDER BY "{ts_col}" DESC
                    ) AS _rn
                    FROM (
                        SELECT * FROM read_parquet('{_sql_str(dest)}')
                        UNION ALL BY NAME
                        SELECT * FROM _new
                    )
                ) WHERE _rn = 1
            ) TO '{_sql_str(tmp)}' (FORMAT PARQUET)
            """
        )
        tmp.replace(dest)  # atomic swap; the read above already completed
        return dest
    finally:
        con.close()
