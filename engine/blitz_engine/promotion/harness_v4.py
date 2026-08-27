"""The v4 two-stage draft/measurement harness — implements EXACTLY promotion-v4 + exec-v2.

Authorized by the exec-v2 freeze PASS (reviewer commit `5a25d98…`): bounded implementation only.
The frozen protocol it executes:

* **Stage 1 (draft)** runs inside EACH arm's frozen checkout (import-resolution pinned and
  hard-asserted, exactly like `execution.py`): build the frozen board for `(year, league_id)`,
  run that checkout's own `draft_league` under the derived eval seed, and emit a DRAFT RECEIPT —
  per-seat `player_id` rosters plus every pairing key. No outcome metric exists at this stage.
* **Stage 2 (measure)** runs ONLY inside the frozen measurement checkout (HEAD must equal the
  measurement SHA and all seven frozen file hashes must verify): load a draft receipt, re-derive
  the board, validate it (exec-v2 rules: exact per-seat roster size, board membership, global
  drafted-id uniqueness, pairing keys, eval-seed formula — the undrafted board complement is the
  shared initial free-agent pool, which `evaluate_rosters` constructs by definition), then replay
  the rosters through the common evaluator to produce a MEASUREMENT RECEIPT carrying the ArmRun.

Both stages embed mechanical tooling provenance, land under write-once stage-separated paths
(`draft/fit`, `draft/confirm`, `measure/fit`, `measure/confirm`), and pass the `HeldOutGuard`
before any work. Every refusal is an `ExecutionError`/`ManifestError`/`HeldOutLeakError` — the
harness aborts, it never degrades. Nothing here runs the authoritative experiment; `rehearse_v4`
is a tiny two-checkout rehearsal whose receipts are labelled non-authoritative.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

from blitz_engine.promotion.execution import (
    BASELINE_SHA,
    CANDIDATE_SHA,
    MANIFEST_SHA256,
    ExecutionError,
    checkout_head,
    load_execution_manifest,
    tooling_provenance,
    verify_arm_checkout,
)
from blitz_engine.promotion.manifest import ManifestError, sha256_file
from blitz_engine.promotion.runner import ArmRun, HeldOutGuard, derive_eval_seed

__all__ = [
    "ARM_POLICY_SHAS",
    "EXEC_V2_SHA256",
    "MEASUREMENT_SHA",
    "V4_MANIFEST_SHA256",
    "assert_complete_fit_frame",
    "draft_arm",
    "effective_v4_manifest_sha256",
    "expected_fit_cells",
    "validate_fit_analysis_receipt",
    "validate_fit_measurement_receipt",
    "load_execution_manifest_v4",
    "mandatory_league_ids",
    "measure_arm",
    "recompute_seat_policy",
    "rehearse_v4",
    "require_fit_verdict",
    "validate_authoritative_draft_receipt",
    "validate_draft_receipt",
    "write_fit_verdict",
    "verify_measurement_checkout",
]

#: Frozen pins for the v4 chain (immutability checks, not configuration).
V4_MANIFEST_SHA256 = "47af290506a2aa9e66add39b62125c12341927814d3cbc660426cc767e32569a"
EXEC_V1_V4_SHA256 = "41e33538c87cadacde3165ea05c7ceb6f42004bda8f992864c9cfa826220c208"
EXEC_V2_SHA256 = "7e88b09087687da3cf328f4fe027df181cf2b82975e605d73519b9ce4ae16480"
MEASUREMENT_SHA = CANDIDATE_SHA  # exec-v2: measurement lives in the accepted combined head

#: Frozen arm-name -> policy SHA identity (exec-v2 `arms`). A receipt may not claim an arm label
#: while carrying another arm's policy code (reviewer blocker 3).
ARM_POLICY_SHAS = {"v5_shipped": BASELINE_SHA, "v6_candidate": CANDIDATE_SHA}


def load_execution_manifest_v4(root: str | Path) -> dict[str, Any]:
    """Hash-load the whole frozen chain (v3, v3-exec-v1, v4, v4-exec-v1, v4-exec-v2) and build
    the effective v4 execution manifest: the v3 effective terms plus the v4 measurement overlay.
    """
    root = Path(root)
    exp = root / ".orchestrator-v6" / "experiments"
    pins = {
        "promotion-v4.json": V4_MANIFEST_SHA256,
        "promotion-v4-exec-v1.json": EXEC_V1_V4_SHA256,
        "promotion-v4-exec-v2.json": EXEC_V2_SHA256,
    }
    for name, want in pins.items():
        p = exp / name
        if not p.is_file():
            raise ManifestError(f"missing frozen file: {p}")
        if (got := sha256_file(p)) != want:
            raise ManifestError(f"{name}: sha256 {got} != frozen {want}")
    v4 = json.loads((exp / "promotion-v4.json").read_text())
    exec_v2 = json.loads((exp / "promotion-v4-exec-v2.json").read_text())
    if v4["supersedes_sha256"] != MANIFEST_SHA256:
        raise ManifestError("promotion-v4 does not supersede the frozen v3 hash")
    if exec_v2["manifest_sha256"] != V4_MANIFEST_SHA256:
        raise ManifestError("exec-v2 references a different v4 manifest hash")
    if exec_v2["supersedes_sha256"] != EXEC_V1_V4_SHA256:
        raise ManifestError("exec-v2 does not supersede the frozen exec-v1 hash")
    sha = exec_v2["arms"]["candidate"]["combined_candidate_sha"]
    if sha != CANDIDATE_SHA or exec_v2["measurement"]["sha"] != MEASUREMENT_SHA:
        raise ManifestError("exec-v2 arm/measurement SHAs do not match the frozen identities")
    if float(exec_v2["metric_binding"]["waiver_cost"]) != 0.0:
        raise ManifestError("metric binding must be waiver_cost = 0.0")

    # v3 terms + candidate SHA + waiver_cost, themselves hash-checked by the v3 loader:
    effective = load_execution_manifest(root)
    effective["_v4"] = {
        "manifest_sha256": V4_MANIFEST_SHA256,
        "exec_v2_sha256": EXEC_V2_SHA256,
        "measurement_sha": MEASUREMENT_SHA,
        "measurement_file_hashes": dict(v4["measurement_evaluator"]["file_hashes"]),
        "pairing_keys": list(v4["pairing_keys"]),
        "roster_rules": list(exec_v2["blocker_2_roster_validation"]["rules"]),
        "arm_shas": {
            a["name"]: a.get("policy_sha") or a.get("combined_candidate_sha")
            for a in exec_v2["arms"].values()
        },
    }
    return effective


def verify_measurement_checkout(checkout: str | Path, effective: dict[str, Any]) -> str:
    """HEAD must equal the frozen measurement SHA and all seven file hashes must verify."""
    head = checkout_head(checkout)
    if head != effective["_v4"]["measurement_sha"]:
        raise ExecutionError(
            f"measurement checkout HEAD {head} != frozen measurement SHA "
            f"{effective['_v4']['measurement_sha']}"
        )
    for rel, want in effective["_v4"]["measurement_file_hashes"].items():
        p = Path(checkout) / rel
        if not p.is_file():
            raise ExecutionError(f"measurement file missing: {rel}")
        if (got := sha256_file(p)) != want:
            raise ExecutionError(f"measurement file drift: {rel} sha256 {got} != frozen {want}")
    return head


def expected_roster_size(row: dict[str, Any]) -> int:
    return sum(int(n) for n in row["starting_slots"].values()) + int(row["bench_slots"])


def validate_draft_receipt(
    receipt: dict[str, Any], row: dict[str, Any], board_ids: frozenset[str]
) -> None:
    """The exec-v2 roster rules plus pairing-key sanity — every violation aborts (BLOCK)."""
    if receipt.get("kind") != "draft":
        raise ExecutionError("not a draft receipt")
    want_sha = ARM_POLICY_SHAS.get(receipt.get("arm"))
    if want_sha is None:
        raise ExecutionError(f"draft receipt arm {receipt.get('arm')!r} is not a frozen arm name")
    if receipt.get("policy_sha") != want_sha:
        raise ExecutionError(
            f"arm {receipt['arm']!r} bound to policy_sha {receipt.get('policy_sha')!r} "
            f"does not match its frozen policy identity {want_sha}"
        )
    teams = int(row["teams"])
    rosters = receipt["rosters"]
    if len(rosters) != teams or len(receipt["seat_policy"]) != teams:
        raise ExecutionError(f"seat count mismatch: {len(rosters)} rosters for {teams} teams")
    size = expected_roster_size(row)
    for seat, roster in enumerate(rosters):
        if len(roster) != size:
            raise ExecutionError(
                f"seat {seat} roster has {len(roster)} players; expected exactly {size}"
            )
    drafted = [pid for roster in rosters for pid in roster]
    if len(set(drafted)) != len(drafted):
        raise ExecutionError("drafted player ids are not globally unique across rosters")
    off_board = sorted(set(drafted) - board_ids)
    if off_board:
        raise ExecutionError(f"drafted ids not on the hashed board: {off_board[:5]}")
    want_seed = derive_eval_seed(receipt["base_seed"], receipt["year"], receipt["league_id"])
    if receipt["eval_seed"] != want_seed:
        raise ExecutionError("draft receipt eval_seed does not follow the frozen derivation")
    if receipt["league_id"] != str(row["id"]):
        raise ExecutionError("draft receipt league_id does not match the league row")
    # The undrafted board complement IS the shared initial free-agent pool; nothing to store —
    # evaluate_rosters constructs exactly board-minus-drafted, which the measurement stage uses.


def mandatory_league_ids(effective: dict[str, Any]) -> frozenset[str]:
    """The frozen 216-mandatory league-id set, derived from the matrix and tied to the manifest's
    frozen count (teams {10,12,14} x bench {4,8}); a drift in either refuses."""
    from blitz_engine.testing import matrix

    ids = frozenset(
        r["id"] for r in matrix.all()
        if int(r["teams"]) in (10, 12, 14) and int(r["bench_slots"]) in (4, 8)
    )
    want = int(effective["league_configurations"]["mandatory_league_id_count"])
    if len(ids) != want:
        raise ExecutionError(f"derived {len(ids)} mandatory league ids != frozen {want}")
    return ids


def _check_authoritative_frame(
    effective: dict[str, Any], *, year: int, league_id: str, base_seed: int, arm: str,
    expected_sha: str, stage: str, n_seasons: int | None = None,
) -> None:
    """Every authoritative parameter must come from the frozen effective manifest; a caller
    override of any of them is refused (reviewer blocker 2)."""
    if int(base_seed) not in [int(s) for s in effective["seed_derivation"]["base_seeds"]]:
        raise ExecutionError(f"authoritative base_seed {base_seed} is not a frozen base seed")
    allowed_years = (
        set(effective["seasons"]) if stage == "fit" else set(effective["held_out_seasons"])
    )
    if int(year) not in allowed_years:
        raise ExecutionError(f"authoritative year {year} is not frozen for stage {stage!r}")
    if str(league_id) not in mandatory_league_ids(effective):
        raise ExecutionError(
            f"authoritative league_id {league_id} is not in the frozen 216-mandatory set"
        )
    arm_shas = effective["_v4"]["arm_shas"]
    if arm not in arm_shas:
        raise ExecutionError(f"authoritative arm {arm!r} is not a frozen arm name")
    if expected_sha != arm_shas[arm]:
        raise ExecutionError(
            f"authoritative arm {arm!r} SHA {expected_sha} != frozen {arm_shas[arm]}"
        )
    if n_seasons is not None and int(n_seasons) != int(effective["evaluator"]["n_seasons"]):
        raise ExecutionError(
            f"authoritative n_seasons {n_seasons} != frozen {effective['evaluator']['n_seasons']}"
        )


def recompute_seat_policy(eval_seed: int, teams: int, effective: dict[str, Any]) -> list[str]:
    """Reproduce the frozen deterministic seat-policy assignment exactly as `draft_league` does:
    round-robin the default policy mix across seats, then shuffle under `default_rng(eval_seed +
    draft_stream)`. The draft stream offset is read from the frozen manifest."""
    from blitz_engine.simulation.season_eval import DEFAULT_POLICY_MIX

    draft_stream = int(effective["seed_derivation"]["stream_offsets"]["draft"])
    rng = np.random.default_rng(int(eval_seed) + draft_stream)
    seats = [DEFAULT_POLICY_MIX[i % len(DEFAULT_POLICY_MIX)] for i in range(int(teams))]
    rng.shuffle(seats)
    return seats


def effective_v4_manifest_sha256(effective: dict[str, Any]) -> str:
    """Deterministic hash of the effective v4 execution manifest (frozen chain + overlays)."""
    return hashlib.sha256(
        json.dumps(effective, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _require_v4_binding(receipt: dict[str, Any], effective: dict[str, Any]) -> None:
    """Every draft receipt must bind itself to the v4 manifest, the exec-v2 addendum, and the
    deterministic effective-v4-manifest hash (reviewer blocker 5)."""
    if receipt.get("manifest_sha256") != V4_MANIFEST_SHA256:
        raise ExecutionError("draft receipt is not bound to the promotion-v4 manifest hash")
    if receipt.get("exec_addendum_sha256") != EXEC_V2_SHA256:
        raise ExecutionError("draft receipt is not bound to the exec-v2 addendum hash")
    if receipt.get("effective_v4_manifest_sha256") != effective_v4_manifest_sha256(effective):
        raise ExecutionError("draft receipt effective-v4-manifest hash mismatch")


def validate_authoritative_draft_receipt(
    receipt: dict[str, Any], row: dict[str, Any], board_ids: frozenset[str],
    effective: dict[str, Any], *, stage: str,
) -> None:
    """The strict authoritative validator: shape + arm<->policy identity, the frozen-manifest
    frame, the recomputed deterministic seat-policy, and the v4/exec-v2/effective-v4 binding.
    Every violation aborts (BLOCK)."""
    validate_draft_receipt(receipt, row, board_ids)
    _check_authoritative_frame(
        effective, year=receipt["year"], league_id=receipt["league_id"],
        base_seed=receipt["base_seed"], arm=receipt["arm"],
        expected_sha=receipt["policy_sha"], stage=stage,
    )
    want = recompute_seat_policy(receipt["eval_seed"], int(row["teams"]), effective)
    if list(receipt["seat_policy"]) != want:
        raise ExecutionError(
            "draft receipt seat_policy does not match the deterministic assignment"
        )
    _require_v4_binding(receipt, effective)


#: Manifest pairing keys carried per measurement (the seat key is per-seat, implicit in per_season).
_RECEIPT_PAIRING_KEYS = ("year", "league_id", "base_seed", "eval_seed", "board_hash", "seat_policy")


def expected_fit_cells(effective: dict[str, Any]) -> set[tuple[str, int, str, int]]:
    """The complete authoritative fit frame: every (arm, fit-year, mandatory-league, base-seed).
    Two frozen arms x fit years {2021, 2024} x 216 mandatory leagues x 4 base seeds = 3456 cells."""
    arms = tuple(effective["_v4"]["arm_shas"])
    years = tuple(int(y) for y in effective["seasons"])
    leagues = tuple(sorted(mandatory_league_ids(effective)))
    seeds = tuple(int(s) for s in effective["seed_derivation"]["base_seeds"])
    return {
        (arm, year, lid, seed)
        for arm in arms for year in years for lid in leagues for seed in seeds
    }


def _measurement_cell_key(doc: dict[str, Any]) -> tuple[str, int, str, int]:
    ar = doc["arm_run"]
    return (ar["arm"], int(ar["year"]), str(ar["league_id"]), int(ar["base_seed"]))


def validate_fit_measurement_receipt(
    doc: dict[str, Any], effective: dict[str, Any]
) -> tuple[str, int, str, int]:
    """Validate one authoritative fit measurement receipt against the frozen protocol; returns its
    (arm, year, league_id, base_seed) cell key. Any violation aborts (BLOCK) — never a soft pass."""
    if doc.get("kind") != "measurement":
        raise ExecutionError("fit frame: not a measurement receipt")
    if doc.get("authoritative") is not True:
        raise ExecutionError("fit frame: non-authoritative receipt in an authoritative fit")
    if doc.get("stage") != "fit":
        raise ExecutionError(f"fit frame: receipt stage {doc.get('stage')!r} is not 'fit'")
    ar = doc.get("arm_run") or {}
    arm, year, lid, base_seed = _measurement_cell_key(doc)
    if arm not in ARM_POLICY_SHAS:
        raise ExecutionError(f"fit frame: receipt arm {arm!r} is not a frozen arm name")
    if ar.get("policy_sha") != ARM_POLICY_SHAS[arm]:
        raise ExecutionError(f"fit frame: arm {arm!r} policy_sha != its frozen identity")
    if doc.get("measured_by_sha") != MEASUREMENT_SHA:
        raise ExecutionError("fit frame: measured_by_sha is not the frozen measurement SHA")
    if doc.get("manifest_sha256") != V4_MANIFEST_SHA256:
        raise ExecutionError("fit frame: receipt not bound to the promotion-v4 manifest hash")
    if doc.get("exec_addendum_sha256") != EXEC_V2_SHA256:
        raise ExecutionError("fit frame: receipt not bound to the exec-v2 addendum hash")
    if doc.get("effective_v4_manifest_sha256") != effective_v4_manifest_sha256(effective):
        raise ExecutionError("fit frame: receipt effective-v4-manifest hash mismatch")
    for key in _RECEIPT_PAIRING_KEYS:
        if ar.get(key) in (None, ""):
            raise ExecutionError(f"fit frame: receipt missing pairing key {key!r}")
    if ar["eval_seed"] != derive_eval_seed(base_seed, year, lid):
        raise ExecutionError("fit frame: receipt eval_seed does not follow the frozen derivation")
    if not doc.get("draft_receipt_sha256"):
        raise ExecutionError("fit frame: receipt does not pin its draft-receipt sha256")
    if int(doc.get("n_seasons", -1)) != int(effective["evaluator"]["n_seasons"]):
        raise ExecutionError("fit frame: receipt n_seasons is not the frozen 8")
    _check_authoritative_frame(
        effective, year=year, league_id=lid, base_seed=base_seed, arm=arm,
        expected_sha=ar["policy_sha"], stage="fit",
    )
    return (arm, year, lid, base_seed)


def assert_complete_fit_frame(
    docs: list[dict[str, Any]], effective: dict[str, Any]
) -> None:
    """The measurement set must cover EXACTLY the frozen fit frame — one receipt per cell, no
    missing, duplicate, or extra cells (reviewer req 2)."""
    cells = [validate_fit_measurement_receipt(d, effective) for d in docs]
    seen: set[tuple[str, int, str, int]] = set()
    dupes = {c for c in cells if c in seen or seen.add(c)}
    if dupes:
        raise ExecutionError(f"fit frame: duplicate cells: {sorted(dupes)[:5]}")
    expected = expected_fit_cells(effective)
    missing = expected - seen
    extra = seen - expected
    if missing:
        raise ExecutionError(
            f"fit frame incomplete: {len(missing)} missing cells, e.g. {sorted(missing)[:3]}"
        )
    if extra:
        raise ExecutionError(f"fit frame: {len(extra)} off-frame cells, e.g. {sorted(extra)[:3]}")


#: The gate names `evaluate_promotion` always emits; a trustworthy report must carry all of them.
_CORE_GATE_NAMES = (
    "deterministic_checks", "started_points_aggregate", "hidden_regression_rule",
    "h2h_win_rate", "playoff_proxy", "championship_proxy", "calibration_gates", "limits",
)
_AUX = ("deterministic", "calibration", "runtime")


def _verdict_from_gates(gates: list[dict[str, Any]]) -> str:
    """The frozen failure interpretation, recomputed from a gate list (gates.py verdict rule)."""
    statuses = [g.get("status") for g in gates]
    if "block" in statuses:
        return "BLOCK"
    if "fail" in statuses:
        return "do_not_ship_candidate"
    if "inconclusive" in statuses:
        return "preserve_v5"
    return "promote"


def _reconstruct_pairs(docs: list[dict[str, Any]]) -> list[tuple[Any, Any]]:
    """Rebuild the frozen (candidate, control) ArmRun pairs from validated measurement receipts."""
    from blitz_engine.promotion.runner import ArmRun

    by_cell: dict[tuple[int, str, int], dict[str, Any]] = {}
    for d in docs:
        run = ArmRun.from_dict(d["arm_run"])
        by_cell.setdefault((run.year, run.league_id, run.base_seed), {})[run.arm] = run
    pairs = []
    for cell, arms in sorted(by_cell.items()):
        if set(arms) != set(ARM_POLICY_SHAS):
            raise ExecutionError(f"fit frame: cell {cell} does not carry both frozen arms")
        pairs.append((arms["v6_candidate"], arms["v5_shipped"]))
    return pairs


def validate_fit_analysis_receipt(
    fit_analysis: dict[str, Any], effective: dict[str, Any], *, measurement_shas: set[str]
) -> str:
    """Validate a fit-analysis receipt WITHOUT trusting caller-authored content. Beyond structure
    and the pinned input set, the embedded report must carry the complete frozen gate schema and a
    verdict the frozen rule re-derives from those gate statuses; a self-hashed report with empty or
    partial gates, or a verdict inconsistent with its gates, is refused (C05C blocker 1)."""
    from blitz_engine.promotion.gates import report_hash

    if fit_analysis.get("kind") != "fit_analysis":
        raise ExecutionError("fit-analysis: not a fit_analysis receipt")
    report = fit_analysis.get("report")
    if not isinstance(report, dict):
        raise ExecutionError("fit-analysis: missing embedded promotion report")
    if fit_analysis.get("report_sha256") != report_hash(report):
        raise ExecutionError("fit-analysis: report_sha256 does not match the embedded report")
    if report.get("stage") != "fit":
        raise ExecutionError("fit-analysis: report is not a fit-stage report")
    if report.get("authoritative") is not True:
        raise ExecutionError("fit-analysis: report is not authoritative")
    want_pairs = len(expected_fit_cells(effective)) // len(effective["_v4"]["arm_shas"])
    if int(report.get("n_pairs", -1)) != want_pairs:
        raise ExecutionError(
            f"fit-analysis: report has {report.get('n_pairs')} pairs, not the frozen {want_pairs}"
        )
    if fit_analysis.get("effective_v4_manifest_sha256") != effective_v4_manifest_sha256(effective):
        raise ExecutionError("fit-analysis: effective-v4-manifest hash mismatch")
    pinned = set((fit_analysis.get("pinned_inputs") or {}).get("measurement_sha256", {}).values())
    if pinned != set(measurement_shas):
        raise ExecutionError("fit-analysis: pinned measurement inputs != the fit frame")
    gates = report.get("gates")
    if not isinstance(gates, list) or not gates:
        raise ExecutionError("fit-analysis: report carries no gate evidence — cannot promote")
    names = {g.get("name") for g in gates}
    missing = [n for n in _CORE_GATE_NAMES if n not in names]
    if missing:
        raise ExecutionError(f"fit-analysis: report missing frozen gate evidence: {missing}")
    verdict = report.get("verdict")
    if verdict != _verdict_from_gates(gates):
        raise ExecutionError("fit-analysis: report verdict is inconsistent with its gate statuses")
    if verdict == "promote" and any(g.get("status") != "pass" for g in gates):
        raise ExecutionError("fit-analysis: promote requires every recorded gate to pass")
    if verdict not in ("BLOCK", "do_not_ship_candidate", "preserve_v5", "promote"):
        raise ExecutionError(f"fit-analysis: report verdict {verdict!r} is not a frozen verdict")
    return verdict


def _run_fit_analysis(
    effective: dict[str, Any], docs: list[dict[str, Any]], aux_docs: dict[str, Any]
) -> Any:
    """Mechanically produce the authoritative fit analysis: rebuild the frozen pairs and call the
    frozen `evaluate_promotion` with the consumed auxiliary evidence. No caller report trusted."""
    from blitz_engine.promotion.gates import evaluate_promotion

    return evaluate_promotion(
        effective, _reconstruct_pairs(docs), stage="fit", authoritative=True,
        calibration_report=aux_docs.get("calibration"),
        deterministic_receipt=aux_docs.get("deterministic"),
        runtime_receipt=aux_docs.get("runtime"),
    )


def write_fit_verdict(
    out_dir: str | Path, *, effective: dict[str, Any], measurement_paths: Any = None,
    fit_measure_paths: Any = None,
    deterministic_receipt_path: str | Path | None = None,
    calibration_report_path: str | Path | None = None,
    runtime_receipt_path: str | Path | None = None,
) -> Path:
    """Produce and record the write-once fit verdict. The report is computed MECHANICALLY by the
    frozen `evaluate_promotion` over the reconstructed frame — never accepted from a caller. `pass`
    is emitted ONLY when that verdict is `promote`; otherwise the frozen-gate verdict is recorded.
    Missing/invalid auxiliary evidence can never promote (reviewer C05C req 1/4/5/6).

    `fit_measure_paths` is the accepted C05B alias for `measurement_paths`."""
    from blitz_engine.promotion.gates import report_hash
    from blitz_engine.promotion.manifest import sha256_file

    supplied = measurement_paths if measurement_paths is not None else fit_measure_paths
    if supplied is None:
        raise ExecutionError("write_fit_verdict: no measurement paths supplied")
    paths = sorted(str(p) for p in supplied)
    docs = [json.loads(Path(p).read_text()) for p in paths]
    assert_complete_fit_frame(docs, effective)  # validates every receipt + exact coverage

    aux_paths = dict(zip(_AUX, (deterministic_receipt_path, calibration_report_path,
                                runtime_receipt_path), strict=True))
    aux_docs = {k: (json.loads(Path(v).read_text()) if v is not None else None)
                for k, v in aux_paths.items()}
    aux_pins = {k: sha256_file(v) for k, v in aux_paths.items() if v is not None}

    report = _run_fit_analysis(effective, docs, aux_docs)
    report_verdict = report["verdict"]
    verdict = "pass" if report_verdict == "promote" else report_verdict

    measurement_pins = {p: sha256_file(p) for p in paths}
    report_sha = report_hash(report)
    fit_analysis = {
        "kind": "fit_analysis",
        "report": dict(report),
        "report_sha256": report_sha,
        "effective_v4_manifest_sha256": effective_v4_manifest_sha256(effective),
        "pinned_inputs": {"measurement_sha256": measurement_pins, "auxiliary_sha256": aux_pins},
    }
    doc = {
        "kind": "fit_verdict",
        "verdict": verdict,
        "report_verdict": report_verdict,
        "manifest_sha256": V4_MANIFEST_SHA256,
        "exec_addendum_sha256": EXEC_V2_SHA256,
        "effective_v4_manifest_sha256": effective_v4_manifest_sha256(effective),
        "fit_receipt_sha256": measurement_pins,
        "auxiliary_sha256": aux_pins,
        "auxiliary_receipt_paths": {k: str(v) for k, v in aux_paths.items() if v is not None},
        "fit_analysis_report_sha256": report_sha,
        "fit_analysis": fit_analysis,
    }
    return _write_once(Path(out_dir) / "fit-verdict.json", doc)


def require_fit_verdict(out_dir: str | Path, effective: dict[str, Any]) -> dict[str, Any]:
    """Confirmation reloads EVERY pinned measurement, revalidates the exact complete frame, reloads
    and re-verifies the pinned auxiliary receipts, RERUNS the frozen analysis from all pinned
    inputs, compares the canonical report hash to the recorded one, and requires `promote`. No
    caller-authored verdict, hash, or partial input set unlocks confirmation (C05C blocker 2)."""
    from blitz_engine.promotion.gates import report_hash
    from blitz_engine.promotion.manifest import sha256_file

    p = Path(out_dir) / "fit-verdict.json"
    if not p.is_file():
        raise ExecutionError("confirmation blocked: no passing fit-verdict receipt exists")
    doc = json.loads(p.read_text())
    if doc.get("verdict") != "pass":
        raise ExecutionError(f"confirmation blocked: fit verdict is {doc.get('verdict')!r}")
    if doc.get("effective_v4_manifest_sha256") != effective_v4_manifest_sha256(effective):
        raise ExecutionError("confirmation blocked: fit-verdict effective-v4 hash mismatch")

    pins = doc.get("fit_receipt_sha256", {})
    docs = []
    for rel, want in pins.items():
        if not Path(rel).is_file() or sha256_file(rel) != want:
            raise ExecutionError(f"confirmation blocked: pinned measurement drift: {rel}")
        docs.append(json.loads(Path(rel).read_text()))
    assert_complete_fit_frame(docs, effective)  # the exact complete frame, re-proved

    aux_pins = doc.get("auxiliary_sha256", {})
    aux_paths = doc.get("auxiliary_receipt_paths", {})
    aux_docs = {k: None for k in _AUX}
    for label, rel in aux_paths.items():
        if not Path(rel).is_file() or sha256_file(rel) != aux_pins.get(label):
            raise ExecutionError(f"confirmation blocked: auxiliary receipt drift: {label}")
        aux_docs[label] = json.loads(Path(rel).read_text())

    report = _run_fit_analysis(effective, docs, aux_docs)  # rerun from pinned inputs
    if report_hash(report) != doc.get("fit_analysis_report_sha256"):
        raise ExecutionError("confirmation blocked: recomputed report hash != recorded")
    if report["verdict"] != "promote":
        raise ExecutionError(
            f"confirmation blocked: recomputed fit verdict is {report['verdict']!r}, not promote"
        )
    validate_fit_analysis_receipt(  # defence in depth: embedded receipt must also be consistent
        doc.get("fit_analysis") or {}, effective, measurement_shas=set(pins.values())
    )
    return doc


def _receipt_path(out_dir: str | Path, kind: str, stage: str, arm: str, r: dict[str, Any]) -> Path:
    return (
        Path(out_dir) / kind / stage
        / f"{arm}-{r['year']}-{r['league_id']}-{r['base_seed']}.json"
    )


def _write_once(path: Path, doc: dict[str, Any]) -> Path:
    if path.exists():
        raise ExecutionError(f"write-once violation: {path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    return path


#: Stage-1 payload — runs inside the ARM checkout with pinned import resolution (see execution.py
#: for why the editable finder must be stripped). Drafts only; emits rosters + pairing keys.
_DRAFT_PAYLOAD = r"""
import json, sys

