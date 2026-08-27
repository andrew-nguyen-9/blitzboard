"""Independent C03 checkpoint acceptance probes.

Run with C03_PROD_ROOT naming the production checkpoint worktree.  The test reads
only immutable experiment/artifact records and does not import producer code.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


def _production_root() -> Path:
    value = os.environ.get("C03_PROD_ROOT")
    assert value, "C03_PROD_ROOT must name the C03 checkpoint worktree"
    return Path(value)


def test_failed_candidate_is_not_published_as_supported_guidance() -> None:
    root = _production_root()
    source_v1_path = (
        root / ".orchestrator-v6/experiments/bench-portfolio-c03-source-v1.json"
    )
    results = json.loads(
        (root / ".orchestrator-v6/experiments/bench-portfolio-c03-results-v1.json").read_text()
    )
    fixture = json.loads((root / "fixtures/bench_shape.json").read_text())

    assert results["disposition"] == "do_not_promote"
    assert not any(results["slice_threshold_clear"].values())

    # Source v1 is immutable negative evidence. C03A must preserve it and publish a
    # new disposition receipt for consumer guidance instead of rewriting history.
    assert hashlib.sha256(source_v1_path.read_bytes()).hexdigest() == (
        "01734b796d605788bf6b6815d2484242a4c25a2fe1c0a148f173280d3efc7e2b"
    )
    receipt_name = fixture["canonical_source_receipt"]
    assert receipt_name == (
        ".orchestrator-v6/experiments/bench-portfolio-c03-source-v2.json"
    )
    disposition_path = root / receipt_name
    assert hashlib.sha256(disposition_path.read_bytes()).hexdigest() == fixture[
        "canonical_source_hash"
    ]
    disposition = json.loads(disposition_path.read_text())
    assert disposition["disposition"] == "do_not_promote"
    assert all(
        row["evidence_status"] == "unsupported"
        for row in disposition["rows"].values()
    )
    assert all(row["evidence_status"] == "unsupported" for row in fixture["rows"].values())
