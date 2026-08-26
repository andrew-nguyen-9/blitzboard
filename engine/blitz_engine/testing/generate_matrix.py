"""Generator for `fixtures/league_matrix.json` (E7a) — run this to regenerate the fixture.

Not imported by `matrix.py` (the loader parses the checked-in JSON only, never regenerates at
import time). Deterministic: same output every run, no RNG.

Usage: ``python -m blitz_engine.testing.generate_matrix`` (writes the fixture in place).

Smoke-subset algorithm (documented per the brief — this is the "generator as
docstring/script" requirement): a **deterministic greedy pairwise-covering** search.
Every row fixes one level per factor (`teams`, `qb_mode`, `scoring`, `te_premium`,
`bench_slots`, `ir_slots`); a "pair" is one (factor_a, factor_b, level_a, level_b) tuple for
one of the 15 factor-combinations. Greedily pick, from the 432 rows in canonical generation
order (ties broken by that same order), the row covering the most not-yet-covered pairs;
repeat until all pairs are covered, then pad up to exactly 16 rows by continuing to draw the
next not-yet-selected row in canonical order (a no-op for coverage, but keeps the checked-in
list a fixed size regardless of how many rows the covering phase needed).
"""
from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path
from typing import Any

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "fixtures" / "league_matrix.json"

FACTORS: dict[str, list[Any]] = {
    "teams": [8, 10, 12, 14],
    "qb_mode": ["1qb", "superflex", "2qb"],
    "scoring": ["std", "half", "ppr"],
    "te_premium": [0.0, 0.5],
    "bench_slots": [4, 6, 8],
    "ir_slots": [0, 1],
}
SMOKE_SIZE = 16


def _row_id(v: dict[str, Any]) -> str:
    return (
        f"t{v['teams']}-{v['qb_mode']}-{v['scoring']}-te{v['te_premium']}"
        f"-b{v['bench_slots']}-ir{v['ir_slots']}"
    )


def _starting_slots(qb_mode: str) -> dict[str, int]:
    slots = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1}
    if qb_mode == "superflex":
        slots["SUPERFLEX"] = 1
    elif qb_mode == "2qb":
        slots["QB"] = 2
    slots["K"] = 1
    slots["DST"] = 1
    return slots


def _all_rows() -> list[dict[str, Any]]:
    rows = []
    for teams in FACTORS["teams"]:
        for qb_mode in FACTORS["qb_mode"]:
            for scoring in FACTORS["scoring"]:
                for te_premium in FACTORS["te_premium"]:
                    for bench_slots in FACTORS["bench_slots"]:
                        for ir_slots in FACTORS["ir_slots"]:
                            v = {
                                "teams": teams,
                                "qb_mode": qb_mode,
                                "scoring": scoring,
                                "te_premium": te_premium,
                                "bench_slots": bench_slots,
                                "ir_slots": ir_slots,
                            }
                            row = {
                                "id": _row_id(v), **v,
                                "starting_slots": _starting_slots(qb_mode),
                            }
                            rows.append(row)
    return rows


def _row_pairs(row: dict[str, Any]) -> set[tuple[str, str, Any, Any]]:
    keys = list(FACTORS)
    return {
        (a, b, row[a], row[b])
        for a, b in combinations(keys, 2)
    }


def _greedy_smoke(rows: list[dict[str, Any]]) -> list[str]:
    all_pairs: set[tuple[str, str, Any, Any]] = set()
    row_pairs = [_row_pairs(r) for r in rows]
    for rp in row_pairs:
        all_pairs |= rp

    uncovered = set(all_pairs)
    selected: list[int] = []
    selected_set: set[int] = set()
    while uncovered:
        best_i, best_gain = -1, -1
        for i, rp in enumerate(row_pairs):
            if i in selected_set:
                continue
            gain = len(rp & uncovered)
            if gain > best_gain:
                best_i, best_gain = i, gain
        if best_gain <= 0:
            break
        selected.append(best_i)
        selected_set.add(best_i)
        uncovered -= row_pairs[best_i]

    # Pad to SMOKE_SIZE with the next not-yet-selected rows in canonical order (deterministic;
    # coverage is already complete, this only fixes the checked-in list's size).
    i = 0
    while len(selected) < SMOKE_SIZE and i < len(rows):
        if i not in selected_set:
            selected.append(i)
            selected_set.add(i)
        i += 1

    if len(selected) > SMOKE_SIZE:
        raise RuntimeError(
            f"greedy covering needed {len(selected)} rows, more than SMOKE_SIZE={SMOKE_SIZE}"
        )
    return [rows[i]["id"] for i in selected]


def generate() -> dict[str, Any]:
    rows = _all_rows()
    smoke = _greedy_smoke(rows)
    return {
        "version": 1,
        "factors": FACTORS,
        "rows": rows,
        "smoke": smoke,
    }


def main() -> None:
    data = generate()
    FIXTURE_PATH.write_text(json.dumps(data, indent=2) + "\n")
    print(f"wrote {len(data['rows'])} rows, {len(data['smoke'])} smoke ids -> {FIXTURE_PATH}")


if __name__ == "__main__":
    main()
