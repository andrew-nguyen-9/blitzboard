"""Independent C05A fit-verdict integrity probe."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from blitz_engine.promotion.execution import ExecutionError
from blitz_engine.promotion.harness_v4 import load_execution_manifest_v4, write_fit_verdict


def test_fit_verdict_refuses_unvalidated_dummy_receipt(tmp_path: Path) -> None:
    root = Path(os.environ["C05_PROD_ROOT"])
    effective = load_execution_manifest_v4(root)
    dummy = tmp_path / "measure" / "fit" / "dummy.json"
    dummy.parent.mkdir(parents=True)
    dummy.write_text(json.dumps({"kind": "measurement"}))

    with pytest.raises(ExecutionError, match="authoritative|complete|promotion|fit"):
        write_fit_verdict(tmp_path, effective=effective, fit_measure_paths=[dummy])