year, league_id, eval_seed, engine_path = json.loads(sys.argv[1])
sys.path.insert(0, engine_path)
sys.meta_path = [
    f for f in sys.meta_path
    if "editable" not in (type(f).__module__ + type(f).__name__).lower()
]
for name in [m for m in list(sys.modules) if m == "blitz_engine" or m.startswith("blitz_engine.")]:
    del sys.modules[name]
import blitz_engine
if not str(blitz_engine.__file__).startswith(engine_path):
    raise SystemExit(
        f"blitz_engine resolved OUTSIDE the arm checkout: {blitz_engine.__file__} "
        f"(required prefix {engine_path}) - refusing to draft"
    )
import hashlib
from blitz_engine.simulation import season_eval as se
from blitz_engine.testing import matrix
row = next(r for r in matrix.all() if r["id"] == league_id)
pool = se.build_players(year, league_id)
rows = [(p.player_id, p.position, float(p.projection))
        for p in sorted(pool, key=lambda p: (-p.projection, p.player_id))]
board_hash = hashlib.sha256(json.dumps(rows).encode()).hexdigest()
rosters, seat_policy = se.draft_league(pool, row, seed=int(eval_seed))
print(json.dumps({
    "board_hash": board_hash,
    "seat_policy": list(seat_policy),
    "rosters": [[p.player_id for p in roster] for roster in rosters],
}))
"""

#: Stage-2 payload — runs inside the MEASUREMENT checkout only; replays given rosters through the
#: common evaluator. The free-agent pool is the board minus the drafted ids, by construction.
_MEASURE_PAYLOAD = r"""
import json, sys

