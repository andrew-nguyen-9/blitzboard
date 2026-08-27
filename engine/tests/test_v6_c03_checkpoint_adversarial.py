"""Independent C03 checkpoint acceptance probes.

Run with C03_PROD_ROOT naming the production checkpoint worktree.  The test reads
only immutable experiment/artifact records and does not import producer code.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def _production_root() -> Path:
    value = os.environ.get("C03_PROD_ROOT")
    assert value, "C03_PROD_ROOT must name the C03 checkpoint worktree"
    return Path(value)


def test_failed_candidate_is_not_published_as_supported_guidance() -> None:
    root = _production_root()
    results = json.loads(
        (root / ".orchestrator-v6/experiments/bench-portfolio-c03-results-v1.json").read_text()
    )
    source = json.loads(
        (root / ".orchestrator-v6/experiments/bench-portfolio-c03-source-v1.json").read_text()
    )
    fixture = json.loads((root / "fixtures/bench_shape.json").read_text())

    assert results["disposition"] == "do_not_promote"
    assert not any(results["slice_threshold_clear"].values())

    # Frozen v1/v2 failure semantics require preserving accepted C02C behavior.
    # A failed candidate may remain in immutable result evidence, but it may not
    # become supported canonical guidance consumed by later production work.
    assert source["disposition"] == "do_not_promote"
    assert all(row["evidence_status"] == "unsupported" for row in source["rows"].values())
    assert all(row["evidence_status"] == "unsupported" for row in fixture["rows"].values())

