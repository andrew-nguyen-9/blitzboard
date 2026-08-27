# C05 — parked status and standing orders for C04 PASS (2026-08-27)

Append-only. Reconciliation commit `35cb31f49f59c9960aae58775474c16cbd4f6328` is independently
verified (Andrew's notice). This branch stays PARKED at accepted-C02 head `417af276`; the frozen
`promotion-v3.json` (sha256 `bbb241603a33697bff376b21a2e57e7e066c3c85186eaaab120485ec6bd941ab`)
is preserved byte-for-byte.

## Owned commit chain (cherry-pick source for the C04-time recreate, in order)

1. `82b7705` — promotion-v3 preregistration + gate machinery (14 files, all new)
2. `a79af01` — C02 adapter + mismatch record (3 files, all new)
3. `996125e` — rebase/transaction-semantics contingency plan
4. `f4c279f` — rebase receipt (accepted C02 recreate)
5. `35cb31f` — accepted-C03 hash reconciliation (independently verified)
6. this record's commit

## Blocked until official C04 PASS supplies the accepted combined head

No execution addendum, no candidate-SHA freeze, no rebase, no authoritative promotion.

## Checklist at C04 PASS (per `C05-adapter-rebase-plan.md`, amended by this directive)

1. Recreate: remove worktree/branch, `git worktree add -b v6/c05-c02-adapter ... <accepted
   combined head>`, cherry-pick the owned chain above.
2. **Verify path ownership**: every owned commit is new-files-only; any cherry-pick conflict
   means the combined tree claimed a C05 path — STOP and report, never resolve silently.
3. Rerun the 37 tests (`tests/test_promotion.py` + `tests/test_promotion_adapter.py`, worktree
   PYTHONPATH form) and ruff on the promotion package.
4. Re-check the started-points transaction-netting wording (`C05-c02-interface-mismatches.md`
   item 2, still OPEN) against the combined head and REPORT the disposition — v4 amendment or
   accepted clarification — BEFORE freezing candidate identity.
5. Only after 1–4: freeze the combined candidate SHA in `promotion-v3-exec-v1.json` (new file;
   promotion-v3.json itself is never edited).
