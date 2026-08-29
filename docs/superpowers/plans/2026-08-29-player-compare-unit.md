# E2 Player Compare Implementation Plan

**Status:** executable plan only after E0q, E0, E0a, and E1 are green. Do not implement in this research phase.

**Authority:** presentation-only. v5 primary, top-four order, scores, and manual pick authority remain
unchanged. Compare never selects, reranks, or autodrafts.

## Outcome

Let the user compare two to four already-displayed candidates on a small set of faithful tradeoffs:
next-turn lineup edge, bye/absence assignments, breakout score contribution, redundancy cost,
market-gap availability, and evidence state. The user can answer “why A instead of B?” without
reading four full cards.

## Evidence

- U0/U1 primary identity matches only 63.12% across opponent assumptions, while the top-four set is
  more stable (Jaccard 0.647). Showing alternatives is more robust than asserting one certain answer.
- Immediate-lineup, coverage, and breakout maxima often identify a different candidate than v5.
- Q0/Q1 find multiple nondominated choices on those three evidence-qualified components in about
  47% of states, with mean frontier size 1.57.
- The primary is dominated on those three displayed components in about 26% of states, but that is
  not an error label because v5 includes residual/constraints outside the panel.
- Candidate market ADP exists in only about 77% of rows and all four ADPs in about 60% of states.
- Under the synthetic 10%/30% market-dropout stress, all four displayed ADPs remain available in
  only 13.86%/1.58% of states; primary match to the complete-input room falls to 32.11%/15.35%.
  Because dropout changes intervening opponent picks, this is a whole-room failure stress—not the
  causal effect of blanking one fixed compare cell.

These results justify a comparison surface. They do not validate a new score, Pareto badge, market
probability, or user-outcome benefit.

## In scope

- compare two to four members of the current `recs` array;
- preserve source order and explicit “v5 order” labels;
- show values from existing `DraftExplanationPayload.components` with state and units;
- show unknown/missing as text, never zero;
- show a single coverage summary such as “stored market ADP available for 2 of 4; source/date unavailable”;
- native, keyboard-operable selection and disclosure;
- responsive table at wide widths and stacked labeled cards when a table cannot remain usable;
- focused component/formatter/accessibility-contract tests.

## Out of scope

- scoring, reranking, Pareto-frontier labels, recommendation mutation, or hidden objectives;
- next-pick survival, what-if simulation, opponent forecasts, or run continuation;
- vendor names, freshness, consensus, or recommendation attribution without provenance;
- persistence, analytics, database, engine, bridge, or deployment;
- deciding which player the user should pick.

## Data contract

For each candidate, derive cells from the existing object only:

| Row | Source | Display contract |
|---|---|---|
| v5 order | index in immutable `recs` | `Primary`, `#2`, `#3`, `#4`; never “confidence rank” |
| player | `player` | link, name, normalized position |
| next-turn lineup edge | `immediate_lineup` component, produced by `marginalStarterValue` | projected optimal-lineup points over the estimated same-position player available next turn; not current-lineup equity and not survival probability |
| absence coverage | `coveredAssignments` plus `bye_absence_coverage` component | lead with concrete slot/week assignments; the component value is a policy-weighted score contribution, not raw expected starts or a health probability |
| breakout | `breakout_option` plus `upsideBasis` | label the numeric value as a weighted score contribution and show its basis; never call it a ceiling projection or probability |
| redundancy | `redundancy_cost` | signed soft score adjustment/state; zero is zero only when measured/fallback value is present and is not “no roster risk” |
| market gap | stored `rank`/`adp` | ordinal arithmetic only; source/date unavailable under current schema |
| evidence | component state + group degradation | measured/fallback/unsupported in text, not color alone |

Do not include legacy residual as a preference control. If shown in full technical details, label it
as score reconciliation outside the comparison components, not “unexplained quality.”

Do not line up component numbers under a generic “points” header. Only the next-turn lineup-edge
field has the projected-lineup-point interpretation above; coverage, breakout, and redundancy are
weighted scoring terms. The default comparison should prefer concrete assignments and plain labels,
with raw scoring terms in details when that is easier to understand faithfully.

## Interaction hierarchy

