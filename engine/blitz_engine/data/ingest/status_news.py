"""Point-in-time NFL status/news ingest.

Fetchers return canonical rows and remain injectable so every persistence guarantee is
testable without a network. The write boundary is per table: fetch, validate, resolve
identities, then atomically append. A failed fetch or schema check never touches that table.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "status_injury_reports": (
        "season", "week", "team", "gsis_id", "source_player_id", "player_name",
        "report_date", "practice_status", "game_status", "injury", "source_url",
        "as_of_utc", "as_of_is_fetch_time", "resolution_failed", "source_record_id",
    ),
    "status_inactives": (
        "season", "week", "game_id", "team", "gsis_id", "source_player_id",
        "player_name", "inactive", "source_url", "as_of_utc", "as_of_is_fetch_time",
        "resolution_failed", "source_record_id",
    ),
    "status_roster_events": (
        "season", "team", "gsis_id", "source_player_id", "player_name", "event_type",
        "roster_status", "depth_position", "depth_rank", "effective_date", "source_url",
        "as_of_utc", "as_of_is_fetch_time", "resolution_failed", "source_record_id",
    ),
    "status_news": (
        "season", "gsis_id", "source_player_id", "player_name", "raw_text", "source_name",
        "source_url", "as_of_utc", "as_of_is_fetch_time", "resolution_failed",
        "source_record_id",
    ),
}

ID_ALIASES = ("gsis_id", "pfr_id", "espn_id", "sleeper_id", "yahoo_id", "mfl_id")
Fetcher = Callable[[datetime, datetime], pd.DataFrame]


class FeedError(RuntimeError):
    """A source failed or violated its pinned contract."""


@dataclass(frozen=True)
class Feed:
    table: str
    source: str
    fetch: Fetcher


@dataclass(frozen=True)
class FeedResult:
    table: str
    rows_fetched: int
    rows_appended: int
    rows_resolved: int
    rows_unresolved: int

    @property
    def resolution_rate(self) -> float:
        total = self.rows_resolved + self.rows_unresolved
        return self.rows_resolved / total if total else 0.0


def _utc(value: Any) -> str:
    parsed = pd.to_datetime(value, utc=True, errors="raise")
    if pd.isna(parsed):
        raise FeedError("as_of_utc must never be null")
    return parsed.isoformat()


def load_player_id_map(path: str | Path) -> dict[tuple[str, str], str]:
    """Load the sanctioned ``player_ids`` crosswalk, including direct GSIS lookup."""
    path = Path(path).expanduser()
    if not path.exists():
        raise FeedError(f"player_ids crosswalk not found: {path}")
    frame = pq.read_table(path).to_pandas()
    if "gsis_id" not in frame or not any(col in frame for col in ID_ALIASES[1:]):
        raise FeedError("player_ids schema drift: gsis_id/crosswalk columns missing")
    result: dict[tuple[str, str], str] = {}
    for row in frame.to_dict("records"):
        gsis = row.get("gsis_id")
        if pd.isna(gsis) or not str(gsis).strip():
            continue
        for column in ID_ALIASES:
            value = row.get(column)
            if value is not None and not pd.isna(value) and str(value).strip():
                result[(column, str(value))] = str(gsis)
    return result


def _resolve(row: dict[str, Any], id_map: Mapping[tuple[str, str], str]) -> None:
    gsis = row.get("gsis_id")
    if gsis is not None and not pd.isna(gsis) and str(gsis).strip():
        row["gsis_id"] = str(gsis)
        row["resolution_failed"] = None
        return
    source_id = row.get("source_player_id")
    source_id_type = row.pop("source_player_id_type", None)
    resolved = (
        id_map.get((str(source_id_type), str(source_id)))
        if source_id_type and source_id
        else None
    )
    row["gsis_id"] = resolved
    row["resolution_failed"] = None if resolved else (
        "source_player_id_missing" if not source_id else f"unmapped_{source_id_type or 'id'}"
    )


def _fingerprint(table: str, row: Mapping[str, Any]) -> str:
    meaningful = {
        key: (None if pd.isna(value) else value)
        for key, value in row.items()
        if key not in {"as_of_utc", "as_of_is_fetch_time", "resolution_failed"}
    }
    payload = json.dumps([table, meaningful], sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def normalize(
    feed: Feed,
    frame: pd.DataFrame,
    *,
    fetched_at: datetime,
    id_map: Mapping[tuple[str, str], str],
) -> pa.Table:
    """Validate a canonical source frame, resolve IDs, and apply PIT metadata."""
    expected = TABLE_COLUMNS.get(feed.table)
    if expected is None:
        raise FeedError(f"unknown table: {feed.table}")
    required = set(expected) - {
        "gsis_id", "as_of_utc", "as_of_is_fetch_time", "resolution_failed", "source_record_id",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise FeedError(f"{feed.source} schema drift for {feed.table}: missing {missing}")

    rows: list[dict[str, Any]] = []
    for original in frame.to_dict("records"):
        row = dict(original)
        supplied_as_of = row.get("as_of_utc")
        row["as_of_utc"] = _utc(supplied_as_of if supplied_as_of is not None else fetched_at)
        row["as_of_is_fetch_time"] = supplied_as_of is None
        _resolve(row, id_map)
        row["source_record_id"] = str(row.get("source_record_id") or _fingerprint(feed.table, row))
        rows.append({column: row.get(column) for column in expected})
    if not rows:
        return pa.Table.from_pylist([], schema=pa.schema([(c, pa.string()) for c in expected]))
    out = pd.DataFrame(rows, columns=expected)
    if out["as_of_utc"].isna().any():
        raise FeedError(f"{feed.table}: as_of_utc must never be null")
    out = out.drop_duplicates(subset=["source_record_id"], keep="first")
    return pa.Table.from_pandas(out, preserve_index=False)


def append_observations(root: str | Path, table: str, incoming: pa.Table) -> tuple[Path, int]:
    """Append unseen source observations, preserving the first observation byte-for-byte."""
    root = Path(root).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    dest = root / f"{table}.parquet"
    if incoming.num_rows == 0:
        return dest, 0
    tmp = dest.with_suffix(".parquet.tmp")
    con = duckdb.connect()
    try:
        con.register("incoming", incoming)
        if dest.exists():
            before = pq.read_metadata(dest).num_rows
            escaped = str(dest).replace("'", "''")
            escaped_tmp = str(tmp).replace("'", "''")
            con.execute(
                f"""COPY (
                    SELECT * FROM read_parquet('{escaped}')
                    UNION ALL BY NAME
                    SELECT i.* FROM incoming i
                    WHERE NOT EXISTS (
                        SELECT 1 FROM read_parquet('{escaped}') e
                        WHERE e.source_record_id = i.source_record_id
                    )
                ) TO '{escaped_tmp}' (FORMAT PARQUET)"""
            )
            tmp.replace(dest)
            return dest, pq.read_metadata(dest).num_rows - before
        pq.write_table(incoming, tmp)
        tmp.replace(dest)
        return dest, incoming.num_rows
    finally:
        con.close()
        if tmp.exists():
            tmp.unlink()


def refresh(
    root: str | Path,
    feeds: Sequence[Feed],
    start: datetime,
    end: datetime,
    *,
    fetched_at: datetime | None = None,
) -> list[FeedResult]:
    """Run an explicit UTC window. Fetch/validation failures write nothing for that table."""
    if start.tzinfo is None or end.tzinfo is None or start >= end:
        raise ValueError("start/end must be timezone-aware and start must precede end")
    root = Path(root).expanduser()
    ids = load_player_id_map(root / "player_ids.parquet")
    now = fetched_at or datetime.now(UTC)
    results: list[FeedResult] = []
    for feed in feeds:
        try:
            raw = feed.fetch(start, end)
            if not isinstance(raw, pd.DataFrame):
                raise FeedError(f"{feed.source} returned {type(raw).__name__}, expected DataFrame")
            normalized = normalize(feed, raw, fetched_at=now, id_map=ids)
        except Exception as exc:
            if isinstance(exc, FeedError):
                raise
            raise FeedError(f"{feed.source} fetch failed: {type(exc).__name__}: {exc}") from exc
        _, appended = append_observations(root, feed.table, normalized)
        resolved = sum(value is not None for value in normalized.column("gsis_id").to_pylist())
        results.append(FeedResult(feed.table, len(raw), appended, resolved, len(raw) - resolved))
    return results


# -- public source adapters ---------------------------------------------------
NFLVERSE_INJURIES = (
    "https://github.com/nflverse/nflverse-data/releases/download/injuries/"
    "injuries_{season}.parquet"
)
NFLVERSE_WEEKLY_ROSTERS = (
    "https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/"
    "roster_weekly_{season}.parquet"
)
NFLVERSE_DEPTH_CHARTS = (
    "https://github.com/nflverse/nflverse-data/releases/download/depth_charts/"
    "depth_charts_{season}.parquet"
)
ESPN_NEWS = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/news"


def _window(frame: pd.DataFrame, column: str, start: datetime, end: datetime) -> pd.DataFrame:
    if column not in frame:
        return frame
    values = pd.to_datetime(frame[column], utc=True, errors="coerce")
    return frame[(values >= start) & (values < end)].copy()


def nflverse_injuries(season: int) -> Fetcher:
    def fetch(start: datetime, end: datetime) -> pd.DataFrame:
        raw = pd.read_parquet(NFLVERSE_INJURIES.format(season=season))
        required = {"season", "week", "team", "gsis_id", "full_name", "report_status"}
        if missing := sorted(required - set(raw.columns)):
            raise FeedError(f"nflverse injuries schema drift: missing {missing}")
        date_col = "date_modified" if "date_modified" in raw else "report_date"
        raw = _window(raw, date_col, start, end)
        return pd.DataFrame({
            "season": raw["season"], "week": raw["week"], "team": raw["team"],
            "gsis_id": raw["gsis_id"], "source_player_id": raw["gsis_id"],
            "player_name": raw["full_name"],
            "report_date": raw.get("report_date", raw.get(date_col)),
            "practice_status": raw.get("practice_status"), "game_status": raw["report_status"],
            "injury": raw.get("report_primary_injury", raw.get("primary_injury")),
            "source_url": NFLVERSE_INJURIES.format(season=season),
            "as_of_utc": raw.get("date_modified"),
        })
    return fetch


def nflverse_roster_events(season: int) -> Fetcher:
    """Weekly roster states. These capture IR/PUP/reserve moves, not signing prose."""
    def fetch(start: datetime, end: datetime) -> pd.DataFrame:
        url = NFLVERSE_WEEKLY_ROSTERS.format(season=season)
        raw = pd.read_parquet(url)
        required = {"season", "team", "gsis_id", "full_name", "status"}
        if missing := sorted(required - set(raw.columns)):
            raise FeedError(f"nflverse weekly_rosters schema drift: missing {missing}")
        date_col = next((c for c in ("date_modified", "gameday", "report_date") if c in raw), None)
        if date_col:
            raw = _window(raw, date_col, start, end)
        return pd.DataFrame({
            "season": raw["season"], "team": raw["team"], "gsis_id": raw["gsis_id"],
            "source_player_id": raw["gsis_id"], "player_name": raw["full_name"],
            "event_type": "weekly_roster_snapshot", "roster_status": raw["status"],
            "depth_position": raw.get("depth_chart_position"), "depth_rank": None,
            "effective_date": raw.get(date_col) if date_col else None, "source_url": url,
            "as_of_utc": raw.get("date_modified"),
        })
    return fetch


def nflverse_depth_events(season: int) -> Fetcher:
    def fetch(start: datetime, end: datetime) -> pd.DataFrame:
        url = NFLVERSE_DEPTH_CHARTS.format(season=season)
        raw = pd.read_parquet(url)
        if "gsis_id" not in raw or not ({"team", "club_code"} & set(raw.columns)):
            raise FeedError("nflverse depth_charts schema drift: identity/team missing")
        date_col = next((c for c in ("dt", "date_modified") if c in raw), None)
        if date_col:
            raw = _window(raw, date_col, start, end)
        return pd.DataFrame({
            "season": raw.get("season", season),
            "team": raw.get("team", raw.get("club_code")), "gsis_id": raw["gsis_id"],
            "source_player_id": raw["gsis_id"],
            "player_name": raw.get("full_name", raw.get("player_name")),
            "event_type": "depth_chart_snapshot", "roster_status": None,
            "depth_position": raw.get("depth_position", raw.get("position")),
            "depth_rank": raw.get("pos_rank", raw.get("depth_team")),
            "effective_date": raw.get(date_col) if date_col else None, "source_url": url,
            "as_of_utc": raw.get(date_col) if date_col else None,
        })
    return fetch


def espn_news(season: int) -> Fetcher:
    """Public ESPN news metadata; raw_text is returned verbatim, with no NLP."""
    def fetch(start: datetime, end: datetime) -> pd.DataFrame:
        request = urllib.request.Request(ESPN_NEWS, headers={"User-Agent": "BlitzBoard/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 — fixed HTTPS URL
            payload = json.load(response)
        if not isinstance(payload.get("articles"), list):
            raise FeedError("ESPN news schema drift: articles list missing")
        rows = []
        for article in payload["articles"]:
            published = article.get("published") or article.get("lastModified")
            published_at = (
                pd.to_datetime(published, utc=True).to_pydatetime() if published else None
            )
            if published_at and not (start <= published_at < end):
                continue
            raw_text = article.get("description") or article.get("headline")
            link = article.get("links", {}).get("web", {}).get("href")
            if not raw_text or not link:
                raise FeedError("ESPN news schema drift: article text/link missing")
            rows.append({
                "season": season, "source_player_id": None, "player_name": None,
                "raw_text": raw_text, "source_name": "ESPN", "source_url": link,
                "as_of_utc": published, "source_record_id": article.get("id"),
            })
        return pd.DataFrame(
            rows,
            columns=(
                "season", "source_player_id", "player_name", "raw_text", "source_name",
                "source_url", "as_of_utc", "source_record_id",
            ),
        )
    return fetch


def default_feeds(season: int) -> tuple[Feed, ...]:
    """Covered public feeds. Official 90-minute inactives intentionally require an adapter."""
    return (
        Feed("status_injury_reports", "nflverse/injuries", nflverse_injuries(season)),
        Feed("status_roster_events", "nflverse/weekly_rosters", nflverse_roster_events(season)),
        Feed("status_roster_events", "nflverse/depth_charts", nflverse_depth_events(season)),
        Feed("status_news", "ESPN/news", espn_news(season)),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Standalone refresh verb; deliberately not registered in ``blitz_engine.cli``."""
    import argparse

    parser = argparse.ArgumentParser(prog="python -m blitz_engine.data.ingest.status_news")
    parser.add_argument("--start", required=True, help="Inclusive ISO-8601 UTC timestamp")
    parser.add_argument("--end", required=True, help="Exclusive ISO-8601 UTC timestamp")
    parser.add_argument("--season", required=True, type=int)
    parser.add_argument("--data-root", default="~/.blitz_engine")
    args = parser.parse_args(argv)
    start = pd.to_datetime(args.start, utc=True).to_pydatetime()
    end = pd.to_datetime(args.end, utc=True).to_pydatetime()
    try:
        results = refresh(args.data_root, default_feeds(args.season), start, end)
    except Exception as exc:  # noqa: BLE001 — operational boundary reports and exits non-zero
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
        return 1
    for result in results:
        print(
            json.dumps({"ok": True, **result.__dict__, "resolution_rate": result.resolution_rate})
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