spec = json.loads(sys.argv[1])
engine_path = spec["engine_path"]
sys.path.insert(0, engine_path)
sys.meta_path = [
    f for f in sys.meta_path
    if "editable" not in (type(f).__module__ + type(f).__name__).lower()
]
for name in [m for m in list(sys.modules) if m == "blitz_engine" or m.startswith("blitz_engine.")]:
    del sys.modules[name]
import blitz_engine
if not str(blitz_engine.__file__).startswith(engine_path):
    raise SystemExit(
        f"blitz_engine resolved OUTSIDE the measurement checkout: {blitz_engine.__file__} "
        f"(required prefix {engine_path}) - refusing to measure"
    )
import hashlib
import numpy as np
from blitz_engine.simulation import season_eval as se
from blitz_engine.testing import matrix
row = next(r for r in matrix.all() if r["id"] == spec["league_id"])
pool = se.build_players(spec["year"], spec["league_id"])
rows = [(p.player_id, p.position, float(p.projection))
        for p in sorted(pool, key=lambda p: (-p.projection, p.player_id))]
board_hash = hashlib.sha256(json.dumps(rows).encode()).hexdigest()
if board_hash != spec["board_hash"]:
    raise SystemExit("measurement board hash mismatch against the draft receipt")
by_id = {p.player_id: p for p in pool}
rosters = [[by_id[pid] for pid in roster] for roster in spec["rosters"]]
cfg = se.EvalConfig(
    n_seasons=int(spec["n_seasons"]), seed=int(spec["eval_seed"]),
    waiver_cost=float(spec["waiver_cost"]),
)
res = se.evaluate_rosters(pool, rosters, row, seat_policy=spec["seat_policy"], config=cfg)
def arr(name):
    a = np.asarray(getattr(res, name, np.empty((0, 0))), dtype=float)
    return a.tolist() if a.size else None
