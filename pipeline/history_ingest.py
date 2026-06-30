"""
history_ingest.py — nflverse / nfl_data_py → `player_stats_history`.

Pulls seasonal (and optionally weekly) stats to feed the regression projector
(D6). Joined to `players` by name (nflverse `player_name`) — refined to GSIS/ESPN
id mapping in P1. Idempotent upsert on (player_id, season, week); safe to re-run.

Usage:
    python history_ingest.py --seasons 2022 2023 2024
    python history_ingest.py --seasons 2024 --weekly
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from common import console, get_supabase, upsert, fetch_all

# Default marker recording which seasons were ingested, so daily CI can skip the
# expensive nflverse download/upsert when nothing changed (past seasons are
# immutable). Lives under a cached dir so it survives across CI runs.
DEFAULT_MARKER = Path(".nflverse_cache/marker.json")


def _marker_covers(marker: Path, seasons: list[int], weekly: bool) -> bool:
    """True if a prior run already ingested every requested season at this
    granularity — i.e. there is nothing new to do."""
    try:
        m = json.loads(marker.read_text())
    except (OSError, ValueError):
        return False
    return m.get("weekly") == weekly and set(seasons) <= set(m.get("seasons", []))


def _write_marker(marker: Path, seasons: list[int], weekly: bool) -> None:
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({
        "seasons": sorted(set(seasons)),
        "weekly": weekly,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }))

# Columns we care about from nfl_data_py seasonal/weekly frames.
STAT_COLS = [
    "games",
    "completions", "attempts", "passing_yards", "passing_tds", "interceptions",
    "passing_2pt_conversions",
    "carries", "rushing_yards", "rushing_tds", "rushing_2pt_conversions",
    "receptions", "targets", "receiving_yards", "receiving_tds",
    "receiving_2pt_conversions",
    "fumbles_lost", "target_share", "air_yards_share",
]


def _id_maps() -> tuple[dict[str, str], dict[str, str]]:
    """Return (gsis_id → players.id, sleeper_id → players.id)."""
    if get_supabase() is None:
        return {}, {}
    rows = fetch_all("players", "id,gsis_id,sleeper_id")
    by_gsis = {r["gsis_id"].strip(): r["id"] for r in rows if r.get("gsis_id")}
    by_sleeper = {str(r["sleeper_id"]): r["id"] for r in rows if r.get("sleeper_id")}
    return by_gsis, by_sleeper


def _gsis_to_sleeper() -> dict[str, str]:
    """nflverse crosswalk: GSIS id → Sleeper id. Sleeper's own gsis coverage is
    spotty, but we have sleeper_id for every player — so GSIS→Sleeper→our id is
    the reliable bridge."""
    import nfl_data_py as nfl
    import pandas as pd

    try:
        ids = nfl.import_ids()
    except Exception as e:
        console.print(f"[yellow]⚠ import_ids() failed ({e}); GSIS-only matching[/yellow]")
        return {}
    out: dict[str, str] = {}
    for _, r in ids.iterrows():
        g, s = r.get("gsis_id"), r.get("sleeper_id")
        if pd.notna(g) and pd.notna(s):
            sid = str(int(s)) if isinstance(s, float) else str(s).strip()
            out[str(g).strip()] = sid
    return out


def load_frames(seasons: list[int], weekly: bool):
    import nfl_data_py as nfl

    if weekly:
        console.print(f"[cyan]→ nflverse weekly stats {seasons}…[/cyan]")
        return nfl.import_weekly_data(seasons)
    console.print(f"[cyan]→ nflverse seasonal stats {seasons}…[/cyan]")
    return nfl.import_seasonal_data(seasons)


def build_rows(df, weekly: bool, by_gsis: dict[str, str], by_sleeper: dict[str, str],
               gsis_to_sleeper: dict[str, str]) -> list[dict]:
    import pandas as pd  # noqa: F401  (nfl_data_py pulls it in)

    # seasonal/weekly frames key player by gsis 'player_id'. Match directly on our
    # gsis ids, else bridge GSIS→Sleeper→our id via the nflverse crosswalk.
    rows: list[dict] = []
    unmatched = 0
    for _, r in df.iterrows():
        gsis = str(r.get("player_id", "")).strip()
        pid = by_gsis.get(gsis)
        if not pid:
            sid = gsis_to_sleeper.get(gsis)
            if sid:
                pid = by_sleeper.get(sid)
        if not pid:
            unmatched += 1
            continue
        stats = {c: (None if c not in df.columns or _na(r[c]) else float(r[c])) for c in STAT_COLS}
        rows.append({
            "player_id": pid,
            "season": int(r["season"]),
            "week": int(r["week"]) if weekly else None,
            "stats": stats,
            "fantasy_pts": _na_to_none(r.get("fantasy_points")),
        })
    if unmatched:
        console.print(f"[yellow]⚠ {unmatched} stat rows unmatched to any player (skipped)[/yellow]")
    return rows


def _na(v) -> bool:
    try:
        import math
        return v is None or (isinstance(v, float) and math.isnan(v))
    except Exception:
        return v is None


def _na_to_none(v):
    return None if _na(v) else float(v)


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest nflverse historical stats.")
    ap.add_argument("--seasons", type=int, nargs="+", required=True)
    ap.add_argument("--weekly", action="store_true", help="weekly granularity (default: seasonal)")
    ap.add_argument("--marker", type=Path, default=DEFAULT_MARKER,
                    help="path to the ingested-seasons marker (default: %(default)s)")
    ap.add_argument("--skip-if-cached", action="store_true",
                    help="exit early (no download/write) if the marker already covers these seasons")
    args = ap.parse_args()

    if args.skip_if_cached and _marker_covers(args.marker, args.seasons, args.weekly):
        console.print(f"[green]✓ history cached for {args.seasons} "
                      f"({'weekly' if args.weekly else 'seasonal'}); skipping.[/green]")
        return

    by_gsis, by_sleeper = _id_maps()
    if not by_gsis and not by_sleeper:
        console.print("[yellow]⚠ no players in DB yet — run player_ingest.py first.[/yellow]")
    gsis_to_sleeper = _gsis_to_sleeper()
    console.print(f"[cyan]crosswalk: {len(gsis_to_sleeper)} GSIS→Sleeper mappings[/cyan]")

    df = load_frames(args.seasons, args.weekly)
    rows = build_rows(df, args.weekly, by_gsis, by_sleeper, gsis_to_sleeper)
    console.print(f"[cyan]matched {len(rows)} stat rows to players[/cyan]")

    # Delete-before-insert for the season scope: the (player_id, season, week) unique
    # key can't dedupe season rows because week is NULL (Postgres NULL != NULL), so
    # plain upsert would accumulate duplicates on every re-run.
    sb = get_supabase()
    if sb is not None:
        d = sb.table("player_stats_history").delete().in_("season", args.seasons)
        d = d.not_.is_("week", "null") if args.weekly else d.is_("week", "null")
        d.execute()

    upsert("player_stats_history", rows, on_conflict="player_id,season,week")
    _write_marker(args.marker, args.seasons, args.weekly)


if __name__ == "__main__":
    main()
