# E1 Compact Recommendations Implementation Plan

**Status:** implemented locally after E0q, E0, and E0a in the active v6 research worktree on 2026-08-29; uncommitted and unshipped. Automated populated-board acceptance is green; native browser zoom, VoiceOver speech, and the 192-pick complete state remain recorded manual QA gaps.

**Authority:** presentation-only. Shipped v5 candidate order, score, policy, and production authority
remain unchanged. C05 stays closed.

## Outcome

The draft-clock surface shows one clear primary, three compact alternatives, one reason each, and one
group-level evidence limitation. Every current explanation claim remains available through native
progressive disclosure. No scorer, simulation, database, market source, or objective changes.

## Evidence

- U0: mean 21.10 formatted explanation lines and 1,033 characters per four-candidate state;
- U1: mean 21.07 lines and 1,032 characters;
- about 13.98 lines are exact duplicates within a state;
- every traced candidate has degraded inputs;
- league evidence is never measured in the accepted trace payload;
- waiver/replacement churn has 0% candidate numeric support;
- stored market ADP is present for all four candidates in only about 60% of control states;
- in the 10%/30% opponent-market dropout stress, all-four ADP support falls to 13.86%/1.58% and
  the available top-four set changes materially; the compact surface must report the actual current
  evidence state rather than promise stability under missing room inputs;
- full artifact tracing adds about 42% campaign time and 6× serialized output, so E1 must consume the
  live `recs` already in memory rather than add capture or a second scorer;
- on the populated synthetic route, the current dense recommendation card measured about 873 px
  high at the overflow-expanded mobile layout and 1,028 px high in the 340 px desktop rail. The four
  candidate items were roughly 187–242 px each. Both cards exceed their 812/720 viewport heights;
  these are layout measurements, not cognitive-load outcomes, and E0a may change the mobile width;
- Q2/Q3 show that a five-row structured-claim fallback would cover every frozen candidate and cut
  formatter rows by 75.4%, but the trace omits live `Recommendation.reasons`, so it does not validate
  the preferred first-chip wording.

These measurements justify reducing default density. Human decision-time/workload benefit remains a
study hypothesis.

## In scope

- change `frontend/components/draft/LiveRecommendations.tsx`;
- add a small pure summary/evidence selector in the same file if needed;
- add focused tests using existing Vitest and `react-dom/server` primitives;
- preserve existing `Recommendation`, `recommendationClaims`, and `recs` input;
- use native `<details>/<summary>` for full evidence;
- improve semantic labels and touch/focus sizing within this component.

Responsive source-order/reflow repair remains the separate E0a native-semantics unit because it
changes `DraftWarRoom` grid composition and several existing semantics, not this component's compact
contract. The populated probe found 60 rows/155 tabbables ahead of recommendations and page overflow
at 320/375, so E0a must be green before E1. E1 then remains compatible with one recommendation
instance before the table on narrow screens and at the right-rail top on desktop.

## Out of scope

- compare selection/state (E2);
- new view tabs/lenses;
- recommendation order, scores, reasons, or scorer calls;
- next-turn survival or what-if;
- market-source provenance schema;
- persistence, analytics, database, feature-flag service, or deployment;
- rewriting explanation semantics or boom/bust uncertainty.

## Default information contract

### Group header

Retain `RECOMMENDED`, `YOUR PICK`, and `IN N` semantics. Add no confidence adjective. If any
candidate has degraded inputs or non-measured league evidence, show one compact group signal such as
`Limited evidence`; its accessible description explains that detailed support varies by candidate.

Do not claim freshness because `PlayerValue` has no source/as-of contract.

### Primary

Visible without expansion:

- ordinal and explicit text “Primary”;
- player link/name and position;
- draft action when it is the user's pick;
- one fidelity-checked reason. Do not automatically use the first existing chip: the current `vona`
  flag is driven by `equityImpact` rather than the next-turn replacement component, `run-risk` copy
  overstates descriptive evidence, and `ADP value` lacks source/as-of provenance;
