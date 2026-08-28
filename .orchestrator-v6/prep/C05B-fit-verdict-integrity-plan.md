# C05B — fit-verdict integrity — Implementation Plan

> REQUIRED SUB-SKILL: superpowers:executing-plans (inline TDD). Checkbox steps.

**Goal:** Replace C05A's rubber-stamp fit-verdict with one that proves the complete authoritative
fit frame, validates every receipt, consumes a hash-pinned fit-analysis report produced through the
frozen promotion gates, and emits `pass` ONLY when that report's verdict is `promote` — otherwise
BLOCK / preserve_v5. Never turn missing or failed evidence into pass.

**Architecture:** All changes in `harness_v4.py` + tests. `evaluate_promotion`/`report_hash`
(gates.py) are the frozen fit-analysis producer; C05B consumes their output, it does not reimplement
gates. C05A corrections and all frozen files stay byte-for-byte intact.

## Global Constraints (verbatim)

- C05 parked, v5 preserved. No authoritative run, policy bridge, new manifest, calibration
  reinterpretation, merge, or PR. (Push allowed for review transport — not in the forbidden list.)
- Preserve every frozen file (manifests, execution.py, runner.py, manifest.py, gates.py, stats.py,
  season_eval.py) and all accepted C05A corrections byte-for-byte. C05B only edits the two
  fit-verdict functions and adds fields/functions additively.
- Base: `ce0758b` (C05A head). Branch/worktree: `v6/c05b-fit-verdict-integrity`.
- Frozen frame: arms {v5_shipped, v6_candidate}; fit years {2021, 2024}; 216 mandatory league ids;
  base seeds {2026082601..04}; measurement SHA `7b3fd735…`; n_seasons 8; one measurement receipt per
  (arm, year, league_id, base_seed) cell ⇒ **3456 receipts / 1728 pairs**.
- Req 8's reviewer dummy-receipt probe is copied byte-for-byte from `b7de57f`.

## Frozen producers consumed (do not reimplement)

- `gates.evaluate_promotion(manifest, arm_pairs, stage="fit", authoritative=True, ...) -> PromotionReport`
  — verdict ∈ {BLOCK, do_not_ship_candidate, preserve_v5, promote}.
- `gates.report_hash(report)` / `canonical_report_json` — byte-stable pin.
- `runner.ArmRun`, `runner.pair_slice`; manifest `thresholds`/`limits`/`calibration_gates`.

## New/changed API in `harness_v4.py`

- `expected_fit_cells(effective) -> set[tuple[str,int,str,int]]` (3456).
- `_measurement_cell_key(doc) -> tuple[str,int,str,int]`.
- `validate_fit_measurement_receipt(doc, effective) -> tuple` (req 3, returns cell key).
- `assert_complete_fit_frame(docs, effective) -> None` (req 2: no missing/dup/extra).
- `validate_fit_analysis_receipt(fit_analysis, effective, *, measurement_shas) -> str` (req 4/7,
  returns the report verdict).
- `write_fit_verdict(out_dir, *, effective, measurement_paths, fit_analysis) -> Path` — REWRITTEN
  (req 1/5/6): derive verdict; `pass` only when report verdict == `promote` and all integrity holds.
- `require_fit_verdict(out_dir, effective) -> dict` — EXTENDED (req 7): confirm requires
  verdict==`pass`, re-validates the fit-analysis receipt hash + complete pinned input set.
- `measure_arm(...)` — additively stamp `n_seasons` and `effective_v4_manifest_sha256` on
  measurement receipts (needed by req 3), preserving all existing fields.

---

### Task 0: worktree ready + preservation baseline (DONE for worktree; record hashes)

- [ ] Record frozen baseline: manifests + execution.py + runner.py + manifest.py + gates.py +
      stats.py + season_eval.py + `harness_v4.py`-C05A-accepted-symbols to `/tmp/c05b-frozen-baseline.txt`.
- [x] Copy reviewer probe byte-for-byte from `b7de57f`.

### Task 1: measurement-receipt frame key + additive receipt fields

