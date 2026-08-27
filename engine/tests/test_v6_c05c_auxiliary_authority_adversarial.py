"""Independent C05C auxiliary-evidence authority probe."""

from __future__ import annotations

import json
import os
from pathlib import Path

from blitz_engine.promotion.harness_v4 import (
    ARM_POLICY_SHAS,
    EXEC_V2_SHA256,
    MEASUREMENT_SHA,
    V4_MANIFEST_SHA256,
    effective_v4_manifest_sha256,
    expected_fit_cells,
    load_execution_manifest_v4,
    write_fit_verdict,
)
from blitz_engine.promotion.runner import derive_eval_seed


def _measurement(effective: dict, arm: str, year: int, league: str, seed: int) -> dict:
    candidate = arm == "v6_candidate"
    return {
        "kind": "measurement",
        "authoritative": True,
        "stage": "fit",
        "measured_by_sha": MEASUREMENT_SHA,
        "draft_receipt_sha256": "d" * 64,
        "n_seasons": 8,
        "manifest_sha256": V4_MANIFEST_SHA256,
        "exec_addendum_sha256": EXEC_V2_SHA256,
        "effective_v4_manifest_sha256": effective_v4_manifest_sha256(effective),
        "arm_run": {
            "arm": arm,
            "policy_sha": ARM_POLICY_SHAS[arm],
            "year": year,
            "league_id": league,
            "base_seed": seed,
            "eval_seed": derive_eval_seed(seed, year, league),
            "board_hash": "b" * 64,
            "seat_policy": ["static_proxy"],
            "per_season": [[1.0 if candidate else 0.0]],
            "h2h_win_rate": [0.6 if candidate else 0.5],
            "playoff_proxy": [0.6 if candidate else 0.5],
            "championship_proxy": [0.6 if candidate else 0.5],
            "synthetic": False,
        },
    }


def test_fit_verdict_never_promotes_fabricated_auxiliary_evidence(tmp_path: Path) -> None:
    root = Path(os.environ["C05_PROD_ROOT"])
    effective = load_execution_manifest_v4(root)
    measurement_paths = []
    for index, cell in enumerate(sorted(expected_fit_cells(effective))):
        path = tmp_path / "measure" / "fit" / f"{index}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_measurement(effective, *cell)))
        measurement_paths.append(path)

    deterministic = tmp_path / "deterministic.json"
    deterministic.write_text(
        json.dumps(
            {
                "invariants_pass": True,
                "leakage_detected": False,
                "nondeterminism_detected": False,
            }
        )
    )
    calibration = tmp_path / "calibration.json"
    calibration.write_text(
        json.dumps(
            {
                "executed": True,
                "benchmarks": [
                    {
                        "id": "fabricated",
                        "snapshot_sha256": "fabricated",
                        "retrieval_utc": "fabricated",
                        "spearman_delta": 1.0,
                        "weighted_rank_error_delta": -1.0,
                        "unmatched_top_100_rate": 0.0,
                    }
                ],
                "deterministic_unit_failures": 0,
                "cohort_material_regressions": 0,
                "top_n_recall_regressions": 0,
                "outlier_and_decomposition_reported": True,
                "missing_data_degrades_explicitly": True,
                "held_out_confirmed": True,
                "season_evaluator_no_regression": True,
            }
        )
    )
    runtime = tmp_path / "runtime.json"
    runtime.write_text("{}")

    verdict_path = write_fit_verdict(
        tmp_path,
        effective=effective,
        measurement_paths=measurement_paths,
        deterministic_receipt_path=deterministic,
        calibration_report_path=calibration,
        runtime_receipt_path=runtime,
    )
    assert json.loads(verdict_path.read_text())["verdict"] != "pass"
