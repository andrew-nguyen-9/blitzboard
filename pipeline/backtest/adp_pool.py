"""Reconstruct the bot-facing draft pool for a historical season from ADP.

Bots draft on a PRE-SEASON signal derived from ADP + positional scarcity — never
hindsight. Evaluation (evaluate.py) scores rosters on REAL actuals, so a good policy
can only win by drafting players who beat their ADP-implied value over the season."""
from __future__ import annotations

import math

# Per-position decay + ceiling/floor spread (half-PPR, superflex priors).
_BASE = {"QB": 300.0, "RB": 230.0, "WR": 220.0, "TE": 160.0, "K": 140.0, "DST": 130.0}
_K = {"QB": 0.045, "RB": 0.070, "WR": 0.060, "TE": 0.080, "K": 0.030, "DST": 0.030}
_CEIL = {"QB": 0.25, "RB": 0.45, "WR": 0.40, "TE": 0.40, "K": 0.20, "DST": 0.25}
_FLOOR = {"QB": 0.20, "RB": 0.35, "WR": 0.30, "TE": 0.30, "K": 0.15, "DST": 0.20}


def _proj(pos: str, pos_rank: int) -> float:
    """Projected season points for the `pos_rank`-th best player at a position."""
    return _BASE.get(pos, 150.0) * math.exp(-_K.get(pos, 0.06) * (pos_rank - 1))


def value_from_adp(players: list[dict], rules) -> list[dict]:
    """Attach a synthetic `value` dict (vor/replacement/boom/bust/adp/rank) to each
    player from its within-position ADP rank. Pure — no I/O."""
    repl_ranks = rules.replacement_ranks()
    by_pos: dict[str, list[dict]] = {}
    for p in players:
        by_pos.setdefault(p["pos"], []).append(p)
    out: list[dict] = []
    for pos, group in by_pos.items():
        group = sorted(group, key=lambda p: p.get("adp") if p.get("adp") is not None else 9999.0)
        repl = _proj(pos, max(1, repl_ranks.get(pos, len(group))))
        for i, p in enumerate(group, start=1):
            proj = _proj(pos, i)
            out.append({**p, "value": {
                "vor": round(proj - repl, 2), "replacement": round(repl, 2),
                "boom": round(proj * (1 + _CEIL.get(pos, 0.35)), 2),
                "bust": round(proj * (1 - _FLOOR.get(pos, 0.30)), 2),
                "adp": p.get("adp"), "rank": 0,
            }})
    out.sort(key=lambda p: p["value"]["adp"] if p["value"]["adp"] is not None else 9999.0)
    for rank, p in enumerate(out, start=1):
        p["value"]["rank"] = rank
    return out


def _ffc_adp(season: int, rules) -> list[dict]:
    """Fantasy Football Calculator superflex ADP for a season (cached JSON)."""
    import json
    import os

    import httpx

    from .cache import _DIR
    os.makedirs(_DIR, exist_ok=True)
    path = os.path.join(_DIR, f"adp_{season}.json")
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
    else:
        # FFC's "2qb" pool is the superflex-equivalent (QBs go early); there is no
        # "superflex" format token. league rules are 12-team superflex → teams=12, 2qb.
        url = (f"https://fantasyfootballcalculator.com/api/v1/adp/2qb"
               f"?teams={rules.league_size}&year={season}&position=all")
        data = httpx.get(url, timeout=30).json()
        with open(path, "w") as f:
            json.dump(data, f)
    rows = (data.get("players") or []) if isinstance(data, dict) else []
    norm = {"PK": "K", "DEF": "DST"}
    return [{"player_key": "", "name": p.get("name", ""), "team": p.get("team", ""),
             "pos": norm.get(p.get("position"), p.get("position")), "adp": p.get("adp")}
            for p in rows]


def draft_pool(season: int) -> list[dict]:
    """Standalone ADP pool for a season (FFC names + reconstructed value)."""
    from .rules import load_rules_fixture
    rules = load_rules_fixture()
    return value_from_adp(_ffc_adp(season, rules), rules)
