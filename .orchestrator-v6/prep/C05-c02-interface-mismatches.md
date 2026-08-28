# C05 ↔ provisional C02 interface mismatches (2026-08-26)

Recorded while building the compatibility adapter on the DISPOSABLE branch `v6/c05-c02-adapter`
(worktree from provisional C02 `edbcc4d`, which has NOT passed review, plus cherry-picked C05 prep
`82b7705`). Nothing here treats provisional C02 behaviour as accepted; the canonical machine-readable
copy of this list is `blitz_engine.promotion.adapter.INTERFACE_MISMATCHES`, and every item is
exercised by `engine/tests/test_promotion_adapter.py` (synthetic/non-authoritative only).

## Mismatches

1. **Proxy field naming/shape.** C05 `ArmRun.playoff_proxy` / `championship_proxy` are per-seat
   tuples; C02 provides `per_season_playoff` / `per_season_champ` `(n_seasons, teams)` 0/1 samples
   (plus per-seat means `playoff_rate` / `champ_rate`). Adapter maps the per-seat season-means,
   which is the seat-clustered unit the frozen CI method expects. A pre-C02 result (empty arrays)
   maps to `None` → the existing `preserve_v5` dependency path.
2. **Metric definition drift.** C02's `per_season` points are **net of transaction cost**
   (`waiver_cost × claims`, charged at season aggregation). promotion-v3's frozen
   `metric_definition` wording does not mention netting. Both arms share the rule, so pairing
   stays valid, but the wording must be reconciled at C02 acceptance — via a promotion-v4
   amendment or an explicit accepted clarification. **The frozen manifest was not edited.**
3. **Calibration report shape.** C02 `calibration/report.json` nests
   `results[format][benchmark][arm]`; the C05 gate expects a flat benchmark list with v6−v5
   deltas. Adapter flattens ids to `<format>/<benchmark>` (4 rows) and computes
   `spearman_delta` / `weighted_rank_error_delta` from the per-arm values.
4. **Snapshot field names.** C02 `raw_sha256` / `retrieved_utc` → gate `snapshot_sha256` /
   `retrieval_utc`. Renamed by the adapter; identity content is preserved (verified 64-hex + UTC
   present for all four benchmarks).
5. **Unmappable attestations.** report.json carries **no** `deterministic_unit_failures`, **no**
   held-out confirmation, **no** season-evaluator no-regression evidence, and no structured
   missing-data-degradation flag (prose notes only). The adapter defaults all four to
   conservative FAIL; they can only be supplied explicitly (`attestations=`), which is the C02
   review's job, and report-derived fields cannot be overridden.
6. **Materiality undefined.** `player-calibration-v1.json` freezes
   `position_or_cohort_material_regression: 0` but defines no materiality rule. Adapter uses the
   strictest reading (any cohort `mean_abs_err` increase counts), which fails easily; a real rule
   needs reviewer definition.
7. **Cohort coverage.** C02 notes `team_change` and `low_availability` cohorts are not computable
   from the frozen snapshot; the calibration manifest lists them as mandatory cohorts.
8. **No machine-readable receipts.** C02 proves determinism and the live leak guard in tests but
   emits no receipt object. `probe_leak_guard` (injects a same-week row, demands `LeakageError`)
   and `deterministic_receipt_from_probes` regenerate the evidence mechanically; a dead guard maps
   to `leakage_detected: true` → BLOCK.
9. **promotion-v3 version collision, resolved by path (observed, not created here).** C02
   committed its calibration preregistration as `experiments/calibration/promotion-v3.json`; C05's
   frozen manifest is `experiments/promotion-v3.json`. No byte collision; renumbering remains
   deferred to integration as both sides' records already state.

## Verified behaviour on this branch (all synthetic/non-authoritative)

- 37 tests pass (26 cherry-picked C05 self-tests re-pass unchanged on the provisional C02 tree +
  11 adapter tests).
- The REAL provisional calibration report maps cleanly, matches C02's own `threshold_checks`
  (superflex improves; 1QB/2QB spearman declines), and **fails** the C05 calibration gate both
  with conservative defaults and even fully attested (the provisional deltas themselves miss the
  frozen `spearman_delta_min 0.0`) — so a clean synthetic points win still ends
  `do_not_ship_candidate`. Provisional C02 output cannot promote anything through this adapter.
- `probe_leak_guard` confirms the evaluator's leakage detector is live at `edbcc4d`.

Commands (from `engine/`, worktree-safe form):
`PYTHONPATH="$PWD" $HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python -m pytest
tests/test_promotion_adapter.py tests/test_promotion.py -q` → 37 passed;
`... -m ruff check blitz_engine/promotion/adapter.py tests/test_promotion_adapter.py` → clean.
