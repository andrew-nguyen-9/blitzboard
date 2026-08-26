"""Adapter from the PROVISIONAL C02 evaluator/calibration surfaces into C05 promotion inputs.

C02 (`edbcc4d`) has NOT passed review. This module exists on the disposable compatibility branch
`v6/c05-c02-adapter` only, so that the moment C02 is accepted the C05 machinery can consume it
without edits to the frozen manifest or the gate code. Nothing here treats provisional behaviour
as accepted, and nothing here may feed an authoritative run.

Three mappings, each a pure function:

* `arm_run_from_result` — `SeasonEvalResult` → `ArmRun`. C02's paired outcome families
  (`per_season`, `per_season_h2h`, `per_season_playoff`, `per_season_champ`) become the C05
  fields; playoff/championship proxies are the per-seat means over the sampled seasons, matching
  the seat-clustered CI unit. A pre-C02 result (empty proxy arrays) maps to `None`, which the
  gates already treat as the inconclusive C02-dependency path.
* `calibration_report_from_c02` — C02's executed `calibration/report.json` → the gate's expected
  report shape, plus an explicit list of gaps the report cannot express (see
  `INTERFACE_MISMATCHES`). Unmappable attestations default to CONSERVATIVE-FAIL and can only be
  supplied explicitly by the caller.
* `probe_leak_guard` / `deterministic_receipt_from_probes` — mechanical probes for the
  `deterministic_receipt` input: the leak probe injects a same-week row through the evaluator's
  `leak` hook and demands `LeakageError`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

from blitz_engine.promotion.runner import ArmRun, derive_eval_seed

if TYPE_CHECKING:
    from blitz_engine.simulation.season_eval import SeasonEvalResult

__all__ = [
    "INTERFACE_MISMATCHES",
    "arm_run_from_result",
    "calibration_report_from_c02",
    "deterministic_receipt_from_probes",
    "probe_leak_guard",
]

#: Frozen record of every C05↔C02 interface mismatch found while building this adapter.
#: These are facts about the provisional surfaces, not judgements; reconciliation belongs to the
#: C02 review and, where the frozen manifest is affected, to a promotion-v4 amendment.
INTERFACE_MISMATCHES = (
    "naming: C05 ArmRun.playoff_proxy/championship_proxy vs C02 per_season_playoff/"
    "per_season_champ (and per-seat means playoff_rate/champ_rate); adapter maps per-seat "
    "season-means",
    "metric definition: C02 per_season points are NET of transaction cost "
    "(waiver_cost x claims); promotion-v3 metric_definition does not mention the netting — "
    "identical rule in both arms keeps pairing valid, but the wording needs a v4 amendment or an "
    "accepted clarification",
    "calibration shape: C02 report.json nests results per format x benchmark x arm; the gate "
    "expects a flat benchmark list with v6−v5 deltas; adapter flattens ids to "
    "'<format>/<benchmark>'",
    "calibration snapshot fields: C02 uses raw_sha256/retrieved_utc; gate expects "
    "snapshot_sha256/retrieval_utc; renamed by adapter",
    "calibration gaps: report.json carries NO deterministic_unit_failures, NO held-out "
    "confirmation, NO season-evaluator no-regression evidence, and no structured "
    "missing-data-degradation flag (only prose notes); these default to conservative FAIL and "
    "must be attested explicitly once C02 is accepted",
    "materiality: player-calibration-v1 threshold position_or_cohort_material_regression=0 "
    "defines no materiality rule; adapter counts ANY cohort mean_abs_err increase (v6 > v5) as "
    "material — strictest reading, fails easily",
    "cohort coverage: C02 notes team_change and low_availability cohorts are not computable from "
    "the frozen snapshot; the manifest lists them as mandatory cohorts",
    "receipts: C02 proves determinism/leak-guard in tests but emits no machine-readable receipt; "
    "probes below regenerate the evidence mechanically",
)


def arm_run_from_result(
    arm: str,
    policy_sha: str,
    result: SeasonEvalResult,
    *,
    year: int,
    league_id: str,
    base_seed: int,
    board_hash: str,
    synthetic: bool = True,
    runtime_s: float = 0.0,
    max_rss_mb: float = 0.0,
) -> ArmRun:
    """Map one C02 `SeasonEvalResult` onto the C05 `ArmRun` pairing/analysis contract."""

    def _proxy(field: str) -> tuple[float, ...] | None:
        a = np.asarray(getattr(result, field, np.empty((0, 0))), dtype=float)
        if a.size == 0:
            return None  # pre-C02 result: the C05 gates read this as the unmet dependency
        return tuple(float(v) for v in a.mean(axis=0))

    return ArmRun(
        arm=arm,
        policy_sha=policy_sha,
        year=int(year),
        league_id=str(league_id),
        base_seed=int(base_seed),
        eval_seed=derive_eval_seed(base_seed, year, league_id),
        board_hash=board_hash,
        seat_policy=tuple(result.seat_policy),
        per_season=tuple(tuple(float(v) for v in row) for row in np.asarray(result.per_season)),
        h2h_win_rate=tuple(float(v) for v in result.h2h_win_rate),
        playoff_proxy=_proxy("per_season_playoff"),
        championship_proxy=_proxy("per_season_champ"),
        runtime_s=runtime_s,
        max_rss_mb=max_rss_mb,
        synthetic=synthetic,
    )


#: Attestations the C02 report cannot express; every one defaults to the failing value.
_CONSERVATIVE_ATTESTATIONS = {
    "deterministic_unit_failures": 1,
    "held_out_confirmed": False,
    "season_evaluator_no_regression": False,
    "missing_data_degrades_explicitly": False,
}


def calibration_report_from_c02(
    report: dict[str, Any], attestations: dict[str, Any] | None = None
) -> tuple[dict[str, Any], list[str]]:
    """C02 `calibration/report.json` → the gate's report shape, plus the list of mapping gaps.

    `attestations` may supply ONLY the keys in `_CONSERVATIVE_ATTESTATIONS`; anything the report
    itself carries cannot be overridden.
    """
    gap_prefixes = ("calibration", "materiality", "cohort")
    gaps = [m for m in INTERFACE_MISMATCHES if m.startswith(gap_prefixes)]
    extra = set(attestations or ()) - set(_CONSERVATIVE_ATTESTATIONS)
    if extra:
        raise ValueError(f"attestations may not override report-derived fields: {sorted(extra)}")

    meta = report["inputs"]["benchmarks"]
    benchmarks: list[dict[str, Any]] = []
    top_n_regressions = 0
    cohort_regressions = 0
    outliers_everywhere = True
    for fmt, benches in report["results"].items():
        for bench_id, arms in benches.items():
            v5, v6 = arms["v5"], arms["v6"]
            m = meta[bench_id]
            benchmarks.append(
                {
                    "id": f"{fmt}/{bench_id}",
                    "snapshot_sha256": m.get("raw_sha256", ""),
                    "retrieval_utc": m.get("retrieved_utc", ""),
                    "spearman_delta": float(v6["spearman_rho"]) - float(v5["spearman_rho"]),
                    "weighted_rank_error_delta": float(v6["weighted_absolute_rank_error"])
                    - float(v5["weighted_absolute_rank_error"]),
                    "unmatched_top_100_rate": max(
                        float(v5["unmatched_top_100_rate"]), float(v6["unmatched_top_100_rate"])
                    ),
                }
            )
            for n in (12, 24, 50):
                if float(v6[f"top_{n}_recall"]) < float(v5[f"top_{n}_recall"]):
                    top_n_regressions += 1
            for cohort, stats in v6.get("cohorts", {}).items():
                base = v5.get("cohorts", {}).get(cohort)
                if base and float(stats["mean_abs_err"]) > float(base["mean_abs_err"]):
                    cohort_regressions += 1  # strictest materiality reading (see mismatches)
            if not v6.get("largest_absolute_outliers"):
                outliers_everywhere = False

    out = {
        "executed": True,
        "benchmarks": benchmarks,
        "top_n_recall_regressions": top_n_regressions,
        "cohort_material_regressions": cohort_regressions,
        "outlier_and_decomposition_reported": outliers_everywhere,
        **_CONSERVATIVE_ATTESTATIONS,
        **{k: v for k, v in (attestations or {}).items()},
    }
    return out, gaps


def probe_leak_guard(year: int, row: dict[str, Any], *, seed: int, n_seasons: int = 1) -> bool:
    """True iff the evaluator's leakage detector is LIVE: an injected same-week row must raise."""
    from blitz_engine.backtest.harness import LeakageError
    from blitz_engine.simulation import season_eval as se

    players = se.build_players(year, str(row["id"]))
    rosters, seats = se.draft_league(players, row, seed=seed)
    cfg = se.EvalConfig(n_seasons=n_seasons, seed=seed)
    try:
        se.evaluate_rosters(
            players, rosters, row, seat_policy=seats, config=cfg, leak={"week": 0}
        )
    except LeakageError:
        return True
    return False


def deterministic_receipt_from_probes(
    *, invariants_pass: bool, determinism_ok: bool, leak_guard_live: bool
) -> dict[str, bool]:
    """The `deterministic_receipt` input, built from mechanical probes rather than assertions.

    A DEAD leak guard is itself a leakage failure (`leakage_detected=True`): the protocol cannot
    trust a run whose guard provably would not have fired.
    """
    return {
        "invariants_pass": bool(invariants_pass),
        "leakage_detected": not leak_guard_live,
        "nondeterminism_detected": not determinism_ok,
    }
