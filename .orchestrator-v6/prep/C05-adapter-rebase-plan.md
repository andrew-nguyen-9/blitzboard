# C05 adapter — rebase and transaction-semantics contingency (2026-08-26)

Directive from Andrew: preserve adapter commit `a79af019bafbaaa03cf3d55dd46600b5097840df`
unchanged; expect (a) this disposable branch to be rebased onto a revised C02 head and (b) the
C02 transaction-cost semantics to change during review.

## Preservation

`a79af01` is frozen — no amend, no rewrite. Any adapter change lands as a NEW commit on this
branch (this file's commit is the first such). The C05 prep commit `82b7705` and its manifest
remain byte-identical as before.

## Rebase protocol (when C02 moves to a new provisional/accepted head)

The branch is disposable by design: do not force-rebase in place. Recreate it:

1. `git worktree remove .worktrees/v6-c05-c02-adapter` and delete `v6/c05-c02-adapter`
   (authorized only when Andrew orders the rebase; this session deletes nothing).
2. `git worktree add -b v6/c05-c02-adapter .worktrees/v6-c05-c02-adapter <new-C02-head>`
3. `git cherry-pick 82b7705 a79af01 <follow-up commits>` — all commits touch only new files, so
   the expected conflict surface is empty; any conflict signals C02 now claims a C05 path and
   must be reported, not resolved silently.
4. Re-run: `PYTHONPATH="$PWD" <main pipeline venv>/python -m pytest tests/test_promotion.py
   tests/test_promotion_adapter.py -q` from `engine/`.

## Transaction-semantics change: expected blast radius

The adapter mapping is semantics-agnostic — `arm_run_from_result` copies `per_season` verbatim,
whatever netting rule produced it. When the semantics change, the expected work is:

| Artifact | Action |
|---|---|
| `adapter.py` `INTERFACE_MISMATCHES` item 2 (net-of-transaction-cost wording) | update text to the new rule in a new commit; the mapping code should not change |
| `test_promotion_adapter.py::test_interface_mismatches_are_recorded` | keeps asserting a "transaction cost" entry exists; update alongside |
| promotion-v3 `metric_definition` wording | still reconciled ONLY via a promotion-v4 amendment or an accepted clarification at C02 acceptance — never by editing v3 |
| fabricated results in tests | unaffected (they fabricate `per_season` directly) |
| `probe_leak_guard` / receipts | unaffected unless the `evaluate_rosters` signature changes; a rebase test failure is the intended detector |

Watch item: if revised C02 changes what `per_season` *contains* per seat (e.g. splits gross
points and cost into separate arrays), `arm_run_from_result` gains a mapping decision — freeze it
in the mismatch record first, then implement, in that order.
