# Draft Board Native Semantics and Control Hierarchy Plan

**Status:** implemented locally after E0q and E0 in the active v6 research worktree on 2026-08-29; uncommitted and unshipped. Automated populated-board acceptance is green; native browser zoom, VoiceOver speech, and the 192-pick complete state remain recorded manual QA gaps.

**Authority:** presentation and native semantics only. No recommendation, score, player order,
draft transition, sync protocol, database, or production-authority change is authorized.

**Goal:** Make the current draft board understandable and operable by keyboard and assistive
technology under draft-clock pressure, while keeping the human's pick action primary and demoting
only the unattended full-draft simulation action.

## 1. Verified current gaps

Static inspection of `frontend/components/draft/DraftWarRoom.tsx` found:

- the search input has placeholder text but no programmatic label;
- Manual/Sleeper/ESPN mode buttons have visual selection but no group label or selected state;
- Board/All teams/Pick log/Analysis buttons have visual selection but no selected state;
- position filters have visual selection but no group label or selected state;
- the best-available table has no caption and the action column header is unnamed;
- the `Pts` header does not say that the unchanged values are projected fantasy points;
- when a player's BlitzBoard rank is absent, the visible `#` value falls back to the filtered
  array index, so search and position filters can display a view position as if it were a global
  rank;
- on narrow screens the grid's source order places the full best-available table before
  `LiveRecommendations`, so the primary and alternatives can sit below as many as 60 visible player
  rows rather than in the clock-pressure path;
- player names are data cells rather than row headers;
- repeated `Draft` or arrow buttons do not include the player in their accessible name;
- the on-clock change is visually prominent but is not a named polite live region;
- the sync-status dot communicates state partly by color and is not explicitly decorative;
- the feed error is visible but is not an alert region;
- `Auto-draft all` appears beside the clock's primary decision controls even though BlitzBoard's
  product principle is human decision support.

The authenticated league selector is a useful existing pattern: it already has `role="group"`, an
accessible group label, and `aria-pressed`. Reuse that pattern.

A direct Playwright probe on 2026-08-29 loaded the no-key `/draft` empty state at 375×812 and
1280×720 with no console/page errors. Axe reported zero definite violations, 25 passes, and one
manual/incomplete gradient contrast check at each viewport; the mobile document had no horizontal
overflow, and its first focus targets exposed usable names. This does not test any control listed
below: the route had zero player rows and no recommendation/table/search region.

A second, disposable localhost probe then exercised the populated path without adding a route,
persisting data, using credentials, or changing product code. A minimal PostgREST-shaped server
returned 96 explicitly synthetic, ranked players (16 at each of QB/RB/WR/TE/K/DEF), an empty
signed-out league list, and no vendor data. Next ran against that server; Playwright 1.61.1, Chrome
for Testing 145.0.7632.6, and axe-core 4.12.1 loaded `/draft` at 320×812, 375×812, 640×812, and
1280×720. The two principal 375/1280 runs returned HTTP 200 with no console or page errors. `Sim to
my pick` advanced exactly five intervening picks to `YOUR PICK`, left 60 available rows visible,
and changed the recommendation heading to `RECOMMENDED · YOUR PICK`.

That populated probe turns several earlier release gaps into observed defects:

- at 375 CSS px the document is 506 px wide (131 px horizontal overflow); at 320 it is still 506
  px wide (186 px overflow). The table's 484 px minimum-content width expands the grid and every
  major board card instead of scrolling only the table. Synthetic names were short and uniform, so
  506 px is an observed fixture result, not a worst-case bound for real long names;
- the recommendation begins about 3,409 px below the top at 375 px, after all 60 table rows;
- the dense recommendation card itself is about 873 px high in that overflow-expanded mobile layout
  and 1,028 px high in the 340 px desktop rail, with candidate blocks about 187–242 px each. E0a
  fixes reachability/reflow, while E1 separately tests compact density; do not hide rows in E0a;
