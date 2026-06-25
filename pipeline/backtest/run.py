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
from .evaluate import SUPERFLEX_SLOTS, aggregate, h2h_record, optimal_week_points
from .rules import load_rules_fixture
from .sim_bridge import run_draft

_SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b")


def _norm_name(s: str) -> str:
    s = (s or "").lower().replace(".", "").replace("'", "")
    s = _SUFFIX.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def join_pool_to_actuals(pool, actuals):
    """Position + display-name lookups keyed by the player_key shared by pool ids and
    actuals (we set sim id == actuals player_key, so rosters index straight in)."""
    pos_by_key = {a["player_key"]: a["pos"] for a in actuals}
    name_by_key = {a["player_key"]: a["name"] for a in actuals}
    for p in pool:
        pos_by_key.setdefault(p["id"], p.get("pos", ""))
    return pos_by_key, name_by_key


def weekly_team_points(rosters, pos_by_key, actuals_by_week, slots) -> list[list[float]]:
    weeks = sorted(actuals_by_week)
    return [[optimal_week_points(team, pos_by_key, actuals_by_week.get(w, {}), slots) for w in weeks]
            for team in rosters]


def _adp_lookup(adp_rows) -> tuple[dict, dict]:
    """Two ADP indexes: offense/K by (norm-name, pos); D/ST by (team, 'DST')."""
    by_name: dict[tuple[str, str], float] = {}
    by_team: dict[tuple[str, str], float] = {}
    for a in adp_rows:
        if a.get("adp") is None:
            continue
        if a["pos"] == "DST":
            by_team[(a.get("team", "").upper(), "DST")] = a["adp"]
        else:
            by_name[(_norm_name(a["name"]), a["pos"])] = a["adp"]
    return by_name, by_team


def _build_pool(season: int, rules, adp_rows):
    """Season-total player universe from actuals, with ADP joined on for bot-facing value."""
    by_key: dict[str, dict] = {}
    for r in season_actuals(season):
        d = by_key.setdefault(r["player_key"], {"player_key": r["player_key"], "name": r["name"],
                                                "pos": r["pos"], "team": r["team"]})
    by_name, by_team = _adp_lookup(adp_rows)
    players, matched = [], 0
    for d in by_key.values():
        if d["pos"] == "DST":
            adp = by_team.get((d["team"].upper(), "DST"))
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


def _actuals_by_week(season: int) -> dict[int, dict[str, float]]:
    abw: dict[int, dict[str, float]] = defaultdict(dict)
    for r in season_actuals(season):
        abw[r["week"]][r["player_key"]] = r["points"]
    return abw


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the v2.4 draft backtest.")
    ap.add_argument("--seasons", type=int, nargs="+", default=[2021, 2022, 2023, 2024])
    ap.add_argument("--seeds", type=int, default=8, help="number of seeds per season")
    ap.add_argument("--policy", default="v2")
    args = ap.parse_args()
    rules = load_rules_fixture()

    points_scores: list[float] = []
    winpct_scores: list[float] = []
    used_seasons: list[int] = []
    for season in args.seasons:
        adp_rows = _ffc_adp(season, rules)
        if not any(a.get("adp") is not None for a in adp_rows):
            console.print(f"[yellow]⚠ no ADP for {season} — skipping (FFC has no archive).[/yellow]")
            continue
        pool, matched = _build_pool(season, rules, adp_rows)
        pos_by_key, _ = join_pool_to_actuals(pool, season_actuals(season))
        abw = _actuals_by_week(season)
        console.print(f"[cyan]{season}: pool {len(pool)} players, {matched} ADP-matched · {args.seeds} seeds[/cyan]")
        for seed in range(args.seeds):
            rosters = run_draft(pool, seed=seed, num_teams=rules.league_size, policy=args.policy)
            wtp = weekly_team_points(rosters, pos_by_key, abw, SUPERFLEX_SLOTS)
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
