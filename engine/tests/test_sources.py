"""E0-sources acceptance — every new source normalizes+writes a fixture, and
degrades to neutral (no crash, flagged unavailable) when its key/payload is absent.

NO live network: keyed sources are driven with `run(store, raw=fixture)`; the degrade
path is asserted with the key deleted from the environment.
"""
from __future__ import annotations

import pandas as pd
import pytest

from blitz_engine.data.sources import (
    SOURCES,
    CoachingRolesSource,
    CombineDraftSource,
    NflverseAdvancedSource,
    VegasOddsSource,
    run_all,
    sources,
)
from blitz_engine.data.sources.base import EngineSource

# -- fixtures per source (raw payload shaped like each upstream) -----------

_NFLVERSE_RAW = [
    {"player_id": "00-1", "player_name": "WR A", "position": "WR", "team": "SF",
     "season": 2025, "week": 1, "snap_pct": 0.82, "routes_run": 34, "air_yards": 120,
     "target_share": 0.28, "ngs_avg_separation": 3.1, "ngs_avg_cushion": 5.4,
     "ngs_yac_above_expected": 1.2, "depth_chart_pos": "WR", "depth_chart_order": 1},
    # present-or-neutral: this row is missing NGS + depth columns entirely.
    {"player_id": "00-2", "player_name": "WR B", "position": "WR", "team": "SF",
     "season": 2025, "week": 1, "snap_pct": 0.40, "routes_run": 12},
    {"no_player_id": True, "season": 2025, "week": 1},  # dropped (missing key col)
]

_COMBINE_RAW = [
    {"player_id": "c-1", "player_name": "RB Z", "position": "RB", "college": "UGA",
     "forty": 4.41, "bench": 22, "vertical": 38.5, "broad_jump": 128, "cone": 6.9,
     "shuttle": 4.2, "ras": 9.4, "draft_year": 2025, "draft_round": 1,
     "draft_pick": 5, "draft_overall": 5, "draft_capital": 30.0},
    {"player_id": "c-2", "player_name": "WR Y", "draft_year": 2025},  # sparse → neutral
]

_COACHING_RAW = [
    {"player_id": "p-1", "player_name": "QB Q", "position": "QB", "team": "SF",
     "season": 2025, "role": "starter", "contract_years_left": 3,
     "contract_apy": 45.0, "contract_guaranteed_pct": 0.6, "head_coach": "Shanahan",
     "offensive_coordinator": "New OC", "play_caller": "Shanahan"},
    {"player_id": "p-2", "season": 2025},  # sparse → neutral columns
]

_ODDS_RAW = [
    {"id": "evt1", "home_team": "SF", "away_team": "SEA", "commence_time": "2025-09-07T20:00:00Z",
     "bookmakers": [
         {"markets": [
             {"key": "h2h", "outcomes": [
                 {"name": "SF", "price": -180}, {"name": "SEA", "price": 155}]},
             {"key": "spreads", "outcomes": [
                 {"name": "SF", "point": -3.5}, {"name": "SEA", "point": 3.5}]},
             {"key": "totals", "outcomes": [
                 {"name": "Over", "point": 47.5}, {"name": "Under", "point": 47.5}]},
         ]},
     ]},
]


# -- registry --------------------------------------------------------------

def test_registry_has_all_four_sources() -> None:
    names = {cls().name for cls in SOURCES}
    assert names == {"nflverse_advanced", "vegas_odds", "combine_draft", "coaching_roles"}
    assert all(isinstance(s, EngineSource) for s in sources())


# -- keyless sources: normalize + write; empty payload degrades neutral ----

@pytest.mark.parametrize(
    "source_cls, raw, table",
    [
        (NflverseAdvancedSource, _NFLVERSE_RAW, "nflverse_advanced"),
        (CoachingRolesSource, _COACHING_RAW, "coaching_roles"),
    ],
)
def test_keyless_source_normalizes_and_writes(source_cls, raw, table, store) -> None:
    src = source_cls()
    res = src.run(store, raw=raw)
    assert res.available is True
    assert res.rows == 2  # sparse rows kept (present-or-neutral), keyless dropped
    assert table in store.tables()
    df = store.table(table).df()
    # provenance stamped on every row
    assert {"prov_source", "prov_dataset", "prov_ingested_at"} <= set(df.columns)
    assert (df["prov_source"] == src.name).all()
    # neutral fill: schema columns all present even when the raw row omitted them
    assert set(src.columns) <= set(df.columns)