- [ ] Test: `measure_arm` authoritative receipt carries `n_seasons` and `effective_v4_manifest_sha256`
      (unit via a crafted receipt dict + `_measurement_cell_key`).
- [ ] Implement `_measurement_cell_key(doc)` (reads arm_run.arm/year/league_id/base_seed).
- [ ] Additively stamp `n_seasons=int(n_seasons)` + `effective_v4_manifest_sha256` in measure_arm's doc.
- [ ] Commit.

### Task 2: per-receipt validation (req 3)

- [ ] Tests (refusals): non-authoritative; wrong stage; arm/SHA mismatch; measured_by_sha ≠ frozen;
      manifest/exec/effective-v4 hash mismatch; missing pairing key; missing draft_receipt_sha256;
      n_seasons ≠ 8. Each raises `ExecutionError`.
- [ ] Implement `validate_fit_measurement_receipt(doc, effective)` — returns cell key on success.
- [ ] Commit.

### Task 3: complete-frame enumeration (req 2)

- [ ] Tests: `expected_fit_cells` has 3456; `assert_complete_fit_frame` refuses a set with a missing
      cell, a duplicate cell, and an extra (off-frame) cell; accepts a synthetic complete set.
- [ ] Implement `expected_fit_cells` + `assert_complete_fit_frame` (multiset equality, explicit
      missing/duplicate/extra messages).
- [ ] Commit.

### Task 4: hash-pinned fit-analysis consumption (req 4)

- [ ] Tests: `validate_fit_analysis_receipt` refuses a receipt whose embedded `report_sha256` ≠
      `report_hash(report)`; whose report stage ≠ fit or not authoritative; whose pinned
      measurement-sha set ≠ the frame's; returns the report verdict on success.
- [ ] Implement `validate_fit_analysis_receipt(fit_analysis, effective, *, measurement_shas)`.
- [ ] Commit.

### Task 5: rewrite `write_fit_verdict` (req 1/5/6)

- [ ] Tests: a complete frame + a `preserve_v5` fit-analysis ⇒ verdict `preserve_v5` (NOT pass);
      a `BLOCK` report ⇒ `BLOCK`; a `do_not_ship_candidate` report ⇒ that; an incomplete frame ⇒
      refuse (never pass); pass ONLY when report verdict == `promote` and every integrity check holds.
- [ ] Implement: `write_fit_verdict` runs `assert_complete_fit_frame`, validates every receipt,
      `validate_fit_analysis_receipt`, then `verdict = "pass" if report_verdict == "promote" else
      report_verdict`. Write-once. Removes the unconditional `"verdict": "pass"`.
- [ ] Commit.

### Task 6: confirm gate re-validates fit-analysis + pinned inputs (req 7)

- [ ] Tests: `require_fit_verdict` refuses when verdict ≠ pass; refuses when the pinned fit-analysis
      receipt hash drifts; refuses when any pinned input is missing/altered; passes on a valid
      complete pass record.
- [ ] Implement: extend `require_fit_verdict` to re-hash the fit-analysis receipt and re-verify every
      pinned measurement sha + auxiliary receipt sha.
- [ ] Commit.

### Task 7: adversarial suite + preservation + checkpoint (req 8/9)

- [x] Add completeness, duplicate, pairing, numerical-failure, calibration-failure adversarial tests
      and copy the reviewer dummy-receipt probe unchanged.
- [x] Full non-authoritative suite green; frozen producer-authored Ruff scope clean.
- [x] Prove frozen files + C05A-accepted symbols byte-for-byte (`shasum -c`); `git diff` shows only
      additive `harness_v4.py` + test files.
- [x] Write `.orchestrator-v6/checkpoints/C05B-fit-verdict-integrity.md`. Commit. Stop for re-review.

## Self-Review

- Spec coverage: req1→T5, req2→T3, req3→T2, req4→T4, req5/6→T5, req7→T6, req8→T7,
  req9→T7. All frozen producers consumed, not reimplemented.
- The verbatim reviewer probe is present and passes; checkpoint is final for independent re-review.
