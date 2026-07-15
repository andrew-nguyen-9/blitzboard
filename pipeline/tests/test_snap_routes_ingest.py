"""v4 E2 — offensive snap % + routes-run ingest.

Covers the shared column contract (offense_snap_pct, routes_run), the GSIS
overlay into build_rows, seasonal aggregation, and the reliability guard: the
ingest must succeed from a vendored parquet when the live nflverse pull is down.

    python -m pytest tests/test_snap_routes_ingest.py
"""
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import history_ingest as hi  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "snap_routes_fixture.parquet"


def _sr_frame():
    return pd.DataFrame({
        "player_id": ["00-0001", "00-0001", "00-0002"],
        "season": [2024, 2024, 2024],
        "week": [1, 2, 1],
        "offense_snap_pct": [0.80, 0.60, 0.50],
        "routes_run": [40.0, 30.0, 20.0],
    })


def test_stat_cols_carry_contract_keys():
    # Shared pipeline column contract fixed by B — E1 reads these.
    assert "offense_snap_pct" in hi.STAT_COLS
    assert "routes_run" in hi.STAT_COLS


def test_index_weekly_keys_by_player_season_week():
    idx = hi.snap_routes_index(_sr_frame(), weekly=True)
    assert idx[("00-0001", 2024, 1)] == (0.80, 40.0)
    assert idx[("00-0001", 2024, 2)] == (0.60, 30.0)
    assert idx[("00-0002", 2024, 1)] == (0.50, 20.0)


def test_index_seasonal_aggregates_mean_snap_sum_routes():
    idx = hi.snap_routes_index(_sr_frame(), weekly=False)
    # snap % averaged across weeks, routes summed (season-long volume); week=None.
    sp, rr = idx[("00-0001", 2024, None)]
    assert sp == pytest.approx(0.70)
    assert rr == pytest.approx(70.0)
    assert idx[("00-0002", 2024, None)] == (pytest.approx(0.50), pytest.approx(20.0))


def test_empty_frame_yields_empty_index():
    assert hi.snap_routes_index(pd.DataFrame(columns=hi.SNAP_ROUTES_COLS), weekly=True) == {}
    assert hi.snap_routes_index(None, weekly=False) == {}


def _stats_df():
    # Minimal weekly frame mimicking nfl_data_py: keyed by GSIS player_id.
    return pd.DataFrame({
        "player_id": ["00-0001", "00-0002"],
        "season": [2024, 2024],
        "week": [1, 1],
        "receptions": [5.0, 3.0],
        "fantasy_points": [12.0, 7.0],
    })


def test_build_rows_overlays_snap_routes_onto_matched_players():
    by_gsis = {"00-0001": "pid-1", "00-0002": "pid-2"}
    idx = hi.snap_routes_index(_sr_frame(), weekly=True)
    rows = hi.build_rows(_stats_df(), weekly=True, by_gsis=by_gsis, by_sleeper={},
                         gsis_to_sleeper={}, snap_routes=idx)
    got = {r["player_id"]: r["stats"] for r in rows}
    assert got["pid-1"]["offense_snap_pct"] == 0.80
    assert got["pid-1"]["routes_run"] == 40.0
    assert got["pid-2"]["offense_snap_pct"] == 0.50
    assert got["pid-2"]["routes_run"] == 20.0
    # Idempotent: a second identical build yields identical rows.
    again = hi.build_rows(_stats_df(), weekly=True, by_gsis=by_gsis, by_sleeper={},
                          gsis_to_sleeper={}, snap_routes=idx)
    assert rows == again


def test_build_rows_without_snap_routes_leaves_keys_null():
    # Contract keys are always present in stats, even absent an overlay.
    rows = hi.build_rows(_stats_df(), weekly=True, by_gsis={"00-0001": "pid-1"},
                         by_sleeper={}, gsis_to_sleeper={})
    stats = rows[0]["stats"]
    assert stats["offense_snap_pct"] is None
    assert stats["routes_run"] is None


def test_reliability_guard_reads_vendored_parquet_when_live_down(monkeypatch):
    # Simulate the live nflverse source being unreachable.
    def _boom(_seasons):
        raise ConnectionError("nflverse unreachable")

    monkeypatch.setattr(hi, "_live_snap_routes", _boom)
    frame = hi.load_snap_routes([2024], parquet=FIXTURE)
    assert not frame.empty
    assert list(frame.columns) == hi.SNAP_ROUTES_COLS
    assert (frame["season"] == 2024).all()
    # Overlay works end-to-end off the vendored frame.
    idx = hi.snap_routes_index(frame, weekly=True)
    assert idx  # non-empty
    sp, rr = next(iter(idx.values()))
    assert 0.0 <= sp <= 1.0 and rr > 0


def test_reliability_guard_empty_when_live_down_and_no_parquet(monkeypatch, tmp_path):
    monkeypatch.setattr(hi, "_live_snap_routes",
                        lambda _s: (_ for _ in ()).throw(ConnectionError("down")))
    frame = hi.load_snap_routes([2024], parquet=tmp_path / "missing.parquet")
    assert frame.empty
    assert list(frame.columns) == hi.SNAP_ROUTES_COLS
