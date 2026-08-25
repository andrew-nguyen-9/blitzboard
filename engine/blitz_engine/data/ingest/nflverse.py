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
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb
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
    skipped: list[int] = field(default_factory=list)
    ingested_at: str = field(default_factory=utc_now_iso)


# -- ingest --------------------------------------------------------------------
def latest_complete_season(today: datetime | None = None) -> int:
    """The most recent NFL season that has finished (season Y runs Sep Y → Feb Y+1)."""
    now = today or datetime.now(UTC)
    return now.year - 1 if now.month >= 3 else now.year - 2


def season_present(root: str | Path, table: str, season: int) -> bool:
    """True if `<root>/<table>.parquet` already holds rows for `season`.

    The resumability probe: a season that landed is never re-fetched (the network step is
    the expensive one). Reads only the Parquet's `season` column with a pushdown filter;
    a table without a `season` column (or no file yet) is simply "not present".
    """
    dest = Path(root).expanduser() / f"{table}.parquet"
    if not dest.exists():
        return False
    con = duckdb.connect()
    try:
        path = str(dest).replace("'", "''")
        cols = con.execute(f"SELECT * FROM read_parquet('{path}') LIMIT 0").df().columns
        if "season" not in cols:
            return False
        row = con.execute(
            f"SELECT 1 FROM read_parquet('{path}') WHERE season = ? LIMIT 1", [season]
        ).fetchone()
        return row is not None
    finally:
        con.close()


def ingest_source(
    store: ParquetStore,
    spec: SourceSpec,
    seasons: Sequence[int],
    *,
    config: EngineConfig | None = None,
    force: bool = False,
) -> IngestResult:
    """Fetch → float32 → stamp provenance → idempotent upsert for one source.

    Older seasons lacking this feed are degraded (flagged in the result), not fetched.
    Seasons already in the table are *skipped* (resumable: re-running a completed season
    is a no-op that costs one Parquet stat probe, not a re-download) unless `force`.
    If nothing is left to fetch, an empty result is returned."""
    cfg = config or store.config or load_config()
    planned, degraded = plan_seasons(spec, seasons)
    if force:
        to_fetch, skipped = planned, []
    else:
        skipped = [s for s in planned if season_present(store.root, spec.table, s)]
        to_fetch = [s for s in planned if s not in set(skipped)]
    if not to_fetch:
        return IngestResult(
            spec.table, spec.source, rows=0, seasons=[], degraded=degraded, skipped=skipped
        )

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
        skipped=skipped,
        ingested_at=at,
    )


def ingest_all(
    store: ParquetStore,
    seasons: Sequence[int],
    *,
    tables: Sequence[str] | None = None,
    config: EngineConfig | None = None,
    force: bool = False,
) -> list[IngestResult]:
    """Ingest every source (or the named subset) for `seasons`. Idempotent end-to-end;
    safe to re-run. Returns one `IngestResult` per source for run provenance/logging."""
    specs = SOURCES if tables is None else tuple(SOURCES_BY_TABLE[t] for t in tables)
    return [ingest_source(store, spec, seasons, config=config, force=force) for spec in specs]


def ingest_season(
    store: ParquetStore,
    season: int,
    *,
    tables: Sequence[str] | None = None,
    config: EngineConfig | None = None,
    force: bool = False,
) -> list[IngestResult]:
    """One season, every source — the per-invocation entry point for the 2014+ backfill.

    The multi-hour full backfill is driven ONE season per process (see this module's
    `__main__`), so a failure/interrupt costs one season, and re-running it is a no-op.
    """
    return ingest_all(store, [season], tables=tables, config=config, force=force)


# -- per-season operational entry point ---------------------------------------
def main(argv: Sequence[str] | None = None) -> int:
    """`python -m blitz_engine.data.ingest.nflverse --season 2014` — ingest one season.

    Prints one JSON line per source (machine-readable run log) and returns a nonzero exit
    code if any source failed. `ponytail:` argparse only, no CLI framework.
    """
    import argparse
    import json

    from blitz_engine.store import ParquetStore as _Store

    ap = argparse.ArgumentParser(prog="blitz-ingest", description="nflverse ingest, one season.")
    ap.add_argument("--season", type=int, required=True)
    ap.add_argument("--data-root", default=None)
    ap.add_argument("--tables", default=None, help="Comma-separated source tables (default: all).")
    ap.add_argument("--force", action="store_true", help="Re-fetch even if the season is present.")
    args = ap.parse_args(argv)

    cfg = load_config(**({"data_root": args.data_root} if args.data_root else {}))
    tables = args.tables.split(",") if args.tables else None
    failures = 0
    with _Store.open(cfg.data_root, cfg) as store:
        specs = SOURCES if tables is None else tuple(SOURCES_BY_TABLE[t] for t in tables)
        for spec in specs:
            try:
                res = ingest_source(store, spec, [args.season], config=cfg, force=args.force)
                print(json.dumps({"season": args.season, "ok": True, **res.__dict__}), flush=True)
            except Exception as exc:  # noqa: BLE001 — one bad feed must not kill the season
                failures += 1
                print(
                    json.dumps(
                        {"season": args.season, "ok": False, "table": spec.table,
                         "error": f"{type(exc).__name__}: {exc}"}
                    ),
                    flush=True,
                )
    return 1 if failures else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
