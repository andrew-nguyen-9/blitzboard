"""
Shared Fantasy Football Calculator (FFC) ADP fetch — free, no key (D6).

Cached per (teams, fmt, year) so multiple projectors share one network call.
Network-failure-safe: returns {} on any error so projectors degrade gracefully.

fmt options: 'standard' | 'ppr' | 'half-ppr' | '2qb' (superflex).
"""
from __future__ import annotations

import csv
import math
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

_DRAFT_SHEET_BLOCKS = (1, 11, 21)
_DRAFT_SHEET_POSITIONS = {
    "QUARTERBACK": "QB",
    "RUNNING BACK": "RB",
    "WIDE RECEIVER": "WR",
    "TIGHT END": "TE",
}


def normalize_player_name(name: str) -> str:
    """Stable player-name key: ASCII, punctuation-free, and without suffixes."""
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"[^a-z0-9 ]", "", text)
    text = re.sub(r"\s+(jr|sr|ii|iii|iv|v)$", "", text.strip())
    return re.sub(r"\s+", " ", text)


def load_draft_sheet(path: str | Path) -> dict[str, dict]:
    """Read the visible QB/RB/WR/TE blocks from a private DraftSheet CSV export."""
    positions: dict[int, str] = {}
    players: dict[str, dict] = {}
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.reader(handle):
            for start in _DRAFT_SHEET_BLOCKS:
                cell = row[start].strip() if start < len(row) else ""
                if cell in _DRAFT_SHEET_POSITIONS:
                    positions[start] = _DRAFT_SHEET_POSITIONS[cell]
                    continue
                if start not in positions or start + 6 >= len(row):
                    continue
                name = row[start + 1].strip()
                ecr = row[start + 6].strip().upper()
                try:
                    tier = int(row[start])
                    points = float(row[start + 3])
                    value = float(row[start + 4])
                    position_rank = float(ecr.removeprefix(positions[start]))
                except (TypeError, ValueError):
                    continue
                if (
                    not name or tier < 1 or position_rank < 1
                    or not all(map(math.isfinite, (points, value, position_rank)))
                ):
                    continue
                entry = {
                    "name": name,
                    "position": positions[start],
                    "points": points,
                    "value": value,
                    "tier": tier,
                    "position_rank": position_rank,
                }
                key = normalize_player_name(name)
                if key in players and players[key] != entry:
                    raise ValueError(f"conflicting DraftSheet rows for {name}")
                players[key] = entry
    if not players:
        raise ValueError("DraftSheet contains no usable player rows")
    return players


@lru_cache(maxsize=8)
def fetch_ffc_adp(teams: int = 12, fmt: str = "half-ppr", year: int = 2025) -> dict:
    """Return { lower_name: {name, position, team, adp, ...} } or {} on failure."""
    try:
        import httpx

        url = f"https://fantasyfootballcalculator.com/api/v1/adp/{fmt}?teams={teams}&year={year}"
        with httpx.Client(timeout=15) as c:
            data = c.get(url).json()
        return {p["name"].lower(): p for p in data.get("players", [])}
    except Exception:
        return {}


def positional_order(adp: dict, position: str) -> list[dict]:
    """ADP entries for one position, sorted best→worst."""
    return sorted(
        (e for e in adp.values() if e.get("position") == position),
        key=lambda e: e.get("adp", 999),
    )
