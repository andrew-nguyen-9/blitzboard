# Draft Recommendation Uncertainty-Semantics Repair Plan

**Status:** implemented locally in the active v6 research worktree on 2026-08-29; uncommitted and unshipped.

**Authority:** presentation/data-contract repair only. No score, rank, candidate, projection model,
database, simulation, C05, or production-authority change is authorized.

## Outcome

Stop presenting the current VORP value row as a P10/median/P90 projected-points distribution. Until
a typed, calibrated projection snapshot reaches the draft page, show one honest group limitation:
`Calibrated projection range unavailable.` Keep the four v5 choices and every score/order unchanged.

This is a correctness repair, not a new uncertainty model. It is the smallest immediate unit and
precedes E0 reason fidelity, E0a native reflow, and E1 compaction so later disclosures do not preserve
a false probability/unit claim.

## Verified current path

1. `frontend/app/draft/page.tsx` calls `getAllPlayersByValue("vorp")`.
2. `DraftWarRoom.tsx` passes those `PlayerWithValue` objects to `LiveRecommendations`.
3. `LiveRecommendations.tsx` calls `playerUncertainty(player.value, null, "pts")` for every displayed
   candidate.
4. With no projection argument, `components/uncertainty/fromValue.ts` maps `value.bust`, `value.value`,
   and `value.boom` to P10, P50, and P90.
5. `RangeBar` announces and displays those as P10, median, and P90 projected points.

That adapter contract does not match the active data:

- Under `VorpEngine`, `boom` is projection ceiling minus replacement and `bust` is projection floor
  minus replacement. Upstream projector constructors commonly create raw floor/ceiling as nominal
  mean ± 1.28 stdev, but that probability/target method is not carried by the `PlayerValue` contract
  and the draft caller does not add replacement back. The active outer values are VOR, not the raw
  projected points claimed by the UI.
- `value` is a shaped ranking quantity (`VOR + 0.5 × upside` for the relevant branch), not a median
  projection and not necessarily between floor/ceiling in a distributional sense.
- Even under `MonteCarloEngine`, where `boom`/`bust` are simulated P90/P10 VOR, `value` is a
  mean-plus-upside ranking score rather than P50. The three-field fallback still cannot declare a
  median or interpolate a distribution.
- Passing the suffix `pts` does not restore raw projected-point units: the outer fields are VOR and
  the center is shaped draft value. A valid raw projection range would require a consistent
  replacement conversion and a declared target.

The repository's `PlayerValue` TypeScript contract correctly calls `boom`/`bust` ceiling/floor VOR,
while `fromValue.ts`, `rowUncertainty.ts`, and player tooltips contain stronger P90/P10 comments.
This is an internal semantic conflict, not evidence that the displayed distribution is valid.

A fresh focused baseline passed 21/21 tests: 18 shared quantile/adapter tests and three live draft
integration tests. One adapter test explicitly freezes `bust/value/boom` as the three fallback
points, while the live source test freezes the single scorer call. These passes prove the current
contract is reproducible; they do not make its draft labels semantically valid. E0q should change
only the draft caller and its renderer contract, leaving the shared 18-test audit boundary explicit.

## Why suppression is the smallest safe draft fix

The draft recommendation has no typed quantile payload, source/as-of time, target definition,
calibration receipt, or engine-kind discriminator sufficient to interpret the fields. Reconstructing
one in the component would repeat the same error. A generic confidence adjective would be worse.

Therefore the first unit should:

- remove `playerUncertainty(player.value, null, "pts")` and its `UncertaintyStrip` from
  `LiveRecommendations`;
- show one visible group-level limitation after the four candidates, not four repeated placeholders;
- preserve the existing value row for ranking/explanation inputs without relabeling it;
- leave the shared uncertainty adapter and player surfaces unchanged pending their own bounded audit.

The group limitation is useful because silent removal could imply that no uncertainty matters. It
must not say data are stale, missing from a named vendor, or low confidence; those facts are unknown.

## Test-first unit E0q — draft-only false-quantile suppression

### Exact files

- `frontend/components/draft/LiveRecommendations.tsx` — remove the invalid adapter/strip and render
  one visible `Calibrated projection range unavailable` limitation for the group;
- `frontend/lib/v6DraftLiveIntegration.c04.test.ts` — assert exact candidate/score/order/scorer
  parity and absence of the value-row quantile adapter on the draft path;
- add `frontend/components/draft/LiveRecommendations.test.ts` only if the existing server-render/source
  contract cannot prove one group limitation and no P10/P50/P90 claim. Add no UI test dependency.

Do not touch `draftAI.ts`, `score.ts`, `valueUnits.ts`, engine/pipeline code, database/query code,
`PlayerValue`, or the shared uncertainty components in U0.

