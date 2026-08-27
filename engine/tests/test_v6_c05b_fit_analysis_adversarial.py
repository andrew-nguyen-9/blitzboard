"""Independent C05B forged fit-analysis probe."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from blitz_engine.promotion.execution import ExecutionError
from blitz_engine.promotion.gates import report_hash
from blitz_engine.promotion.harness_v4 import (
    effective_v4_manifest_sha256,
    expected_fit_cells,
    load_execution_manifest_v4,
    require_fit_verdict,
    validate_fit_analysis_receipt,
)
from blitz_engine.promotion.manifest import sha256_file


def _forged_fit_analysis(effective: dict, measurement_shas: set[str]) -> dict:
    report = {
        "stage": "fit",
        "authoritative": True,
        "n_pairs": len(expected_fit_cells(effective)) // 2,
        "verdict": "promote",
        "gates": [],
    }
    return {
        "kind": "fit_analysis",
        "report": report,
        "report_sha256": report_hash(report),
        "effective_v4_manifest_sha256": effective_v4_manifest_sha256(effective),
        "pinned_inputs": {
            "measurement_sha256": {
                f"measurement-{i}": sha for i, sha in enumerate(sorted(measurement_shas))
            }
        },
    }


def test_fit_analysis_refuses_self_hashed_caller_authored_promote() -> None:
    root = Path(os.environ["C05_PROD_ROOT"])
    effective = load_execution_manifest_v4(root)
    cell_count = len(expected_fit_cells(effective))
    measurement_shas = {f"{i:064x}" for i in range(cell_count)}
    fit_analysis = _forged_fit_analysis(effective, measurement_shas)

    with pytest.raises(ExecutionError, match="gate|calibration|runtime|promotion"):
        validate_fit_analysis_receipt(
            fit_analysis, effective, measurement_shas=measurement_shas
        )


def test_confirmation_refuses_one_file_forged_pass(tmp_path: Path) -> None:
    root = Path(os.environ["C05_PROD_ROOT"])
    effective = load_execution_manifest_v4(root)
    fake_measurement = tmp_path / "not-a-measurement.json"
    fake_measurement.write_text("{}")
    measurement_sha = sha256_file(fake_measurement)
    fit_analysis = _forged_fit_analysis(effective, {measurement_sha})
    (tmp_path / "fit-verdict.json").write_text(
        json.dumps(
            {
                "verdict": "pass",
                "effective_v4_manifest_sha256": effective_v4_manifest_sha256(effective),
                "fit_receipt_sha256": {str(fake_measurement): measurement_sha},
                "fit_analysis": fit_analysis,
            }
        )
    )

    with pytest.raises(ExecutionError, match="complete|measurement|frame|promotion"):
        require_fit_verdict(tmp_path, effective)
