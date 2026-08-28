# C04A-claude — bounded live recommendation correction

## Status

C04A correction committed for independent re-review. This record does not issue a checkpoint
verdict, integrate the branch, authorize C05, or reinterpret C02/C03 evidence.

## Identity

- accepted combined C03 base: `8694d98186e5800e5439725973bb8789ebdb2979`;
- preserved C04 checkpoint: `31030f812c349c46f9ef1d1345a65a6505560b2e`;
- C04 BLOCK review: `2dd08397869f0fc577af70b68c1fe12b76d2a799`;
- bounded C04A correction: `6d303a94fee2c640f9cc4815ea49dcaa5350cbd2`;
- branch: `v6/c04-c03-accepted`;
- checkpoint: the commit containing this immutable record.

`C04-claude.md` remains byte-for-byte unchanged from the preserved C04 checkpoint. No C02/C03
artifact, coefficient, promotion record, unrelated UI, or protected branch was changed.

## Correction

The real `DraftWarRoom` recommendation path now calls `scoreBoardWithExplanations` exactly once and
does not call `scoreBoard` independently. The explained scorer still owns its single shipped-policy
call. Direct equivalence coverage proves candidate order and numeric scores equal the shipped
`scoreBoard` output for identical inputs.

Each live `Recommendation` carries its structured explanation. `LiveRecommendations` renders
deterministic claims exclusively through `formatDraftExplanation`, including coverage details,
league provenance, unsupported/fallback states, and missing candidate-evidence degradation.

The C03 league key is derived from live team count, legal QB slots, scoring label, bench size,
normalized TE-premium evidence, and normalized IR evidence. A canonical key is emitted only when
every frozen factor is known and representable. Missing, custom, or out-of-domain factors produce a
descriptive custom key and therefore the resolver's explicit fallback; no canonical key is guessed.
Current imported configurations that do not supply TE-premium or IR evidence degrade explicitly.

No score/simulation pass, Monte Carlo operation, randomness, network call, or artifact generation
was introduced into the browser recommendation path.

## Verification

Executed in `.worktrees/v6-c04-c03-accepted` with that worktree's local dependencies:

```text
reviewer probe unchanged:
  C04_PROD_ROOT="$PWD" $HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python -m pytest -q
    $HOME/Documents/GitHub/blitzboard/.worktrees/v6-review/engine/tests/test_v6_c04_live_integration_adversarial.py
  1 passed

focused C04 frontend:
  vitest run v6DraftIntegration, v6DraftTrace, v6Explanation,
    v6DraftExplanation.c03Interface, v6DraftLiveScoring, v6DraftLiveIntegration.c04
  6 files passed; 59 passed; 4 skipped

full frontend:
  npm test
  61 files passed; 553 passed; 4 skipped

TypeScript: npm run typecheck — passed
lint: npm run lint — 0 errors; 1 pre-existing useEspnSync exhaustive-deps warning
production build: npm run build — passed
C03 generator:
  PYTHONPATH=engine $HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python
    scripts/generateBenchShapeArtifact.py --check — bench-shape parity exact
C03 shape/interface:
  PYTHONPATH=engine $HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python -m pytest -q
    engine/tests/test_v6BenchShapeProduction.py engine/tests/test_v6BenchShape_adversarial.py
    engine/tests/test_v6BenchShapePublicInterface_freeze.py — 19 passed
git diff --check — clean
```

The four visible skips are unchanged and remain limited to producer-issued paired outcome
identifiers absent from accepted C02/C03 (`per_season`, `per_season_h2h`,
`per_season_playoff`, and `per_season_champ`). They are not C03 artifact skips and no evidence was
invented to convert them.

## Stop

Stopping at this immutable C04A producer checkpoint for independent re-review. No integration,
push, merge, PR, experiment, release, or C05 execution occurred.
