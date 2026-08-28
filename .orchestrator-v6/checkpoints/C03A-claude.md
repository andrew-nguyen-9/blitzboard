# C03A-claude — enforce failed-candidate consumer disposition

## Status

Bounded C03A correction complete and committed for independent re-review. This checkpoint does not
change the official C03 `BLOCK`, reinterpret numerical evidence, or issue a promotion verdict.

## Identity and chronology

- accepted C02C production: `417af276dd4438d8a35f38d08bfc26206044925e`
- reviewed C03 checkpoint: `573e9ab2e127b6be79937c2c6cd32b5fc7227f3d`
- official C03 BLOCK review: `ff50f69325625fbef9c6f6ea89755e22a2e1e74c`
- reviewer contradiction correction: `03be8aa313ca778956cffb8bc4379a97efea75b3`
- exact amended reviewer files applied locally: `0da40d9954336665300c7577e7abb4222c462b8a`
- append-only disposition amendment: `8e4ff5fdc7083016c343bf2016aabbe0e310aa22`
- bounded C03A production correction: `1f70ed6b9f7ca599192f6637f0d90f3d5c473c97`
- checkpoint: the commit containing this record

The v5 disposition amendment was committed alone before source-v2, generator, artifact, resolver
test, or compatibility behavior changed.

## Correction

The immutable authoritative `do_not_promote` result now controls consumer eligibility:

- source-v1 remains immutable negative evidence;
- source-v2 records all nine candidate rows as `unsupported`;
- `interpolation_sources` is empty, so no uncleared candidate row can seed interpolation;
- all 216 canonical matrix rows are `unsupported` with explicit unsupported provenance;
- generated TypeScript names and hashes source-v2 exactly;
- engine and browser resolution returns `degraded: true`, `unsupported_evidence`, finite soft costs,
  and no hard cap for every canonical row.

The failed selected compositions are not copied into the corrected canonical artifact. Unsupported
rows use the already-frozen conservative exact-budget soft fallback.

## Accepted C02C preservation

`fixtures/bench_shape_c02c.json` is an exact byte copy of the accepted C02C fixture at
`417af276dd4438d8a35f38d08bfc26206044925e`. Its SHA-256 is
`b672610e291aa97f5be7853c16c2e53db201f74638257acc40e7c129c46ad2ee`.

Schema-v2 presence no longer removes those accepted bounds. `bench_bounds`, K/DST timing, and
`to_requirements` continue through the accepted C02C fixture, including its hard solver constraints.
An all-matrix test independently reconstructs the accepted interpolation and verifies every returned
bound. The C03 soft artifact is not activated as failed portfolio guidance.

No portfolio formula, experiment threshold, seed, numerical result, evaluator behavior, C04 surface,
or live draftAI path changed.

## Immutable evidence and hashes

- manifests v1-v4 retain SHA-256 `42da8d2c...`, `c6848cb0...`, `900d6b2f...`, and `912c4c4b...`;
- v5 disposition amendment:
  `d4210e9063b58daeb9ad39016d7ca2059b39230da8cd9ea3747c436103495709`;
- results-v1:
  `3634b803859e63a1620f923b6fdc89a6b6d36ba56698882cbb07e773a9b02e5f`;
- source-v1:
  `01734b796d605788bf6b6815d2484242a4c25a2fe1c0a148f173280d3efc7e2b`;
- source-v2:
  `58b611f5b768dc0b95867410ccd815be39e390cd2711a4f67f8e8844c43f9e90`;
- original C03-claude:
  `b81e98851bd48f4abed38face62e3255e6f5f916caafb0a46997e62f158c1fc2`;
- canonical fixture:
  `96cabb5f4db802237a0081e6effd40bdfa8548179ac3c8297464bf05ecbcdde8`;
- generated TypeScript:
  `208ecb3854bcecf4c1dc9eb5a7f8538542d523df79adb8e058bb29412f2ab0eb`.

The canonical fixture is 283,770 bytes. The compact generated browser artifact is 122,824 bytes,
below the frozen 262,144-byte gate.

## Verification

Amended reviewer gate, unchanged from `03be8aa`:

```sh
C03_PROD_ROOT=$PWD \
  "$HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python" -m pytest -q \
  engine/tests/test_v6_c03_checkpoint_adversarial.py
# 1 passed in 0.05s
```

Focused C03/C02C engine verification:

```sh
PYTHONPATH=engine "$HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python" -m pytest -q \
  engine/tests/test_v6BenchPortfolio_production.py \
  engine/tests/test_v6BenchShapeProduction.py \
  engine/tests/test_v6BenchPortfolio_adversarial.py \
  engine/tests/test_v6BenchShape_adversarial.py \
  engine/tests/test_v6BenchShapePublicInterface_freeze.py \
  engine/tests/test_roster_shape.py engine/tests/test_waiver_realism.py
# 556 passed in 11.60s
```

Other gates:

```sh
"$HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python" -m ruff check \
  engine/blitz_engine/value/bench_portfolio.py \
  engine/blitz_engine/value/bench_shape.py \
  engine/blitz_engine/value/roster_shape.py \
  engine/tests/test_roster_shape.py \
  engine/tests/test_v6BenchPortfolio_production.py \
  engine/tests/test_v6BenchShapeProduction.py \
  engine/tests/test_v6BenchShape_adversarial.py \
  engine/tests/test_v6_c03_checkpoint_adversarial.py \
  scripts/generateBenchShapeArtifact.py \
  scripts/generateC03ADispositionReceipt.py scripts/runC03BenchPortfolio.py
# All checks passed.

"$HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python" \
  scripts/generateC03ADispositionReceipt.py
# verified immutable receipt

"$HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python" \
  scripts/generateBenchShapeArtifact.py --check
# bench-shape parity: exact

cd frontend
npm test -- --run lib/benchShape.test.ts
# 2 passed

npm run typecheck
# passed

npm run build
# passed; one pre-existing useEspnSync React-hook dependency warning

git diff --check
# clean
```

The existing isolated drift gate also passed inside the focused suite and proves a one-byte generated
artifact change fails check mode.

## Experiment disposition

The authoritative C03 experiment was not rerun. Results-v1 remains `do_not_promote`; every mandatory
slice remains uncleared, and `t14-2qb-std-te0.5-b4-ir1` remains unsupported. C03A changes only how
that immutable negative result is exposed to consumers.

## Stop

Stopping at the immutable C03A producer checkpoint for independent re-review. No C04 work, live
integration, push, merge, PR, release, authoritative rerun, or branch/worktree deletion occurred.
