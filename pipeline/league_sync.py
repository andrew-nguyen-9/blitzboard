"""
league_sync.py — ESPN → leagues, rosters, standings (P3).

Pulls my ESPN league (teams, rosters, standings, settings) via the unofficial
`espn-api` lib using cookie auth (espn_s2 + SWID). Read-only enrichment — ESPN is
NEVER the player backbone (D1). Rosters map ESPN player ids → our players.id.

ESPN's API is unofficial and fragile (D4/D7); this script fails loudly but never
corrupts data — upserts are idempotent and keyed on (league_id, espn_team_id).

Usage:
    python league_sync.py                       # uses ESPN_* from .env
    python league_sync.py --league 123456 --season 2025
"""
from __future__ import annotations

import argparse
import os

from common import console, get_supabase, retry_api, upsert, fetch_all


def _espn_player_id_map(sb) -> dict[str, str]:
    """ESPN player id (str) → our players.id."""
    rows = fetch_all("players", "id,espn_id")
    return {str(r["espn_id"]): r["id"] for r in rows if r.get("espn_id")}


@retry_api
def _load_espn_league(league_id: int, season: int, s2: str | None, swid: str | None):
    from espn_api.football import League

    return League(league_id=league_id, year=season, espn_s2=s2, swid=swid)


def _ensure_league_row(sb, league_id: str, season: int, name: str) -> str | None:
    """Find or create the leagues row; return its uuid."""
    existing = (
        sb.table("leagues")
        .select("id")
        .eq("platform", "espn").eq("external_id", str(league_id)).eq("season", season)
        .limit(1).execute().data
    )
    if existing:
        return existing[0]["id"]
    ins = sb.table("leagues").insert({
        "platform": "espn", "external_id": str(league_id), "season": season, "name": name,
    }).execute()
    return ins.data[0]["id"] if ins.data else None


def main() -> None:
    ap = argparse.ArgumentParser(description="Sync an ESPN league.")
    ap.add_argument("--league", default=os.getenv("ESPN_LEAGUE_ID"))
    ap.add_argument("--season", type=int, default=int(os.getenv("ESPN_SEASON", "2025")))
    args = ap.parse_args()

    if not args.league:
        console.print("[red]No league id — set ESPN_LEAGUE_ID in .env or pass --league.[/red]")
        return

    sb = get_supabase()
    if sb is None:
        console.print("[red]Supabase not configured — set pipeline/.env.[/red]")
        return

    s2, swid = os.getenv("ESPN_S2"), os.getenv("ESPN_SWID")
    if not s2 or not swid:
        console.print("[yellow]⚠ ESPN_S2 / ESPN_SWID not set — only works for PUBLIC leagues.[/yellow]")

    try:
        league = _load_espn_league(int(args.league), args.season, s2, swid)
    except Exception as e:  # unofficial API: fail loudly, corrupt nothing
        console.print(f"[red]ESPN load failed (fragile API): {e}[/red]")
        return

    name = getattr(league.settings, "name", f"League {args.league}")
    league_uuid = _ensure_league_row(sb, args.league, args.season, name)
    if not league_uuid:
        console.print("[red]Could not resolve leagues row.[/red]")
        return

    epid = _espn_player_id_map(sb)
    console.print(f"[cyan]{name}: {len(league.teams)} teams[/cyan]")

    rows = []
    unmapped = 0
    for t in league.teams:
        pids = []
        for p in getattr(t, "roster", []) or []:
            our = epid.get(str(getattr(p, "playerId", "")))
            if our:
                pids.append(our)
            else:
                unmapped += 1
        owners = getattr(t, "owners", None) or []
        owner = owners[0].get("displayName") if owners and isinstance(owners[0], dict) else (owners[0] if owners else None)
        rows.append({
            "league_id": league_uuid,
            "espn_team_id": getattr(t, "team_id", None),
            "team_name": getattr(t, "team_name", None),
            "owner": owner,
            "abbrev": getattr(t, "team_abbrev", None),
            "logo_url": getattr(t, "logo_url", None),
            "division": getattr(t, "division_name", None),
            "player_ids": pids,
            "wins": getattr(t, "wins", 0),
            "losses": getattr(t, "losses", 0),
            "ties": getattr(t, "ties", 0),
            "points_for": getattr(t, "points_for", 0),
            "points_against": getattr(t, "points_against", 0),
            "standing": getattr(t, "standing", None),
        })

    upsert("rosters", rows, on_conflict="league_id,espn_team_id")
    if unmapped:
        console.print(f"[yellow]⚠ {unmapped} rostered players unmapped to our players table[/yellow]")
    console.print(f"[green]✓ synced {len(rows)} teams for {name}[/green]")


if __name__ == "__main__":
    main()
