"""
player_ingest.py — Sleeper → `players` (+ raw trending).

Sleeper is the canonical player universe (D1): free, public, no auth.
Pulls the full NFL player map and (optionally) trending adds/drops.
Idempotent upsert on `sleeper_id`; safe to re-run.

Usage:
    python player_ingest.py                 # full player universe
    python player_ingest.py --trending      # also pull trending adds/drops
    python player_ingest.py --limit 50      # smoke test
"""
from __future__ import annotations

import argparse

import httpx

from common import console, retry_api, upsert

SLEEPER_BASE = "https://api.sleeper.app/v1"
FANTASY_POSITIONS = {"QB", "RB", "WR", "TE", "K", "DEF"}


@retry_api
def _get(url: str) -> dict | list:
    with httpx.Client(timeout=30) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.json()


def fetch_players() -> dict:
    """Full Sleeper player map: { sleeper_id: {player fields...} }."""
    console.print("[cyan]→ fetching Sleeper player universe…[/cyan]")
    return _get(f"{SLEEPER_BASE}/players/nfl")  # type: ignore[return-value]


def normalize(sleeper_id: str, p: dict) -> dict | None:
    """Map a Sleeper player record → our `players` row. Skip non-fantasy."""
    pos = p.get("position")
    if pos not in FANTASY_POSITIONS:
        return None
    full = p.get("full_name") or " ".join(
        x for x in [p.get("first_name"), p.get("last_name")] if x
    )
    if not full:
        return None
    return {
        "sleeper_id": sleeper_id,
        "espn_id": str(p["espn_id"]) if p.get("espn_id") else None,
        # Sleeper carries its own id crosswalk — gsis_id is the nflverse join key.
        # (Sleeper occasionally pads ids with whitespace → strip for clean joins.)
        "gsis_id": (p.get("gsis_id") or "").strip() or None,
        "yahoo_id": str(p["yahoo_id"]) if p.get("yahoo_id") else None,
        "full_name": full,
        "position": pos,
        "nfl_team": p.get("team"),
        "age": p.get("age"),
        "years_exp": p.get("years_exp"),
        "status": p.get("status"),
        "injury_status": p.get("injury_status"),
        "search_name": full.lower(),
        "metadata": {
            "fantasy_positions": p.get("fantasy_positions"),
            "depth_chart_order": p.get("depth_chart_order"),
            "number": p.get("number"),
        },
    }


@retry_api
def fetch_trending(kind: str, lookback_hours: int = 24, limit: int = 50) -> list[dict]:
    url = f"{SLEEPER_BASE}/players/nfl/trending/{kind}?lookback_hours={lookback_hours}&limit={limit}"
    return _get(url)  # type: ignore[return-value]


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest Sleeper player universe.")
    ap.add_argument("--trending", action="store_true", help="also pull trending adds/drops")
    ap.add_argument("--limit", type=int, default=None, help="cap players (smoke test)")
    args = ap.parse_args()

    raw = fetch_players()
    rows = []
    for sid, p in raw.items():
        row = normalize(sid, p)
        if row:
            rows.append(row)
        if args.limit and len(rows) >= args.limit:
            break
    console.print(f"[cyan]normalized {len(rows)} fantasy-relevant players[/cyan]")
    upsert("players", rows, on_conflict="sleeper_id")

    if args.trending:
        for kind in ("add", "drop"):
            t = fetch_trending(kind)
            console.print(f"[cyan]trending {kind}: {len(t)} players[/cyan]")
            # NOTE: maps sleeper_id → count; joined to players downstream by trending.py (P4).
            console.print_json(data=t[:5])


if __name__ == "__main__":
    main()
