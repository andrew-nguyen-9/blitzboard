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


# -- resumability (E9): a completed season is never re-fetched --------------------
def test_season_present_detects_landed_seasons(tmp_path) -> None:
    import pyarrow as pa

    from blitz_engine.data.ingest import season_present

    assert not season_present(tmp_path, "pbp", 2021)  # no file yet
    frame = stamp(pa.Table.from_pandas(_fixture_pbp(2021), preserve_index=False), "nflverse")
    upsert_parquet(tmp_path, "pbp", frame, ("game_id", "play_id"))
    assert season_present(tmp_path, "pbp", 2021)
    assert not season_present(tmp_path, "pbp", 2022)


def test_ingest_season_skips_a_completed_season(tmp_path) -> None:
    """The resumable backfill: re-running a landed season costs a probe, not a download."""
    from blitz_engine.data.ingest import SourceSpec, ingest_season, nflverse
    from blitz_engine.store import ParquetStore

    calls: list[list[int]] = []

    def fetch(seasons: list[int]) -> pd.DataFrame:
        calls.append(list(seasons))
        return _fixture_pbp(seasons[0])

    spec = SourceSpec("pbp", ("game_id", "play_id"), 2014, fetch)
    with ParquetStore.open(tmp_path / "store") as store:
        original, nflverse.SOURCES_BY_TABLE["pbp"] = nflverse.SOURCES_BY_TABLE["pbp"], spec
        try:
            first = ingest_season(store, 2019, tables=["pbp"])
            second = ingest_season(store, 2019, tables=["pbp"])
            forced = ingest_season(store, 2019, tables=["pbp"], force=True)
        finally:
            nflverse.SOURCES_BY_TABLE["pbp"] = original

    assert first[0].rows == 5 and first[0].seasons == [2019] and first[0].skipped == []
    assert second[0].rows == 0 and second[0].skipped == [2019]  # no-op re-run
    assert forced[0].rows == 5  # force re-fetches
    assert calls == [[2019], [2019]]  # exactly two fetches: the first and the forced one


def test_latest_complete_season_tracks_the_calendar() -> None:
    from datetime import UTC, datetime

    from blitz_engine.data.ingest import latest_complete_season

    assert latest_complete_season(datetime(2026, 8, 25, tzinfo=UTC)) == 2025
    assert latest_complete_season(datetime(2026, 1, 5, tzinfo=UTC)) == 2024  # season in progress


# -- per-player status feeds (injuries / weekly_rosters / depth_charts / player_ids) ----
def _fixture_status(table: str, n: int = 4, note: str = "a") -> pd.DataFrame:
    """A tiny frame shaped like one status feed, carrying every key column of its spec.

    `note` is the non-key payload the update test mutates."""
    frames = {
        "injuries": lambda: {
            "season": [2021] * n,
            "game_type": ["REG"] * n,
            "week": [1 + i % 2 for i in range(n)],
            "team": ["GB", "GB", "KC", "KC"][:n],
            "gsis_id": [f"00-000{i}" for i in range(n)],
            "full_name": [f"Player {i}" for i in range(n)],
            "report_status": [note] * n,
        },
        "weekly_rosters": lambda: {
            "season": [2021] * n,
            "game_type": ["REG"] * n,
            "week": [1] * n,
            "team": ["GB"] * n,
            "player_id": [f"00-000{i}" for i in range(n)],
            "player_name": [f"Player {i}" for i in range(n)],
            "status": ["ACT", "TRC", "ACT", "RES"][:n],
            "depth_chart_position": [note] * n,
        },
        "depth_charts": lambda: {
            "season": [2021] * n,
            "game_type": ["REG"] * n,
            "week": [1] * n,
            "club_code": ["GB"] * n,
            "gsis_id": [f"00-000{i}" for i in range(n)],
            "depth_position": ["WR", "WR", "RB", "QB"][:n],
            "formation": ["Offense"] * n,
            "depth_team": ["1", "2", "1", "1"][:n],
            "position": [note] * n,
            # the 2025-schema key columns, padded exactly as the fetch wrapper pads them
            **{c: [None] * n for c in ("dt", "team", "espn_id", "pos_grp_id", "pos_id",
                                       "pos_slot")},
        },
        "player_ids": lambda: {
            "mfl_id": [f"{1000 + i}" for i in range(n)],
            "gsis_id": [f"00-000{i}" for i in range(n)],
            "pfr_id": [f"Pfr{i}" for i in range(n)],
            "name": [note] * n,
        },
    }
    return pd.DataFrame(frames[table]())


