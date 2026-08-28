# C02B-claude — response to C02A-codex BLOCK

## Identity

- base: `de42301a0ab98342ed967136b36ee0af71307aa2` (C02A head, the reviewed commit)
- branch: `v6/bench-portfolio`; head = the commit containing this file
- review responded to: `C02A-codex.md` at review commit `e5cd566` (verdict: BLOCK),
  supplemental remote evidence `52ccba9` (laptop-2 commit `0993a9c`)
- scope: EXACTLY the six C02B requirements. Accepted C02A cost/breakout behavior and
  the immutable `C02-claude.md` / `C02A-claude.md` records are preserved (an
  uncommitted draft supplement to C02A-claude.md was reverted before this work; its
  substance lives here and in the manifests). No integration, no C03 production, no
  push, no merge.
- git identity: Andrew; no assistant attribution; date 2026-08-27

## Requirement 1 — append-only manifests BEFORE code changes

Three append-only preregistrations, each committed alone and strictly before the
behavior it governs (v1 and every prior version preserved byte-for-byte):

- `waiver-realism-v2.json` (`b2e2f29`): one shared per-team weekly move budget +
  the explicit transaction-cost vs outcome-family reconciliation
  (`started_points`/`per_season` NET of the single accounting charge; H2H and the
  playoff/championship proxies ON-FIELD — seeding by wins with GROSS points; promotion
  experiments must declare net vs on-field per family and may not mix them).
- `waiver-realism-v3.json` (`a82db26`): roster-wide drop feasibility — the drop is the
  lowest forward-looking nonstarter with NO role-space/nominal-position requirement;
  the add must be slot-legal; post-swap lineup coverage may not decrease; a started
  body is replaceable only when no feasible nonstarter drop exists.
- `waiver-realism-v4.json` (`b6f081c`): the exact budget formula the laptop-2 suite
  semantics require — total weekly claims ≤ max(`waiver_moves_per_week`,
  `proactive_moves_per_week`), emergency ≤ `waiver_moves_per_week` drawing first,
  upside ≤ `proactive_moves_per_week` from the remainder (v2's "waiver_moves_per_week
  IS the budget" wording was contradicted by `limit=0, proactive_limit=1` needing to
  permit one upside claim, and is replaced append-only, not rewritten).

## Requirement 2 — roster-wide lowest-nonstarter drop

`_best_upgrade` no longer restricts drop candidates to the add's role space. The drop
is the lowest forward-looking nonstarter roster-wide (deterministic (projection,
index) order) — a dead or configuration-ineligible bench body (e.g. a WR in a lineup
with no WR-capable slot) is droppable for any legal add. Removing a nonstarter can
never reduce lineup coverage, so nonstarter drops are feasible by construction; the
explicit post-swap fill check binds on started-body drops, which remain allowed only
when no nonstarter exists (K/DST streaming preserved; dropping a slot's only possible
filler stays forbidden). The add must still be eligible for at least one actual
lineup slot. The `slots=None` reviewer-probe fallback is unchanged.

## Requirement 3 — one combined weekly allowance

`_run_waivers` enforces the v4 formula: a shared per-team weekly allowance of
max(limit, proactive_limit), decremented by every executed claim of either kind;
emergencies draw first and are additionally capped by `limit`; upside claims are
additionally capped by `proactive_limit`. With defaults (1, 1) an executed emergency
claim consumes the week and blocks a same-week upside claim. Distinct
emergency/upside counters and the season cap (`season_moves_cap`) are retained and
reconcile to `waiver_adds`.

## Requirement 4 — laptop-2 suite + production equivalents

- Reviewer suites run UNCHANGED from the reviewer tree against production code
  (worktree PYTHONPATH form): `test_v6_c02_remote_adversarial.py` **7/7 passed**
  (both previously red cases green: cross-role dead-body drop; combined weekly cap)
  and `test_v6_c02_decision_adversarial.py` **2/2 passed**.
- Production-owned equivalents added to `tests/test_waiver_realism.py`:
  `test_dead_bench_body_dropped_for_cross_role_upgrade` (direct + end-to-end: a
  config-ineligible bench WR is the roster-wide lowest nonstarter and is dropped for
  a legal RB, exactly one seat clearing the margin gate) and
  `test_combined_weekly_cap_production_equivalent` (defaults permit one total claim
  when an emergency and an upside opportunity coexist; the emergency wins the
  allowance). The two C02A-supplement budget tests
  (`test_emergency_consumes_the_shared_weekly_budget`,
  `test_budget_boundary_emergency_blocks_same_week_upside` with its no-emergency
  control and budget-2 branch) land in this commit as well.

## Requirement 5 — every frozen calibration threshold explicitly disposed

`.orchestrator-v6/experiments/calibration/threshold-disposition-addendum.json`
(append-only; frozen benchmark data untouched, no existing failure reinterpreted, no
coefficient promoted) completes the executed report:

- `deterministic_unit_failures` — MET. `unmatched_top_100_rate` — MET (0.0 everywhere).
- `spearman_delta_min` / `weighted_rank_error_delta_max` — FAILED on 1QB and 2QB, MET
  on superflex (as already recorded in C02; restated, not reinterpreted).
- `position_or_cohort_material_regression` (previously omitted) — **FAILED** under the
  conservative operationalization (the frozen manifest defines no materiality bar, so
  ANY regressing position/cohort counts): every comparison carries at least one
  regression (largest: superflex rookie +4.5, 2QB veteran_30+ +3.4, 1QB-ADP TE +3.53),
  including superflex despite its aggregate gains (QB −19.76). Full per-comparison
  delta tables are embedded in the addendum. Consequence: DO_NOT_PROMOTE — already the
  standing disposition.
- `season_evaluator_no_regression_tolerance` (previously omitted) — **INCONCLUSIVE,
  NOT EXECUTED**: the leakage-safe arm-vs-arm season comparison belongs to C05's
  preregistered matched-seat machinery (promotion-v3 at `82b7705`, candidate SHA
  null); running it un-preregistered here would break the experiment-freezing
  contract. Per the frozen manifest, inconclusive → PRESERVE_SHIPPED_VALUE; the
  evidence obligation transfers to C05.

Net disposition unchanged: `executed_report_only`, shipped constants preserved.

## Requirement 6 — records

`C02-claude.md` and `C02A-claude.md` byte-identical to their committed forms. This
file is the C02B record and is immutable once committed.

## Coefficients — none tuned

Player-value constants untouched. The evaluator changes are decision-rule structure
under the preregistered manifests; the only defaults remain margin 0.15 (frozen in
v1) and `waiver_cost` 0.0 (gate inert by default).

## Verification (this worktree)

- reviewer suites: remote **7/7**, decision **2/2**, both unchanged, against
  production code.
- engine: ruff clean on changed files; `tests/test_waiver_realism.py` **21 passed**
  (17 C02A-preserved + 4 supplement/production-equivalent); full suite
  **4144 passed, 1 skipped** (worktree PYTHONPATH form) — the bench-insurance
  contrast and every prior evaluator acceptance property under the corrected rule.
- pipeline: **157 passed** (untouched). frontend: untouched since the C02-certified
  492/492 at `edbcc4d`.
- `git diff --check` clean; reviewer worktree untouched.

## Stop

Stopping for independent re-review. No integration, no C03 production, no push, no
merge; the disposable C03 compatibility branch is its owner's to recreate from C02B.
