# C03-codex — independent whole-bench portfolio review

## Verdict: BLOCK

- accepted production base: `417af276dd4438d8a35f38d08bfc26206044925e`
- frozen interface: `a3394b0a6c72174894bd8a44b33c702372903d11`
- reviewed production head: `573e9ab2e127b6be79937c2c6cd32b5fc7227f3d`
- experiment implementation head: `cde6518facef12fa483cadbcd684f9281a8c0745`
- review order: acceptance criteria, implementation, artifacts, receipts, and independent
  adversarial execution first; `C03-claude.md` reconciled only after blind findings were frozen
  in `.orchestrator-v6/reviews/C03-blind.md`

## Proven requirements

The implementation exhaustively enumerates 126 four-slot and 1,287 eight-slot vectors, conserves
the exact bench budget, scores complete compositions, maximum-matches FLEX/superflex/2QB holes,
and reacts to the frozen league dimensions. The accepted C02C adapter is deterministic on the
focused reproduction and retains shared waiver outcomes and paired metric families.

Schema-v2 structure, exact source hashing, generated TypeScript parity, one-byte drift failure,
finite soft curves, browser-only static data, explicit fallback, runtime, and memory gates are
proven. The known `t14-2qb-std-te0.5-b4-ir1` row remains explicitly unsupported. Frozen interface
and experiment v1-v4 blobs are unchanged, chronology is linear, ownership is bounded, Git identity
is Andrew's, and both producer and review worktrees were clean at review start.

Independent focused verification: **547 passed**, Ruff clean, exact generator parity green, and
`git diff --check` clean. Producer receipts and hashes reconcile.

## Blocking contradiction: failed candidate is published as supported guidance

The authoritative experiment is valid negative evidence: `disposition = do_not_promote`; every
mandatory slice fails at least one preregistered superiority threshold; the blocked slice fails
again. Frozen v1/v2 failure semantics require `DO_NOT_PROMOTE_PRESERVE_C02C_BEHAVIOR`.

The immutable source nevertheless labels eight failed candidate selections `measured`. The
generator publishes those exact selections plus 207 interpolations as non-degraded schema-v2
guidance. The frontend resolver exposes no separate promotion-eligibility state and will return the
failed rows for scoring. In the engine, schema v2 also makes `to_requirements` drop the accepted
C02C independent bench bounds entirely. Therefore integrating this checkpoint changes accepted
behavior using a candidate whose promotion gate failed.

Calling `measured` provenance rather than eligibility does not resolve the observable behavior:
the frozen interface has one evidence status, and consumers apply `measured`/`interpolated` rows
without degradation. The reviewer-owned acceptance probe fails deterministically at the source
status assertion. Numerical failure is not being re-litigated; its frozen disposition is being
enforced.

## Required C03A correction

1. Preserve experiment manifests v1-v4, results-v1, source-v1, and `C03-claude.md` byte-for-byte.
   The negative result remains harvested evidence and must not be rerun or reinterpreted.
2. Add an append-only disposition amendment before correction behavior. It must bind
   `do_not_promote` to consumer eligibility: failed candidate selections may be retained as
   historical measured provenance, but cannot be emitted as non-degraded production guidance.
3. Publish a new immutable source/disposition receipt version in which every uncleared candidate
   row resolves `unsupported`; interpolation may not originate from an uncleared row. Regenerate
   the canonical and browser artifacts from that new receipt with exact parity and explicit
   degradation.
4. Preserve accepted C02C production behavior. Schema-v2 presence must not silently remove the
   accepted legacy bounds or otherwise activate failed portfolio values. If legacy compatibility
   needs a separate immutable input, add it explicitly and prove byte identity to accepted C02C.
5. Run the reviewer test unchanged, all prior C03/C02C gates, schema/hash/parity/drift tests,
   frontend resolver tests, TypeScript/build, Ruff, full focused engine verification, and
   `git diff --check`. Add a direct test that a global `do_not_promote` result cannot yield a
   measured/interpolated non-degraded consumer resolution.
6. Write immutable `C03A-claude.md` and stop for re-review. Do not integrate, begin a C04
   checkpoint, rerun the authoritative experiment, push, merge, or open a PR.

No portfolio formula, experiment threshold, seed, numerical result, C02 evaluator behavior, C04
surface, or unrelated production path is in scope for C03A.