### Failing tests first

Freeze a four-candidate fixture with non-null `boom`, `bust`, and `value`. Against current code, the
new assertions must fail because the renderer emits the invalid strip. Assert after the repair:

1. four candidate IDs, order, scores, links, reasons, and authorized draft actions are identical;
2. `scoreBoardWithExplanations` remains called once in `DraftWarRoom`;
3. no draft recommendation calls `playerUncertainty` with a value row and null projection;
4. no `P10`, `P50`, `P90`, `median`, probability, distribution, or `pts` range is derived from those
   three fields;
5. exactly one visible group limitation says calibrated projection range is unavailable;
6. the limitation is not hover-only and is announced in ordinary reading order, not as a noisy live
   alert;
7. null/non-null value fields do not drop a candidate or change score/order.

### Verification

Run the focused renderer/live-integration/explanation tests, then full frontend test, typecheck,
lint, and build. Reuse E0a's populated browser harness for 320/375/1280 visual and axe checks after
E0a exists; before then, use the disposable localhost procedure with an explicit limitation.

The post-E0q renderer is the baseline E1 must preserve in full-evidence disclosure. E1 may consolidate
the limitation with other group data state, but must not restore the old strip under `<details>`.

## Follow-on audit U1 — shared uncertainty surfaces

E0q intentionally does not rewrite a cross-product adapter while fixing the draft. Before changing
the player table or detail page, audit these paths separately:

- `frontend/lib/rowUncertainty.ts` uses the same value-row P10/P50/P90 fallback;
- `frontend/app/players/[id]/page.tsx` may have an actual projection row, but must prove the row's
  `floor`, `mean`, `ceiling`, and `stdev` target/units before a Gaussian or quantile label;
- `frontend/lib/playerTooltip.ts` calls boom/bust P90/P10 without checking engine kind;
- `frontend/components/uncertainty/fromValue.ts` permits both true projection inputs and ambiguous
  value inputs in one loose type.

U1 should first inventory live engine kinds and snapshot schemas, then split ambiguous inputs rather
than add booleans:

```text
ProjectionQuantileSnapshot
  player_id
  target                  season fantasy points | VOR | weekly points | other declared target
  unit
  quantiles[]             explicit probability/value pairs
  model_id/version
  source/as_of
  calibration_receipt

RankingValueSnapshot
  engine                  vorp | monte_carlo
  value/vor/replacement
  ceiling_vor/floor_vor
  rank/adp
```

Only the first type may reach `UncertaintyStrip`. Do not infer quantile probabilities from field
names such as floor/ceiling. Keep current raw fields available for value/rank explanations with their
actual units.

## Experiment-first reintroduction

Reintroduce a draft risk range only after a point-in-time snapshot proves:

- one declared target and horizon appropriate to the user question;
- explicit quantile probabilities, not renamed ceiling-week semantics;
- consistent raw projection or VOR units across every displayed point;
- calibration/coverage on out-of-time seasons and relevant rookie/incomplete-history strata;
- model/source/as-of provenance and an honest stale/missing fallback;
- no double discount with health/startability or draft-turn survival;
- comprehension testing that distinguishes projection range, health/startability, and next-turn
  availability.

Compare calibrated percentage plus out-of-N frequency wording against the qualitative unavailable
fallback. Measure target/horizon comprehension, appropriate reliance, and decision quality; do not
use acceptance or trust alone as success. Zhang, Liao, and Bellamy's FAccT experiment found that
confidence display could improve trust calibration without improving joint accuracy, in a different
binary task ([paper](https://doi.org/10.1145/3351095.3372852)). This is adjacent caution, not a draft
effect estimate.

## Reject or defer

- Reject `bust/value/boom` → P10/P50/P90 on the active VORP draft path.
- Reject adding replacement to all three and calling the result a distribution; the middle remains
  a shaped ranking score.
- Reject Gaussian quantiles from mean/stdev without a validated distributional/calibration contract.
- Reject relabeling season-total conformal intervals as the existing ceiling-week boom/bust feature.
- Reject a single combined “confidence” score across production, health, evidence freshness, and
  draft-turn survival.
- Defer new engine quantile publication until the point-in-time archival and calibration plans can
  supply real labels.

## Acceptance and rollback

E0q is accepted when the draft contains no false quantile/unit claim, the one group limitation is
visible and accurate, four candidates/order/scores/actions remain identical, and focused/full
frontend gates pass. Reverting the component/test unit restores the former presentation with no data
migration; because that presentation is semantically invalid, rollback is for diagnosis only, not a
safe release fallback. A safe operational fallback is the group limitation with no range.

Shipped v5 remains ranking authority throughout. U0 does not promote a model or reopen C05.
