"""Weekly actual fantasy points 2021–2025 under the seeded league rules.

Offense scores directly from nflverse weekly frames via models.scoring. K and D/ST
are added by pbp_kicking / pbp_defense (Tasks 3–4), then season_actuals unions all
three. Every script reuses pipeline/models/scoring.py — no scoring logic is
duplicated here (DoD: reuse over reinvention)."""
from __future__ import annotations

from models.scoring import score_stats

from .cache import cached

_OFF_POS = {"QB", "RB", "WR", "TE"}

# nflverse weekly columns we map into a scoring.score_stats stat line.
_OFF_COLS = (
    "passing_yards", "passing_tds", "interceptions", "passing_2pt_conversions",
    "rushing_yards", "rushing_tds", "rushing_2pt_conversions",
    "receptions", "receiving_yards", "receiving_tds", "receiving_2pt_conversions",
    "fumbles_lost",
)


def score_offense_week(stats: dict, scoring: dict) -> float:
    """One offensive stat line → fantasy points (thin wrapper over score_stats)."""
    return score_stats(stats, scoring)


def _weekly_frame(season: int):
    import nfl_data_py as nfl
    return cached(f"weekly_{season}", lambda: nfl.import_weekly_data([season]))


def offense_weekly(season: int) -> list[dict]:
    from .rules import load_rules_fixture
    sc = load_rules_fixture().scoring
    df = _weekly_frame(season)
    if "season_type" in df.columns:
        df = df[df["season_type"] == "REG"]
    cols = set(df.columns)
    rows: list[dict] = []
    for _, r in df.iterrows():
        pos = str(r.get("position") or "")
        if pos not in _OFF_POS:
            continue
        stats = {c: (None if c not in cols or r[c] != r[c] else float(r[c])) for c in _OFF_COLS}
        rows.append({
            "player_key": str(r["player_id"]),
            "name": str(r.get("player_display_name") or r.get("player_name") or ""),
            "pos": pos,
            "team": str(r.get("recent_team") or r.get("team") or ""),
            "season": int(r["season"]),
            "week": int(r["week"]),
            "points": score_offense_week(stats, sc),
        })
    return rows
