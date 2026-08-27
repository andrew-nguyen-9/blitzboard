# C04-claude — live scoring explanations and accepted bench-shape consumption

## Status

C04 production checkpoint committed for independent review. This record does not issue a PASS,
integrate the branch, authorize C05, or reinterpret C02/C03 evidence.

## Identity and transfer chain

- accepted combined C03 integration base: `8694d98186e5800e5439725973bb8789ebdb2979`;
- transferred C04 preparation commits, individually and in order:
  `93d59ce85649c20b5e0590aebe5aed18fe1af467`,
  `41cca5adfee06f0f27fe24d3f471fdb483e4922b`,
  `9539cee35e6fd30dbc5c22667975b8399d5ce870`, and
  `1d1f388f393216bc5bbf12f834d02683b7bbe931`;
- accepted-base cherry-picks: `b9c66c5`, `dd73a8e`, `f5c2bed`, `2e3fb7d`;
- C04 accepted-C03 implementation: `bf8591a288ca4d45bfb84a8e6b75363d4feb00d7`;
- branch: `v6/c04-c03-accepted`;
- checkpoint: the commit containing this immutable record.

No disposable branch was merged. All four transfers were conflict-free. Andrew's configured Git
identity was preserved and no assistant attribution was added.

## Production surface

`frontend/lib/v6DraftLiveScoring.ts` is the live C04 seam. It calls the shipped deterministic
`scoreBoard` once, decorates each result, and does not replace or duplicate the draft policy. Each
payload contains:

- immediate legal-lineup contribution and assignment evidence;
- candidate-aware bye/absence value plus covered week, slot, and starter records;
- structured contingent starter, evidence kind, inheritance probability, value, and degradation;
- breakout value with an explicit ceiling-unit basis;
- candidate replacement/churn evidence when supplied, otherwise an explicit unsupported/null state;
- accepted C03 soft redundancy cost and provenance;
- component total, shipped score, and named `legacyPolicyResidual` so reconciliation is exact;
- deterministic producer-blind trace and zero simulation/rollout/Monte Carlo counters.

Formatting in `v6DraftExplanation.ts` is UI-independent and derives claims only from structured
fields. The browser path imports no engine, Python, filesystem, crypto, network, randomness, or
simulation implementation.

## Accepted C03 disposition

C03's canonical artifact is intentionally all `unsupported` following its authoritative
`do_not_promote` disposition. C04 consumes that result honestly:

- canonical rows present as `unsupported`, `degraded: true`, `unsupported_evidence`;
- missing/custom keys present as `fallback`, `missing_league_key`;
- finite marginal costs remain soft and never reject a legal candidate or become a hard cap;
- unsupported costs do not silently change the shipped total; score reconciliation retains the
  shipped policy as authority;
- canonical/generated source hash and row-key parity are executed in C04 tests;
- no measured or interpolated C03 evidence is invented.

## Accepted C02 boundary

Accepted C02/C03 does not publish candidate add/drop records or stable producer-issued paired
outcome identifiers. C04 therefore defaults replacement/churn to `null`, `unsupported`, and
`accepted_c02_c03_have_no_candidate_transaction_evidence`. An explicit external candidate record can
be adapted without browser recomputation, but aggregate waiver counters never become candidate
value.

Four visible test skips remain, one for each paired outcome family (`per_season`,
`per_season_h2h`, `per_season_playoff`, `per_season_champ`), solely awaiting a producer-issued
identifier. These are not C03 dependency skips and cannot be made truthful from accepted data.

## Acceptance coverage

Executable coverage includes 1QB, superflex, pure 2QB, four/eight benches, TE premium, IR/no-IR,
custom/missing-key fallback, legal starters, multi-QB scarcity, K/DST anti-hoarding, soft-no-cap
behavior, coverage eligibility and same-bye negatives, contingent-role false positives, ambiguous
depth, unsupported evidence presentation, missing-input degradation, structured-claim formatting,
score reconciliation, trace determinism, artifact parity, and browser runtime guards.

## Verification

Run in `.worktrees/v6-c04-c03-accepted` after local `frontend/npm ci` (426 packages):

```text
focused C04/C03 frontend: 6 files passed; 51 passed, 4 skipped
full frontend: 60 files passed; 543 passed, 4 skipped
frontend typecheck: passed
frontend lint: 0 errors; 1 pre-existing useEspnSync exhaustive-deps warning
frontend production build: passed
C03 generator --check: bench-shape parity exact
C03 focused shape pytest: 19 passed
git diff --check: clean
```

No C04 production experiment, authoritative rerun, push, merge, PR, release, or protected-branch
change occurred.

## Stop

Stopping at the immutable C04 producer checkpoint for independent review. Integration and C05 remain
unauthorized until the independent C04 verdict and normal checkpoint protocol permit them.
