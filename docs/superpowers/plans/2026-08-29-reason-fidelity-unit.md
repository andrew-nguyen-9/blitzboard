# E0 Recommendation-Reason Fidelity Repair Plan

**Status:** implemented locally after E0q in the active v6 research worktree on 2026-08-29; uncommitted and unshipped.

**Authority:** presentation/explanation repair only. Candidate scores, order, v5 authority, C05,
simulation, and production data remain unchanged.

## Outcome

Before BlitzBoard makes any reason more prominent in a compact clock-pressure UI, every compact tag
must describe the quantity that actually triggered it. This unit repairs three current semantics and
one fallback without adding a metric:

1. `VONA` is triggered by the existing `marginalStarterValue` explanation component, not by current-
   lineup `equityImpact`;
2. run copy reports recent observed concentration and does not instruct the user that it will continue;
3. the upside title says projection mean, not median or probability;
4. the ADP/rank-gap tag discloses that source/date are unavailable, and is ineligible as the compact
   headline until provenance exists;
5. the no-signal fallback says the player is a displayed alternative, not an asserted “best value”;
6. the expanded `immediate_lineup` formatter says that its value is projected lineup points over an
   estimated next-turn positional replacement, not generic current-lineup contribution;
7. expanded degraded-input copy translates internal snake-case reason codes into bounded user-facing
   limitations instead of exposing implementation identifiers under every candidate.

## Evidence and defect contract

`DraftWarRoom.tsx` currently passes `vona: equity >= 10`. `equity` is computed by
`equityImpact`, the increase in the optimal lineup against the roster as it stands now. The chip
title instead claims “value over the next available at this position.” That quantity already exists:
`scoreBoardWithExplanations` stores `marginalStarterValue` in the `immediate_lineup` component.

`detectRuns` observes the recent 1.5-round window. The current “A run is underway — get ahead of it”
title adds an unvalidated continuation/action claim. U0/U1 show that hot positions are common enough
to matter, but the human picker has no run-response parameter and no real history validates
continuation.

`valueFlag` compares stored `adp` and `rank`, but `PlayerValue` has no source, product kind, or as-of
field. “ADP value” may describe the arithmetic, but it cannot imply a named/current market.

The `upside` flag compares raw projection ceiling with raw projection mean (`boom > mean * 1.12`),
while its title says “median outcome.” No median is used, and the archived ceiling is not a calibrated
probability. Copy must use the actual mean/ceiling contract and preserve the separate warning that
season-total intervals cannot be substituted for ceiling-week semantics.

The structured formatter currently emits `Immediate lineup contribution: N.` for the component
produced by `marginalStarterValue`. That name omits both the next-turn replacement comparator and the
unit. Coverage, breakout, and redundancy component values are weighted score terms, so a future
compare surface must not place all components under a generic projected-points label. E0 only repairs
the visible immediate-lineup sentence; it does not rename the stable internal component key or
rewrite scoring terms.

The populated browser probe also rendered
`accepted_c02_c03_have_no_candidate_transaction_evidence` and `missing_league_key` directly in the
clock-pressure UI. Those are trace/provenance identifiers, not user explanations. The raw codes must
remain in the structured payload for auditability, while the formatter maps known codes to plain
limitations and maps an unknown code to one honest generic limitation without echoing or inventing
meaning. This is copy fidelity, not evidence promotion.

This is not a rare screenshot artifact. A direct count over the immutable U0 and U1 traces finds the
same distribution in each 11,400-candidate arm: 11,400 candidate-transaction codes, 5,760
`unsupported_evidence`, 5,640 `missing_league_key`, and six existing plain-text depth-order
limitations. Every traced candidate therefore carries at least one raw machine code today. The U0/
U1 evidence hashes are `3a2ca8b1…`/`16421499…`; this count is a deterministic descriptive query over
those receipts, not a new campaign or human-comprehension result.

## In scope

- correct the boolean feeding `WhyKey = "vona"` using the already computed explanation component;
- revise the `run`, `upside`, `value`, and empty-input fallback label/title strings;
- add pure contract tests for every reason input and order;
- add one live-integration source/fixture assertion proving score/order/scorer count do not change;
- relabel the existing expanded immediate-lineup formatter sentence with its next-turn comparator,
  projected-lineup-point unit, and uncalibrated-survival limitation;
- humanize the existing degraded-input line inside the same formatter, preserving raw payload codes,
  component state, score, and evidence IDs;
- expose a small pure `isCompactReasonEligible` helper only if E1 cannot safely filter `value` without
  duplicating the rule. Prefer a local predicate over a new type hierarchy.

## Out of scope

- changing `marginalStarterValue`, `equityImpact`, `detectRuns`, `valueFlag`, or score weights;
- adding survival probabilities, freshness, vendor names, or source ingestion;
- changing candidate order or the number of candidates;
- compact renderer, compare panel, persistence, analytics, or deployment;
- claiming that the repaired reason improves decisions.

## Test-first sequence

### 1. Freeze the mismatch

Add a fixture where current-lineup equity exceeds 10 but `immediate_lineup`/VONA is zero, and another
where the structured VONA component exceeds 10. The first must not emit VONA; the second must. The
test should fail against the current wiring.

