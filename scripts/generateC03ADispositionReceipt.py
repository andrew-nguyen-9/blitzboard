#!/usr/bin/env python3
"""Create the append-only C03A consumer-disposition receipt from immutable evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / ".orchestrator-v6/experiments"
SOURCE_V1 = EXPERIMENTS / "bench-portfolio-c03-source-v1.json"
RESULTS_V1 = EXPERIMENTS / "bench-portfolio-c03-results-v1.json"
SOURCE_V2 = EXPERIMENTS / "bench-portfolio-c03-source-v2.json"
SOURCE_V1_SHA256 = "01734b796d605788bf6b6815d2484242a4c25a2fe1c0a148f173280d3efc7e2b"
RESULTS_V1_SHA256 = "3634b803859e63a1620f923b6fdc89a6b6d36ba56698882cbb07e773a9b02e5f"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, object]:
    if _sha256(SOURCE_V1) != SOURCE_V1_SHA256:
        raise ValueError("immutable source-v1 hash mismatch")
    if _sha256(RESULTS_V1) != RESULTS_V1_SHA256:
        raise ValueError("immutable results-v1 hash mismatch")
    source = json.loads(SOURCE_V1.read_text())
    results = json.loads(RESULTS_V1.read_text())
    if results["disposition"] != "do_not_promote":
        raise ValueError("C03A receipt requires the authoritative do_not_promote disposition")
    if any(results["slice_threshold_clear"].values()):
        raise ValueError("C03A receipt cannot suppress a cleared candidate row")
    rows = {
        key: {
            "league_config_key": key,
            "evidence_status": "unsupported",
            "unsupported_reason": "authoritative candidate disposition is do_not_promote",
            "historical_evidence": {
                "receipt": ".orchestrator-v6/experiments/bench-portfolio-c03-source-v1.json",
                "prior_evidence_status": row["evidence_status"],
            },
        }
        for key, row in sorted(source["rows"].items())
    }
    return {
        "schema_version": 2,
        "source_kind": "consumer_disposition",
        "source_receipt": (
            ".orchestrator-v6/experiments/bench-portfolio-c03-source-v2.json"
        ),
        "amends": ".orchestrator-v6/experiments/bench-portfolio-c03-source-v1.json",
        "disposition_amendment": (
            ".orchestrator-v6/experiments/bench-portfolio-c03-v5.json"
        ),
        "results_receipt": (
            ".orchestrator-v6/experiments/bench-portfolio-c03-results-v1.json"
        ),
        "disposition": "do_not_promote",
        "source_v1_sha256": SOURCE_V1_SHA256,
        "results_v1_sha256": RESULTS_V1_SHA256,
        "interpolation_sources": [],
        "rows": rows,
    }


def main() -> int:
    rendered = json.dumps(build(), indent=2, sort_keys=True) + "\n"
    if SOURCE_V2.exists():
        if SOURCE_V2.read_text() != rendered:
            raise SystemExit(f"refusing to overwrite immutable receipt: {SOURCE_V2}")
        print(f"verified immutable receipt {SOURCE_V2}")
        return 0
    SOURCE_V2.write_text(rendered)
    print(f"wrote {SOURCE_V2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