@pytest.mark.parametrize("source_cls", [NflverseAdvancedSource, CoachingRolesSource])
def test_keyless_source_empty_payload_degrades_neutral(source_cls, store) -> None:
    src = source_cls()
    for empty in (None, [], [{"junk": 1}]):
        res = src.run(store, raw=empty)
        assert res.available is True
        assert res.rows == 0
    assert src.table not in store.tables()  # nothing written → downstream reads neutral


# -- keyed sources: absent key → unavailable; present key → writes ---------

@pytest.mark.parametrize(
    "source_cls, key, raw, expect_rows",
    [
        (CombineDraftSource, "CFBD_API_KEY", _COMBINE_RAW, 2),
        (VegasOddsSource, "ODDS_API_KEY", _ODDS_RAW, 1),
    ],
)
def test_keyed_source_absent_key_degrades_and_is_flagged(
    source_cls, key, raw, expect_rows, store, monkeypatch
) -> None:
    monkeypatch.delenv(key, raising=False)
    src = source_cls()
    assert src.enabled is False
    res = src.run(store)  # no raw, no key → must NOT fetch or write, must not raise
    assert res.available is False
    assert res.rows == 0
    assert res.keys_present == {key: False}
    assert res.reason and key in res.reason
    assert src.table not in store.tables()


@pytest.mark.parametrize(
    "source_cls, key, raw, expect_rows, table",
    [
        (CombineDraftSource, "CFBD_API_KEY", _COMBINE_RAW, 2, "combine_draft"),
        (VegasOddsSource, "ODDS_API_KEY", _ODDS_RAW, 1, "vegas_odds"),
    ],
)
def test_keyed_source_with_key_and_fixture_writes(
    source_cls, key, raw, expect_rows, table, store, monkeypatch
) -> None:
    monkeypatch.setenv(key, "test-key")
    src = source_cls()
    assert src.enabled is True
    res = src.run(store, raw=raw)  # raw provided → no network
    assert res.available is True
    assert res.rows == expect_rows
    assert res.keys_present == {key: True}
    df = store.table(table).df()
    assert {"prov_source", "prov_dataset", "prov_ingested_at"} <= set(df.columns)


def test_odds_source_reuses_pipeline_consensus(monkeypatch, store) -> None:
    """The vegas source delegates to the pipeline OddsAdapter (consensus row/event)."""
    monkeypatch.setenv("ODDS_API_KEY", "x")
    VegasOddsSource().run(store, raw=_ODDS_RAW)
    row = store.table("vegas_odds").df().iloc[0]
    assert row["event_id"] == "evt1"
    assert row["home_spread"] == -3.5
    assert row["total"] == 47.5


# -- run_all: degrade-safe, reports keys without failing -------------------

def test_run_all_degrade_safe_reports_keys(store, monkeypatch) -> None:
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    monkeypatch.delenv("CFBD_API_KEY", raising=False)
    # keyless sources would otherwise hit the network in fetch() — stub to empty.
    monkeypatch.setattr(NflverseAdvancedSource, "fetch", lambda self: [])
    monkeypatch.setattr(CoachingRolesSource, "fetch", lambda self: [])
    results = run_all(store)  # no network: keyless fetch → [], keyed → unavailable
    assert len(results) == len(SOURCES)
    by_name = {r.name: r for r in results}
    assert by_name["vegas_odds"].available is False
    assert by_name["combine_draft"].available is False
    assert by_name["nflverse_advanced"].available is True  # keyless, always enabled
    assert by_name["coaching_roles"].available is True
    assert all(isinstance(r.rows, int) for r in results)  # never raised


def test_provenance_dataframe_is_writable(store) -> None:
    """A stamped row round-trips through the store as a real parquet table."""
    src = NflverseAdvancedSource()
    src.run(store, raw=_NFLVERSE_RAW)
    back = store.query("SELECT COUNT(*) AS n FROM nflverse_advanced").fetchone()[0]
    assert back == 2
    assert isinstance(store.table("nflverse_advanced").df(), pd.DataFrame)
