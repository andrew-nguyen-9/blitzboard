"""C03 complete bench portfolios and the accepted-C02C measurement adapter.

The selector enumerates every exact-budget count vector and scores the composition as a whole.
It is deterministic, local/free, and separate from the authoritative season-outcome evaluator:
the static score chooses an arm; C02C then measures that arm against the accepted legacy control.
"""
from __future__ import annotations

import math
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

POSITIONS: tuple[str, ...] = ("QB", "RB", "WR", "TE", "K", "DST")
BLOCKED_SLICE = "t14-2qb-std-te0.5-b4-ir1"


@dataclass(frozen=True)
class PortfolioSelection:
    league_config_key: str
    bench_slots: int
    composition: dict[str, int]
    score: float
    soft_marginal_costs: dict[str, list[float]]
    vectors_evaluated: int


def enumerate_feasible_vectors(bench_slots: int) -> tuple[dict[str, int], ...]:
    """Every weak composition of ``bench_slots`` across the six stable positions."""
    if type(bench_slots) is not int or bench_slots < 0:
        raise ValueError("bench_slots must be a non-negative integer")
    out: list[dict[str, int]] = []

    def visit(prefix: tuple[int, ...], remaining: int) -> None:
        if len(prefix) == len(POSITIONS) - 1:
            values = (*prefix, remaining)
            out.append(dict(zip(POSITIONS, values, strict=True)))
            return
        for count in range(remaining + 1):
            visit((*prefix, count), remaining - count)

    visit((), bench_slots)
    expected = math.comb(bench_slots + len(POSITIONS) - 1, len(POSITIONS) - 1)
    if len(out) != expected:  # defensive: vector coverage is a zero-tolerance gate
        raise RuntimeError(f"enumerated {len(out)} vectors; expected {expected}")
    return tuple(out)


def _eligible(slot: str, qb_mode: str) -> frozenset[str]:
    if slot == "FLEX":
        return frozenset({"RB", "WR", "TE"})
    if slot in {"SUPERFLEX", "OP", "SFLX"}:
        return frozenset({"QB", "RB", "WR", "TE"})
    if slot == "QB2" and qb_mode == "2qb":
        return frozenset({"QB"})
    return frozenset({slot.removesuffix("2")})


def maximum_hole_coverage(
    vector: Mapping[str, int], holes: Iterable[str], qb_mode: str
) -> int:
    """Maximum matching of distinct bench bodies to simultaneous starter holes."""
    bodies = [p for p in POSITIONS for _ in range(int(vector.get(p, 0)))]
    hole_list = list(holes)
    assignment: dict[int, int] = {}

    def place(body: int, seen: set[int]) -> bool:
        for hole, slot in enumerate(hole_list):
            if hole in seen or bodies[body] not in _eligible(slot, qb_mode):
                continue
            seen.add(hole)
            prior = assignment.get(hole)
            if prior is None or place(prior, seen):
                assignment[hole] = body
                return True
        return False

    return sum(place(body, set()) for body in range(len(bodies)))


def portfolio_score(vector: Mapping[str, int], row: Mapping[str, Any]) -> float:
    """Preregistered whole-portfolio-v1 selection score."""
    bench = int(row["bench_slots"])
    if set(vector) != set(POSITIONS) or any(type(vector[p]) is not int for p in POSITIONS):
        raise ValueError("composition must contain integer counts for all positions")
    if any(vector[p] < 0 for p in POSITIONS) or sum(vector.values()) != bench:
        raise ValueError("composition violates the exact bench budget")
    mode = str(row["qb_mode"])
    if mode not in {"1qb", "superflex", "2qb"}:
        raise ValueError(f"unsupported qb_mode {mode}")

    need = {"QB": 1.0, "RB": 2.0, "WR": 2.0, "TE": 1.0, "K": 0.15, "DST": 0.15}
    if mode == "superflex":
        need["QB"] += 0.9
    elif mode == "2qb":
        need["QB"] += 1.15
    flex = int(row["starting_slots"].get("FLEX", 0))
    need["RB"] += 0.35 * flex
    need["WR"] += 0.40 * flex
    need["TE"] += 0.10 * flex + 0.9 * float(row["te_premium"])

    replace = {"QB": 0.7, "RB": 0.9, "WR": 1.0, "TE": 0.65, "K": 0.12, "DST": 0.12}
    if mode != "1qb":
        replace["QB"] += 1.15
    replace["TE"] += 0.8 * float(row["te_premium"])
    scarcity = 1.0 + 0.045 * (int(row["teams"]) - 10) + 0.035 * (bench - 4)
    no_ir = 1.18 if int(row["ir_slots"]) == 0 else 1.0

    score = 0.0
    for pos in POSITIONS:
        count = vector[pos]
        for depth in range(1, count + 1):
            marginal = (need[pos] * 2.2 + replace[pos] * scarcity) / depth
            if pos in {"QB", "RB", "WR", "TE"}:
                marginal *= no_ir
                marginal += int(row["ir_slots"]) * 0.12 / depth
            score += marginal
        if count > 1 and pos in {"QB", "RB", "WR", "TE"}:
            score -= 0.22 * count * (count - 1) / 2

    holes = ["QB", "RB", "WR", "TE", *(["FLEX"] * flex)]
    if mode == "superflex":
        holes.append("SUPERFLEX")
    elif mode == "2qb":
        holes.append("QB2")
    score += 0.55 * maximum_hole_coverage(vector, holes, mode)
    return round(score, 10)


