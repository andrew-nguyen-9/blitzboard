"""Independent promotion-v4 exec-v2 freeze acceptance probe."""

from __future__ import annotations

import json
import os
from pathlib import Path


def test_exec_v2_reconciles_rehearsal_tooling_identity() -> None:
    root = Path(os.environ["C05_PROD_ROOT"])
    addendum = json.loads(
        (root / ".orchestrator-v6/experiments/promotion-v4-exec-v2.json").read_text()
    )
    expected = addendum["blocker_1_tooling_identity"]["rehearsal_tooling_head"]
    fit = root / ".orchestrator-v6/prep/c05-rehearsal/fit"
    actual = {
        json.loads(path.read_text())["produced_by_tooling"]["tooling_head"]
        for path in fit.glob("*.json")
    }
    assert actual == {expected}
