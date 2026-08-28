"""NON-AUTHORITATIVE dry runs of the C05 promotion machinery.

Two validation modes, both explicitly labelled so no output can be mistaken for the authoritative
v5-vs-v6 experiment (which is blocked until C02/C03/C04 pass and the candidate SHA is frozen):

* ``synthetic`` — fabricated matched pairs over every mandatory high-risk slice, one fit stage and
  one held-out confirm stage, proving the whole report path end to end.
* ``null`` — the REAL evaluator at this checkout runs BOTH arms with identical policy code and
  identical seeds on a small subset of rows. Common random numbers make every paired delta exactly
  zero, so the run must come back ``preserve_v5`` (zero evidence); it also proves determinism by
  executing one arm twice and comparing byte-for-byte.

Usage (from ``engine/``, worktree-safe form):

    PYTHONPATH="$PWD" <venv>/python -m blitz_engine.promotion.dryrun <out_dir>

Protocol deviations, dry run only: ``n_seasons`` is reduced and only a subset of the 216 mandatory
rows is evaluated; both deviations are recorded in the receipt.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from blitz_engine.promotion.gates import (
    NON_AUTHORITATIVE_LABEL,
    canonical_report_json,
    evaluate_promotion,
    final_verdict,
    report_hash,
)
from blitz_engine.promotion.manifest import load_manifest, verify_board_corpus
from blitz_engine.promotion.runner import (
    ArmRun,
    HeldOutGuard,
    assert_deterministic,
    derive_eval_seed,
    run_arm,
)

#: Small but pointed null-run subset: the blocked slice's family plus a plain small league.
NULL_ROWS = ("t14-2qb-std-te0.5-b4-ir1", "t10-1qb-std-te0.0-b4-ir0")
NULL_N_SEASONS = 2


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _synthetic_pair(
    lid: str, year: int, base_seed: int, delta: float, i: int
) -> tuple[ArmRun, ArmRun]:
    rng = np.random.default_rng(1000 + i)
    ctrl = rng.normal(1000.0, 20.0, size=(3, 4))
    cand = ctrl + delta + rng.normal(0.0, 0.5, size=(3, 4))
    common = dict(
        year=year, league_id=lid, base_seed=base_seed,
        eval_seed=derive_eval_seed(base_seed, year, lid),
        board_hash=f"synthetic-board-{lid}", synthetic=True,
        seat_policy=("static_proxy", "vorp_adp", "engine_msv", "static_proxy"),
    )
    mk = lambda arm, sha, m, h2h, po: ArmRun(  # noqa: E731
        arm=arm, policy_sha=sha,
        per_season=tuple(tuple(map(float, r)) for r in m),
        h2h_win_rate=(h2h,) * 4, playoff_proxy=(po,) * 4, championship_proxy=(po,) * 4,
        **common,
    )
    return mk("v6_candidate", "synthetic-cand", cand, 0.51, 0.31), mk(
        "v5_shipped", "synthetic-ctrl", ctrl, 0.50, 0.30
    )


def _passing_receipts() -> dict[str, Any]:
    bench = {
        "id": "synthetic-benchmark", "snapshot_sha256": "00" * 32,
        "retrieval_utc": "2026-08-26T00:00:00Z", "spearman_delta": 0.01,
        "weighted_rank_error_delta": -0.05, "unmatched_top_100_rate": 0.0,
    }
    return dict(
        deterministic_receipt={
            "invariants_pass": True, "leakage_detected": False, "nondeterminism_detected": False,
        },
        runtime_receipt={"wall_clock_hours": 0.01, "peak_rss_gib": 0.5},
        calibration_report={
            "executed": True, "benchmarks": [bench], "deterministic_unit_failures": 0,
            "cohort_material_regressions": 0, "top_n_recall_regressions": 0,
            "outlier_and_decomposition_reported": True, "missing_data_degrades_explicitly": True,
            "held_out_confirmed": True, "season_evaluator_no_regression": True,
        },
    )


def synthetic_dryrun(manifest: dict[str, Any]) -> dict[str, Any]:
    """Fit + confirm over all mandatory slices with fabricated positive deltas."""
    seeds = manifest["seed_derivation"]["base_seeds"]
    fit_pairs = [
        _synthetic_pair(lid, year, seeds[0], delta=5.0, i=i)
        for i, lid in enumerate(manifest["mandatory_high_risk_slices"])
        for year in manifest["seasons"]
    ]
    confirm_pairs = [
        _synthetic_pair(lid, manifest["held_out_seasons"][0], seeds[0], delta=5.0, i=500 + i)
        for i, lid in enumerate(manifest["mandatory_high_risk_slices"])
    ]
    rec = _passing_receipts()
    fit = evaluate_promotion(manifest, fit_pairs, stage="fit", **rec)
    confirm = evaluate_promotion(manifest, confirm_pairs, stage="confirm", **rec)
    return {
        "mode": "synthetic",
        "fit_verdict": fit["verdict"],
        "confirm_verdict": confirm["verdict"],
        "final_verdict": final_verdict(fit, confirm),
        "fit_report_sha256": report_hash(fit),
        "confirm_report_sha256": report_hash(confirm),
        "byte_stable": canonical_report_json(fit)
        == canonical_report_json(evaluate_promotion(manifest, fit_pairs, stage="fit", **rec)),
        "fit_report": json.loads(canonical_report_json(fit)),
        "confirm_report": json.loads(canonical_report_json(confirm)),
    }


def null_dryrun(manifest: dict[str, Any]) -> dict[str, Any]:
    """Real evaluator, both arms identical code + seeds → every delta must be exactly zero."""
    from blitz_engine.testing import matrix

    year = int(manifest["seasons"][0])
    base_seed = int(manifest["seed_derivation"]["base_seeds"][0])
    guard = HeldOutGuard(list(manifest["seasons"]), list(manifest["held_out_seasons"]))
    rows = {r["id"]: r for r in matrix.all()}

    t0 = time.perf_counter()
    pairs: list[tuple[ArmRun, ArmRun]] = []
    determinism_checked = False
    for lid in NULL_ROWS:
        row = rows[lid]

        def one(arm: str, row: dict[str, Any] = row) -> ArmRun:
            return run_arm(
                arm, "b81541c226dd5aeeacbe9ed79df927853a4b8954", year, row, base_seed,
                n_seasons=NULL_N_SEASONS, guard=guard, stage="fit",
            )

        cand = one("null_candidate")
        if not determinism_checked:  # prove the evaluator is byte-stable on one slice
            assert_deterministic(lambda: one("null_candidate"))
            determinism_checked = True
        ctrl = one("null_control")
        pairs.append((cand, ctrl))

    rec = _passing_receipts()
    rec["deterministic_receipt"]["nondeterminism_detected"] = not determinism_checked
    rec["runtime_receipt"] = {
        "wall_clock_hours": (time.perf_counter() - t0) / 3600.0,
        "peak_rss_gib": max(p[0].max_rss_mb for p in pairs) / 1024.0,
    }
    report = evaluate_promotion(manifest, pairs, stage="fit", **rec)
    deltas_all_zero = all(
        np.array_equal(np.asarray(c.per_season), np.asarray(k.per_season)) for c, k in pairs
    )
    return {
        "mode": "null (real evaluator, identical arms, common random numbers)",
        "rows": list(NULL_ROWS),
        "year": year,
        "base_seed": base_seed,
        "n_seasons_deviation": NULL_N_SEASONS,
        "board_hashes": {p[0].league_id: p[0].board_hash for p in pairs},
        "determinism_check": "passed (one arm executed twice, byte-identical)",
        "crn_deltas_all_zero": deltas_all_zero,
        "verdict": report["verdict"],
        "expected_verdict": "preserve_v5",
        "runtime_receipt": rec["runtime_receipt"],
        "report_sha256": report_hash(report),
        "report": json.loads(canonical_report_json(report)),
    }


def main(out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(
        _repo_root() / ".orchestrator-v6" / "experiments" / "promotion-v3.json"
    )
    mismatches = verify_board_corpus(manifest, _repo_root())
    receipt = {
        "label": NON_AUTHORITATIVE_LABEL,
        "authoritative": False,
        "manifest": "promotion-v3.json",
        "manifest_sha256": manifest["_manifest_sha256"],
        "board_corpus_verified": mismatches == [],
        "board_corpus_mismatches": mismatches,
        "synthetic": synthetic_dryrun(manifest),
        "null": null_dryrun(manifest),
    }
    path = out / "C05-dryrun-receipt.json"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    ok = (
        receipt["board_corpus_verified"]
        and receipt["synthetic"]["final_verdict"] == "promote"
        and receipt["synthetic"]["byte_stable"]
        and receipt["null"]["verdict"] == "preserve_v5"
        and receipt["null"]["crn_deltas_all_zero"]
    )
    print(f"{path}: {'OK' if ok else 'UNEXPECTED'} — see receipt")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
