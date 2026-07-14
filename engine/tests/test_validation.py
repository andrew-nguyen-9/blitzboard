"""E0-ingest validation-gate tests — no network. A clean fixture store passes; a
deliberately-corrupted store BLOCKS (gate raises ValidationError)."""
from __future__ import annotations

import pandas as pd
import pytest

from blitz_engine.data.ingest import stamp, upsert_parquet
from blitz_engine.data.validation import (
    TableSpec,
    ValidationError,
    gate,
    validate,
)

KEYS = ("game_id", "play_id")
SPEC = TableSpec(
    "pbp",
    required_columns=("game_id", "play_id", "season"),
    key_columns=KEYS,
    min_rows=3,
)


def _clean_pbp(n: int = 5) -> object:
    import pyarrow as pa

    df = pd.DataFrame(
        {
            "game_id": [f"2021_0{i}" for i in range(n)],
            "play_id": list(range(n)),
            "season": [2021] * n,
        }
    )
    return stamp(pa.Table.from_pandas(df, preserve_index=False), "nflverse")


def _write(store, table) -> None:
    upsert_parquet(store.root, "pbp", table, KEYS)


def test_gate_passes_on_clean_store(store) -> None:
    _write(store, _clean_pbp())
    report = gate(store, [SPEC])  # must not raise
    assert report.ok


def test_gate_blocks_missing_table(store) -> None:
    with pytest.raises(ValidationError) as exc:
        gate(store, [SPEC])  # nothing written → table absent
    assert any(f.check == "exists" for f in exc.value.report.failures)


def test_gate_blocks_missing_required_column(store) -> None:
    import pyarrow as pa

    df = pd.DataFrame({"game_id": ["2021_00"], "play_id": [0]})  # no `season`
    _write(store, stamp(pa.Table.from_pandas(df, preserve_index=False), "nflverse"))
    with pytest.raises(ValidationError) as exc:
        gate(store, [SPEC])
    assert any(f.check == "schema" for f in exc.value.report.failures)


def test_gate_blocks_too_few_rows(store) -> None:
    _write(store, _clean_pbp(n=1))  # < min_rows=3
    report = validate(store, [SPEC])
    assert not report.ok
    assert any(f.check == "row_count" for f in report.failures)


def test_gate_blocks_duplicate_keys(store) -> None:
    import pyarrow as pa

    # bypass the idempotent upsert to plant a poisoned duplicate row
    poison = pa.concat_tables([_clean_pbp(3), _clean_pbp(3)])
    import pyarrow.parquet as pq

    pq.write_table(poison, store.path("pbp"))
    with pytest.raises(ValidationError) as exc:
        gate(store, [SPEC])
    assert any(f.check == "key_unique" for f in exc.value.report.failures)


def test_gate_blocks_null_provenance(store) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    from blitz_engine.data.ingest import INGESTED_AT_COL, SOURCE_COL

    df = pd.DataFrame(
        {
            "game_id": [f"2021_0{i}" for i in range(4)],
            "play_id": list(range(4)),
            "season": [2021] * 4,
            SOURCE_COL: [None] * 4,  # provenance wiped
            INGESTED_AT_COL: [None] * 4,
        }
    )
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), store.path("pbp"))
    with pytest.raises(ValidationError) as exc:
        gate(store, [SPEC])
    assert any(f.check == "provenance" for f in exc.value.report.failures)


def test_gate_blocks_stale_data(store) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    from blitz_engine.data.ingest import INGESTED_AT_COL

    df = pd.DataFrame(
        {
            "game_id": [f"2021_0{i}" for i in range(4)],
            "play_id": list(range(4)),
            "season": [2021] * 4,
        }
    )
    table = stamp(pa.Table.from_pandas(df, preserve_index=False), "nflverse")
    # force an ancient ingest timestamp
    table = table.drop_columns(INGESTED_AT_COL).append_column(
        INGESTED_AT_COL, pa.array(["2000-01-01T00:00:00+00:00"] * 4, pa.string())
    )
    pq.write_table(table, store.path("pbp"))
    fresh_spec = TableSpec(
        "pbp", required_columns=("season",), key_columns=KEYS, min_rows=1, freshness_days=7
    )
    report = validate(store, [fresh_spec])
    assert any(f.check == "freshness" and not f.ok for f in report.failures)
