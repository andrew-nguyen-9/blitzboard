"""Independent C05 second-freeze provenance probe."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def test_rehearsal_receipt_names_its_actual_tooling_commit() -> None:
    root = Path(os.environ["C05_PROD_ROOT"])
    receipt_path = root / (
        ".orchestrator-v6/prep/c05-rehearsal/fit/"
        "v6_candidate-2021-t10-1qb-std-te0.0-b4-ir0-2026082601.json"
    )
    receipt = json.loads(receipt_path.read_text())
    tooling_sha = receipt["produced_by_tooling_head"]

    # A receipt cannot claim a tooling commit that does not contain the harness that made it.
    found = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{tooling_sha}:engine/blitz_engine/promotion/execution.py"],
        capture_output=True,
        text=True,
    )
    assert found.returncode == 0, (
        f"receipt claims tooling SHA {tooling_sha}, but that commit has no execution harness"
    )
