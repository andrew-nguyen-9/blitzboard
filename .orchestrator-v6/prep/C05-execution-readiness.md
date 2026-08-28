# C05 — execution readiness record for second freeze review (2026-08-27)

Append-only. Responds to the BLOCK in `C05-exec-v1-freeze-review.md` (review commit
`03fc3d87c951fd3b749ec41e9e6f842d97329cc9`). Preserved byte-for-byte and re-verified:
`promotion-v3.json` (`bbb24160…6bd941ab`), `promotion-v3-exec-v1.json` (`24e5e50a…c3b7ad`),
candidate SHA `7b3fd73578943b992402ad693259a3e92358da69`, all accepted policy code. No
authoritative fit or held-out execution ran. Correction commit: `9939179`.

## Blockers answered (engine/blitz_engine/promotion/execution.py + runner.py)

1. **Effective manifest.** `load_execution_manifest(root)` hash-verifies BOTH frozen files
   against pinned sha256 constants, cross-checks the addendum's manifest hash and candidate SHA,
   then injects exactly two values into an in-memory copy: the frozen candidate SHA and
   `evaluator.waiver_cost = 0.0` (any nonzero binding refuses with a promotion-v4 pointer). The
   on-disk manifest keeps its immutable null (asserted by test).
2. **C02 proxy mapping.** `run_arm` now routes through `adapter.arm_run_from_result`: accepted
   C02 `per_season_playoff`/`per_season_champ` become per-seat proxies in every arm receipt;
   pre-C02 results map to `None`. Verified by the reviewer probe (byte-identical copy, sha256
   `57954ae05d731ac4d538f512f6a352c488384a13ef26f7a0790df1e64e80a125`, passing unchanged).
3. **Checkout-verified arm receipts.** `produce_arm_receipt` asserts the arm checkout's actual
   `git rev-parse HEAD` equals the frozen arm SHA before anything runs (the C05 tooling tree is
   mechanically refused as candidate identity), executes the evaluator inside that checkout, and
   writes write-once, fit/confirm-separated receipts behind the `HeldOutGuard`.

## Rehearsal finding — the resolution trap, caught and closed

The first rehearsal produced IMPOSSIBLE receipts: the v5 baseline arm emitted C02 proxy fields
and both arms' deltas were exactly zero. Root cause (probe receipt in tooling history): the
venv's editable blitz_engine install registers a meta-path finder that OVERRIDES `PYTHONPATH`,
so both arm subprocesses silently imported the TOOLING tree's evaluator — the CLAUDE.md worktree
trap, now in subprocess form. The payload now strips editable finders, pins the checkout's
`engine/` first, purges preloaded modules, and hard-asserts `blitz_engine.__file__` is inside
the arm checkout, refusing the receipt otherwise. The corrupted first-run receipts were never
committed and were regenerated.

## Exact arm commands

From the tooling tree, `<venv>` = the main checkout's `pipeline/.venv/bin/python`:

    # control arm (baseline), one slice:
    git worktree add --detach <scratch>/arm-v5 01f01d3c5f9c00a046edd43707db75ce1426c0e8
    <venv> -c "from blitz_engine.promotion.execution import *; from blitz_engine.promotion.runner import HeldOutGuard; \
      e = load_execution_manifest('<tooling-root>'); \
      produce_arm_receipt('v5_shipped', '<scratch>/arm-v5', BASELINE_SHA, effective=e, \
        year=<Y>, league_id='<ID>', base_seed=<S>, n_seasons=8, stage='fit', \
        guard=HeldOutGuard(e['seasons'], e['held_out_seasons']), out_dir='<receipts>', \
        tooling_head=checkout_head('<tooling-root>'), authoritative=<bool>)"

    # candidate arm: identical with arm-v6 / CANDIDATE_SHA / 'v6_candidate'
    git worktree add --detach <scratch>/arm-v6 7b3fd73578943b992402ad693259a3e92358da69

(`PYTHONPATH=<tooling-root>/engine` for the driver; the payload subprocess pins the ARM
checkout's engine itself. `authoritative=True` stays prohibited until second freeze review.)

## Two-checkout rehearsal (NON-AUTHORITATIVE, receipts in `prep/c05-rehearsal/`)

Real baseline (`01f01d3c`) vs real candidate (`7b3fd735`) checkouts, slice
`t10-1qb-std-te0.0-b4-ir0` / 2021 / seed 2026082601 / n_seasons=1:

- both arm HEADs verified; board hashes IDENTICAL across checkouts (`d5a2eca5…`, CRN holds);
- pairing valid; started-points delta −10.26 on this single tiny slice (noise-level sample,
  justifies nothing — but proves the arms ran DIFFERENT evaluators);
- candidate proxies present; **control proxies absent** (v5 predates them) — see mismatch below.

## Gate evidence

- reviewer test unchanged: 2/2 pass (with `C05_PROD_ROOT` set to the tooling root);
- full promotion suite: **45 passed** (37 prior + 6 execution + 2 reviewer); ruff clean;
- hash/immutability: pins asserted in tests; frozen files re-hashed at commit time;
- leakage/determinism: leak-guard probe live (adapter test), null-CRN determinism receipts in
  `prep/c04-accepted/C05-dryrun-receipt.json`; `git diff --check` clean; worktree clean at stop.

## OPEN MISMATCH for second freeze review (not resolved here — not mine to decide)

**The control arm cannot emit playoff/championship samples**: the v5 baseline evaluator predates
them, so paired playoff/champ metrics are `None` and the frozen gate reads them as INCONCLUSIVE —
under promotion-v3 the authoritative verdict can then never exceed `preserve_v5`, regardless of
started-points evidence. Resolution options (reviewer/Andrew's call, each needing a promotion-v4
amendment or an accepted clarification): (a) compute control proxies by replaying v5-drafted
rosters through the accepted C02 evaluator (same CRN; changes the control's evaluator identity),
(b) restrict the secondary playoff/champ gates to candidate-vs-candidate comparisons, or
(c) accept the inconclusive reading as designed and gate promotion on the remaining criteria.

Stopped for second freeze review. No push, merge, or PR.
