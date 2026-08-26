"""Gate evaluation for the C05 promotion protocol — the frozen thresholds, mechanically applied.

`evaluate_promotion` turns validated matched pairs into a `PromotionReport` whose verdict follows
the manifest's `failure_interpretation` exactly:

    BLOCK                    — deterministic/invariant failure, leakage, nondeterminism
    do_not_ship_candidate    — a numerical gate failed (including calibration and limits)
    preserve_v5              — inconclusive: zero evidence, missing mandatory evidence,
                               or a dependency (e.g. C02's playoff proxies) not yet available
    promote                  — every gate passed

Pairing mismatches and held-out leaks raise BEFORE any statistic is computed — they are protocol
violations, not results. Every report carries `authoritative`; a report produced from synthetic
data or without the frozen candidate SHA is stamped non-authoritative and can justify nothing.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np

from blitz_engine.promotion.runner import ArmRun, HeldOutGuard, PromotionError, pair_slice
from blitz_engine.promotion.stats import boot_seed, paired_ci95, slice_no_regression

__all__ = [
    "PromotionReport",
    "calibration_gate",
    "canonical_report_json",
    "evaluate_promotion",
    "final_verdict",
    "report_hash",
]

NON_AUTHORITATIVE_LABEL = "SYNTHETIC / NON-AUTHORITATIVE — cannot justify shipping"


class PromotionReport(dict):
    """A plain dict with a stable identity; see `canonical_report_json` for the byte-stable form."""


def _gate(gates: list[dict[str, Any]], name: str, status: str, detail: str) -> None:
    gates.append({"name": name, "status": status, "detail": detail})


def calibration_gate(report: dict[str, Any] | None, calib: dict[str, Any]) -> dict[str, Any]:
    """Apply the reviewer-frozen player-calibration gates (promotion-v3 `calibration_gates`).

    `report` is C02's executed calibration report; `calib` is the manifest's `calibration_gates`
    object. Missing report, unfrozen sources, or any threshold miss ⇒ fail (never inconclusive,
    per the manifest's `missing_report_interpretation`).
    """
    if report is None or not report.get("executed"):
        return {"status": "fail", "detail": "no executed calibration report"}
    problems: list[str] = []
    benches = report.get("benchmarks", [])
    if not benches:
        problems.append("no benchmark snapshots")
    for b in benches:
        for k in ("id", "snapshot_sha256", "retrieval_utc"):
            if not b.get(k):
                problems.append(f"benchmark source identity not frozen: missing {k}")
        if b.get("spearman_delta", -1.0) < 0.0:
            problems.append(f"{b.get('id')}: spearman_delta < 0")
        if b.get("weighted_rank_error_delta", 1.0) > 0.0:
            problems.append(f"{b.get('id')}: weighted_rank_error_delta > 0")
        if b.get("unmatched_top_100_rate", 1.0) > 0.02:
            problems.append(f"{b.get('id')}: unmatched_top_100_rate > 0.02")
    if report.get("deterministic_unit_failures", 1) != 0:
        problems.append("deterministic unit failures present")
    if report.get("cohort_material_regressions", 1) != 0:
        problems.append("material cohort regression")
    if report.get("top_n_recall_regressions", 1) != 0:
        problems.append("top-N recall regression")
    if not report.get("outlier_and_decomposition_reported"):
        problems.append("per-player outlier/decomposition report missing")
    if not report.get("missing_data_degrades_explicitly"):
        problems.append("missing-data rows not explicitly degraded")
    if not report.get("held_out_confirmed"):
        problems.append("held-out confirmation missing")
    if not report.get("season_evaluator_no_regression"):
        problems.append("season-evaluator no-regression evidence missing")
    if problems:
        return {"status": "fail", "detail": "; ".join(problems)}
    return {"status": "pass", "detail": f"{len(benches)} frozen benchmarks, all thresholds met"}


def evaluate_promotion(
    manifest: dict[str, Any],
    arm_pairs: list[tuple[ArmRun, ArmRun]],
    *,
    stage: str = "fit",
    calibration_report: dict[str, Any] | None = None,
    deterministic_receipt: dict[str, Any] | None = None,
    runtime_receipt: dict[str, Any] | None = None,
    authoritative: bool = False,
    require_full_coverage: bool | None = None,
) -> PromotionReport:
    """Validate every pair, then apply the frozen gates for one stage ('fit' or 'confirm')."""
    if stage not in ("fit", "confirm"):
        raise PromotionError(f"unknown stage {stage!r}")
    if authoritative:
        sha = manifest["arms"]["candidate"].get("combined_candidate_sha")
        if not sha:
            raise PromotionError(
                "execution precondition unmet: combined_candidate_sha is null — "
                "C02/C03/C04 must pass and the candidate SHA must be frozen first"
            )
    if require_full_coverage is None:
        require_full_coverage = authoritative

    # ── pairing + held-out validation, strictly BEFORE any statistic ──
    guard = HeldOutGuard(list(manifest["seasons"]), list(manifest["held_out_seasons"]))
    slices = []
    for cand, ctrl in arm_pairs:
        s = pair_slice(cand, ctrl)  # raises PairingError on any CRN violation
        guard.check(s["year"], stage=stage)  # raises HeldOutLeakError on a leak
        slices.append(s)

    seeds = manifest["seed_derivation"]["base_seeds"]
    thr = manifest["thresholds"]
    gates: list[dict[str, Any]] = []
    synthetic = any(s["synthetic"] for s in slices)

    # ── deterministic correctness / leakage / nondeterminism ──
    if deterministic_receipt is None:
        _gate(gates, "deterministic_checks", "inconclusive", "no deterministic-checks receipt")
    elif deterministic_receipt.get("leakage_detected") or deterministic_receipt.get(
        "nondeterminism_detected"
    ):
        _gate(gates, "deterministic_checks", "block", "leakage or nondeterminism detected")
    elif not deterministic_receipt.get("invariants_pass"):
        _gate(gates, "deterministic_checks", "block", "roster/correctness invariants failed")
    else:
        _gate(gates, "deterministic_checks", "pass", "invariants pass; no leakage; deterministic")

    # ── primary: aggregate started points ──
    agg = (
        np.concatenate([s["started_points"] for s in slices])
        if slices
        else np.empty(0)
    )
    if agg.size == 0 or not np.any(agg != 0.0):
        _gate(
            gates, "started_points_aggregate", "inconclusive",
            "zero started-points evidence — does not promote",
        )
        agg_ci = None
    else:
        mean, lo, hi = paired_ci95(agg, seed=boot_seed(seeds, f"{stage}/aggregate/started_points"))
        agg_ci = {"mean": mean, "ci95": [lo, hi], "n_seats": int(agg.size)}
        status = "pass" if lo > thr["started_points_ci95_lower"] else "fail"
        _gate(
            gates, "started_points_aggregate", status,
            f"mean {mean:+.3f}, CI95 [{lo:+.3f}, {hi:+.3f}], lower bound must exceed "
            f"{thr['started_points_ci95_lower']}",
        )

    # ── mandatory high-risk slices, zero tolerance ──
    tol = thr["mandatory_slice_no_regression_tolerance"]
    by_league: dict[str, list[np.ndarray]] = {}
    for s in slices:
        by_league.setdefault(s["league_id"], []).append(s["started_points"])
    slice_report: dict[str, Any] = {}
    for lid in manifest["mandatory_high_risk_slices"]:
        if lid not in by_league:
            slice_report[lid] = {"status": "missing"}
            if require_full_coverage:
                _gate(gates, f"slice:{lid}", "inconclusive", "mandatory slice has no evidence")
            continue
        d = np.concatenate(by_league[lid])
        ok = slice_no_regression(d, tolerance=tol)
        slice_report[lid] = {"status": "pass" if ok else "fail", "mean": float(d.mean())}
        if not ok:
            _gate(
                gates, f"slice:{lid}", "fail",
                f"mean paired delta {float(d.mean()):+.3f} < {-tol} "
                f"(no_regression tolerance {tol})",
            )
    if all(v["status"] == "pass" for v in slice_report.values()) and slice_report:
        _gate(
            gates, "mandatory_high_risk_slices", "pass",
            f"{len(slice_report)} slices, none regressed",
        )

    # ── hidden-regression rule over every evaluated league id ──
    hidden = []
    for lid, ds in sorted(by_league.items()):
        d = np.concatenate(ds)
        if d.size < 2 or not np.any(d != 0.0):
            continue
        _, lo, hi = paired_ci95(d, seed=boot_seed(seeds, f"{stage}/league/{lid}"))
        if hi < 0.0:
            hidden.append(f"{lid}: CI95 upper {hi:+.3f} < 0")
    _gate(
        gates, "hidden_regression_rule",
        "fail" if hidden else "pass",
        "; ".join(hidden) if hidden else f"{len(by_league)} league ids, no significant regression",
    )
    if require_full_coverage:
        want = int(manifest["league_configurations"]["mandatory_league_id_count"])
        if len(by_league) < want:
            _gate(
                gates, "league_coverage", "inconclusive",
                f"only {len(by_league)}/{want} mandatory league ids evaluated",
            )

    # ── secondary metrics ──
    def _secondary(metric: str, bound: float) -> None:
        arrs = [s[metric] for s in slices if s.get(metric) is not None]
        if not arrs:
            _gate(
                gates, metric, "inconclusive",
                "metric unavailable (C02 paired-proxy dependency)" if metric != "h2h_win_rate"
                else "no H2H evidence",
            )
            return
        d = np.concatenate(arrs)
        mean, lo, hi = paired_ci95(d, seed=boot_seed(seeds, f"{stage}/aggregate/{metric}"))
        status = "pass" if lo >= bound else "fail"
        _gate(
            gates, metric, status,
            f"mean {mean:+.4f}, CI95 [{lo:+.4f}, {hi:+.4f}], lower >= {bound}",
        )

    _secondary("h2h_win_rate", thr["h2h_ci95_lower"])
    _secondary("playoff_proxy", thr["playoff_or_championship_ci95_lower"])
    _secondary("championship_proxy", thr["playoff_or_championship_ci95_lower"])

    # ── calibration gates (reviewer-frozen) ──
    cg = calibration_gate(calibration_report, manifest["calibration_gates"])
    _gate(gates, "calibration_gates", cg["status"], cg["detail"])

    # ── runtime/memory limits ──
    limits = manifest["limits"]
    if runtime_receipt is None:
        _gate(gates, "limits", "inconclusive", "no runtime/memory receipt")
    else:
        over = []
        if runtime_receipt.get("wall_clock_hours", 0.0) > limits["wall_clock_hours_max"]:
            over.append("wall clock over limit")
        if runtime_receipt.get("peak_rss_gib", 0.0) > limits["peak_rss_gib_max"]:
            over.append("peak RSS over limit")
        _gate(gates, "limits", "fail" if over else "pass", "; ".join(over) or "within limits")

    # ── verdict per the frozen failure interpretation ──
    statuses = [g["status"] for g in gates]
    if "block" in statuses:
        verdict = "BLOCK"
    elif "fail" in statuses:
        verdict = "do_not_ship_candidate"
    elif "inconclusive" in statuses:
        verdict = "preserve_v5"
    else:
        verdict = "promote"

    report = PromotionReport(
        manifest_sha256=manifest.get("_manifest_sha256"),
        schema_version=manifest["schema_version"],
        stage=stage,
        authoritative=bool(authoritative and not synthetic),
        synthetic=synthetic,
        n_pairs=len(slices),
        aggregate=agg_ci,
        slices=slice_report,
        gates=gates,
        verdict=verdict,
        held_out_access_log=guard.access_log,
    )
    if not report["authoritative"]:
        report["label"] = NON_AUTHORITATIVE_LABEL
    return report


def final_verdict(fit: PromotionReport, confirm: PromotionReport) -> str:
    """Promotion needs BOTH stages to pass; the worse verdict always wins."""
    if confirm["stage"] != "confirm" or fit["stage"] != "fit":
        raise PromotionError("final_verdict needs one fit report and one confirm report")
    order = {"BLOCK": 0, "do_not_ship_candidate": 1, "preserve_v5": 2, "promote": 3}
    return min((fit["verdict"], confirm["verdict"]), key=lambda v: order[v])


def canonical_report_json(report: PromotionReport) -> str:
    """Byte-stable serialisation: sorted keys, no volatile fields (receipts live elsewhere)."""
    return json.dumps(report, sort_keys=True, separators=(",", ":"), default=_jsonable)


def _jsonable(o: Any) -> Any:
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"not JSON-serialisable: {type(o)}")


def report_hash(report: PromotionReport) -> str:
    return hashlib.sha256(canonical_report_json(report).encode()).hexdigest()
