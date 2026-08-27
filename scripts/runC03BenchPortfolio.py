#!/usr/bin/env python3
"""Execute the preregistered C03 measurement once and freeze its source receipts."""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import subprocess
import time
from pathlib import Path

from blitz_engine.testing import matrix
from blitz_engine.value.bench_portfolio import BLOCKED_SLICE, measure_portfolio

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".orchestrator-v6/experiments/bench-portfolio-c03-v2.json"
RESULTS = ROOT / ".orchestrator-v6/experiments/bench-portfolio-c03-results-v1.json"
SOURCE = ROOT / ".orchestrator-v6/experiments/bench-portfolio-c03-source-v1.json"
SOURCE_ID = ".orchestrator-v6/experiments/bench-portfolio-c03-source-v1.json"
EVALUATOR_SHA = "417af276dd4438d8a35f38d08bfc26206044925e"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _clears(metrics: dict, thresholds: dict) -> bool:
    return (
        metrics["started_points"]["lo"] >= thresholds["started_points_ci95_lower_bound"]
        and metrics["h2h"]["lo"] >= thresholds["paired_h2h_ci95_lower_bound"]
        and metrics["playoff"]["lo"] >= thresholds["playoff_proxy_ci95_lower_bound"]
        and metrics["championship"]["lo"] >= thresholds["championship_proxy_ci95_lower_bound"]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="run the write-once authoritative job")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    if not args.execute:
        print(json.dumps({"manifest_sha256": _sha256(MANIFEST), "configs": manifest["mandatory_configs"]}, indent=2))
        return 0
    if RESULTS.exists() or SOURCE.exists():
        raise FileExistsError("authoritative v1 receipt already exists; amendments require v2 paths")
    head = _head()
    if len(head) != 40:
        raise RuntimeError("implementation HEAD is not a full commit SHA")

    started = time.perf_counter()
    rows = []
    for key in manifest["mandatory_configs"]:
        row = matrix.by_id(key)
        measured = measure_portfolio(
            row,
            seasons=manifest["fit_seasons"] + manifest["held_out_seasons"],
            board_seeds=manifest["board_seeds"],
            season_seeds=manifest["season_seeds"],
        )
        if key == BLOCKED_SLICE:
            measured["held_out"] = measure_portfolio(
                row,
                seasons=manifest["held_out_seasons"],
                board_seeds=manifest["board_seeds"],
                season_seeds=manifest["season_seeds"],
            )["metrics"]
        rows.append(measured)
        print(f"measured {key}: {measured['metrics']['started_points']}", flush=True)

    thresholds = json.loads(
        (ROOT / ".orchestrator-v6/experiments/bench-portfolio-c03-v1.json").read_text()
    )["thresholds"]
    deterministic = all(
        row["lineup_illegal_count"] == 0
        and row["bench_budget_violation_count"] == 0
        and row["selection"]["vectors_evaluated"]
        == (126 if row["selection"]["composition"] and sum(row["selection"]["composition"].values()) == 4 else 1287)
        for row in rows
    )
    slice_clear = {row["league_config_key"]: _clears(row["metrics"], thresholds) for row in rows}
    blocked = next(row for row in rows if row["league_config_key"] == BLOCKED_SLICE)
    blocked_clear = slice_clear[BLOCKED_SLICE] and _clears(blocked["held_out"], thresholds)
    disposition = "promotable" if deterministic and all(slice_clear.values()) and blocked_clear else "do_not_promote"
    elapsed = time.perf_counter() - started
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_mib = rss / (1024 * 1024) if rss > 10_000_000 else rss / 1024
    result = {
        "schema_version": 1,
        "experiment_id": "bench-portfolio-c03-v3-execution",
        "manifest_v1_sha256": _sha256(ROOT / ".orchestrator-v6/experiments/bench-portfolio-c03-v1.json"),
        "manifest_v2_sha256": _sha256(MANIFEST),
        "manifest_v3_sha256": _sha256(ROOT / ".orchestrator-v6/experiments/bench-portfolio-c03-v3.json"),
        "producer_sha": head,
        "evaluator_sha": EVALUATOR_SHA,
        "disposition": disposition,
        "deterministic_gates_pass": deterministic,
        "slice_threshold_clear": slice_clear,
        "blocked_slice_clear": blocked_clear,
        "runtime_seconds": round(elapsed, 6),
        "peak_rss_mib": round(rss_mib, 6),
        "rows": rows,
    }
    RESULTS.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

    source_rows = {}
    for row in rows:
        key = row["league_config_key"]
        status = "measured"
        if key == BLOCKED_SLICE and not blocked_clear:
            status = "unsupported"
        source_rows[key] = {
            "league_config_key": key,
            "evidence_status": status,
            "selection": row["selection"],
            "metrics": row["metrics"],
            "n_pairs": row["metrics"]["started_points"]["n"],
            "seeds": sorted(set(manifest["board_seeds"] + manifest["season_seeds"])),
            "unsupported_reason": (
                "known regression slice did not clear its preregistered aggregate and held-out thresholds"
                if status == "unsupported" else None
            ),
        }
    source = {
        "schema_version": 1,
        "source_kind": "authoritative_c03_measurement",
        "source_receipt": SOURCE_ID,
        "results_receipt": str(RESULTS.relative_to(ROOT)),
        "producer_sha": head,
        "evaluator_sha": EVALUATOR_SHA,
        "disposition": disposition,
        "rows": source_rows,
    }
    SOURCE.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    print(f"wrote {RESULTS.relative_to(ROOT)} and {SOURCE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
