from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from blitz_engine.data.ingest.status_news import Feed, FeedError, refresh

START = datetime(2025, 9, 3, tzinfo=UTC)
END = datetime(2025, 9, 4, tzinfo=UTC)
FETCHED = datetime(2025, 9, 4, 12, tzinfo=UTC)


def _ids(root) -> None:
    pq.write_table(
        pa.table({"mfl_id": ["1", "2"], "gsis_id": ["00-001", "00-002"],
                  "pfr_id": ["Alpha00", "Beta00"], "espn_id": ["101", "102"]}),
        root / "player_ids.parquet",
    )


def _injuries() -> pd.DataFrame:
    return pd.DataFrame([{
        "season": 2025, "week": 1, "team": "CHI", "source_player_id": "Alpha00",
        "source_player_id_type": "pfr_id", "player_name": "A Player",
        "report_date": "2025-09-03", "practice_status": "Limited Participation",
        "game_status": "Questionable", "injury": "hamstring",
        "source_url": "https://example.test/report", "as_of_utc": "2025-09-03T21:00:00Z",
    }])


def test_rerun_is_idempotent_and_preserves_first_observation(tmp_path) -> None:
    _ids(tmp_path)
    feed = Feed("status_injury_reports", "fixture", lambda _s, _e: _injuries())
    first = refresh(tmp_path, [feed], START, END, fetched_at=FETCHED)
    second = refresh(tmp_path, [feed], START, END,
                     fetched_at=datetime(2025, 9, 5, tzinfo=UTC))
    landed = pq.read_table(tmp_path / "status_injury_reports.parquet").to_pandas()
    assert first[0].rows_appended == 1
    assert second[0].rows_appended == 0
    assert len(landed) == 1
    assert landed.loc[0, "as_of_utc"] == "2025-09-03T21:00:00+00:00"


def test_duplicate_rows_in_one_response_are_written_once(tmp_path) -> None:
    _ids(tmp_path)
    rows = pd.concat([_injuries(), _injuries()], ignore_index=True)
    refresh(tmp_path, [Feed("status_injury_reports", "fixture", lambda _s, _e: rows)],
            START, END, fetched_at=FETCHED)
    assert pq.read_table(tmp_path / "status_injury_reports.parquet").num_rows == 1


def test_source_failure_writes_nothing(tmp_path) -> None:
    _ids(tmp_path)
    def fail(_start, _end):
        raise TimeoutError("rate limited")
    with pytest.raises(FeedError, match="rate limited"):
        refresh(tmp_path, [Feed("status_inactives", "official", fail)], START, END)
    assert not (tmp_path / "status_inactives.parquet").exists()


def test_schema_drift_writes_nothing(tmp_path) -> None:
    _ids(tmp_path)
    with pytest.raises(FeedError, match="schema drift"):
        refresh(tmp_path, [Feed("status_news", "news", lambda _s, _e: pd.DataFrame([{}]))],
                START, END)
    assert not (tmp_path / "status_news.parquet").exists()


def test_player_ids_bridge_and_resolution_failure_are_retained(tmp_path) -> None:
    _ids(tmp_path)
    rows = pd.concat([_injuries(), _injuries().assign(source_player_id="Missing00")],
                     ignore_index=True)
    result = refresh(tmp_path, [Feed("status_injury_reports", "fixture",
                                    lambda _s, _e: rows)], START, END)
    landed = pq.read_table(tmp_path / "status_injury_reports.parquet").to_pandas()
    assert result[0].resolution_rate == 0.5
    assert landed.loc[0, "gsis_id"] == "00-001"
    unresolved = landed[landed["gsis_id"].isna()].iloc[0]
    assert unresolved["resolution_failed"] == "unmapped_pfr_id"


def test_fetch_time_fallback_is_marked_and_as_of_never_null(tmp_path) -> None:
    _ids(tmp_path)
    frame = _injuries().drop(columns="as_of_utc")
    refresh(tmp_path, [Feed("status_injury_reports", "fixture", lambda _s, _e: frame)],
            START, END, fetched_at=FETCHED)
    landed = pq.read_table(tmp_path / "status_injury_reports.parquet").to_pandas()
    assert landed["as_of_utc"].notna().all()
    assert landed["as_of_is_fetch_time"].tolist() == [True]


def test_invalid_window_fails_before_fetch(tmp_path) -> None:
    called = False
    def fetch(_start, _end):
        nonlocal called
        called = True
        return _injuries()
    with pytest.raises(ValueError):
        refresh(tmp_path, [Feed("status_injury_reports", "fixture", fetch)], END, START)
    assert not called