def select_portfolio(row: Mapping[str, Any]) -> PortfolioSelection:
    """Exhaustively choose one composition and derive finite soft opportunity costs."""
    vectors = enumerate_feasible_vectors(int(row["bench_slots"]))
    scored = [(portfolio_score(v, row), tuple(v[p] for p in POSITIONS), v) for v in vectors]
    best_score, _tie, best = max(scored, key=lambda item: (item[0], tuple(-n for n in item[1])))
    costs: dict[str, list[float]] = {}
    bench = int(row["bench_slots"])
    for pos in POSITIONS:
        curve = []
        for depth in range(bench + 1):
            constrained = max(score for score, _key, v in scored if v[pos] == depth)
            curve.append(round(max(0.0, best_score - constrained), 6))
        costs[pos] = curve
    return PortfolioSelection(
        league_config_key=str(row["id"]),
        bench_slots=bench,
        composition=dict(best),
        score=best_score,
        soft_marginal_costs=costs,
        vectors_evaluated=len(vectors),
    )


def _normal_ci(values: Sequence[float]) -> dict[str, float]:
    a = np.asarray(values, dtype=np.float64)
    mean = float(a.mean())
    half = 1.96 * float(a.std(ddof=1)) / math.sqrt(a.size) if a.size > 1 else float("inf")
    return {"mean": mean, "lo": mean - half, "hi": mean + half, "n": int(a.size)}


def measure_portfolio(
    row: Mapping[str, Any],
    *,
    seasons: Sequence[int],
    board_seeds: Sequence[int],
    season_seeds: Sequence[int],
) -> dict[str, Any]:
    """Authoritative mirrored candidate-vs-legacy measurement through public C02C APIs."""
    from blitz_engine.simulation import season_eval as se
    from blitz_engine.value.roster_shape import Preset, ablation_presets, shape_pick_fn

    started = time.perf_counter()
    selection = select_portfolio(row)
    control = ablation_presets(row)["e6"]
    candidate = Preset(
        demand=tuple((p, selection.composition[p]) for p in POSITIONS),
        ceiling=tuple((p, selection.composition[p]) for p in POSITIONS),
        kdst_at=control.kdst_at,
    )
    pick_fn = shape_pick_fn({"control": control, "candidate": candidate})
    fields = {
        "started_points": "per_season",
        "h2h": "per_season_h2h",
        "playoff": "per_season_playoff",
        "championship": "per_season_champ",
    }
    paired: dict[str, list[float]] = {name: [] for name in fields}
    waiver: list[float] = []
    illegal = 0

    for year in seasons:
        players = se.build_players(year, str(row["id"]))
        for board_seed in board_seeds:
            rosters_by_parity = []
            policies_by_parity = []
            for parity in (0, 1):
                policies = [
                    "candidate" if seat % 2 == parity else "control"
                    for seat in range(int(row["teams"]))
                ]
                rosters, assigned = se.draft_league(
                    players, row, seed=int(board_seed), policies=policies, pick_fn=pick_fn
                )
                rosters_by_parity.append(rosters)
                policies_by_parity.append(assigned)
                expected_size = sum(int(n) for n in row["starting_slots"].values()) + int(
                    row["bench_slots"]
                )
                illegal += sum(len(roster) != expected_size for roster in rosters)
            for season_seed in season_seeds:
                cfg = se.EvalConfig(n_seasons=1, seed=int(season_seed))
                results = [
                    se.evaluate_rosters(
                        players,
                        rosters_by_parity[parity],
                        row,
                        seat_policy=policies_by_parity[parity],
                        config=cfg,
                    )
                    for parity in (0, 1)
                ]
                for seat in range(int(row["teams"])):
                    candidate_run = 0 if results[0].seat_policy[seat] == "candidate" else 1
                    control_run = 1 - candidate_run
                    if results[control_run].seat_policy[seat] != "control":
                        raise RuntimeError("mirrored arm assignment drift")
                    for name, field in fields.items():
                        paired[name].append(
                            float(
                                getattr(results[candidate_run], field)[0, seat]
                                - getattr(results[control_run], field)[0, seat]
                            )
                        )
                    waiver.append(
                        float(
                            results[candidate_run].waiver_adds[seat]
                            - results[control_run].waiver_adds[seat]
                        )
                    )

    return {
        "league_config_key": str(row["id"]),
        "selection": {
            "composition": selection.composition,
            "score": selection.score,
            "soft_marginal_costs": selection.soft_marginal_costs,
            "vectors_evaluated": selection.vectors_evaluated,
        },
        "metrics": {name: _normal_ci(values) for name, values in paired.items()},
        "waiver_adds": _normal_ci(waiver),
        "lineup_illegal_count": int(illegal),
        "bench_budget_violation_count": int(
            sum(selection.composition.values()) != int(row["bench_slots"])
        ),
        "runtime_seconds": round(time.perf_counter() - started, 6),
    }


__all__ = [
    "BLOCKED_SLICE",
    "POSITIONS",
    "PortfolioSelection",
    "enumerate_feasible_vectors",
    "maximum_hole_coverage",
    "measure_portfolio",
    "portfolio_score",
    "select_portfolio",
]
