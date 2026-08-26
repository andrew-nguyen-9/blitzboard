#!/usr/bin/env python3
"""Independent C03 synthetic prototype: exhaustive bench-vector enumeration.

This is deliberately not production code and does not import the production evaluator. It makes
the acceptance mechanics executable before C03 implementation exists.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import resource
import time
import tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

POSITIONS = ("QB", "RB", "WR", "TE", "K", "DST")
EVIDENCE_STATUSES = frozenset({"measured", "interpolated", "unsupported"})
BLOCKED_SLICE = "t14-2qb-std-te0.5-b4-ir1"


@dataclass(frozen=True)
class League:
    key: str
    teams: int
    qb_mode: str
    bench_slots: int
    te_premium: float
    ir_slots: int
    flex_slots: int = 1


def enumerate_vectors(bench_slots: int) -> list[dict[str, int]]:
    """Return every weak composition of the exact budget in stable lexical order."""
    if not isinstance(bench_slots, int) or bench_slots < 0:
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
    return out


def expected_vector_count(bench_slots: int) -> int:
    return math.comb(bench_slots + len(POSITIONS) - 1, len(POSITIONS) - 1)


def eligible_positions(slot: str, qb_mode: str) -> frozenset[str]:
    if slot == "FLEX":
        return frozenset({"RB", "WR", "TE"})
    if slot == "SUPERFLEX":
        return frozenset({"QB", "RB", "WR", "TE"})
    if slot == "QB2" and qb_mode == "2qb":
        return frozenset({"QB"})
    return frozenset({slot.removesuffix("2")})


def maximum_hole_coverage(vector: Mapping[str, int], holes: Iterable[str], qb_mode: str) -> int:
    """Maximum bipartite match of bench bodies to simultaneous starter holes."""
    bodies = [p for p in POSITIONS for _ in range(int(vector.get(p, 0)))]
    hole_list = list(holes)
    assigned: dict[int, int] = {}

    def place(body_idx: int, seen: set[int]) -> bool:
        for hole_idx, slot in enumerate(hole_list):
            if hole_idx in seen or bodies[body_idx] not in eligible_positions(slot, qb_mode):
                continue
            seen.add(hole_idx)
            previous = assigned.get(hole_idx)
            if previous is None or place(previous, seen):
                assigned[hole_idx] = body_idx
                return True
        return False

    return sum(place(i, set()) for i in range(len(bodies)))


def portfolio_score(vector: Mapping[str, int], league: League) -> float:
    """Synthetic soft objective exercising C03 dimensions, not a fitted football claim."""
    if set(vector) != set(POSITIONS) or any(type(vector[p]) is not int or vector[p] < 0 for p in POSITIONS):
        raise ValueError("vector must contain non-negative integer counts for every position")
    if sum(vector.values()) != league.bench_slots:
        raise ValueError("bench-budget violation")
    if league.qb_mode not in {"1qb", "superflex", "2qb"}:
        raise ValueError("unsupported qb_mode")

    starter_need = {"QB": 1.0, "RB": 2.0, "WR": 2.0, "TE": 1.0, "K": 0.15, "DST": 0.15}
    if league.qb_mode == "superflex":
        starter_need["QB"] += 0.9
    elif league.qb_mode == "2qb":
        starter_need["QB"] += 1.15
    starter_need["RB"] += 0.35 * league.flex_slots
    starter_need["WR"] += 0.40 * league.flex_slots
    starter_need["TE"] += 0.10 * league.flex_slots + league.te_premium * 0.9

    # Larger leagues and deeper benches make waivers less replaceable. No-IR increases active
    # fragility coverage; IR adds a smaller upside-stash benefit instead of a positional cap.
    scarcity = 1.0 + (league.teams - 10) * 0.045 + (league.bench_slots - 4) * 0.035
    no_ir_fragility = 1.18 if league.ir_slots == 0 else 1.0
    score = 0.0
    for pos in POSITIONS:
        count = vector[pos]
        replaceability = {"QB": 0.7, "RB": 0.9, "WR": 1.0, "TE": 0.65, "K": 0.12, "DST": 0.12}[pos]
        if pos == "QB" and league.qb_mode != "1qb":
            replaceability += 1.15
        if pos == "TE":
            replaceability += league.te_premium * 0.8
        for depth in range(1, count + 1):
            marginal = (starter_need[pos] * 2.2 + replaceability * scarcity) / depth
            if pos in {"QB", "RB", "WR", "TE"}:
                marginal *= no_ir_fragility
                marginal += league.ir_slots * 0.12 / depth
            score += marginal

        # Same-position contingencies share failure modes and bye coverage; keep the cost soft.
        if count > 1 and pos in {"QB", "RB", "WR", "TE"}:
            score -= 0.22 * count * (count - 1) / 2

    # Explicit legal substitution value for representative simultaneous starter absences.
    holes = ["QB", "RB", "WR", "TE"] + ["FLEX"] * league.flex_slots
    if league.qb_mode == "superflex":
        holes.append("SUPERFLEX")
    elif league.qb_mode == "2qb":
        holes.append("QB2")
    score += 0.55 * maximum_hole_coverage(vector, holes, league.qb_mode)
    return round(score, 10)


def best_complete_vector(league: League) -> tuple[dict[str, int], float]:
    scored = ((portfolio_score(v, league), tuple(v[p] for p in POSITIONS), v) for v in enumerate_vectors(league.bench_slots))
    score, _tie, vector = max(scored, key=lambda x: (x[0], tuple(-n for n in x[1])))
    return vector, score


def old_independent_bound_vector(league: League) -> dict[str, int]:
    """Counterfactual: independently take every position's positive marginal optimum.

    The result intentionally has no shared-budget repair because that is the defect under test:
    six local optima are not a feasible portfolio.
    """
    vector: dict[str, int] = {}
    for pos in POSITIONS:
        best_n, best = 0, float("-inf")
        for n in range(league.bench_slots + 1):
            probe = {p: 0 for p in POSITIONS}
            probe[pos] = n
            # Compare on a relaxed one-position curve using the same diminishing returns.
            relaxed = League(league.key, league.teams, league.qb_mode, n, league.te_premium, league.ir_slots, league.flex_slots)
            value = portfolio_score(probe, relaxed)
            if value > best:
                best_n, best = n, value
        vector[pos] = best_n
    return vector


def canonical_json_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def validate_shape_artifact(data: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(data.get("schema_version"), int) or data.get("schema_version", 0) < 2:
        errors.append("schema_version must be integer >= 2")
    source_hash = data.get("canonical_source_hash")
    if not isinstance(source_hash, str) or len(source_hash) != 64 or any(c not in "0123456789abcdef" for c in source_hash):
        errors.append("canonical_source_hash must be lowercase sha256")
    rows = data.get("rows")
    if not isinstance(rows, dict):
        return errors + ["rows must be an object"]
    for key, row in rows.items():
        prefix = f"rows.{key}"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if row.get("league_config_key") != key:
            errors.append(f"{prefix}.league_config_key mismatch")
        status = row.get("evidence_status")
        if status not in EVIDENCE_STATUSES:
            errors.append(f"{prefix}.evidence_status invalid")
        vector = row.get("composition")
        bench_slots = row.get("bench_slots")
        if not isinstance(vector, dict) or set(vector) != set(POSITIONS):
            errors.append(f"{prefix}.composition incomplete")
        elif any(type(vector[p]) is not int or vector[p] < 0 for p in POSITIONS) or sum(vector.values()) != bench_slots:
            errors.append(f"{prefix}.composition violates budget")
        costs = row.get("soft_marginal_costs")
        if not isinstance(costs, dict) or set(costs) != set(POSITIONS):
            errors.append(f"{prefix}.soft_marginal_costs incomplete")
        elif any(not isinstance(v, list) or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in v) for v in costs.values()):
            errors.append(f"{prefix}.soft_marginal_costs malformed")
        if "hard_caps" in row or "hi" in row or "lo" in row:
            errors.append(f"{prefix} contains forbidden hard positional caps")
        measured_fields = {"n", "seeds", "source_receipt"}
        if status != "measured" and measured_fields.intersection(row):
            errors.append(f"{prefix} non-measured row claims measured provenance")
        if key == BLOCKED_SLICE and status != "unsupported":
            errors.append(f"{prefix} blocked slice must remain unsupported")
    return errors


def fallback_shape(bench_slots: int, reason: str) -> dict[str, Any]:
    """Explicit degraded soft fallback; it cannot encode a hard rejection."""
    return {
        "evidence_status": "unsupported",
        "degraded": True,
        "degraded_reason": reason,
        "soft_marginal_costs": {p: [round(0.25 * i, 2) for i in range(bench_slots + 1)] for p in POSITIONS},
        "hard_caps": None,
    }


MANDATORY_SYNTHETIC = (
    League("t10-1qb-half-te0.0-b4-ir0", 10, "1qb", 4, 0.0, 0),
    League("t10-superflex-half-te0.5-b8-ir1", 10, "superflex", 8, 0.5, 1),
    League("t10-2qb-ppr-te0.0-b8-ir0", 10, "2qb", 8, 0.0, 0),
    League("t12-1qb-ppr-te0.5-b8-ir0", 12, "1qb", 8, 0.5, 0),
    League("t12-superflex-std-te0.0-b4-ir1", 12, "superflex", 4, 0.0, 1),
    League("t12-2qb-half-te0.5-b8-ir1", 12, "2qb", 8, 0.5, 1),
    League("t14-1qb-half-te0.0-b4-ir1", 14, "1qb", 4, 0.0, 1),
    League("t14-superflex-ppr-te0.5-b8-ir0", 14, "superflex", 8, 0.5, 0),
    League(BLOCKED_SLICE, 14, "2qb", 4, 0.5, 1),
)


def run_receipt() -> dict[str, Any]:
    tracemalloc.start()
    start = time.perf_counter()
    rows = []
    for league in MANDATORY_SYNTHETIC:
        best, score = best_complete_vector(league)
        old = old_independent_bound_vector(league)
        rows.append({
            "league": asdict(league),
            "enumerated_vectors": expected_vector_count(league.bench_slots),
            "best_complete_vector": best,
            "best_synthetic_score": score,
            "old_independent_vector": old,
            "old_budget_total": sum(old.values()),
            "old_is_feasible": sum(old.values()) == league.bench_slots,
            "evidence_status": "unsupported" if league.key == BLOCKED_SLICE else "synthetic_only",
        })
    elapsed = time.perf_counter() - start
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS reports bytes; Linux reports KiB. This repository runs on macOS, but label both safely.
    rss_mib = rss_bytes / (1024 * 1024) if rss_bytes > 10_000_000 else rss_bytes / 1024
    return {
        "receipt_schema_version": 1,
        "kind": "synthetic_not_promotion_evidence",
        "prototype": "scripts/v6BenchPortfolioPrototype.py",
        "position_order": list(POSITIONS),
        "elapsed_seconds": round(elapsed, 6),
        "tracemalloc_peak_mib": round(peak / (1024 * 1024), 6),
        "process_peak_rss_mib": round(rss_mib, 6),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    receipt = run_receipt()
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
