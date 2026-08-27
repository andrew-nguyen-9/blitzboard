"""Independent promotion-v4 freeze probes."""

from __future__ import annotations

import json
import os
from pathlib import Path


def test_exec_freeze_tooling_identity_matches_rehearsal_receipts() -> None:
    root = Path(os.environ["C05_PROD_ROOT"])
    experiments = root / ".orchestrator-v6" / "experiments"
    addendum = json.loads((experiments / "promotion-v4-exec-v1.json").read_text())
    frozen_head = addendum["tooling_provenance_at_freeze"]["tooling_head"]

    fit = root / ".orchestrator-v6" / "prep" / "c05-rehearsal" / "fit"
    receipt_heads = {
        json.loads(path.read_text())["produced_by_tooling"]["tooling_head"]
        for path in fit.glob("*.json")
    }
    assert receipt_heads == {frozen_head}