### 2. Rewire only the displayed reason

In the existing `scored.map`, read the `immediate_lineup` component from `sp.explanation` and pass
`vona: value >= 10` to `reasonChips`. Do not call `marginalStarterValue` again. Assert the source still
contains one `scoreBoardWithExplanations` invocation and no extra scoring pass.

### 3. Make copy evidence-bounded

Recommended exact semantics:

| Key | Compact label | Accessible title | Compact-headline eligibility |
|---|---|---|---|
| `need` | `fills need` | existing factual open-slot text | yes |
| `vona` | `next-turn edge` | lineup value over the estimated next-turn replacement; not a survival probability | yes |
| `scarce` | `scarce` | existing starter-caliber supply text | yes |
| `run` | `recent run` | recent picks are concentrated at this position | yes, descriptive |
| `upside` | `upside` | projection ceiling is at least 12% above projection mean; not a probability | yes |
| `value` | `rank/ADP gap · source/date unknown` | BlitzBoard rank is 12+ picks earlier than stored ADP; source/date unavailable | no until provenance |
| fallback | `board alternative` | one of the four current BlitzBoard options | yes |

Keep `vona` as the internal key so the unit stays small, but do not require users to decode the
acronym under the clock. Expanded details may define “value over next available” after stating that
this is the current deterministic replacement estimate, not a calibrated survival probability.

Known expanded degradation mappings:

| Raw payload code | User-facing limitation |
|---|---|
| `accepted_c02_c03_have_no_candidate_transaction_evidence` | candidate-level waiver/churn evidence unavailable |
| `aggregate_only_no_candidate_transactions` | candidate-level waiver/churn evidence unavailable |
| `missing_league_key` | matching league evidence unavailable |
| `unsupported_evidence` | league evidence is not supported for this configuration |
| `missing_bye_metadata` | bye-week data unavailable |
| `missing_ceiling` | ceiling projection unavailable |
| `missing_authoritative_depth` | authoritative depth-role evidence unavailable |
| `depth chart order missing or non-authoritative` | authoritative depth-role evidence unavailable |
| any unknown nonempty code | additional evidence unavailable |

Deduplicate after mapping so two raw provenance paths do not produce repeated user text. Do not
display a vendor, timestamp, probability, or cause that is absent from the code. Tests retain and
assert the original raw codes on `payload.degradedInputs` separately from formatted copy.

### 4. Verify invariants

Run reason, live-scoring, live-integration, and full frontend tests, then typecheck, lint, and build.
Assert identical candidate IDs/order/scores for a frozen state before and after. The only expected
payload difference is explanation-chip key/copy where the old trigger was semantically wrong.

The expected formatter text changes are presentation-only. Freeze the exact immediate sentence and
known/unknown degradation mappings in the existing explanation/live-scoring tests and assert that
`componentTotal`, score, component key/value/state,
and candidate order are identical. Q2/Q3's row-count feasibility remains descriptive, but E1 must
take expanded-claim byte parity against the post-E0 formatter baseline rather than the old string.

## Exact files

- `frontend/components/draft/DraftWarRoom.tsx` — use the existing structured component for the VONA flag;
- `frontend/components/draft/reasons.ts` — bounded labels/titles and optional compact eligibility;
- `frontend/components/draft/reasons.test.ts` — exact copy/order/fallback contract;
- `frontend/lib/v6DraftLiveIntegration.c04.test.ts` — single scorer and source wiring assertion.
- `frontend/lib/v6DraftExplanation.ts` — truthful expanded label for the existing component only;
- `frontend/lib/v6DraftExplanation.c03Interface.test.ts` — exact label plus unchanged numeric/state
  contract; touch `v6DraftLiveScoring.test.ts` only if a pre-existing assertion there must be updated.

Do not touch engine, bridge, database, query, policy, or market-ingestion files.

## Acceptance

- next-turn-edge tag iff the declared structured next-turn-replacement component crosses the existing threshold;
- run copy is descriptive and contains no future/imperative claim;
- upside copy names mean rather than median and makes no calibrated-probability claim;
- rank/ADP tag states source/date unavailable and is not selected as the E1 compact headline;
- no essential limitation exists only in a hover-dependent `title` attribute;
- fallback makes no “best,” “optimal,” or vendor claim;
- expanded next-turn-edge text names its projected-lineup-point unit, estimated replacement
  comparator, and unavailable survival probability;
- expanded degraded limitations contain no raw snake-case/internal phase identifier, known codes
  map exactly, unknown codes degrade generically, and the structured raw payload remains unchanged;
- four IDs/order/scores and scorer-call count are unchanged;
- no new numeric field or second computation;
- targeted and full frontend gates pass;
- removal of the six-file bounded unit restores prior copy/wiring with no data migration.

## Handoff

E0q first suppresses the false draft quantile strip. After E0 is green, E0a repairs populated source
order/reflow/native semantics. E1 may then compact the default hierarchy using the repaired eligible
chips, with Q2/Q3's structured-claim selector as a tested fallback. E2 compare remains separate.
