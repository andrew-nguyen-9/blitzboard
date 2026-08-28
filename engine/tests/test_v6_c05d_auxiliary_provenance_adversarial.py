"""Independent C05D auxiliary-provenance authority probe."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path

from blitz_engine.promotion.harness_v4 import (
    ARM_POLICY_SHAS,
    EXEC_V2_SHA256,
    MEASUREMENT_SHA,
    V4_MANIFEST_SHA256,
    effective_v4_manifest_sha256,
    expected_fit_cells,
    fit_frame_sha256,
    load_execution_manifest_v4,
    validate_auxiliary,
    write_fit_verdict,
)
from blitz_engine.promotion.manifest import sha256_file
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


def test_auxiliary_refuses_caller_fabricated_tooling_provenance() -> None:
    root = Path(os.environ["C05_PROD_ROOT"])
    effective = load_execution_manifest_v4(root)
    frame_sha = "f" * 64
    forged_provenance = {
        "tooling_head": "0" * 40,
        "tooling_tree_clean": True,
        "clean_definition": "caller assertion",
        "execution_module_sha256": "0" * 64,
        "effective_manifest_sha256": "0" * 64,
    }
    common = {
        "effective_v4_manifest_sha256": effective_v4_manifest_sha256(effective),
        "fit_frame_sha256": frame_sha,
        "produced_by_tooling": forged_provenance,
    }
    deterministic = {
        **common,
        "kind": "deterministic_receipt",
        "invariants_pass": True,
        "leakage_detected": False,
        "nondeterminism_detected": False,
    }
    runtime = {
        **common,
        "kind": "runtime_receipt",
        "wall_clock_hours": 1.0,
        "peak_rss_gib": 1.0,
    }

    validated = validate_auxiliary(
        effective,
        frame_sha,
        deterministic=deterministic,
        calibration=None,
        runtime=runtime,
    )
    assert validated["deterministic"] is None
    assert validated["runtime"] is None


def test_fit_verdict_refuses_caller_added_calibration_authority(tmp_path: Path) -> None:
    root = Path(os.environ["C05_PROD_ROOT"])
    effective = deepcopy(load_execution_manifest_v4(root))
    effective["calibration_gates"]["accepted_report_sha256"] = "a" * 64
    paths = []
    for index, cell in enumerate(sorted(expected_fit_cells(effective))):
        path = tmp_path / "measure" / "fit" / f"{index}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_measurement(effective, *cell)))
        paths.append(path)

    pins = {str(path): sha256_file(path) for path in paths}
    frame_sha = fit_frame_sha256(pins)
    common = {
        "effective_v4_manifest_sha256": effective_v4_manifest_sha256(effective),
        "fit_frame_sha256": frame_sha,
        "produced_by_tooling": {"tooling_head": "fabricated"},
    }
    auxiliary = {
        "deterministic": {
            **common,
            "kind": "deterministic_receipt",
            "invariants_pass": True,
            "leakage_detected": False,
            "nondeterminism_detected": False,
        },
        "runtime": {
            **common,
            "kind": "runtime_receipt",
            "wall_clock_hours": 1.0,
            "peak_rss_gib": 1.0,
        },
        "calibration": {
            **common,
            "kind": "calibration_receipt",
            "accepted": True,
            "accepted_report_sha256": "a" * 64,
            "source_manifest_sha256": effective["calibration_gates"]["source_manifest_sha256"],
            "source_amendment_sha256": effective["calibration_gates"]["source_amendment_sha256"],
            "report": {
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
            },
        },
    }
    aux_paths = {}
    for name, doc in auxiliary.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(doc))
        aux_paths[name] = path

    verdict_path = write_fit_verdict(
        tmp_path,
        effective=effective,
        measurement_paths=paths,
        deterministic_receipt_path=aux_paths["deterministic"],
        calibration_report_path=aux_paths["calibration"],
        runtime_receipt_path=aux_paths["runtime"],
    )
    assert json.loads(verdict_path.read_text())["verdict"] != "pass"
