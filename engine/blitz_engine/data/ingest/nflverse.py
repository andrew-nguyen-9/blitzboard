"""nflverse / nfl_data_py ingest: 2014+ play-by-play + all available advanced stats.

Each source is one `SourceSpec` (table name, dedup keys, earliest available season,
fetch fn). Adding a source is adding a spec — no ETL framework (`ponytail:`).

DEGRADE, DON'T FAIL (brief): advanced feeds start in different years (NGS 2016, PFR
2018, FTN 2022). Requesting an older season doesn't error — that season is *flagged*
degraded for that source and simply not fetched. Play-by-play covers the full 2014+
range, so a model always has the spine even when the advanced layers are thin.

`nfl_data_py` is imported lazily inside each fetch fn (same pattern as
`pipeline/history_ingest.py`); it is never needed to import this module or run tests.
The fetch step is the ONLY networked step — everything downstream is fixture-testable.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pyarrow as pa

from blitz_engine.config import EngineConfig, load_config
from blitz_engine.data.ingest.provenance import stamp, to_float32, utc_now_iso
from blitz_engine.data.ingest.upsert import upsert_parquet

if TYPE_CHECKING:
    import pandas as pd

    from blitz_engine.store import ParquetStore

FIRST_SEASON = 2014
SOURCE_NAME = "nflverse/nfl_data_py"


# -- lazy fetch wrappers (network) ---------------------------------------------
def _fetch_pbp(seasons: list[int]) -> pd.DataFrame:
    import nfl_data_py as nfl

    return nfl.import_pbp_data(seasons, downcast=True, cache=False)


def _fetch_ngs(stat_type: str) -> Callable[[list[int]], pd.DataFrame]:
    def fetch(seasons: list[int]) -> pd.DataFrame:
        import nfl_data_py as nfl

        return nfl.import_ngs_data(stat_type=stat_type, years=seasons)

    return fetch


def _fetch_weekly_pfr(stat_type: str) -> Callable[[list[int]], pd.DataFrame]:
    def fetch(seasons: list[int]) -> pd.DataFrame:
        import nfl_data_py as nfl

        return nfl.import_weekly_pfr(s_type=stat_type, years=seasons)

    return fetch


def _fetch_snap_counts(seasons: list[int]) -> pd.DataFrame:
    import nfl_data_py as nfl

    return nfl.import_snap_counts(seasons)


def _fetch_ftn(seasons: list[int]) -> pd.DataFrame:
    import nfl_data_py as nfl

    return nfl.import_ftn_data(seasons)


# -- source registry -----------------------------------------------------------
@dataclass(frozen=True)
class SourceSpec:
    """One nflverse feed → one store table."""

    table: str
    keys: tuple[str, ...]
    first_season: int
    fetch: Callable[[list[int]], pd.DataFrame]
    source: str = SOURCE_NAME


SOURCES: tuple[SourceSpec, ...] = (
    SourceSpec("pbp", ("game_id", "play_id"), 2014, _fetch_pbp),
    SourceSpec("ngs_passing", ("season", "week", "player_gsis_id"), 2016, _fetch_ngs("passing")),
    SourceSpec("ngs_rushing", ("season", "week", "player_gsis_id"), 2016, _fetch_ngs("rushing")),
    SourceSpec(
        "ngs_receiving", ("season", "week", "player_gsis_id"), 2016, _fetch_ngs("receiving")
    ),
    SourceSpec("pfr_pass", ("season", "week", "pfr_player_id"), 2018, _fetch_weekly_pfr("pass")),
    SourceSpec("pfr_rush", ("season", "week", "pfr_player_id"), 2018, _fetch_weekly_pfr("rush")),
    SourceSpec("pfr_rec", ("season", "week", "pfr_player_id"), 2018, _fetch_weekly_pfr("rec")),
    SourceSpec("snap_counts", ("game_id", "pfr_player_id"), 2014, _fetch_snap_counts),
    SourceSpec("ftn_charting", ("nflverse_game_id", "nflverse_play_id"), 2022, _fetch_ftn),
)
SOURCES_BY_TABLE = {s.table: s for s in SOURCES}


# -- planning + result ---------------------------------------------------------
def plan_seasons(spec: SourceSpec, seasons: Sequence[int]) -> tuple[list[int], list[int]]:
    """Split requested seasons into (to_fetch, degraded) for a source. `degraded`
    seasons predate the feed and are flagged, never fetched, never an error."""
    fetch = sorted(s for s in seasons if s >= spec.first_season)
    degraded = sorted(s for s in seasons if s < spec.first_season)
    return fetch, degraded


@dataclass
class IngestResult:
    """What one source ingest did — logged as run provenance."""

    table: str
    source: str
    rows: int = 0
    seasons: list[int] = field(default_factory=list)
    degraded: list[int] = field(default_factory=list)
    ingested_at: str = field(default_factory=utc_now_iso)


# -- ingest --------------------------------------------------------------------
def ingest_source(
    store: ParquetStore,
    spec: SourceSpec,
    seasons: Sequence[int],
    *,
    config: EngineConfig | None = None,
) -> IngestResult:
    """Fetch → float32 → stamp provenance → idempotent upsert for one source.

    Older seasons lacking this feed are degraded (flagged in the result), not fetched.
    If every requested season is degraded, nothing is fetched and an empty result is
    returned — the source simply has no data that far back."""
    cfg = config or store.config or load_config()
    to_fetch, degraded = plan_seasons(spec, seasons)
    if not to_fetch:
        return IngestResult(spec.table, spec.source, rows=0, seasons=[], degraded=degraded)

    at = utc_now_iso()
    df = spec.fetch(to_fetch)
    table = pa.Table.from_pandas(df, preserve_index=False)
    table = to_float32(table, cfg.dtype)
    table = stamp(table, spec.source, at=at)
    upsert_parquet(store.root, spec.table, table, spec.keys)
    return IngestResult(
        spec.table,
        spec.source,
        rows=table.num_rows,
        seasons=to_fetch,
        degraded=degraded,
        ingested_at=at,
    )


def ingest_all(
    store: ParquetStore,
    seasons: Sequence[int],
    *,
    tables: Sequence[str] | None = None,
    config: EngineConfig | None = None,
) -> list[IngestResult]:
    """Ingest every source (or the named subset) for `seasons`. Idempotent end-to-end;
    safe to re-run. Returns one `IngestResult` per source for run provenance/logging."""
    specs = SOURCES if tables is None else tuple(SOURCES_BY_TABLE[t] for t in tables)
    return [ingest_source(store, spec, seasons, config=config) for spec in specs]
