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


# PBP columns we need for distance-K (Task 3) and yardage/points-allowed D/ST (Task 4).
_PBP_COLS = [
    "play_type", "field_goal_result", "kick_distance", "extra_point_result",
    "kicker_player_id", "season", "week", "season_type",
    "sack", "interception", "fumble_lost", "fumble_recovery_1_team",
    "safety", "touchdown", "return_touchdown", "posteam", "defteam",
    "yards_gained", "home_team", "away_team", "home_score", "away_score",
]


def _pbp_frame(season: int):
    import nfl_data_py as nfl
    return cached(f"pbp_{season}", lambda: nfl.import_pbp_data([season], columns=_PBP_COLS))


def kicking_weekly(season: int) -> list[dict]:
    from .rules import load_rules_fixture
    from .pbp_kicking import kicker_week_buckets
    from models.scoring import score_kicking
    sc = load_rules_fixture().scoring
    df = _pbp_frame(season)
    if "season_type" in df.columns:
        df = df[df["season_type"] == "REG"]
    buckets = kicker_week_buckets(df.to_dict("records"))
    return [{"player_key": kid, "name": kid, "pos": "K", "team": "",
             "season": s, "week": w, "points": score_kicking(b, sc)}
            for (kid, s, w), b in buckets.items()]


def defense_weekly(season: int) -> list[dict]:
    from .rules import load_rules_fixture
    from .pbp_defense import team_week_dst
    from models.scoring import score_defense
    sc = load_rules_fixture().scoring
    df = _pbp_frame(season)
    if "season_type" in df.columns:
        df = df[df["season_type"] == "REG"]
    lines = team_week_dst(df.to_dict("records"))
    return [{"player_key": tm, "name": f"{tm} D/ST", "pos": "DST", "team": tm,
             "season": s, "week": w, "points": score_defense(d, sc)}
            for (tm, s, w), d in lines.items()]


def season_actuals(season: int) -> list[dict]:
    """All weekly actual points (offense + K + D/ST) for a season, under league rules."""
    return offense_weekly(season) + kicking_weekly(season) + defense_weekly(season)
