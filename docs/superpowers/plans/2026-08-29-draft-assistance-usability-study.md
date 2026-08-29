# Draft-Assistance Usability Study Plan

**Status:** preregistration template; no participant data have been collected.

**Authority:** this study evaluates presentation usefulness. It does not fit or promote the draft
policy, validate a vendor recommendation, prove a roster will win, or turn synthetic survival into a
probability. Shipped v5 remains production authority.

## 1. Decision problem

Under a draft clock, the user needs to:

1. recognize the primary v5 option;
2. notice two or three defensible alternatives;
3. understand the most consequential tradeoff;
4. recognize missing/stale evidence;
5. compare options when their preferred objective differs from v5;
6. make their own selection without mistaking a view for an automatic strategy rewrite.

The current four-candidate surface averages 21.10 formatted explanation lines and 1,033 explanation
characters before names, chips, equity, and uncertainty. About 13.98 lines are exact duplicates
within the same state. This establishes a density problem, not a human workload effect. The study
tests whether compaction and optional compare improve outcomes without hiding faithful evidence.

## 2. Research questions

### Primary

- Does a compact hierarchy reduce task time while preserving or improving tradeoff comprehension?
- Does optional compare improve correct identification of objective-specific differences without
  causing users to believe the board reranked the players?

### Secondary

- Does compaction reduce perceived workload?
- Do users detect missing/degraded market and league evidence?
- Can users distinguish market rank disagreement, draft-turn survival, and health/startability?
- How often do users open details or compare, and is that action useful in disagreement states?
- Does keyboard/mobile use change task time, errors, or abandonment?
- In a later, separately analyzed pilot, does a non-forcing user-first shortlist/objective step reduce
  primary anchoring without adding unacceptable clock cost or abandonment?

### Not tested by this study

- season wins, H2H quality, playoff odds, or roster optimality;
- calibration of next-turn survival;
- accuracy of synthetic opponent profiles;
- superiority of one participant's fantasy strategy;
- vendor or platform recommendation quality.

## 3. Variants

Keep the underlying four candidates, order, structured payload, and v5 primary identical within each
task.

Apply E0q false-quantile suppression, E0 reason fidelity, and E0a native source-order/reflow/semantics
to **all** study variants before timing. Otherwise A carries known copy/probability/navigation defects
while B/C remove them, confounding information density with truthfulness and basic operability.
Preserve separately labeled pre-repair screenshots/fixtures for regression history, not as the study
control.

### A. Current dense surface

The current dense `LiveRecommendations` presentation after E0q/E0/E0a: all candidates,
fidelity-checked chips, equity, formatted explanation lines, one honest unavailable-range state,
and repaired navigation/reflow. It does not restore the former false quantile strip.

### B. Compact hierarchy

- primary and three alternatives visible;
- one evidence-backed reason per candidate and the most consequential shared or primary limitation;
- one group-level evidence/freshness signal;
- native progressive disclosure retains every current formatted claim.

Do not use the existing first chip unchanged: VONA, run, and unknown-source market-gap cases fail the
pre-study fidelity audit. Q2/Q3 show that a structured formatter-claim fallback can cover every
frozen candidate and reduce rows by 75.4%. Freeze a repaired/allowlisted chip-or-claim selector
before the formative pilot, then code whether participants can restate it and whether it
distinguishes the candidate. If it repeatedly fails, revise and refreeze B before the main study;
do not choose among selectors after viewing confirmatory outcomes.

### C. Compact hierarchy plus optional compare

Variant B plus a two-to-four candidate comparison with immediate-lineup, absence coverage, breakout,
redundancy, and evidence-state rows. Compare does not rerank.

### D. Optional descriptive room dynamics, only after A-C

A later experiment may add observed recent position counts/window. It must not say a run will
continue or attach an uncalibrated survival percentage. Do not mix D into the first A-C study.

### E. Advice-order pilot, only after A-C