- 155 visible tabbable elements precede the first recommendation control, including 60 player
  links and 60 assign buttons;
- the first table action is about 93.5×24.4 CSS px and an on-the-clock recommendation `Draft`
  action about 56.4×18.4 CSS px. These measurements miss BlitzBoard's 44×44 consequential-action
  goal; a WCAG minimum conclusion still requires spacing and exception analysis;
- axe found four serious `aria-prohibited-attr` violations on unlabeled-role status-dot spans, one
  minor empty action-header violation, and one moderate heading-order violation. It also marked the
  four `UncertaintyStrip` wrapper labels as serious manual/incomplete cases because a plain `div`
  does not reliably support that name. Four contrast checks remained manual/incomplete because the
  layered background could not be computed; they are not confirmed contrast failures;
- filtering to WR preserved the stored global rank (`3`) rather than renumbering the first visible
  row, confirming the intended rank behavior when a rank exists. The separate null-rank fallback
  defect remains established by source inspection.

The localhost server and Next process were stopped after the probe. Screenshots were visually
inspected but are not treated as screen-reader or conformance evidence. No VoiceOver, 200% browser
zoom, connected/stalled feed, complete-draft, light-theme, or human usability result is claimed.

The current `frontend/scripts/axe-smoke.mjs` cannot prevent this regression: it scans only `/` and
`/kit`, the workflow builds with no draft data, and `.github/workflows/ci.yml` marks the whole job
`continue-on-error`. Do not pretend that adding `/draft` to its route array would help; without a
populated server-side data source, that only retests the already-clean empty shell.

## 2. Chosen design

Use native buttons, labels, table semantics, `aria-pressed`, `<details>`, and live-region
attributes in the existing component. Do not build a tab system, roving-focus controller, menu,
headless component wrapper, UI kit, or new state abstraction.

### Standards basis and limits