print(json.dumps({
    "board_hash": board_hash,
    "per_season": np.asarray(res.per_season, dtype=float).tolist(),
    "h2h_win_rate": np.asarray(res.h2h_win_rate, dtype=float).tolist(),
    "per_season_playoff": arr("per_season_playoff"),
    "per_season_champ": arr("per_season_champ"),
}))
"""


def _run_payload(payload: str, arg: Any, checkout: str | Path, python: str) -> dict[str, Any]:
    env = {**os.environ, "PYTHONPATH": str(Path(checkout) / "engine")}
    proc = subprocess.run(
        [python, "-c", payload, json.dumps(arg)], env=env, capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise ExecutionError(f"payload failed in {checkout}: {proc.stderr[-800:]}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


def draft_arm(
    arm: str,
    checkout: str | Path,
    expected_sha: str,
    *,
    effective: dict[str, Any],
    year: int,
    league_id: str,
    base_seed: int,
    stage: str,
    guard: HeldOutGuard,
    out_dir: str | Path,
    tooling_root: str | Path,
    python: str = sys.executable,
    authoritative: bool = False,
) -> Path:
    """Stage 1: verified arm checkout drafts one slice; write-once draft receipt."""
    if stage not in ("fit", "confirm"):
        raise ExecutionError(f"unknown stage {stage!r}")
    if authoritative:
        _check_authoritative_frame(
            effective, year=year, league_id=league_id, base_seed=base_seed,
            arm=arm, expected_sha=expected_sha, stage=stage,
        )
    provenance = tooling_provenance(tooling_root)
    guard.check(year, stage=stage)
    if stage == "confirm":
        require_fit_verdict(out_dir, effective)
    head = verify_arm_checkout(checkout, expected_sha)
    eval_seed = derive_eval_seed(base_seed, year, league_id)
    payload = _run_payload(
        _DRAFT_PAYLOAD, [year, league_id, eval_seed, str(Path(checkout) / "engine")],
        checkout, python,
    )
    receipt = {
        "kind": "draft",
        "arm": arm,
        "policy_sha": head,
        "year": int(year),
        "league_id": str(league_id),
        "base_seed": int(base_seed),
        "eval_seed": eval_seed,
        "board_hash": payload["board_hash"],
        "seat_policy": payload["seat_policy"],
        "rosters": payload["rosters"],
        "stage": stage,
        "produced_by_tooling": provenance,
        "manifest_sha256": V4_MANIFEST_SHA256,
        "exec_addendum_sha256": EXEC_V2_SHA256,
        "effective_v4_manifest_sha256": effective_v4_manifest_sha256(effective),
        "authoritative": bool(authoritative),
        "label": None if authoritative else "NON-AUTHORITATIVE rehearsal/probe receipt",
    }
    return _write_once(_receipt_path(out_dir, "draft", stage, arm, receipt), receipt)


def measure_arm(
    draft_receipt_path: str | Path,
    measurement_checkout: str | Path,
    *,
    effective: dict[str, Any],
    n_seasons: int,
    guard: HeldOutGuard,
    out_dir: str | Path,
    tooling_root: str | Path,
    python: str = sys.executable,
    authoritative: bool = False,
) -> Path:
    """Stage 2: the frozen common evaluator replays one draft receipt; write-once measurement
    receipt. All exec-v2 roster rules are enforced here, BEFORE the evaluator runs."""
    provenance = tooling_provenance(tooling_root)
    receipt = json.loads(Path(draft_receipt_path).read_text())
    stage = receipt["stage"]
    if bool(authoritative) != bool(receipt.get("authoritative", False)):
        raise ExecutionError(
            f"authority mismatch: draft receipt authoritative={receipt.get('authoritative')} "
            f"but measurement authoritative={authoritative}; draft and measurement authority must "
            "match and an authoritative run refuses non-authoritative input"
        )
    if authoritative:
        _check_authoritative_frame(
            effective, year=receipt["year"], league_id=receipt["league_id"],
            base_seed=receipt["base_seed"], arm=receipt["arm"],
            expected_sha=receipt["policy_sha"], stage=stage, n_seasons=n_seasons,
        )
    guard.check(receipt["year"], stage=stage)
    if stage == "confirm":
        require_fit_verdict(out_dir, effective)
    measured_by = verify_measurement_checkout(measurement_checkout, effective)

    from blitz_engine.testing import matrix

    row = next(r for r in matrix.all() if r["id"] == receipt["league_id"])
    from blitz_engine.simulation import season_eval as se

    board_ids = frozenset(
        p.player_id for p in se.build_players(receipt["year"], receipt["league_id"])
    )
    if authoritative:
        validate_authoritative_draft_receipt(receipt, row, board_ids, effective, stage=stage)
    else:
        validate_draft_receipt(receipt, row, board_ids)

    payload = _run_payload(
        _MEASURE_PAYLOAD,
        {
            "year": receipt["year"], "league_id": receipt["league_id"],
            "eval_seed": receipt["eval_seed"], "n_seasons": int(n_seasons),
            "waiver_cost": float(effective["evaluator"]["waiver_cost"]),
            "board_hash": receipt["board_hash"], "rosters": receipt["rosters"],
            "seat_policy": receipt["seat_policy"],
            "engine_path": str(Path(measurement_checkout) / "engine"),
        },
        measurement_checkout, python,
    )

    def _proxy(name: str) -> tuple[float, ...] | None:
        a = payload.get(name)
        return None if a is None else tuple(
            float(v) for v in np.asarray(a, dtype=float).mean(axis=0)
        )

    run = ArmRun(
        arm=receipt["arm"],
        policy_sha=receipt["policy_sha"],
        year=receipt["year"],
        league_id=receipt["league_id"],
        base_seed=receipt["base_seed"],
        eval_seed=receipt["eval_seed"],
        board_hash=receipt["board_hash"],
        seat_policy=tuple(receipt["seat_policy"]),
        per_season=tuple(tuple(float(v) for v in r) for r in payload["per_season"]),
        h2h_win_rate=tuple(float(v) for v in payload["h2h_win_rate"]),
        playoff_proxy=_proxy("per_season_playoff"),
        championship_proxy=_proxy("per_season_champ"),
        synthetic=not authoritative,
    )
    doc = {
        "kind": "measurement",
        "measured_by_sha": measured_by,
        "measurement_file_hashes_verified": True,
        "draft_receipt_sha256": sha256_file(draft_receipt_path),
        "arm_run": run.to_dict(),
        "stage": stage,
        "n_seasons": int(n_seasons),
        "produced_by_tooling": provenance,
        "manifest_sha256": V4_MANIFEST_SHA256,
        "exec_addendum_sha256": EXEC_V2_SHA256,
        "effective_v4_manifest_sha256": effective_v4_manifest_sha256(effective),
        "authoritative": bool(authoritative),
        "label": None if authoritative else "NON-AUTHORITATIVE rehearsal/probe receipt",
    }
    return _write_once(_receipt_path(out_dir, "measure", stage, receipt["arm"], receipt), doc)


def rehearse_v4(
    repo_root: str | Path,
    scratch: str | Path,
    out_dir: str | Path,
    *,
    league_id: str = "t10-1qb-std-te0.0-b4-ir0",
    year: int = 2021,
    base_seed: int = 2026082601,
    n_seasons: int = 1,
) -> dict[str, Any]:
    """Cheap NON-AUTHORITATIVE two-stage rehearsal of the full v4 protocol on one slice.

    Drafts in real baseline/candidate checkouts, measures BOTH rosters through the frozen common
    evaluator, pairs the results, and proves measurement determinism by measuring the candidate
    receipt twice (second pass into a scratch dir) and comparing the ArmRun byte-for-byte.
    """
    from blitz_engine.promotion.runner import pair_slice

    root, scratch = Path(repo_root), Path(scratch)
    effective = load_execution_manifest_v4(root)
    provenance = tooling_provenance(root)
    guard = HeldOutGuard(list(effective["seasons"]), list(effective["held_out_seasons"]))
    arms = {"v5_shipped": (scratch / "arm-v5", BASELINE_SHA),
            "v6_candidate": (scratch / "arm-v6", CANDIDATE_SHA)}
    measure_co = scratch / "measure"
    runs: dict[str, ArmRun] = {}
    draft_paths: dict[str, Path] = {}
    try:
        for co, sha in [*arms.values(), (measure_co, MEASUREMENT_SHA)]:
            subprocess.run(
                ["git", "-C", str(root), "worktree", "add", "--detach", str(co), sha],
                capture_output=True, text=True, check=True,
            )
        for arm, (co, sha) in arms.items():
            draft_paths[arm] = draft_arm(
                arm, co, sha, effective=effective, year=year, league_id=league_id,
                base_seed=base_seed, stage="fit", guard=guard, out_dir=out_dir,
                tooling_root=root,
            )
            mp = measure_arm(
                draft_paths[arm], measure_co, effective=effective, n_seasons=n_seasons,
                guard=guard, out_dir=out_dir, tooling_root=root,
            )
            runs[arm] = ArmRun.from_dict(json.loads(mp.read_text())["arm_run"])
        # determinism: measure the candidate draft receipt again into scratch, compare byte-wise
        again = measure_arm(
            draft_paths["v6_candidate"], measure_co, effective=effective, n_seasons=n_seasons,
            guard=guard, out_dir=scratch / "determinism-check", tooling_root=root,
        )
        rerun = ArmRun.from_dict(json.loads(again.read_text())["arm_run"])
        deterministic = rerun == runs["v6_candidate"]
        s = pair_slice(runs["v6_candidate"], runs["v5_shipped"])
        pairing = {
            "paired": True,
            "started_points_delta_mean": float(np.mean(s["started_points"])),
            "h2h_delta_mean": float(np.mean(s["h2h_win_rate"])),
            "playoff_proxy_available_both_arms": s["playoff_proxy"] is not None,
            "championship_proxy_available_both_arms": s["championship_proxy"] is not None,
            "playoff_delta_mean": None if s["playoff_proxy"] is None
            else float(np.mean(s["playoff_proxy"])),
            "championship_delta_mean": None if s["championship_proxy"] is None
            else float(np.mean(s["championship_proxy"])),
        }
    finally:
        for co in [*(c for c, _ in arms.values()), measure_co]:
            subprocess.run(
                ["git", "-C", str(root), "worktree", "remove", "--force", str(co)],
                capture_output=True, text=True,
            )
    summary = {
        "label": "NON-AUTHORITATIVE v4 two-stage rehearsal — justifies nothing",
        "protocol": "promotion-v4 + exec-v2",
        "produced_by_tooling": provenance,
        "slice": {"year": year, "league_id": league_id, "base_seed": base_seed,
                  "n_seasons_deviation": n_seasons},
        "arm_policy_heads": {a: runs[a].policy_sha for a in runs},
        "measured_by": MEASUREMENT_SHA,
        "board_hashes": {a: runs[a].board_hash for a in runs},
        "measurement_deterministic": deterministic,
        "pairing": pairing,
    }
    p = Path(out_dir) / "rehearsal-summary.json"
    p.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary
