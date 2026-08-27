# C03-claude — whole-bench portfolio and shared bench-shape artifact

## Status

Implementation checkpoint committed for independent review. The deterministic implementation and
artifact gates pass, but the single authoritative experiment's preregistered disposition is
**`do_not_promote`**. This record does not issue a PASS or integrate the bench shape into live draftAI.

## Identity and commit chain

- accepted C02C base: `417af276dd4438d8a35f38d08bfc26206044925e`
- independent C03 preparation reapplied: `8e9a36d99e1646acea81e6a6b5ff2c76f36abbaa`
- accepted compatibility report: `9fbee0876444f48ece206c63c950284a0b923199`
- frozen public interface: `a3394b0a6c72174894bd8a44b33c702372903d11`
- preregistration v2: `bc4579cf8a0c7d9cf2045cc9678ecdda8dacf6e5`
- evaluator-adapter amendment v3: `685fcd1b3585203c199798d53fb32a1f72aa671f`
- reconciled interface-SHA amendment v4: `a17894c9bc2681719d82f851406a3d68a416d6df`
- deterministic implementation: `3f205663e2b5c7b70944574c2e2f7d41b31c050a`
- reconciled execution guard: `cde6518facef12fa483cadbcd684f9281a8c0745`
- evidence, canonical artifact, and browser lookup: `570d7611217bae313e87fa46a208bdcf02d2cfd5`
- checkpoint: the commit containing this record

The frozen interface files and experiment manifests v1-v4 were read cumulatively and remain
byte-for-byte unchanged.

## Implementation

The implementation enumerates every non-negative six-position composition whose sum is the exact
bench budget, scores the complete portfolio jointly, uses maximum matching for lineup substitution,
and adapts the accepted C02C point-in-time evaluator with shared waiver outcomes, paired metrics, and
deterministic seeds. Bench evidence is consumed only as finite soft marginal costs. It never becomes
a positional floor, ceiling, or legality rule.

The schema-v2 canonical fixture contains all 216 supported matrix keys. It has 8 measured rows, 207
interpolated rows, and one unsupported row. Missing, malformed, mismatched, and unsupported evidence
degrades explicitly to a conservative exact-budget composition and finite soft costs.

The checked-in TypeScript artifact is static browser data. The browser resolver has no Node,
filesystem, crypto, process, network, randomness, or simulation dependency. C04 explanation/UI and
live draftAI surfaces were not edited.

## Artifact identity

- canonical source receipt:
  `.orchestrator-v6/experiments/bench-portfolio-c03-source-v1.json`
- canonical source receipt SHA-256:
  `01734b796d605788bf6b6815d2484242a4c25a2fe1c0a148f173280d3efc7e2b`
- embedded `canonical_source_hash`: the same value
- canonical `fixtures/bench_shape.json` SHA-256:
  `f8a212e58b1b714e866c403e0caca07891adde8c7cb2984d788c3e950d279bda`
- generated TypeScript SHA-256:
  `a7aaf2cbfd593099bcb4b4c5f75a092f54db3e191bf7812b83897afc215a7cb9`
- authoritative results SHA-256:
  `3634b803859e63a1620f923b6fdc89a6b6d36ba56698882cbb07e773a9b02e5f`
- canonical fixture size: 343,266 bytes
- generated TypeScript size: 175,063 bytes, below the frozen 262,144-byte limit

## Authoritative experiment

The authoritative command was executed exactly once after the reconciled v4 guard was committed:

```sh
PYTHONPATH=engine "$HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python" \
  scripts/runC03BenchPortfolio.py --execute
```

Result: deterministic gates passed; runtime 48.684338 seconds; peak RSS 285.28125 MiB;
`blocked_slice_clear: false`; disposition `do_not_promote`.

Every mandatory slice conserved its bench budget and produced legal lineups, but every slice failed
at least one preregistered superiority threshold:

- `t10-1qb-half-te0.0-b4-ir0`
- `t10-superflex-half-te0.5-b8-ir1`
- `t10-2qb-ppr-te0.0-b8-ir0`
- `t12-1qb-ppr-te0.5-b8-ir0`
- `t12-superflex-std-te0.0-b4-ir1`
- `t12-2qb-half-te0.5-b8-ir1`
- `t14-1qb-half-te0.0-b4-ir1`
- `t14-superflex-ppr-te0.5-b8-ir0`
- `t14-2qb-std-te0.5-b4-ir1`

The last slice remains explicitly `unsupported`; it was not cleared by evidence. The first eight
rows are labeled `measured` to describe their provenance, not to claim promotion eligibility.

## Verification

Commands and results:

```sh
"$HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python" -m ruff check \
  engine/blitz_engine/value/bench_portfolio.py \
  engine/blitz_engine/value/bench_shape.py \
  engine/blitz_engine/value/roster_shape.py \
  engine/tests/test_roster_shape.py \
  engine/tests/test_v6BenchPortfolio_production.py \
  engine/tests/test_v6BenchShapeProduction.py \
  engine/tests/test_v6BenchShape_adversarial.py \
  scripts/generateBenchShapeArtifact.py scripts/runC03BenchPortfolio.py
# All checks passed.

PYTHONPATH=engine "$HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python" -m pytest -q \
  engine/tests/test_v6BenchPortfolio_production.py \
  engine/tests/test_v6BenchShapeProduction.py \
  engine/tests/test_v6BenchPortfolio_adversarial.py \
  engine/tests/test_v6BenchShape_adversarial.py \
  engine/tests/test_v6BenchShapePublicInterface_freeze.py \
  engine/tests/test_roster_shape.py engine/tests/test_waiver_realism.py
# 551 passed in 9.58s

cd frontend && npm ci
# added 426 packages in 17s

npm test -- --run lib/benchShape.test.ts
# 2 passed

npm run typecheck
# passed

npm run build
# passed; one pre-existing useEspnSync React-hook dependency warning

PYTHONPATH=engine "$HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python" \
  scripts/generateBenchShapeArtifact.py --check
# bench-shape parity: exact

git diff --check
# clean
```

The generator's isolated drift test also proves that a one-byte TypeScript change fails check mode.
Frontend dependencies were installed locally in this worktree; no other worktree's `node_modules`
was reused.

## Stop

Stopping at the committed C03 checkpoint for independent review. No authoritative rerun, C04 work,
live integration, push, merge, PR, release, or branch/worktree deletion was performed.