- WCAG 2.2 is a W3C Recommendation. Its Name, Role, Value and Status Messages criteria require
  programmatically available component names/states and status changes; Labels or Instructions
  requires labels for inputs ([WCAG 2.2](https://www.w3.org/TR/WCAG22/),
  [Name, Role, Value](https://www.w3.org/WAI/WCAG22/Understanding/name-role-value),
  [Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages),
  [Labels or Instructions](https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions.html)).
- WAI's Authoring Practices guidance recommends native naming methods, unique action names, and
  `aria-pressed` for stable-label toggle buttons. APG is informative implementation guidance, not
  itself a conformance guarantee ([names and descriptions](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/),
  [button pattern](https://www.w3.org/WAI/ARIA/apg/patterns/button/)).
- The APG tabs pattern requires tab/tablist/tabpanel relationships and specific focus/arrow-key
  behavior. The current controls do not implement that contract, which is why this plan uses native
  pressed buttons instead of applying `role="tab"` cosmetically
  ([tabs pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/)).
- WAI table guidance calls for header cells and explicit row/column scope where both dimensions have
  headers ([tables with two headers](https://www.w3.org/WAI/tutorials/tables/two-headers/)).
- WCAG Reflow permits two-dimensional scrolling for tabular sections while expecting surrounding
  controls/content to reflow, supporting a table-local scroll container only if observed
  ([Reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow)).
- WCAG 2.2 AA Target Size (Minimum) uses 24×24 CSS pixels or specified spacing exceptions; 44×44 is
  the stricter enhanced target. Use 44×44 as a BlitzBoard goal for consequential draft actions,
  while reporting the actual conformance criterion accurately
  ([minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum),
  [enhanced](https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced)).

These sources specify semantics and testable constraints; they do not show that this exact draft
flow is understandable in VoiceOver or another assistive technology. Automated axe and source
assertions cannot replace populated-route keyboard and screen-reader verification.

### Why pressed groups, not ARIA tabs

The controls swap full board views but do not implement the keyboard and `tabpanel` relationships
required by a tab widget. A labeled group of pressed buttons accurately exposes the current state
while retaining native button behavior. Arrow-key navigation is not invented.

### Why native disclosure for full autodraft

`Sim to my pick` helps the user advance a manual test room to their next decision and remains a
visible secondary action. `Auto-draft all` removes every remaining human choice, so place only that
action inside a native `<details>` disclosure labeled `Simulation tools`. Keep Undo and Reset
visible. Do not delete full simulation without usage evidence.

## 3. Exact interaction contract

### 3.1 Sync mode

- Wrap Manual, Sleeper Live, and ESPN Live in a group labeled `Draft input source`.
- Each button exposes `aria-pressed` from the existing `mode`/`liveSetup` state.
- Preserve current click behavior and visible copy.
- Give the ID field a programmatic label that changes with the selected source:
  `ESPN league ID` or `Sleeper draft ID`.
- Do not imply official vendor endorsement or reliability through the label.
- Mark the colored status dot `aria-hidden="true"`; the adjacent text remains the state.
- Use `role="status"` for connection state only if testing confirms it does not announce on every
  polling render. Prefer `aria-live="polite"` and stable text.
- Give the stalled-feed message `role="alert"`; retain the manual-fallback action.

### 3.2 Board views

- Wrap the four view buttons in a group labeled `Draft board view`.
- Expose `aria-pressed={view === v}`.
- Keep all buttons in normal tab order and preserve the existing state transition.
- Do not add `role="tab"` or `aria-controls` without a complete tab pattern.

### 3.3 Clock and simulation controls

- Name the clock block `Draft status` and make its changing text a polite, atomic status region.
- Do not announce decorative round/pick text separately from the status sentence.
- E0a announces draft-state transitions only; it does not add or mirror a per-second countdown. Any
  later timer must distinguish host, BlitzBoard, and study timing authority and pass the separate
  [draft-clock accessibility plan](2026-08-29-draft-clock-experiments.md).
- Keep `Sim to my pick`, Undo, and Reset visible in manual mode.
- Move `Auto-draft all` behind `<details><summary>Simulation tools</summary>…</details>`.
- Inside the disclosure, describe the consequence in one sentence: it completes every remaining
  pick using the local simulation policy; it is not a forecast or recommendation authority.
- The button remains disabled when the draft is complete.
- Opening the disclosure changes no state and triggers no simulation.

### 3.4 Search and position filters

- Label the search control `Search available players`; placeholder may remain visual help.
- Prefer `type="search"` so platform clear behavior is available without a dependency.
- Wrap position buttons in a group labeled `Filter by position`.
- Expose `aria-pressed={pos === p}` and keep visible labels unchanged.
- Do not announce a result count on every keystroke unless a user study identifies that need.

### 3.5 Best-available table

- Add a visually hidden caption: `Available players ranked by BlitzBoard`.
- Replace the ambiguous visible `#` header with `Rank` and give it the full accessible name
  `BlitzBoard rank`.
- Render the stored BlitzBoard rank when present. When `PlayerValue.rank` is null, render an em dash
  with accessible text `BlitzBoard rank unavailable`; never substitute the filtered/search result
  index (`i + 1`) as though it were a global rank.
- Keep the position, points, and action columns.
- Relabel `Pts` as visible `Proj pts` with the accessible name `Projected fantasy points`; keep the
  exact `projPoints(p)` value and missing-value behavior, and do not add a freshness/source claim.
- Give the action header visually hidden text `Draft action` instead of an empty header.
- Render the player cell as `<th scope="row">` while keeping the existing link.
- Give each manual action an accessible name containing the player and destination, for example:
  `Draft Jordan Example to my team` or `Assign Jordan Example to Team 4`.
- Do not put market source, confidence, or recommendation probability into that action label.
- Retain visible compact button text.
- Ensure `No players match` continues to span all five columns.

### 3.6 Narrow screens and zoom

Do not hide candidate identity, position, or action. Test 375 px and 200% zoom as product smoke
states, and also test the 320-CSS-pixel-equivalent Reflow boundary; the easier smoke states do not
establish WCAG conformance. If the existing `overflow-hidden` clips the table, use one labeled
horizontal scroll region around the table rather than shrinking text below design tokens. Give a
keyboard-focusable scroll region an accessible name only
if overflow is actually observed. It is now observed at both 320 and 375 CSS px: constrain the grid
children with native CSS sizing and put horizontal overflow on the named table wrapper, not the page.
The 640 px probe did not overflow, so do not add a page-wide scroll mechanism.

The recommendation is the product's primary decision-support output and must precede the long player
table in narrow-screen source order. Render exactly one `LiveRecommendations` instance as its own
grid child, followed by the main board and then the secondary roster/plan panels. At `lg`, place the
main board in the left column spanning the recommendation and secondary-panel rows, with the single
recommendation instance at the top of the right rail. Do not render separate mobile/desktop copies,
use CSS visual order that contradicts source order, or invoke the scorer again. Preserve the current
desktop visual relationship and all panel contents.

The smallest proven layout is the existing grid with explicit minimum sizing, not a new component:

- grid columns at `lg`: `minmax(0, 1fr)` plus the existing 340 px rail;
- child 1: the only recommendation, source-first, `lg` column 2/row 1;
- child 2: the main board, `min-width: 0`, `lg` column 1/row 1 spanning both rail rows;
- child 3: secondary panels, `min-width: 0`, `lg` column 2/row 2;
- the available-player table wrapper changes from clipping overflow to a single horizontal-scroll
  region with a stable accessible name. Keep the table's cells/actions intact; do not make the
  entire page or every card horizontally scrollable.

If implementation evidence shows that CSS grid placement creates a reading-order mismatch in a
tested desktop screen reader, keep DOM/source order authoritative and revise the large-screen
placement. Do not solve it with a second hidden recommendation copy.

## 4. Test-first execution boundary

### Task A — state and name contract

**Files:**

- modify `frontend/components/draft/DraftWarRoom.tsx`;
- add `frontend/components/draft/DraftWarRoom.a11y.test.ts` only if the existing source-contract
  pattern cannot be folded coherently into `frontend/lib/v6DraftLiveIntegration.c04.test.ts`.
- modify `frontend/components/draft/RosterHealthPanel.tsx` and
  `frontend/components/draft/BenchPanel.tsx` only for the populated-route status-dot axe defects;
  use meaningful native/ARIA semantics without changing visible values or status calculation.
- modify section-heading elements in `LiveRecommendations.tsx` and the existing sidebar components
  only as needed to restore a sequential heading outline; do not restyle or compact them in this
  unit.
- add `frontend/scripts/draft-board-smoke.mjs` as the single reproducible populated-route browser
  gate; use no new package, fixture route, database, external request, or persisted artifact.

Before markup changes, add focused assertions for:

- labels for sync source, view, search, and position filter;
- selected state on each current mode/view/position button;
- named clock status;
- player-specific draft/assign action names;
- row-header and action-header semantics;
- projected-points header semantics with exact numeric parity;
- labeled BlitzBoard-rank header and null-rank behavior under position/search filtering;
- feed alert and decorative status dot;
- `Auto-draft all` present only inside native disclosure;
- exactly one recommendation region before the player table in source order, with large-screen
  placement at the right-rail top;
- one call to the scorer and unchanged recommendation data flow.
- no unsupported `aria-label` on plain status-dot spans. E0q removes the invalid draft uncertainty
  strip; the shared wrapper is outside E0a and belongs to the cross-product uncertainty audit;
- sequential heading levels and no empty table header in the populated board;
- page width equals viewport width at 320 and 375 CSS px, with any necessary horizontal scrolling
  confined to the labeled table region;
- the recommendation action precedes all 60 player-row actions in source and keyboard order;
- consequential action target measurements are recorded against both the 24×24-or-spacing WCAG
  minimum and the separate 44×44 product goal.

The current repository uses source-contract assertions in
`v6DraftLiveIntegration.c04.test.ts`. Reuse that minimal idiom if it can assert the contract without
creating a broad renderer. Do not add Testing Library or another dependency for this unit.

### Task B — minimal native markup

Change only the affected JSX and attributes. Reuse existing state and handlers. Do not extract a
component unless the resulting one-file change becomes harder to review than the current markup.

Required invariants:

- `setMode`, `setView`, `setPos`, `draft`, `runSim`, `undo`, and `reset` receive the same values;
- player sort/filter/order is byte-equivalent;
- missing-rank rendering does not create a new ordinal, change order, or alter scoring;
- full simulation remains available but never runs from disclosure open;
- live-sync fallback behavior is unchanged;
- no new effect, listener, context, or state is introduced.

### Task C — mobile decision-path source order

Split the current right rail without duplicating it: one recommendation grid child, the main board
grid child spanning the desktop rail rows, and one secondary-panels grid child. Verify that the
source order is recommendation → board → secondary panels, while desktop placement remains board
left and recommendation/secondary panels right. The same `recs` object reaches the only
`LiveRecommendations` instance, and `scoreBoardWithExplanations` remains invoked once.

Use a populated long-player fixture at 375 px to show that the current-pick recommendation and its
draft action are reachable before table scrolling. This verifies the intended information path; it
does not establish faster decisions or lower workload.

### Task D — static and interaction verification

Add one bounded QA script, `frontend/scripts/draft-board-smoke.mjs`, only when implementing this
unit. It should use Node's built-in `http`/process APIs plus the already-installed Playwright and axe
packages to:

1. bind disposable loopback ports and return a fixed, explicitly synthetic 96-player
   PostgREST-shaped payload plus an empty signed-out league list;
2. start a local Next development server with only those loopback public URL/placeholder-key values;
3. prove the current pre-fix page fails the declared source-order/reflow/axe assertions, then prove
   the implementation passes them at 320, 375, 640, and 1280 CSS px;
4. exercise `Sim to my pick`, search/filter, one recommendation draft action, Undo, empty filter,
   and the secondary simulation disclosure without contacting Sleeper/ESPN;
5. stop both child processes in `finally`/signal handlers and write no screenshot, credential,
   fixture row, or server state into the repository by default.

Do not add a production fixture route, mock database dependency, second Playwright config, test-only
condition in `DraftPage`, or vendor-shaped real identity. Keep the script out of the existing
shell-only `axe-smoke.mjs` so each gate has one honest data contract. A later CI change may make the
new script blocking only after its runtime is measured and it is green on a clean implementation;
do not claim the current non-blocking shell job covers it.

The current UI simulation passes `randomness: 0.06` without an `rng`, so it falls back to
`Math.random`. The smoke gate should assert transition invariants—five intervening picks for the
default slot, unique player IDs, legal pick destinations, and `YOUR PICK`—not exact simulated player
identities. Exact replay belongs to the seeded offline harness; E0a must not change simulation
authority just to make a presentation test deterministic.

Run focused contract tests, typecheck, lint, full frontend tests, and build. Then run a populated
local board through:

- keyboard-only traversal and activation;
- VoiceOver or an equivalent screen-reader announcement check;
- axe scan;
- 375 px width;
- 200% browser zoom;
- the 320-CSS-pixel-equivalent Reflow boundary for non-table content, with any table scrolling
  contained to the named table region;
- light/dark themes if both are user-selectable on the route;
- manual, Sleeper-setup, ESPN-setup, connected, stalled, empty-filter, and complete-draft states;
- reduced-motion preference, confirming this unit introduced no motion.

Record screenshots only as QA evidence; screenshots do not establish screen-reader correctness.
If a populated lawful fixture cannot be provided without external credentials, stop and report the
interactive QA gap rather than testing only the empty page and claiming success.

## 5. Usability study hooks

This unit fixes objective semantics and can ship after accessibility verification without waiting
for the larger E1/E2 efficacy study. Still measure these observational outcomes in the later study:

- time to locate a named player and draft them;
- wrong-player or wrong-team action rate;
- time to identify the active view and position filter;
- accidental full-autodraft activation rate;
- successful switch to manual after a feed stall;
- keyboard task completion and assistive-label comprehension.

Do not claim that demoting full autodraft improves decisions until measured. The immediate
justification is alignment with the user-controlled product principle and reduced accidental-action
risk, not an outcome-performance claim.

## 6. Missing and degraded behavior

- Missing player values keep the route's existing empty state; no controls are fabricated.
- A player row with a missing BlitzBoard rank remains visible in its existing order and says rank
  unavailable; filtered view order is never promoted to a rank.
- Missing market source does not alter labels in this unit.
- Missing sync connection keeps Manual selected or the existing setup state visible.
- A stalled feed retains its error and manual fallback.
- A complete draft disables simulation and action buttons as before.
- A player with no team still receives a complete accessible action name based on the on-clock
  fantasy team; no NFL-team inference is inserted.
- Unknown player name falls back to existing displayed identity; do not announce a blank action.

## 7. Exact non-goals

- recommendation hierarchy, compare state, preference objectives, or next-turn probability;
- changing candidate IDs, order, scores, or visibility;
- duplicating recommendation markup for responsive layouts;
- removing manual simulation or live-sync modes;
- a general tabs, buttons, disclosure, table, or form component library;
- installing Testing Library, an accessibility widget, or another dependency;
- claiming ESPN, Sleeper, or another vendor recommends any player;
- dense live announcements of pick-log changes;
- redesigning all draft subcomponents in the same unit.

## 8. Acceptance criteria

1. Every mode, view, position, search, table, and repeated draft action has an accurate accessible
   name/state/relationship.
2. Player names are row headers and the action column is named.
3. Rank is labeled as BlitzBoard rank; a missing rank is unavailable rather than the filtered row index.
4. Projected fantasy points are labeled explicitly and retain exact numeric/missing parity.
5. Clock and feed-error changes are announced once at an appropriate urgency.
6. Color is not the only sync-state signal.
7. `Auto-draft all` requires opening the secondary disclosure; no other behavior changes.
8. The primary recommendation, top-four IDs/order/scores, player table order, pick transitions, and
   sync mapping are unchanged.
9. No scorer, engine, query, schema, dependency, or production authority changes.
10. Focused/full frontend gates pass.
11. Populated-route keyboard, screen-reader, axe, 375 px, 200% zoom, and 320-CSS-pixel-equivalent
   Reflow checks pass with recorded limitations.
12. On narrow screens, the single recommendation region precedes the long player table and the
    secondary panels follow it; on desktop, the recommendation remains the right-rail lead.
13. Reverting this one unit restores the prior markup with no data migration or stored-state loss.
14. Axe reports no `aria-prohibited-attr`, empty-table-header, or heading-order violation on the
    populated fixture; unresolved contrast computation is reported separately from actual failures.
15. At 320 and 375 CSS px the page itself has zero horizontal overflow, the table remains operable
    in its own labeled region, and no 60-row/table-action block precedes the recommendation.

## 9. Rollback and ordering

Rollback is a bounded markup/QA-test revert across the declared existing components. Stored picks,
league configuration, and recommendation payloads remain compatible. Stop and revert if pressed state is incorrect, announcements become
repetitive, keyboard focus is trapped/lost, full autodraft becomes easier to trigger accidentally,
or narrow-screen access to the draft action worsens.

Recommended ordering is E0q false-quantile suppression, E0 reason fidelity, then this native-semantics
unit, then E1. The populated evidence makes source order/reflow an E1 prerequisite, and both E0q/E0a
touch `LiveRecommendations.tsx`. Avoid concurrent landing; sequence the units to keep review and
rollback unambiguous.
