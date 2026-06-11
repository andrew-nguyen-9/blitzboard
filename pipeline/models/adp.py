"""
Shared Fantasy Football Calculator (FFC) ADP fetch — free, no key (D6).

Cached per (teams, fmt, year) so multiple projectors share one network call.
Network-failure-safe: returns {} on any error so projectors degrade gracefully.

fmt options: 'standard' | 'ppr' | 'half-ppr' | '2qb' (superflex).
"""
from __future__ import annotations

from functools import lru_cache


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