[Rieger and Manzey's two 60-person time-pressure experiments](https://doi.org/10.1177/0018720820965019)
found different performance/reliance patterns when an automated binary cue preceded inspection
versus followed the participant's initial decision. That luggage-screening result is adjacent
evidence, not a draft-interface prescription.
Only after the hierarchy study, compare the normal immediate-primary display with a lightweight
user-first shortlist or objective selection before revealing BlitzBoard's primary. Do not require a
pick, conceal legal alternatives, or add friction to the production board from this pilot. Measure
tradeoff accuracy, weak-candidate rejection, anchoring to the primary, time, abandonment, and whether
participants understand that the user retains final authority. Keep this result separate from A-C;
neither reliance nor agreement with BlitzBoard is a success endpoint.

## 4. Task-state sampling

Use three frozen state pools:

1. the 54-state high-disagreement catalog for stress and tradeoff tasks;
2. a separately frozen synthetic-reference sample drawn from U0 decision states, stratified by
   early/middle/late and league format;
3. a separately selected missing/degraded-market sample from the frozen T0/T1/T3 traces, including
   mixed-known and no-ADP candidate sets.

The 54-state catalog is deliberately extreme: 53/54 primaries change across opponent assumptions and
mean top-four Jaccard is 0.129. It cannot estimate how often ordinary users encounter disagreement.
N0 additionally found that the catalog has higher candidate ADP support than the full U population
(87.96% versus 77.32%), only one no-ADP state, no DST candidate, and 53/54 primary changes versus
36.88% in the full population. Report all three pools separately; include unchanged-primary controls
and late K/DST cases outside the stress catalog. Even the U0 reference pool is synthetic 2024-proxy
development evidence, so its frequencies are generator frequencies, not live-user prevalence.

### 4.1 Exact freeze rules before prototyping

- **Stress stratum:** keep the existing 54 locators unchanged. Do not replace an awkward or weak
  state after seeing a prototype.
- **Synthetic-reference stratum:** within each format × slot-band × early/middle/late cell, order
  eligible U0 states by SHA-256 of a frozen sampling seed plus `(derived_seed, pick_no)` and take the
  first required locator. This samples independently of score, overlap, component winner, and UI
  appearance. If a smaller participant block is needed, freeze the block assignment before viewing
  outcomes rather than post-selecting “representative” screens.
- **Degraded-data stratum:** select from T1/T3 by declared stored-ADP support categories—four known,
  one-to-three known, and none known—crossed with early/middle/late. Prefer exact format/slot balance;
  use U0 rather than a dropout arm for complete-support controls. O0 confirms mixed-known coverage in
  all 54 exact cells, but no-ADP coverage is absent in two early cells. For those two, relax slot
  within the same format and phase; if still empty, use mixed-known and preserve a gap flag. Never
  fill from future data, silently relax format/QB mode, or substitute a visually convenient state.
- **Late special-teams stratum:** because N0 contains no DST and only eight K appearances, freeze
  dedicated late K and DST states as boundary tests and report them separately from aggregate task
  time.

Each locator receipt must contain the source artifact evidence hash, selection seed/rule, group,
derived seed, trace index, pick number, candidate IDs, stored-ADP support count, evidence states, and
its own evidence hash. A resolver must fail closed on a changed source hash, missing locator,
candidate mismatch, or duplicate stimulus. The receipt selects stimuli; it does not copy full player
payloads or create model authority.

The same frozen selected state must be rendered in A/B/C. Never compare a T1 screen with a T3 screen
and attribute a choice difference to presentation: market dropout changed the simulated intervening
picks and therefore the candidate pool before the UI task began.

Balance each participant's tasks across:

- 10/12/14 teams;
- 1QB/2QB/superflex;
- front/middle/back seats;
- early/middle/late draft;
- single- and multi-position candidate sets;
- complete and partial stored-market-ADP support;
- fallback/unsupported evidence now, and measured evidence only after a valid point-in-time fixture
  exists;
- a weak-choice state where no option should be described as certain or excellent;
- an incomplete-history state only after a truthful point-in-time fixture exists.

Do not fabricate vendor names, probabilities, freshness, or rookie status in a task.

### 4.2 Draft-clock protocol

“Under draft-clock pressure” requires a visible, reproducible deadline; ordinary task timing alone
does not test pressure. The instrumentation pilot may run without an enforced deadline while wording,
focus, and task duration defects are repaired. Before the main A/B/C study, freeze one supported clock
duration from the target league/platform configuration (for example 30, 60, or 90 seconds), show the
same countdown and warnings in every variant, and keep practice trials outside endpoints. Do not pick
the deadline after inspecting which variant wins.

When time expires, record a timeout and allow the participant to finish for comprehension scoring;
do not auto-select a candidate, replace the answer with a random choice, or score the timeout as
agreement with BlitzBoard. Report correct-task time both with the frozen censoring rule and among
completed responses, plus timeout/abandonment counts by variant and input mode. A separate deadline
manipulation (for example 30 versus 90 seconds) requires its own powered, counterbalanced study; do
not add it to A/B/C opportunistically.

The study logger should record displayed time remaining when details, compare, or a lens is opened.
This can reveal whether deeper views remain reachable late in the clock, but it cannot identify a
participant's sophistication or establish an opponent-model coefficient.

## 5. Task types

### T1. Primary recognition

Prompt: “Which player is BlitzBoard's current v5 primary?”

Measures: correctness, time, accidental selection of an alternative, confidence.

### T2. Tradeoff comprehension

Prompt: “What is the most important reason to consider Player B, and what do you give up versus
Player A?”

Score against the structured component payload using a frozen answer rubric. Multiple paraphrases
may be correct; graders are blind to variant.

### T3. Objective alignment

Prompt: “You care most about immediate starter value / absence coverage / upside / roster balance.
Which displayed option best matches that goal?”

Correctness means matching the maximum relevant displayed component when it is informative. The task
does not call that player globally optimal.

### T4. Evidence limitation

Prompt: “What information is missing or degraded here? What conclusion should you avoid?”

Correct answers distinguish unavailable stored market ADP, unsupported league evidence, and uncalibrated
survival. A response claiming vendor advice or probability is an error.

### T5. Free decision

Prompt: “Which option would you draft, if any, and why?”

There is no correctness score. Measure time, chosen option, information opened, stated rationale,
confidence, and whether the rationale matches visible evidence. This task assesses decision support,
not policy quality.

### T6. Recall after action

After selection, ask for the primary reason, main tradeoff, and evidence state without reopening the
panel. This tests whether the hierarchy supports a usable mental model.

## 6. Endpoints

### Co-primary endpoints

- tradeoff-comprehension accuracy on T2/T3;
- task completion time for correct T2/T3 responses.

Use a hierarchical rule: first require comprehension noninferiority, then test time improvement. Do
not trade correctness for speed.

### Secondary endpoints

- evidence-limitation accuracy;
- erroneous probability/vendor inference rate;
- details-open and compare-open rate;
- time from opening compare to correct response;
- confidence and confidence-accuracy calibration for factual T1–T4 only; T5 confidence is
  descriptive because the user's preference choice has no correctness label;
- short-form workload rating after each block;
- NASA-TLX after each variant block if participant burden remains acceptable;
- keyboard errors, focus loss, horizontal-scroll failures, and abandoned tasks;
- stated preference with a free-text reason.

Do not collapse all endpoints into one “usability score.”

## 7. Pilot and main study

### Pilot

Recruit 6-8 participants for instrumentation, wording, timing, accessibility, and task-ceiling/floor
checks. Pilot results may change task wording, logging defects, and block length. They may not be
pooled into confirmatory results or used to pick the winning variant.

Include a mix of fantasy-draft familiarity and at least one keyboard-only or assistive-technology
workflow when feasible. If accessibility participants cannot be recruited for the pilot, conduct a
separate expert/assistive-technology audit and record that human coverage is missing.

### Main sample

Determine sample size from the pilot's within-participant variance and a predeclared minimally
important effect. A reasonable starting design target is:

- comprehension noninferiority margin no larger than 5 percentage points;
- at least 15% median correct-task-time improvement for B versus A;
- workload direction consistent with time/comprehension rather than a standalone significance win.

Freeze effect, power, alpha/multiplicity, exclusion, and sample size before main outcomes. If the
required sample is impractical for a valid local study, report an exploratory study and do not make
release claims from significance tests.

## 8. Assignment and counterbalancing

Use a within-participant design for efficiency, with A/B/C order assigned by a balanced Latin square.
Randomize state-to-variant mapping within strata so no participant sees the same underlying state in
multiple variants. Counterbalance task order and rotate player labels only when links/identity are not
part of the task.

Use practice tasks before timing. Do not include practice in endpoints. Pause the timer during
technical interruptions and retain an interruption flag.

## 9. Analysis

- analyze correct-task time with a prespecified robust paired method or mixed model;
- analyze binary comprehension with participant and state effects;
- cluster uncertainty by participant and state as the design requires;
- report medians/quantiles and raw denominators, not only means/p-values;
- report variant × experience and variant × device interactions as exploratory unless powered;
- keep stress, synthetic-reference, and degraded-data estimates separate;
- include every preregistered task after applying frozen exclusions;
- publish null, negative, and preference-conflict results.

For view disagreement, report:

- how often a lens identifies a different candidate;
- whether the participant recognizes that as an objective-specific highlight;
- whether it improves T3 accuracy/time;
- whether it increases false belief that v5 changed its primary;
- whether the participant found the disagreement useful in free-decision rationale.

## 10. Privacy and consent

Before participation, explain that:

- tasks use synthetic/historical development states;
- no roster is guaranteed to win;
- responses evaluate the interface, not the participant's fantasy skill;
- participation is voluntary and may stop at any time;
- screen/audio recording is optional and separately consented;
- compensation, retention, access, deletion, and contact process are defined.

Collect the minimum data: pseudonymous participant ID, experience band, device/input mode, task
events, answers, timings, and workload. Do not collect platform credentials, real private league
data, manager names, or unrelated browsing. Store consent separately from task records.

## 11. Accessibility protocol

For every variant, test:

- keyboard-only traversal and visible focus;
- focus restoration after compare/details close;
- screen-reader names, list/table relationships, and selected/expanded states;
- 375 CSS px and 200% zoom as product smoke states, plus the 320-CSS-pixel-equivalent WCAG Reflow
  boundary without hiding the draft action; isolate necessary table scrolling from the page;
- consequential draft-action targets aim for 44×44 CSS px; separately verify WCAG 2.2 AA's
  24×24-or-spacing minimum and report which criterion is being claimed;
- high contrast and non-color-only encodings;
- reduced-motion behavior;
- long names, large text, and missing values;
- horizontal compare behavior with persistent labels.

The current repository has native buttons, global focus styling, and an ordered recommendation list,
but no draft-specific browser/axe/keyboard test was found. Playwright 1.61.1 and its Chromium
executable are available through the shared root dependency tree; the optional gstack browse helper
itself still requires a separate one-time build and was not installed. A direct 2026-08-29
Playwright probe loaded `/draft` at 375×812 and 1280×720 with no console/page errors. The no-key
route rendered only its honest empty state, so it could not exercise any draft control. Axe reported
zero definite violations, 25 passes, and one manual/incomplete contrast check on gradient-backed
empty-state text at each viewport; the 375 px document had no horizontal overflow. These are
empty-shell checks, not populated-board, keyboard-flow, contrast-conformance, or screen-reader
passes.

A subsequent disposable localhost fixture exercised 96 explicitly synthetic players without
credentials, vendor data, persisted records, a fixture route, or product-code changes. The board
loaded without console/page errors and `Sim to my pick` advanced five intervening picks correctly.
At 375 px, however, the page expanded to 506 px and placed the recommendation about 3,409 px below
the top. Its first control followed 155 tabbables, including 60 player links and 60 row actions. The
same 506 px page at 320 px produced 186 px overflow. Axe-core 4.12.1 found four serious unsupported
status-dot labels, an empty table header, and a heading-order defect; uncertainty-wrapper labels and
layered-background contrast remained manual/incomplete. The recommendation draft action measured
about 56×18 CSS px, below the stated 44×44 product goal. These observations require a native
semantics/reflow repair before A/B/C timing; otherwise the study would confound hierarchy with a
known navigation and clipping failure. They still do not establish screen-reader behavior, human
workload, contrast failure, or WCAG conformance.

## 12. Instrumentation contract

Log only local study events:

- variant and anonymized state ID;
- task start/answer/end timestamps;
- frozen clock duration, displayed time remaining at each interaction, and timeout state;
- details/compare/lens open and close;
- focus-loss/technical interruption;
- chosen displayed rank and objective;
- answer rubric code and grader disagreement;
- evidence-state acknowledgement;
- device/input mode.

Do not log full player payloads when a catalog locator/hash is enough. The study harness should run
offline against frozen fixtures so no external platform or production analytics authority is needed.

## 13. Release interpretation

### Build/retain compact hierarchy when

- expanded detail retains 100% of current formatted claims;
- default explanation rows fall at least 50% on U0/U1 fixtures;
- comprehension meets the frozen noninferiority gate;
- correct-task time improves by the frozen meaningful amount or workload materially improves without
  time/comprehension harm;
- evidence-limitation errors do not increase;
- accessibility gates pass.

### Add optional compare when

- T3 tradeoff/objective accuracy improves;
- users understand compare does not rerank v5;
- missing cells remain comprehensible;
- opening compare does not obstruct the draft action or cause unacceptable time cost.

### Reject or revise when

- users become faster by skipping limitations and comprehension falls;
- compare increases probability/vendor misconceptions;
- mobile/keyboard users cannot complete tasks;
- the stress catalog drives benefits that do not reproduce in the synthetic-reference sample;
- participants consistently ask for a metric whose data contract does not exist.

## 14. Likely repository files after study approval

- `frontend/components/draft/LiveRecommendations.tsx`;
- a pure compact-summary helper in `frontend/lib/v6DraftExplanation.ts` only if needed;
- focused renderer/formatter tests;
- `frontend/components/draft/PlayerCompare.tsx` in a separate E2 unit;
- local study fixtures referencing `usability-state-catalog.json`, not copied production payloads;
- draft-specific browser/accessibility tests after the browser QA setup is explicitly authorized.

No engine, policy, query, database, or deployment file should change for E1/E2.

## 15. Rollback and next action

Rollback removes the compact renderer or compare component and restores the prior presentation; the
scorer, candidate order, structured payload, roster state, and production data remain unchanged.

The next action is a no-data pilot protocol review: freeze the prevalence-state sample, answer
rubrics, event schema, consent text, and counterbalancing table. Then implement an offline prototype
of A/B only. Do not recruit participants or claim usability improvement until that package is
reviewed.
