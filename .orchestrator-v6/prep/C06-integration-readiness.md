# C06 integration readiness ledger

Prepared 2026-08-26. This is a coordination record, not authority to merge, push, open a
PR, release, delete a branch, or rewrite another session's worktree.

## Current immutable anchors

- v6 baseline: `01f01d3c5f9c00a046edd43707db75ce1426c0e8`
- accepted C01A production: `b81541c226dd5aeeacbe9ed79df927853a4b8954`
- accepted C01A review: `2be8a226769977c14df9bae135be43fa77dc8c09`
- production integration/open-C02 commit: `13ec3c2672010a81f8e72944bd891f855d1413b7`
- C03 preparation: `5741cd6ad2fcc0d9523f0a2034ca17123b670011`
- C04 preparation: `3f074134a59ab85164e40fc4799e418aa036d603`
- C05 preparation: `82b7705038a6fd420517bfadb77dea5357660927`; manifest
  `promotion-v3.json` SHA-256
  `bbb241603a33697bff376b21a2e57e7e066c3c85186eaaab120485ec6bd941ab`;
  worktree reported and independently observed clean.

## Remaining useful parallel work

All conflict-free build tracks are occupied: C02 production/review, C03 preparation,
C04 preparation, and C05 infrastructure. The only additional safe track is C06 readiness:
maintain this ledger, prepare combined-tree commands, identify overlap, and preserve a
producer-blind final audit. Do not begin a final C06 verdict while C02-C05 are incomplete.

## Integration rule

Do not merge whole preparation branches. Integrate reviewed, owned commits individually
onto `v6/bench-portfolio` in checkpoint order. Before every transfer, require a clean source
worktree, record source and target SHAs, inspect the commit's file list, and use a normal
cherry-pick or rebase without author rewriting.

1. Finish C02 on `v6/bench-portfolio`; require immutable `C02-claude.md` and independent
   `C02-codex.md` with `PASS`. Integrate no C03 behavior before that verdict.
2. Cherry-pick C03 preparation commit `5741cd6...` onto the accepted C02 production head.
   Rebase/continue the C03 implementation from that combined head. Because C03 production
   is assigned to Codex, a different session must perform the producer-blind checkpoint
   review.
3. After C03 `PASS`, cherry-pick C04 preparation commit `3f07413...`. Implement C04 from
   the accepted C03 head; use a separate reviewer for its checkpoint verdict.
4. Integrate C05 preparation commit `82b7705...` only after inspecting the combined tree
   for its three orchestration-path collisions (below). Its promotion package and tests are
   otherwise new paths. Run the
   authoritative C05 experiment only against the frozen, combined C02-C04 candidate SHA.
5. A failed or inconclusive C05 numerical candidate does not promote. Preserve the shipped
   behavior and document the result under a new immutable result path.
6. Begin C06 only after all prerequisite checkpoint records and hashes are in the combined
   tree. C06 must audit the combined tree, not the preparation branches in isolation.

Preparation commits may be integrated earlier only when their expected failures/skips remain
honest and do not make the repository's required default test commands fail.

## C06 combined-tree gate

At the final candidate SHA, capture clean receipts for:

- frontend build, typecheck, lint, full tests, and generated-artifact parity;
- pipeline full pytest and player-calibration reproduction;
- engine Ruff, full pytest, focused C02/C03/C05 reproduction, determinism, and leakage;
- canonical bench-shape source and generated-artifact hashes;
- mandatory league slices, especially `t14-2qb-std-te0.5-b4-ir1`;
- matched-seat/common-random-number integrity and held-out isolation;
- runtime and memory limits;
- repository cleanliness, forbidden paths, secret patterns, and `git diff --check`;
- comparison with the original checkout and immutable v6 baseline;
- requirement status as proven, contradicted, incomplete, or missing.

Landing remains blocked unless every required item is proven or Andrew explicitly removes it
from scope.

## Known integration hazards

- C03 and C04 prep commits are disjoint today, but their eventual production implementations
  converge on bench shape, draft scoring, explanations, and `DraftWarRoom.tsx`; retain strict
  C03-before-C04 sequencing.
- C05 manifests must never overwrite promotion v1/v2 or reviewer calibration preregistration.
- C05 adds `promotion-v3.json`, while C02 was previously assigned that name. If C02 commits a
  different v3 first, preserve it byte-for-byte and renumber the C05 manifest to v4 with all
  internal version/supersession/hash references updated in one explicit integration commit.
  Never resolve this by choosing one silently or overwriting either file.
- C05 also carries byte-identical copies of reviewer-owned
  `player-calibration-v1.json` and `player-calibration-v1.md`. If the combined branch already
  contains those exact hashes, retain the existing files and omit the duplicate additions. If
  hashes differ, stop: that is an immutable-preregistration conflict requiring adjudication.
- C05's reported synthetic dry runs are infrastructure proofs only. They cannot satisfy C05,
  clear the blocked 14-team slice, or justify a promotion verdict.
- Active worktrees contain legitimate uncommitted work. Never clean, reset, or switch them from
  another session.
- The main checkout currently contains unrelated user-owned changes/artifacts. Do not use it as
  an integration scratch tree or include those paths in v6 commits.
