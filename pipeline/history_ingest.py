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

from common import console, get_supabase, upsert, fetch_all, retry_api

# Cached dir surviving across CI runs (gitignored). Holds the ingested-seasons
# marker and the vendored snap/routes parquet used as the reliability fallback
# when the live nflverse pull is unreachable (see load_snap_routes).
CACHE_DIR = Path(".nflverse_cache")
# Default marker recording which seasons were ingested, so daily CI can skip the
# expensive nflverse download/upsert when nothing changed (past seasons are
# immutable).
DEFAULT_MARKER = CACHE_DIR / "marker.json"
# Vendored parquet fallback carrying offensive snap % + routes-run (E2).
SNAP_ROUTES_PARQUET = CACHE_DIR / "snap_routes.parquet"


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
    # E2 opportunity signals — shared column contract (E1 reads these to compute
    # routes_trend). Overlaid from load_snap_routes(), not the seasonal/weekly frame.
    "offense_snap_pct",  # offensive snap share, 0-1
    "routes_run",        # routes run, count (proxy: offensive snaps, see load_snap_routes)
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


# --- E2: offensive snap % + routes-run -------------------------------------
# Free nflverse exposes offensive snap share (import_snap_counts.offense_pct) but
# NOT a per-player routes-run count (that lives behind paid PFF). Offensive snaps
# (import_snap_counts.offense_snaps) is the closest real opportunity proxy and is
# what we store under `routes_run` — a consistent per-player weekly count that
# E1's routes_trend differences. snap_counts keys players by pfr_player_id, so we
# bridge pfr_id → GSIS via the nflverse id crosswalk to match build_rows' key.
SNAP_ROUTES_COLS = ["player_id", "season", "week", "offense_snap_pct", "routes_run"]


@retry_api
def _live_snap_routes(seasons: list[int]):
    """Fetch per-game offensive snap % + routes-run from nflverse, keyed by GSIS
    id. Retried on transient failure; raises if the live source is unreachable so
    load_snap_routes can fall back to the vendored parquet."""
    import nfl_data_py as nfl
    import pandas as pd

    console.print(f"[cyan]→ nflverse snap counts {seasons}…[/cyan]")
    snaps = nfl.import_snap_counts(seasons)
    ids = nfl.import_ids()[["pfr_id", "gsis_id"]].dropna()
    pfr2gsis = dict(zip(ids["pfr_id"].astype(str).str.strip(),
                        ids["gsis_id"].astype(str).str.strip()))

    off = snaps[(snaps["offense_pct"].notna()) & (snaps["offense_snaps"] > 0)].copy()
    off["player_id"] = off["pfr_player_id"].astype(str).str.strip().map(pfr2gsis)
    off = off.dropna(subset=["player_id"])
    out = pd.DataFrame({
        "player_id": off["player_id"].values,
        "season": off["season"].astype(int).values,
        "week": off["week"].astype(int).values,
        "offense_snap_pct": off["offense_pct"].astype(float).values,
        "routes_run": off["offense_snaps"].astype(float).values,
    })
    return out[SNAP_ROUTES_COLS]


def load_snap_routes(seasons: list[int], parquet: Path = SNAP_ROUTES_PARQUET):
    """Per-game snap %/routes frame with a reliability guard: try the live
    nflverse pull (retried); if it is unreachable, read the vendored parquet.
    Returns an empty frame only when neither source is available."""
    import pandas as pd

    try:
        frame = _live_snap_routes(seasons)
        _vendor_snap_routes(frame, parquet)  # refresh the offline fallback
        return frame
    except Exception as e:  # noqa: BLE001 — any live failure → offline fallback
        if parquet.exists():
            console.print(f"[yellow]⚠ live snap/routes pull failed ({e}); "
                          f"reading vendored {parquet}[/yellow]")
            frame = pd.read_parquet(parquet)
            return frame[frame["season"].isin(seasons)].reset_index(drop=True)
        console.print(f"[yellow]⚠ snap/routes unavailable ({e}) and no vendored "
                      f"parquet at {parquet}; skipping opportunity signals[/yellow]")
        return pd.DataFrame(columns=SNAP_ROUTES_COLS)


def _vendor_snap_routes(frame, parquet: Path) -> None:
    """Persist a fresh snap/routes frame as the offline fallback (best-effort)."""
    try:
        parquet.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(parquet, index=False)
    except Exception as e:  # noqa: BLE001 — vendoring is best-effort, never fatal
        console.print(f"[yellow]⚠ could not vendor snap/routes parquet ({e})[/yellow]")


def snap_routes_index(frame, weekly: bool) -> dict[tuple, tuple[float | None, float | None]]:
    """Index a snap/routes frame to (player_id, season, week|None) →
    (offense_snap_pct, routes_run). Seasonal ingest aggregates across weeks:
    snap % averaged, routes summed (season-long opportunity volume)."""
    if frame is None or len(frame) == 0:
        return {}
    if weekly:
        agg = frame.copy()
        agg["week"] = agg["week"].astype(int)
        keys = list(zip(agg["player_id"], agg["season"].astype(int), agg["week"]))
    else:
        g = frame.groupby(["player_id", "season"], as_index=False).agg(
            offense_snap_pct=("offense_snap_pct", "mean"),
            routes_run=("routes_run", "sum"))
        agg = g
        keys = [(pid, int(s), None) for pid, s in zip(g["player_id"], g["season"])]
    return {
        k: (_na_to_none(sp), _na_to_none(rr))
        for k, sp, rr in zip(keys, agg["offense_snap_pct"], agg["routes_run"])
    }


def build_rows(df, weekly: bool, by_gsis: dict[str, str], by_sleeper: dict[str, str],
               gsis_to_sleeper: dict[str, str],
               snap_routes: dict[tuple, tuple] | None = None) -> list[dict]:
    import pandas as pd  # noqa: F401  (nfl_data_py pulls it in)

    # seasonal/weekly frames key player by gsis 'player_id'. Match directly on our
    # gsis ids, else bridge GSIS→Sleeper→our id via the nflverse crosswalk.
    snap_routes = snap_routes or {}
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
        # Overlay E2 opportunity signals (keyed by GSIS id, same as snap_routes).
        sr = snap_routes.get((gsis, int(r["season"]), int(r["week"]) if weekly else None))
        if sr is not None:
            stats["offense_snap_pct"], stats["routes_run"] = sr
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
    sr_frame = load_snap_routes(args.seasons)
    snap_routes = snap_routes_index(sr_frame, args.weekly)
    console.print(f"[cyan]snap/routes: {len(snap_routes)} player-periods[/cyan]")
    rows = build_rows(df, args.weekly, by_gsis, by_sleeper, gsis_to_sleeper, snap_routes)
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