1. A single `Compare` button appears after the compact E1 list; it does not displace draft actions.
2. Opening compare starts with primary + #2 selected. The user may select up to four candidates.
3. Candidate selection uses native checkboxes with name and position in the accessible label.
4. The compare region has a heading and concise statement: “Comparison does not change v5 order.”
5. Close/Escape restores focus to the opener. Browser back behavior is defined only if a dialog or
   route is used; prefer inline disclosure to avoid new navigation state.
6. Draft buttons remain in the main ordered list. Do not duplicate a destructive/commit action in
   every compare column for the first version.

Prefer native `<details>` or inline state owned by `PlayerCompare`. Do not add a modal dependency.

## Responsive and accessibility contract

Wide layout may use a semantic table with row headers and candidate column headers. At 375 px and
200% zoom, switch to candidate cards with repeated visible metric labels rather than a tiny or
unbounded horizontal matrix. If horizontal scrolling is retained for an intermediate width, keep
row labels visible and announce the scroll region.

Required checks:

- every cell has a programmatic row/candidate relationship;
- selection state is announced;
- open/close focus is deterministic;
- no information is color-only;
- missing, negative, and zero values are distinguishable;
- long names and four selections do not obscure the main draft action;
- keyboard-only completion, screen reader reading order, 375 px, 200% zoom, high contrast, and
  reduced motion pass before release.

## Test-first sequence

### 1. Freeze immutable order

Given four recommendations with deliberately unsorted component values, assert compare renders them
in input/v5 order and does not mutate `recs`. A component maximum must not move a column.

### 2. Freeze mixed evidence

Use one measured, one fallback, one unsupported/null, and one negative component. Assert exact text,
state, sign, and “unavailable” behavior. Zero must not substitute for null.

### 3. Freeze incomplete market coverage

Fixtures cover 4/4, 2/4, 1/4, and 0/4 stored market ADPs. Assert all candidates remain selectable,
the coverage denominator is visible, and no vendor/date/probability text appears. Exercise those
fixtures in early, middle, and late state shapes; M1/M3 shows severe missingness in every stage, not
only late rounds.

### 4. Freeze tradeoff states

Reference catalog locators for:

- multiple nondominated candidates;
- primary dominated on the three displayed components;
- all candidates same position;
- mixed positions;
- weak/unsupported candidates.

Tests assert faithful cells and unchanged order, not a “correct pick.” Do not copy full ignored
artifacts into source fixtures.

### 5. Render interaction

Using existing React/Vitest primitives, test default primary + #2 selection, add/remove candidates,
maximum four, meaningful names, inline disclosure, and focus contract where the test environment can
observe it. Add no testing dependency solely for this unit.

### 6. Verify

Run focused compare/E1/C04 tests, full frontend tests, typecheck, lint, and build. Then complete the
authorized browser/accessibility matrix. No usability benefit is claimed until the separate study.

## Exact files

- new `frontend/components/draft/PlayerCompare.tsx`;
- new focused `frontend/components/draft/PlayerCompare.test.tsx` or `.test.ts`;
- `frontend/components/draft/LiveRecommendations.tsx` for the entry point and existing `recs` handoff;
- `frontend/components/draft/DraftWarRoom.tsx` only if selection cannot stay local; avoid if possible;
- `frontend/lib/v6DraftLiveIntegration.c04.test.ts` for single-scorer/order contract if existing tests
  do not already cover it.

No engine, bridge, query, database, market-ingestion, or scoring file changes.

## Acceptance

- user can compare two to four current candidates without changing v5 order;
- every displayed value maps to the correct component/state/unit;
- component score contributions are not relabeled as player projections, expected starts, or
  probabilities;
- missing/null, zero, negative, fallback, and unsupported remain distinct;
- market arithmetic is ordinal and explicitly source/date unavailable;
- no Pareto/global-quality badge, probability, vendor recommendation, or “optimal” claim;
- main draft action remains visible/reachable;
- mobile and assistive-technology gates pass;
- scorer call count and exact top-four IDs/order/scores remain unchanged;
- full frontend verification passes.

## Rollback and study gate

Remove `PlayerCompare` and its entry control. E1 remains intact; no data migration or cache invalidation
exists. Add compare to production only after the local study shows better objective/tradeoff
comprehension without unacceptable correct-task time, evidence-state errors, or accessibility harm.
