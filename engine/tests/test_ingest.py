"""E0-ingest tests — no network. A fixture PBP season proves float32 casting,
provenance stamping, and idempotent upsert (re-ingest = no dup rows)."""
from __future__ import annotations

import pandas as pd
import pyarrow.parquet as pq
import pytest

from blitz_engine.data.ingest import (
    INGESTED_AT_COL,
    SOURCE_COL,
    SOURCES_BY_TABLE,
    plan_seasons,
    stamp,
    to_float32,
    upsert_parquet,
)


def _fixture_pbp(season: int, n: int = 5) -> pd.DataFrame:
    """A tiny PBP-shaped frame keyed by (game_id, play_id)."""
    return pd.DataFrame(
        {
            "game_id": [f"{season}_0{i % 2}" for i in range(n)],
            "play_id": list(range(n)),
            "season": [season] * n,
            "week": [1] * n,
            "epa": [0.1 * i for i in range(n)],  # float64 → must become float32
        }
    )


def test_to_float32_downcasts_only_floats() -> None:
    import pyarrow as pa

    table = pa.Table.from_pandas(_fixture_pbp(2020), preserve_index=False)
    out = to_float32(table, "float32")
    assert out.schema.field("epa").type == pa.float32()
    assert out.schema.field("play_id").type == table.schema.field("play_id").type


def test_stamp_is_idempotent_and_adds_provenance() -> None:
    import pyarrow as pa

    table = pa.Table.from_pandas(_fixture_pbp(2020), preserve_index=False)
    once = stamp(table, "nflverse", at="2026-01-01T00:00:00+00:00")
    twice = stamp(once, "nflverse", at="2026-01-02T00:00:00+00:00")
    assert SOURCE_COL in twice.column_names and INGESTED_AT_COL in twice.column_names
    # re-stamping replaces, never duplicates the provenance columns
    assert twice.column_names.count(SOURCE_COL) == 1
    assert twice.column(INGESTED_AT_COL)[0].as_py() == "2026-01-02T00:00:00+00:00"


def test_upsert_is_idempotent(tmp_path) -> None:
    import pyarrow as pa

    keys = ("game_id", "play_id")
    frame = stamp(
        to_float32(pa.Table.from_pandas(_fixture_pbp(2021), preserve_index=False)),
        "nflverse",
        at="2026-01-01T00:00:00+00:00",
    )
    dest = upsert_parquet(tmp_path, "pbp", frame, keys)
    assert pq.read_table(dest).num_rows == 5

    # re-ingest the identical season (newer timestamp) → still exactly 5 rows, no dups
    frame2 = stamp(
        to_float32(pa.Table.from_pandas(_fixture_pbp(2021), preserve_index=False)),
        "nflverse",
        at="2026-06-01T00:00:00+00:00",
    )
    upsert_parquet(tmp_path, "pbp", frame2, keys)
    assert pq.read_table(dest).num_rows == 5


def test_upsert_appends_new_keys(tmp_path) -> None:
    import pyarrow as pa

    keys = ("game_id", "play_id")
    a = stamp(pa.Table.from_pandas(_fixture_pbp(2021, n=3), preserve_index=False), "nflverse")
    upsert_parquet(tmp_path, "pbp", a, keys)
    b = stamp(pa.Table.from_pandas(_fixture_pbp(2022, n=4), preserve_index=False), "nflverse")
    dest = upsert_parquet(tmp_path, "pbp", b, keys)
    # disjoint (season baked into game_id) → union of both
    assert pq.read_table(dest).num_rows == 7


def test_upsert_requires_keys(tmp_path) -> None:
    import pyarrow as pa

    with pytest.raises(ValueError):
        upsert_parquet(tmp_path, "pbp", pa.table({"a": [1]}), keys=())


def test_plan_seasons_degrades_older_seasons() -> None:
    ngs = SOURCES_BY_TABLE["ngs_passing"]  # first_season 2016
    to_fetch, degraded = plan_seasons(ngs, [2014, 2015, 2016, 2020])
    assert to_fetch == [2016, 2020]
    assert degraded == [2014, 2015]  # flagged, never an error

    pbp = SOURCES_BY_TABLE["pbp"]  # first_season 2014 → nothing degraded in range
    assert plan_seasons(pbp, [2014, 2015]) == ([2014, 2015], [])
