# C05 prep — unresolved dependencies on C02/C03/C04 (2026-08-26)

The authoritative v5-vs-v6 promotion experiment CANNOT run until every item below exists. The
machinery in `engine/blitz_engine/promotion/` enforces this mechanically where it can
(`evaluate_promotion(..., authoritative=True)` raises while `combined_candidate_sha` is null;
absent playoff proxies and absent calibration reports gate to `preserve_v5` /
`do_not_ship_candidate` respectively).

## From C02 (evaluator realism + calibration) — blocking

1. **Paired playoff/championship proxy metrics on `SeasonEvalResult`.** Today the result carries
   `started_points`, `h2h_win_rate`, `per_season` only. `ArmRun.playoff_proxy` /
   `championship_proxy` stay `None` until C02 lands; the manifest thresholds
   (`playoff_or_championship_ci95_lower = -0.002`) are already frozen and wired.
   Integration point: populate the two fields in `runner.run_arm` from the C02 result surface.
2. **Executed player-calibration report** satisfying every `player-calibration-v1.json`
   threshold, with frozen benchmark snapshots (retrieval UTC, content hash, match report) and
   held-out confirmation. Feed it to `evaluate_promotion(calibration_report=...)`; the expected
   shape is documented by `gates.calibration_gate` and exercised in `tests/test_promotion.py`.
3. **Proactive-waiver / transaction-cost / leakage-detection receipts** for the
   `deterministic_receipt` input (`invariants_pass`, `leakage_detected`,
   `nondeterminism_detected`).

## From C03 (bench portfolios / shared shape) — blocking

4. Versioned `fixtures/bench_shape.json` (schema_version, source_hash, evidence status, league
   key) and the cleared-or-still-blocked status of `t14-2qb-std-te0.5-b4-ir1`. The slice stays in
   `mandatory_high_risk_slices` with tolerance 0.0 either way.
5. Any change to the board corpus or league matrix invalidates the frozen hashes in
   `promotion-v3.json` `board_corpus.files` → requires a v4 amendment before running.

## From C04 (live integration) — blocking

6. Shared overfill lookup + explanation surfaces must be in the combined tree so the candidate
   arm's policy identity is the real shipped v6 stack, not a partial one.

## Final precondition

7. C02, C03, C04 each independently PASS; the combined candidate SHA is frozen in
   `promotion-v3-exec-v1.json` (new file, versioned, never editing promotion-v3.json); only then
   is `authoritative=True` legal. Dry-run results (see `C05-dryrun.md`) justify nothing.
