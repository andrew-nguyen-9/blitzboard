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

# ── NFL team source-of-truth (F3) ────────────────────────────────────────────
# The 32 canonical NFL team codes the WHOLE pipeline joins on (Sleeper's modern
# set — matches the REMAP target in value_engine_run.enrich_byes, the FFC-ADP
# defense join in special_teams.py, and the D/ST nfl_team match). `nfl_team` must
# be one of these or NULL; anything else silently mis-attaches a player to the
# wrong (or a non-existent) team, which is the roster bug this fixes.
NFL_TEAMS = frozenset({
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET",
    "GB", "HOU", "IND", "JAX", "KC", "LV", "LAC", "LAR", "MIA", "MIN", "NE",
    "NO", "NYG", "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
})

# Legacy / relocated / variant abbreviations Sleeper (and joined sources) still
# emit → canonical code. Left side is what we might SEE; right side is canonical.
_TEAM_ALIASES = {
    "OAK": "LV",  "LVR": "LV",                 # Raiders (Oakland → Las Vegas)
    "SD": "LAC",  "SDG": "LAC",                # Chargers (San Diego → LA)
    "STL": "LAR", "LA": "LAR", "SL": "LAR",    # Rams (St. Louis / bare "LA")
    "WSH": "WAS", "WFT": "WAS",                # Commanders (WSH / Football Team)
    "JAC": "JAX",                              # Jaguars
    "ARZ": "ARI", "BLT": "BAL", "CLV": "CLE",  # nflverse/PFR-style variants
    "HST": "HOU",
    "GBP": "GB",  "KCC": "KC",  "SFO": "SF",   # padded 3-letter variants
    "TBB": "TB",  "NOR": "NO",  "NWE": "NE",
    "NEP": "NE",  "TAM": "TB",  "GNB": "GB",
    "KAN": "KC",  "SFO49": "SF",
}

# Non-team markers Sleeper uses for players with no active NFL team.
_NON_TEAM = {"", "FA", "NONE", "NULL", "0", "RET", "DEV", "PS", "PRA"}


def normalize_team(raw) -> str | None:
    """Map a raw Sleeper team value → a CANONICAL NFL code (or None).

    Pure & idempotent: ``normalize_team(normalize_team(x)) == normalize_team(x)``.
    Free agents / retired / unrecognized codes → None (never a wrong team)."""
    if raw is None:
        return None
    code = str(raw).strip().upper()
    if not code or code in _NON_TEAM:
        return None
    code = _TEAM_ALIASES.get(code, code)
    return code if code in NFL_TEAMS else None


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
        # canonical team is the source of truth — see normalize_team (F3)
        "nfl_team": normalize_team(p.get("team")),
        "age": p.get("age"),
        "years_exp": p.get("years_exp"),
        "status": p.get("status"),
        "injury_status": p.get("injury_status"),
        "search_name": full.lower(),
        "metadata": {
            "fantasy_positions": p.get("fantasy_positions"),
            "depth_chart_order": p.get("depth_chart_order"),
            "depth_chart_position": p.get("depth_chart_position"),
            # Sleeper's composite consensus rank (lower=better, 999=irrelevant);
            # 98% coverage → orders the deep/bench pool sensibly (#2 more data).
            "search_rank": p.get("search_rank"),
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