- equity only when current code would show a positive value, labeled in visible plain language such
  as `+10 projected lineup pts` rather than the unexplained `eq` abbreviation;
- no new confidence badge. E0q removes the existing value-row uncertainty strip because it falsely
  labels VORP fields P10/median/P90 points. Preserve the one group-level calibrated-range-unavailable
  state; do not restore the strip in default or details.

Do not derive a new “best reason” score or confidence.

The one-line reason and every consequential qualifier must be visible text. A hover `title` may
repeat optional detail, but it cannot be the only location for source/date unknown, missing evidence,
or probability limitations; touch, keyboard, and screen-reader users must receive the same claim.

### Alternatives

Three alternatives remain visible in existing order. Each shows rank, name, position, one fidelity-
checked reason, and draft action under the same rule as today. Additional chips, full explanation text, and
uncertainty details move to disclosure; they are not deleted.

The alternative's one-line reason is the immediate tradeoff cue. E1 must not invent a comparative
numeric delta. A future E2 compare panel can show validated component differences.

### Full evidence disclosure

Use one group-level native `<details>` after the compact ordered list. Inside, provide a heading for
each candidate and include:

- every reason chip/title currently available;
- equity under the existing definition;
- every string returned by `recommendationClaims(recommendation)` in the same order and text;
- the post-E0q group limitation in ordinary visible text; no reconstructed range from value fields;
- candidate-specific degraded/missing state.

The default group signal consolidates repetition; expanded content remains faithful even when lines
repeat. Do not deduplicate expanded claims if deduplication would erase which candidate they apply to.

## Pure summary rules

Use a deterministic, presentation-only selector after a focused reason-fidelity test. Safe options
are a directly supported need/scarcity/upside chip or the first nonzero structured formatter claim
modeled by Q2/Q3. The plain-language `next-turn edge` label may be used only when driven by the
explanation's `immediate_lineup`/`marginalStarterValue` value and must not imply a survival
probability; run text must describe observed recent picks, and a
market-gap label must disclose unavailable source/date. Never fall back to an asserted “best” merely
because no chip fires.

The intended shape is:

```text
compactReason(recommendation) = first fidelity-eligible chip
                                else first supported nonzero structured claim
allClaims(recommendation) = recommendationClaims(recommendation)
groupLimited(recs) = any explanation.degradedInputs nonempty
                     or leagueEvidence.presentationState != measured
```

Do not choose a tradeoff by comparing component magnitudes in E1; those comparisons require E2
semantics/tests.

## Test-first sequence

### Task 1. Freeze current payload parity

Add focused tests before changing markup:

1. four input recommendations produce four visible compact candidates in the same order;
2. `recommendationClaims` returns the fixture's exact full strings;
3. summary selection rejects or truthfully relabels the current VONA/run/unknown-source cases,
   uses a supported structured fallback, and does not sort/mutate candidate order;
4. group evidence is limited when one candidate is fallback/unsupported and measured only when all
   are measured with no degraded inputs;
5. null stored ADP or uncertainty does not remove a candidate.
6. no essential qualifier is available only through hover/title text.
7. positive equity uses the same number but a visible projected-lineup-points unit; zero/negative
   behavior remains unchanged.

Repeat mixed-ADP fixtures in early, middle, and late recommendation shapes. The M1/M3 stress found
that 30% room-level dropout left all four ADPs in only 4.41% of first-third states and none in the
middle/final thirds; the fallback is not a late-round-only branch.

Run the focused test and confirm the new expected compact behavior fails before implementation.

### Task 2. Implement the compact default

Modify `LiveRecommendations.tsx` only:

- preserve an ordered list and stable `player.id` keys;
- visually distinguish primary without changing DOM order;
- render one reason by default;
- render group evidence state once;
- keep all four draft buttons under the current `onDraft && isMyPick` rule;
- maintain link/action accessible names;
- use `min-h-11`/equivalent 44 CSS-pixel action target without hiding the name;
- do not add `use client`, local state, effects, or a dependency.

Run focused tests.

### Task 3. Add native full-evidence disclosure