STATUS_TABLES = ("injuries", "weekly_rosters", "depth_charts", "player_ids")


@pytest.mark.parametrize("table", STATUS_TABLES)
def test_status_spec_is_registered_with_the_feeds_own_first_season(table: str) -> None:
    """`first_season` is the FEED's start, not 2014 — otherwise `plan_seasons` falsely
    degrades a season that is actually available."""
    spec = SOURCES_BY_TABLE[table]
    assert spec.table == table
    assert spec.keys, "an unkeyed spec cannot upsert idempotently"
    assert spec.first_season <= 2014
    assert plan_seasons(spec, [2014, 2025]) == ([2014, 2025], [])


@pytest.mark.parametrize("table", STATUS_TABLES)
def test_status_feed_key_is_idempotent_and_updates_in_place(table: str, tmp_path) -> None:
    """The key is a true primary key: re-ingesting the same rows does not duplicate them,
    and a changed row replaces its predecessor instead of adding one."""
    from blitz_engine.data.ingest import SourceSpec, ingest_source
    from blitz_engine.store import ParquetStore

    keys = SOURCES_BY_TABLE[table].keys
    frame = _fixture_status(table)
    present = [k for k in keys if k in frame.columns]
    assert len(frame) == len(frame.drop_duplicates(subset=present))

    payload = {"df": frame}

    def fetch(seasons: list[int]) -> pd.DataFrame:  # noqa: ARG001 — fixture, no network
        return payload["df"]

    spec = SourceSpec(table, keys, 2001, fetch)
    with ParquetStore.open(tmp_path / "store") as store:
        first = ingest_source(store, spec, [2021])
        second = ingest_source(store, spec, [2021], force=True)  # the same rows again
        payload["df"] = _fixture_status(table, note="b")  # one non-key column changed
        third = ingest_source(store, spec, [2021], force=True)
        landed = pq.read_table(store.root / f"{table}.parquet").to_pandas()

    assert first.rows == second.rows == third.rows == 4
    assert len(landed) == 4, "re-ingest duplicated rows — the key is not a primary key"
    changed = next(
        c for c in ("report_status", "depth_chart_position", "position", "name")
        if c in landed.columns
    )
    assert set(landed[changed]) == {"b"}, "the changed row did not update in place"
    assert {SOURCE_COL, INGESTED_AT_COL} <= set(landed.columns)


def test_depth_charts_union_key_keeps_both_schemas(tmp_path) -> None:
    """nflverse rebuilt depth charts for 2025 (dt/team/pos_id/pos_slot, no season/week).
    Both schemas share one table: the union key must not collapse the new-schema rows,
    whose old-schema key columns are ALL null (DuckDB partitions nulls together)."""
    from blitz_engine.data.ingest import SourceSpec, ingest_source
    from blitz_engine.store import ParquetStore

    keys = SOURCES_BY_TABLE["depth_charts"].keys
    payload = {"df": _fixture_status("depth_charts")}
    new = pd.DataFrame(
        {
            "dt": ["2025-08-03T10:09:07Z"] * 4,
            "team": ["BUF"] * 4,
            "gsis_id": [None, None, "00-0001", "00-0002"],  # a null gsis_id is real in 2025
            "espn_id": ["1", "2", "3", "4"],
            "pos_grp_id": ["21"] * 4,
            "pos_id": ["1"] * 4,
            "pos_slot": [1, 1, 2, 3],
            "pos_rank": [7, 13, 1, 1],
            **{c: [None] * 4 for c in ("season", "game_type", "week", "club_code",
                                       "depth_position", "formation", "depth_team")},
        }
    )

    def fetch(seasons: list[int]) -> pd.DataFrame:  # noqa: ARG001 — fixture, no network
        return payload["df"]

    spec = SourceSpec("depth_charts", keys, 2001, fetch)
    with ParquetStore.open(tmp_path / "store") as store:
        ingest_source(store, spec, [2021])
        payload["df"] = new
        ingest_source(store, spec, [2025])
        landed = pq.read_table(store.root / "depth_charts.parquet").to_pandas()

    assert len(landed) == 8, "the union key collapsed one of the two schemas"
    assert landed["season"].notna().sum() == 4  # the old half
    assert landed["dt"].notna().sum() == 4  # the new half
