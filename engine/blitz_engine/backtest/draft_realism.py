"""C06 draft-realism land gate over the shipped TypeScript v5 policy."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from blitz_engine.backtest.static_fit import run_bridge
from blitz_engine.simulation import season_eval as se
from blitz_engine.testing import matrix
from blitz_engine.value.roster_solver import (
    InfeasibleRosterError,
    Player,
    RosterRequirements,
    optimize_lineup,
    slot_accepts,
)

ROOT = Path(__file__).resolve().parents[3]
SCENARIO_IDS = (
    "t10-1qb-std-te0.0-b4-ir0",
    "t10-2qb-ppr-te0.0-b8-ir1",
    "t12-1qb-half-te0.0-b6-ir0",
    "t12-2qb-half-te0.0-b6-ir0",
    "t14-1qb-half-te0.0-b8-ir0",
    "t14-superflex-ppr-te0.0-b6-ir0",
)
EVALUATOR = "draftAI.DEFAULT_POLICY(v5) + season_eval.evaluate_rosters"


@dataclass(frozen=True)
class DraftSpec:
    index: int
    base_seed: int
    derived_seed: int
    row: dict[str, Any]
    test_seat: int
    slot_band: str
    season: int = 2024


def row(row_id: str) -> dict[str, Any]:
    return matrix.by_id(row_id)


def _seed(base_seed: int, index: int) -> int:
    raw = hashlib.blake2s(f"{base_seed}:{index}".encode(), digest_size=4).digest()
    return int.from_bytes(raw) & 0x7FFF_FFFF


def draft_specs(base_seed: int, count: int) -> list[DraftSpec]:
    """Deterministic, seat-stratified jobs over the required canonical matrix slices."""
    out: list[DraftSpec] = []
    for i in range(count):
        league = row(SCENARIO_IDS[i % len(SCENARIO_IDS)])
        seed = _seed(base_seed, i)
        teams = int(league["teams"])
        cuts = (0, max(1, teams // 3), max(2, 2 * teams // 3), teams)
        band_idx = i % 3
        seat = random.Random(seed).randrange(cuts[band_idx], cuts[band_idx + 1])
        out.append(
            DraftSpec(
                index=i,
                base_seed=base_seed,
                derived_seed=seed,
                row=league,
                test_seat=seat,
                slot_band=("front", "middle", "back")[band_idx],
            )
        )
    return out


def draft(specs: list[DraftSpec]) -> list[dict[str, Any]]:
    """Batch the real shipped policy; all non-test seats are seeded dummy autodrafters."""
    jobs = [
        {
            "row": spec.row,
            "seed": spec.derived_seed,
            "arms": {"v5": {}},
            "assign": ["v5"] * int(spec.row["teams"]),
        }
        for spec in specs
    ]
    return run_bridge(jobs)


def _requirements(league: dict[str, Any]) -> RosterRequirements:
    starters = tuple(
        slot for slot, count in league["starting_slots"].items() for _ in range(int(count))
    )
    return RosterRequirements(starters=starters, bench_size=int(league["bench_slots"]))


def validate_rosters(
    rosters: list[list[se.SeasonPlayer]], league: dict[str, Any]
) -> list[dict[str, Any]]:
    """Reject duplicate, short, or starter-incomplete rosters using the existing solver."""
    expected = len(_requirements(league).starters) + int(league["bench_slots"])
    ids = [p.player_id for roster in rosters for p in roster]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate player selected")
    reports: list[dict[str, Any]] = []
    for roster_ in rosters:
        if len(roster_) != expected:
            raise ValueError(f"illegal roster size {len(roster_)} != {expected}")
        players = [Player(p.player_id, p.position, p.projection, p.bye_week) for p in roster_]
        try:
            lineup = optimize_lineup(players, _requirements(league))
        except InfeasibleRosterError as exc:
            raise ValueError(f"illegal roster: {exc}") from exc
        reports.append(
            {
                "legal": lineup.is_legal,
                "starter_complete": len(lineup.starters) == len(_requirements(league).starters),
                "missing_bye_count": sum(p.bye_week <= 0 for p in roster_),
            }
        )
    return reports


def classify_team(
    *,
    legal: bool,
    complete: bool,
    started_points: float,
    league_median: float,
    delta_ci: tuple[float, float],
    h2h: float,
    playoff: float,
    playoff_baseline: float,
) -> dict[str, Any]:
    """Cohort-relative quality label; ``winnable`` is a model proxy, never a guarantee."""
    if not legal or not complete:
        return {"classification": "UNACCEPTABLE", "winnable": False}
    winnable = started_points >= league_median or delta_ci[1] >= 0
    strength = started_points / league_median if league_median else 0.0
    dominated = (
        strength < 0.85 and delta_ci[1] < 0 and h2h < 0.40 and playoff < 0.5 * playoff_baseline
    )
    if dominated:
        label = "UNACCEPTABLE"
        winnable = False
    elif not winnable or strength < 0.95 or h2h < 0.45 or playoff < 0.5 * playoff_baseline:
        label = "BORDERLINE"
    else:
        label = "ACCEPTABLE"
    return {"classification": label, "winnable": bool(winnable)}


def _normal_ci(values: np.ndarray) -> tuple[float, float]:
    mean = float(values.mean())
    if len(values) < 2:
        return mean, mean
    margin = 1.96 * float(values.std(ddof=1)) / len(values) ** 0.5
    return mean - margin, mean + margin


def evaluate_draft(
    spec: DraftSpec,
    result: dict[str, Any],
    *,
    n_seasons: int = 4,
    seat_policy: list[str] | None = None,
    evaluator: str = EVALUATOR,
    pool_override: list[se.SeasonPlayer] | None = None,
) -> dict[str, Any]:
    """Evaluate one shipped-v5 draft against its own autodraft cohort."""
    started = time.perf_counter()
    pool = pool_override or se.build_players(spec.season, spec.row["id"])
    by_id = {p.player_id: p for p in pool}
    rosters = [[by_id[pid] for pid in ids] for ids in result["rosters"]]
    flat = [p.player_id for roster_ in rosters for p in roster_]
    duplicate_free = len(flat) == len(set(flat))
    legality: list[dict[str, Any]] = []
    lineups = []
    for roster_ in rosters:
        try:
            legality.append(validate_rosters([roster_], spec.row)[0])
            players = [Player(p.player_id, p.position, p.projection, p.bye_week) for p in roster_]
            lineups.append(optimize_lineup(players, _requirements(spec.row)))
        except ValueError as exc:
            legality.append(
                {
                    "legal": False,
                    "starter_complete": False,
                    "missing_bye_count": sum(p.bye_week <= 0 for p in roster_),
                    "error": str(exc),
                }
            )
            lineups.append(None)
    outcome = se.evaluate_rosters(
        pool,
        rosters,
        spec.row,
        seat_policy=seat_policy or ["v5"] * len(rosters),
        config=se.EvalConfig(n_seasons=n_seasons, seed=spec.derived_seed),
    )
    seat = spec.test_seat
    median = float(np.median(outcome.started_points))
    deltas = outcome.per_season[:, seat] - np.median(outcome.per_season, axis=1)
    ci = _normal_ci(deltas)
    lineup = lineups[seat]
    bench = list(lineup.bench) if lineup is not None else []
    all_bench = [p.value for item in lineups if item is not None for p in item.bench]
    bench_median = statistics.median(all_bench) if all_bench else 0.0
    bench_quality = (
        statistics.mean(p.value for p in bench) / bench_median if bench and bench_median else 0.0
    )
    covered = 0
    starters = list(lineup.starters) if lineup is not None else []
    for slot, starter in starters:
        if any(slot_accepts(slot, p.position) and p.bye_week != starter.bye_week for p in bench):
            covered += 1
    coverage = covered / len(starters) if starters else 0.0
    position_counts: dict[str, int] = {}
    for p in rosters[seat]:
        position_counts[p.position] = position_counts.get(p.position, 0) + 1
    upside_cut = float(np.percentile(all_bench, 75)) if all_bench else float("inf")
    quality = classify_team(
        legal=bool(legality[seat]["legal"] and duplicate_free),
        complete=bool(legality[seat]["starter_complete"]),
        started_points=float(outcome.started_points[seat]),
        league_median=median,
        delta_ci=ci,
        h2h=float(outcome.h2h_win_rate[seat]),
        playoff=float(outcome.playoff_rate[seat]),
        playoff_baseline=min(se.EvalConfig().playoff_slots, spec.row["teams"]) / spec.row["teams"],
    )
    team = {
        **legality[seat],
        "duplicate_free": duplicate_free,
        "starter_strength_vs_median": round(float(outcome.started_points[seat]) / median, 4),
        "bench_coverage": round(coverage, 4),
        "replacement_quality": round(bench_quality, 4),
        "bye_absence_coverage": round(coverage, 4),
        "contingent_role_upside": {
            "contingent_role": "unavailable: no authoritative role-transfer metadata",
            "upside_proxy_count": sum(p.value >= upside_cut for p in bench),
        },
        "positional_scarcity_redundancy": position_counts,
        "paired_h2h": round(float(outcome.h2h_win_rate[seat]), 4),
        "playoff_proxy": round(float(outcome.playoff_rate[seat]), 4),
        "championship_proxy": round(float(outcome.champ_rate[seat]), 4),
        "uncertainty": {
            "started_points_delta_ci95": [round(ci[0], 3), round(ci[1], 3)],
            "degraded_inputs": ["adp", "injury_status", "contingent_role"],
            "n_seasons": n_seasons,
            "limitations": "local historical corpus and proxy playoffs; no win guarantee",
        },
        **quality,
    }
    return {
        "index": spec.index,
        "season": spec.season,
        "base_seed": spec.base_seed,
        "derived_seed": spec.derived_seed,
        "format_fixture": spec.row["id"],
        "draft_position": seat + 1,
        "slot_band": spec.slot_band,
        "number_of_teams": spec.row["teams"],
        "player_selections": result["rosters"],
        "outcome_metrics": {
            "started_points": [round(float(v), 3) for v in outcome.started_points],
            "h2h": [round(float(v), 4) for v in outcome.h2h_win_rate],
            "playoff": [round(float(v), 4) for v in outcome.playoff_rate],
            "championship": [round(float(v), 4) for v in outcome.champ_rate],
        },
        "test_team": team,
        "all_rosters_legal": all(item["legal"] for item in legality),
        "duplicate_free": duplicate_free,
        "elapsed_seconds": round(time.perf_counter() - started, 4),
        "model_evaluator": evaluator,
        "synthetic_non_authoritative": True,
    }


def run_batch(base_seed: int, count: int, *, n_seasons: int = 2) -> dict[str, Any]:
    """Run the bounded fail-fast C06 batch and return one deterministic-order report."""
    started = time.perf_counter()
    specs = draft_specs(base_seed, count)
    results = [
        evaluate_draft(spec, drafted, n_seasons=n_seasons)
        for spec, drafted in zip(specs, draft(specs), strict=True)
    ]
    labels = {name: 0 for name in ("ACCEPTABLE", "BORDERLINE", "UNACCEPTABLE")}
    for result in results:
        labels[result["test_team"]["classification"]] += 1
    return {
        "schema_version": 1,
        "authority": "shipped v5 production behavior",
        "c05_promotion": "excluded; no fit or confirmation executed",
        "synthetic_non_authoritative": True,
        "base_seed": base_seed,
        "draft_count": count,
        "season_evaluations_per_draft": n_seasons,
        "elapsed_seconds": round(time.perf_counter() - started, 4),
        "summary": {
            "legal_drafts": sum(r["all_rosters_legal"] for r in results),
            "duplicate_free_drafts": sum(r["duplicate_free"] for r in results),
            "classifications": labels,
            "formats": sorted({r["format_fixture"] for r in results}),
            "slot_bands": sorted({r["slot_band"] for r in results}),
        },
        "drafts": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-seed", type=int, default=20260828)
    parser.add_argument("--count", type=int, default=18)
    parser.add_argument("--seasons", type=int, default=2)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_batch(args.base_seed, args.count, n_seasons=args.seasons)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