Render one `<details>` with a meaningful `<summary>` such as “Full evidence for 4 candidates.” Keep
candidate headings and their full current claim arrays. Ensure details follow the ordered list in DOM
order and opening it does not move the draft action.

Add server-rendered markup tests with the existing `react-dom/server` package for:

- one ordered list and four items;
- explicit primary label;
- native details/summary;
- every current full claim in expanded markup;
- no unsupported numeric probability/vendor text;
- draft buttons present only when authorized by props.

Avoid adding Testing Library/jsdom solely for this unit. Browser interaction/accessibility checks are
manual/future-tool gates, not a reason to add a dependency.

### Task 4. Information-density regression fixture

Create a small fixture derived from the existing structured test payload, not a copied production
artifact. Count default explanation rows separately from expanded claims:

- default formatted explanation rows fall at least 50% versus the current renderer contract;
- primary plus three alternatives remain visible;
- expanded claim multiset per candidate equals the pre-change output exactly.

“Pre-change” here means the post-E0 formatter baseline. E0 intentionally repairs the ambiguous
`immediate_lineup` sentence before E1 freezes byte parity; E1 must not restore the older wording.

Do not call the row reduction a cognitive-load improvement.

### Task 5. Full verification

Run:

```text
cd frontend
npm test -- --run
npm run typecheck
npm run lint
npm run build
```

Then run the existing C04/live-scoring/explanation focused contracts and confirm `DraftWarRoom.tsx`
still calls `scoreBoardWithExplanations` once in the unchanged memo.

Reuse E0a's dependency-free populated `draft-board-smoke.mjs` and direct installed Playwright for
320/375/640/1280 reflow, source/focus order, axe, long-name, and action-target regression. Also
verify real 200% browser zoom, keyboard order, VoiceOver/equivalent structure, high contrast, reduced
motion, and both themes manually; automated browser checks do not establish those results.

## Exact expected file set

Likely changed:

- `frontend/components/draft/LiveRecommendations.tsx`;
- `frontend/components/draft/LiveRecommendations.test.tsx` or a colocated `.test.ts` if pure/server
  rendering does not need JSX.

Change `frontend/lib/v6DraftExplanation.ts` only if the existing `recommendationClaims` contract
cannot support a pure group-evidence selector without duplication. Do not move types or create a
generic presentation framework preemptively.

E0 owns `reasons.ts`, `DraftWarRoom.tsx`, and formatter copy; E0a owns grid/source-order and the
populated smoke harness. E0q owns suppression of the false value-row quantile strip. A failing E1
test must not reopen those files/contracts unless it proves a defect and the plan boundary is
updated before editing.

No other file should change unless a failing existing contract proves it necessary.

## Acceptance criteria

- exact four IDs/order/scores/reason inputs preserved;
- no change to `DraftWarRoom`, `draftAI`, bridge, engine, queries, schema, or vendor data;
- default explanation rows at least 50% lower on the frozen fixture;
- full expanded claim parity per candidate;
- one group evidence signal; no hidden degraded state;
- no P10/P50/P90 or points range reconstructed from `PlayerValue.bust/value/boom`;
- weak/missing candidates remain visible and can have unfavorable/limited evidence;
- native semantic controls and ordered reading order;
- draft action remains reachable and correctly gated;
- with the recommendation region scrolled to its own top at 375×812, primary, three alternatives,
  group evidence, and the full-evidence summary fit within that viewport without clipping; global
  page chrome is outside this bounded density measure;
- focused and full frontend verification passes, aside from any explicitly documented inherited
  warning;
- manual browser/accessibility gate completed before release, not assumed from unit tests.

## Rollback

Revert the component/test change. There is no migration, persisted state, cache, scorer, model, or
artifact compatibility concern. The current dense renderer returns immediately with the same `recs`.

## Handoff to E2

Only after E1 is stable and the local study protocol is ready, add optional compare as a separate
unit. E2 may use all existing component values, but it must retain v5 order, per-cell unavailable
states, and “stored market ADP available for N of 4.” Do not fold compare state into E1.
