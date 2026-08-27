#!/usr/bin/env python3
"""Generate schema-v2 bench shape and browser data from an immutable C03 source receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / ".orchestrator-v6/experiments/bench-portfolio-c03-source-v2.json"
DEFAULT_FIXTURE = ROOT / "fixtures/bench_shape.json"
DEFAULT_TS = ROOT / "frontend/lib/generated/benchShape.generated.ts"
MATRIX = ROOT / "fixtures/league_matrix.json"
POSITIONS = ("QB", "RB", "WR", "TE", "K", "DST")
BLOCKED = "t14-2qb-std-te0.5-b4-ir1"


def _fallback_selection(bench: int) -> dict[str, Any]:
    composition = {position: 0 for position in POSITIONS}
    order = ("RB", "WR", "QB", "TE", "K", "DST")
    for index in range(bench):
        composition[order[index % len(order)]] += 1
    costs = {
        position: [round(0.25 * depth, 6) for depth in range(bench + 1)]
        for position in POSITIONS
    }
    return {"composition": composition, "soft_marginal_costs": costs}


def _features(row: dict[str, Any]) -> tuple[float, ...]:
    return (
        (int(row["teams"]) - 10) / 4,
        {"1qb": 0.0, "superflex": 0.5, "2qb": 1.0}[row["qb_mode"]],
        {"std": 0.0, "half": 0.5, "ppr": 1.0}[row["scoring"]],
        float(row["te_premium"]) * 2,
        (int(row["bench_slots"]) - 4) / 4,
        float(row["ir_slots"]),
    )


def _distance(a: dict[str, Any], b: dict[str, Any]) -> tuple[float, str]:
    af, bf = _features(a), _features(b)
    # QB mode and bench depth dominate; the remaining dimensions break supported ties.
    weights = (1.0, 4.0, 0.5, 1.0, 4.0, 1.0)
    return sum(w * (x - y) ** 2 for w, x, y in zip(weights, af, bf, strict=True)), str(b["id"])


def build(source_path: Path) -> dict[str, Any]:
    raw = source_path.read_bytes()
    source = json.loads(raw)
    matrix = json.loads(MATRIX.read_text())
    supported_rows = [
        row for row in matrix["rows"]
        if row["teams"] in {10, 12, 14} and row["bench_slots"] in {4, 8}
    ]
    by_id = {row["id"]: row for row in supported_rows}
    source_rows = source["rows"]
    measured_keys = [
        key for key, rec in source_rows.items() if rec["evidence_status"] == "measured"
    ]
    globally_unsupported = source.get("disposition") == "do_not_promote"
    if globally_unsupported:
        if measured_keys or any(
            rec["evidence_status"] != "unsupported" for rec in source_rows.values()
        ):
            raise ValueError("do_not_promote source contains consumer-eligible rows")
        if source.get("interpolation_sources"):
            raise ValueError("do_not_promote source may not seed interpolation")
    elif not measured_keys:
        raise ValueError("source receipt contains no measured rows")

    rows: dict[str, Any] = {}
    for row in supported_rows:
        key = row["id"]
        if globally_unsupported:
            status = "unsupported"
            selection = _fallback_selection(int(row["bench_slots"]))
            provenance = {
                "kind": "unsupported",
                "reason": "authoritative candidate disposition is do_not_promote",
                "nearest_measured_keys": [],
            }
        elif key in source_rows:
            rec = source_rows[key]
            status = rec["evidence_status"]
            if key == BLOCKED and status != "unsupported":
                raise ValueError("blocked slice may not be generated as supported")
            selection = rec["selection"]
            if status == "measured":
                provenance = {
                    "kind": "measured",
                    "source_receipt": source["source_receipt"],
                    "producer_sha": source["producer_sha"],
                    "evaluator_sha": source["evaluator_sha"],
                    "n_pairs": rec["n_pairs"],
                    "seeds": rec["seeds"],
                }
            else:
                provenance = {
                    "kind": "unsupported",
                    "reason": rec["unsupported_reason"],
                    "nearest_measured_keys": sorted(measured_keys, key=lambda k: _distance(row, by_id[k]))[:2],
                }
        else:
            same_budget = [
                candidate for candidate in measured_keys
                if int(by_id[candidate]["bench_slots"]) == int(row["bench_slots"])
            ]
            if not same_budget:
                raise ValueError(f"{key}: no measured source with the same bench budget")
            nearest = min(same_budget, key=lambda candidate: _distance(row, by_id[candidate]))
            selection = source_rows[nearest]["selection"]
            if key == BLOCKED:
                status = "unsupported"
                provenance = {
                    "kind": "unsupported",
                    "reason": "blocked slice has no authoritative clearing evidence",
                    "nearest_measured_keys": [nearest],
                }
            else:
                status = "interpolated"
                provenance = {
                    "kind": "interpolated",
                    "source_receipt": source["source_receipt"],
                    "source_keys": [nearest],
                    "method": "nearest_normalized_league_features_v1",
                }
        composition = {p: int(selection["composition"][p]) for p in POSITIONS}
        costs = {p: [float(x) for x in selection["soft_marginal_costs"][p]] for p in POSITIONS}
        bench = int(row["bench_slots"])
        if sum(composition.values()) != bench:
            raise ValueError(f"{key}: source composition violates bench budget")
        if any(len(costs[p]) != bench + 1 for p in POSITIONS):
            raise ValueError(f"{key}: marginal curve length must be bench_slots + 1")
        rows[key] = {
            "league_config_key": key,
            "evidence_status": status,
            "bench_slots": bench,
            "composition": composition,
            "soft_marginal_costs": costs,
            "provenance": provenance,
        }
    return {
        "schema_version": 2,
        "canonical_source_hash": hashlib.sha256(raw).hexdigest(),
        "canonical_source_receipt": str(source["source_receipt"]),
        "rows": rows,
    }


def render_fixture(artifact: dict[str, Any]) -> str:
    return json.dumps(artifact, indent=2, sort_keys=True) + "\n"


def render_typescript(artifact: dict[str, Any]) -> str:
    # Browser artifact is generated data, so compact JSON keeps it below the frozen 256 KiB gate.
    rows = json.dumps(artifact["rows"], sort_keys=True, separators=(",", ":"))
    return (
        "/** Generated by scripts/generateBenchShapeArtifact.py; do not edit. */\n"
        f"export const BENCH_SHAPE_SCHEMA_VERSION = {artifact['schema_version']} as const;\n"
        "export const BENCH_SHAPE_CANONICAL_SOURCE_HASH = "
        f"{json.dumps(artifact['canonical_source_hash'])} as const;\n"
        "export const BENCH_SHAPE_CANONICAL_SOURCE_RECEIPT = "
        f"{json.dumps(artifact['canonical_source_receipt'])} as const;\n"
        f"export const BENCH_SHAPE_ROWS = {rows} as const;\n"
    )


def _check(path: Path, expected: str) -> bool:
    return path.exists() and path.read_text() == expected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--typescript", type=Path, default=DEFAULT_TS)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    artifact = build(args.source.resolve())
    fixture = render_fixture(artifact)
    typescript = render_typescript(artifact)
    if args.check:
        drift = []
        if not _check(args.fixture, fixture):
            drift.append(str(args.fixture))
        if not _check(args.typescript, typescript):
            drift.append(str(args.typescript))
        if drift:
            raise SystemExit("bench-shape drift: " + ", ".join(drift))
        print("bench-shape parity: exact")
        return 0
    args.fixture.parent.mkdir(parents=True, exist_ok=True)
    args.typescript.parent.mkdir(parents=True, exist_ok=True)
    args.fixture.write_text(fixture)
    args.typescript.write_text(typescript)
    print(f"wrote {args.fixture} and {args.typescript}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
