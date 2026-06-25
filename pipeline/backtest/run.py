"""Backtest orchestrator: seasons × seeds × policy → season points-for + H2H, with CIs.

Builds each season's draft pool from the actuals universe (so every drafted player has
real results), attaches a bot-facing ADP value, runs each mock draft through the shared
TS policy via the Node bridge, and scores every resulting roster on weekly-optimal actual
points. FFC has no 2025 ADP archive (checked 2026-06), so the default season set is
2021–2024; any season with no ADP is skipped with a warning (revisit 2025 in v2.4.3).

Usage:
    python -m backtest.run --seasons 2021 2022 2023 2024 --seeds 8 --policy v2
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict

from common import console

from .actuals import season_actuals
from .adp_pool import _ffc_adp, value_from_adp
from .evaluate import aggregate, h2h_record, optimal_week_points, slots_from_rules
from .rules import load_rules_fixture
from .sim_bridge import run_draft

_SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b")


def _norm_name(s: str) -> str:
    s = (s or "").lower().replace(".", "").replace("'", "")
    s = _SUFFIX.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def _abbr_name(s: str) -> str:
    """Reduce a name to first-initial + last-name, lowercased. Bridges nflverse PBP's
    abbreviated kicker names ('M.Prater') to FFC's full names ('Matt Prater') for the K
    ADP join, since both collapse to 'mprater'."""
    parts = [p for p in re.split(r"[ .]+", (s or "").replace("'", "")) if p]
    parts = [p for p in parts if not _SUFFIX.fullmatch(p.lower())]
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1]).lower()
    return _norm_name(s)


# Team-code divergences between nflverse (actuals) and FFC (ADP) → one canonical form so
# D/ST ADP actually joins (e.g. Rams LAR/STL→LA, Commanders WSH→WAS, Jaguars JAC→JAX).
_TEAM_CANON = {"LAR": "LA", "STL": "LA", "SL": "LA", "SD": "LAC", "OAK": "LV",
               "JAC": "JAX", "WSH": "WAS", "ARZ": "ARI", "CLV": "CLE", "HST": "HOU", "BLT": "BAL"}


def _canon_team(code: str) -> str:
    c = (code or "").upper()
    return _TEAM_CANON.get(c, c)


def join_pool_to_actuals(pool, actuals):
    """Position lookup keyed by the player_key shared by pool ids and actuals (we set sim
    id == actuals player_key, so rosters index straight in)."""
    pos_by_key = {a["player_key"]: a["pos"] for a in actuals}
    for p in pool:
        pos_by_key.setdefault(p["id"], p.get("pos", ""))
    return pos_by_key


def weekly_team_points(rosters, pos_by_key, actuals_by_week, slots) -> list[list[float]]:
    weeks = sorted(actuals_by_week)
    return [[optimal_week_points(team, pos_by_key, actuals_by_week.get(w, {}), slots) for w in weeks]
            for team in rosters]


def _adp_lookup(adp_rows) -> tuple[dict, dict, dict]:
    """Three ADP indexes: offense by (norm-name, pos); D/ST by (canonical-team, 'DST');
    K by (initial+lastname, 'K') to bridge nflverse's abbreviated kicker names."""
    by_name: dict[tuple[str, str], float] = {}
    by_team: dict[tuple[str, str], float] = {}
    by_abbr: dict[tuple[str, str], float] = {}
    for a in adp_rows:
        if a.get("adp") is None:
            continue
        if a["pos"] == "DST":
            by_team[(_canon_team(a.get("team", "")), "DST")] = a["adp"]
        elif a["pos"] == "K":
            by_abbr[(_abbr_name(a["name"]), "K")] = a["adp"]
        else:
            by_name[(_norm_name(a["name"]), a["pos"])] = a["adp"]
    return by_name, by_team, by_abbr


def _build_pool(actuals, rules, adp_rows):
    """Season-total player universe from actuals, with ADP joined on for bot-facing value."""
    by_key: dict[str, dict] = {}
    for r in actuals:
        by_key.setdefault(r["player_key"], {"player_key": r["player_key"], "name": r["name"],
                                            "pos": r["pos"], "team": r["team"]})
    by_name, by_team, by_abbr = _adp_lookup(adp_rows)
    players, matched = [], 0
    for d in by_key.values():
        if d["pos"] == "DST":
            adp = by_team.get((_canon_team(d["team"]), "DST"))
        elif d["pos"] == "K":
            adp = by_abbr.get((_abbr_name(d["name"]), "K"))
        else:
            adp = by_name.get((_norm_name(d["name"]), d["pos"]))
        if adp is not None:
            matched += 1
        players.append({**d, "adp": adp})
    valued = value_from_adp(players, rules)
    pool = [{"id": p["player_key"], "full_name": p["name"], "position": p["pos"],
             "nfl_team": p["team"], "bye_week": None, "metadata": {}, "value": p["value"]}
            for p in valued]
    return pool, matched


def _actuals_by_week(actuals) -> dict[int, dict[str, float]]:
    abw: dict[int, dict[str, float]] = defaultdict(dict)
    for r in actuals:
        abw[r["week"]][r["player_key"]] = r["points"]
    return abw


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the v2.4 draft backtest.")
    ap.add_argument("--seasons", type=int, nargs="+", default=[2021, 2022, 2023, 2024])
    ap.add_argument("--seeds", type=int, default=8, help="number of seeds per season")
    ap.add_argument("--policy", default="v2")
    args = ap.parse_args()
    rules = load_rules_fixture()
    slots = slots_from_rules(rules)

    points_scores: list[float] = []
    winpct_scores: list[float] = []
    used_seasons: list[int] = []
    for season in args.seasons:
        adp_rows = _ffc_adp(season, rules)
        if not any(a.get("adp") is not None for a in adp_rows):
            console.print(f"[yellow]⚠ no ADP for {season} — skipping (FFC has no archive).[/yellow]")
            continue
        actuals = season_actuals(season)  # compute once; reused for pool, weeks, and join
        pool, matched = _build_pool(actuals, rules, adp_rows)
        pos_by_key = join_pool_to_actuals(pool, actuals)
        abw = _actuals_by_week(actuals)
        console.print(f"[cyan]{season}: pool {len(pool)} players, {matched} ADP-matched · {args.seeds} seeds[/cyan]")
        for seed in range(args.seeds):
            rosters = run_draft(pool, seed=seed, num_teams=rules.league_size, policy=args.policy)
            wtp = weekly_team_points(rosters, pos_by_key, abw, slots)
            for t in range(len(rosters)):
                points_scores.append(sum(wtp[t]))
                w, l, ti = h2h_record(t, wtp)
                winpct_scores.append(100.0 * w / max(1, w + l + ti))
        used_seasons.append(season)

    if not points_scores:
        console.print("[red]No seasons had ADP — nothing to score.[/red]")
        return
    pa = aggregate(points_scores)
    wa = aggregate(winpct_scores)
    console.print(f"\n[bold]policy={args.policy}  seasons={used_seasons}  seeds={args.seeds}[/bold]")
    console.print(f"  season points-for:  {pa['mean']:.0f}  (95% CI {pa['lo']:.0f}–{pa['hi']:.0f})")
    console.print(f"  H2H win%:           {wa['mean']:.1f}%  (95% CI {wa['lo']:.1f}–{wa['hi']:.1f})")


if __name__ == "__main__":
    main()
