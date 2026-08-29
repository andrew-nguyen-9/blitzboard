# Draft-assistance deep experiment campaign

Status: preregistered at 2026-08-29 04:34 CDT, before new campaign execution.

This campaign evaluates development robustness and integration readiness for a human-controlled
draft board. It does not promote a policy, reopen C05, calibrate 2026 survival, or authorize a
production change. Shipped v5 remains production authority.

Across 29 core and post-core campaign arms, 6,696 drafts completed; every draft was legal and
duplicate-free. These are synthetic development drafts, not 6,696 observed human rooms. The
campaign also emitted 9,120 deterministic decision states across U/T trace arms for explanation,
missingness, and choice-surface analysis.

The later P0 performance diagnostic executed another 360 paired control/trace drafts, bringing the
session execution total to 7,056. P0 retained only a compact timing/size receipt, not another set of
full draft artifacts.

## Checkpoint schedule

| Checkpoint | Planned evidence | Actual status |
|---|---|---|
| 04:30 CDT | authority, dirty-state, data-boundary audit | Complete; no real 2026 survival labels |
| 05:00 CDT | orchestration gate and targeted baseline tests | Recorded 05:00: gate PASS; 51 engine tests; baseline frontend 216 PASS/4 skipped; A0-A3 2,160 legal/duplicate-free drafts and 51,840 trajectories |
| 06:00 CDT | primary homogeneous/heterogeneous campaign and exact replay | Recorded 06:00: A0-A3 all legal/duplicate-free; wide `(1,4,8,12)` failed its H2H gate; `(4,8,12)` and `(4,8)` passed the primary seed; R1/R2 timing-independent hashes matched exactly |
| 07:00 CDT | alternate seed and bounded-mixture sensitivity | Recorded 07:00:08: `(4,8)` failed alternate-seed noninferiority; `(4,8,12)` passed the sequential fallback overall but retained format-sensitive negatives; six-seed development interval crossed zero. Receipt/path audits passed with documented provenance limitations; no promotion. |
| 08:00 CDT | missing-market stress and subgroup/stability synthesis | Recorded 08:00:11: D/T/M show no safe QB, slot, or stage slice under missing stored ADP; N0 proves the 54-state usability catalog is an extreme stress set; O0 finds mixed-known fixtures in all 54 cells with two exact no-ADP gaps. All 82 artifact hash contracts and fresh full frontend/pipeline gates pass; full engine reproduces the 20 documented authority/dirty-tree refusals. No promotion. |
| 09:00 CDT | usability contracts, full verification, integration decisions | Recorded 09:00:33: populated-board reflow/source-order/ARIA/target-size defects and the false draft-quantile contract are now bounded prerequisites; E0q → E0 → E0a → E1 → E2 is consistent across every handoff. A separate advice-order pilot was added from peer-reviewed time-pressure evidence without changing the default hierarchy. Deliverable structure, 15-document local links/whitespace, diff checks, capability-map paths, and orchestration validation pass. HEAD/artifact counts are unchanged; no product or production authority changed. |
| 10:00 CDT | final audit, expansion plan, next independent unit | Recorded 10:00:07: all 14 linked worktrees and 21 local/27 remote refs were re-audited; the two authoritative dirty checkouts, active HEAD `e5eb357…`, and 33/18/108 ignored artifact counts are preserved. Twenty-one planning/state documents have zero local-link or trailing-whitespace defects; all 11 view contracts have every required field; diff and orchestration validation pass. Fresh executable gates remain frontend 584/4 skipped with typecheck/build, pipeline 157, and focused engine 51. Full-engine authority refusals remain honestly non-green. E0q is the next independent unit; no commit, push, merge, deploy, promotion, vendor access, product code, or production authority changed. |
| 11:02 CDT (extended) | E0q/E0/E0a implementation and verification | Recorded 11:02:49: all three planned E0-family units are implemented locally without scoring, schema, query, simulation-authority, or production-authority changes. Frontend gates pass with 587 tests and 4 skips, typecheck, build, and lint with one inherited warning. The populated 96-player browser gate passes at 320/375/640/1280 CSS px across dark/light themes, reduced motion, synthetic connected/stalled feed states, axe, keyboard activation, and draft transitions. It also found and repaired player-specific recommendation action names and one actual light-theme footer contrast defect. Focused active engine suites pass 51/51; the full engine run records 3,911 pass, 1 skip, and the same 20 clean-tree/C05-environment authority refusals. Native browser zoom, VoiceOver speech, and the 192-pick complete state remain manual QA gaps. No commit, push, merge, deploy, promotion, vendor access, or production authority changed. |
| 11:13 CDT (extended) | E1 compact recommendation hierarchy | Recorded 11:13:01: E1 is implemented locally in `LiveRecommendations.tsx` with one primary, three ordered alternatives, one fidelity-eligible visible reason each, visible projected-lineup-point equity, one group evidence signal, and one native full-evidence disclosure preserving every reason and formatted claim. The 375 px populated card is 462 px high, including the collapsed disclosure summary, within the 812 px decision viewport. The browser gate passes long-name handling, disclosure/action stability, dark/light/high-contrast modes, reduced motion, synthetic connected/stalled feeds, axe, keyboard order, and 320/375/640/1280 reflow. Frontend gates pass with 593 tests and 4 skips, typecheck, build, and lint with one inherited warning. A proposed primary tint was rejected after axe measured 4.27:1 contrast; the existing accent border distinguishes the primary without that regression. Native browser zoom, VoiceOver speech, and the 192-pick complete state remain manual QA gaps. No scorer, order, score, schema, query, simulation, vendor, production-authority, commit, push, merge, or deployment change occurred. |

Every scheduled timestamp is now recorded from the actual local clock; no checkpoint was claimed early.

## Preregistered questions and thresholds

All new cells use frozen 2024 FFC aggregate ADP, the canonical 2024 outcome fixture, six league
scenarios, front/middle/back bands, paired test seats and seeds, the shipped TypeScript v5 picker,
and the existing evaluator. Each opponent remains a seeded `pickHumanAdp` agent. A profile rotates
bounded `topK` values by seat; this changes reach tolerance without exposing model fields.

Primary reference: homogeneous `topK=8`. Primary treatment: rotating `(1,4,8,12)`. Secondary
mixtures are `(4,8,12)` and `(4,8)`. Treatment minus reference is acceptable as a robustness result
when the lower 95% paired H2H bound exceeds -0.01, every roster is legal, every draft is
duplicate-free, and starter-strength/playoff intervals show no clear material harm. Superiority is
not required and will not be inferred from a noninferiority pass.

The primary seed is `2026082902`; alternate seed `2026082917` tests bounded variation. Primary
cells use 30 repetitions per scenario/slot (540 drafts per arm) and 24 season trajectories per
draft. Alternate-seed cells use 20 repetitions and 16 trajectories. Exact replay reruns a reduced
2-repetition primary profile twice and requires identical timing-independent hashes.

Market dropout tests remove 10% and 30% of ranks reproducibly under the selected opponent mixture.
They measure degradation behavior only. Because missing ranks weaken or distort simulated rivals,
league-outcome gains are never product-quality evidence. The meaningful outputs are ranked-pick
coverage, extreme-reach rate, legality, recommendation/pick stability, and failure transparency.

## Planned cells

| ID | Seed | Reps | Trajectories | Opponents | Dropout | Purpose |
|---|---:|---:|---:|---|---:|---|
| A0 | 2026082902 | 30 | 24 | homogeneous `(8)` | 0% | primary reference |
| A1 | 2026082902 | 30 | 24 | `(1,4,8,12)` | 0% | primary heterogeneity |
| A2 | 2026082902 | 30 | 24 | `(4,8,12)` | 0% | remove deterministic rank follower |
| A3 | 2026082902 | 30 | 24 | `(4,8)` | 0% | smallest plausible mixture |
| B0 | 2026082917 | 20 | 16 | homogeneous `(8)` | 0% | alternate-seed reference |
| B1 | 2026082917 | 20 | 16 | selected smallest adequate mixture | 0% | bounded variation |
| B2 | 2026082917 | 20 | 16 | `(4,8,12)` | 0% | post-failure fallback robustness; added after B1 failed |
| D0 | 2026082902 | 20 | 16 | selected mixture | 0% | paired degradation control |
| D1 | 2026082902 | 20 | 16 | selected mixture | 10% | moderate missing-market stress |
| D3 | 2026082902 | 20 | 16 | selected mixture | 30% | failure/degradation stress |
| R1/R2 | 2026082999 | 2 | 4 | selected mixture | 0% | exact hash replay |
| U0/U1 | 2026082941 | 10 | 4 | homogeneous and selected mixture | 0% | opt-in top-four recommendation/explanation trace |
| S0-S5 | 2026083001-06 | 8 | 8 | homogeneous `(8)` vs `(4,8,12)` | 0% | post-core six-seed stability expansion |
| T0/T1/T3 | 2026083011 | 4 | 2 | `(4,8,12)` | 0/10/30% | degraded-market decision-surface expansion |
| P0 | 2026083021-25 | 2 | 1 | `(4,8,12)` | 0% | five-pair opt-in trace overhead/parity |
| Q0/Q1 | existing U0/U1 | — | — | homogeneous / `(4,8)` | 0% | evidence-qualified top-four Pareto diagnostic |
| Q2/Q3 | existing U0/U1 | — | — | homogeneous / `(4,8)` | 0% | preregistered compact-hierarchy feasibility diagnostic |
| M1/M3 | existing T0/T1/T3 | — | — | `(4,8)` | 10/30% | post-07 deterministic subgroup stability by QB mode, slot band, and normalized draft stage |
| N0 | existing U0/U1 + usability catalog | — | — | homogeneous / `(4,8)` | 0% | post-07 deterministic usability-stimulus coverage and selection-bias audit |
| O0 | existing T0/T1/T3 | — | — | `(4,8,12)` | 0/10/30% | post-07 degraded-data usability-stratum feasibility audit; no stimulus selection |

The “selected” mixture is chosen by adequacy, not best realized league outcome: prefer `(4,8)` if
its paired H2H lower bound clears -0.01 and its allocation diagnostics are not materially less
plausible than the wider profiles; otherwise use `(4,8,12)` only if it clears the same rule. If
neither passes, no mixture is selected as adequate and `(1,4,8,12)` remains a stress profile only.
This ordering was recorded while A2/A3 were still running and before their results were inspected;
it prevents outcome shopping.

S0-S5 was added only after the preregistered core completed, because the user requested scope
expansion through later checkpoints. It is explicitly exploratory. Six consecutive, prelisted
seeds each pair 144 homogeneous and 144 `(4,8,12)` drafts. Report every per-seed mean, sign, and
interval; the minimum/maximum mean; a seed-cluster bootstrap; legality; pick stability; and 1QB,
2QB, and superflex slices. Do not call the profile stable merely because a pooled interval passes.
Flag any seed mean below -0.01 and any format-direction pattern that fails to reproduce. No cell is
dropped after inspection.

T0/T1/T3 is another post-core exploratory expansion. It records the deterministic top four at
every test turn under complete, 10%-missing, and 30%-missing opponent market boards. The primary
outputs are exact primary match, top-four overlap, availability of stored-market-ADP fields, explanation
degradation, and whether four legal candidates remain. Outcome gains are ignored because D0-D3
already show that metadata dropout weakens the field. The UI gate is honest fallback, not stable
recommendations at any cost.

P0 alternates trace-off/trace-on order across five seed pairs after all product conclusions above
were recorded. It measures only the artifact bridge's full-draft elapsed time and serialized size.
Every paired pick trace and roster must be byte-identical. This cannot establish live React latency;
the bridge performs whole drafts and outcome evaluation, while the live board scores one state.

Q0/Q1 uses only the previously frozen U traces. For each state, it intersects components that are
numeric and not `unsupported` for all four candidates, then counts nondominated candidates across
immediate-lineup, bye/absence, and breakout value. It reports primary-dominated rate and frontier
size. This is a descriptive tradeoff diagnostic; component Pareto dominance is not global draft
quality because v5 includes legacy policy residual and other constraints.

Q2/Q3 also uses only the frozen U traces and runs before any product renderer is changed. It models
a conservative E1-compatible hierarchy as four candidate-specific structured-claim rows plus one shared evidence-
limitation row, while retaining every current `formatDraftExplanation` line in candidate details.
A reason is the first existing formatted, candidate-specific nonzero claim in formatter order;
league/degradation lines move to the shared row, and a zero redundancy line is not treated as a
reason. Report reason coverage, default-row reduction, expanded-claim parity, and states needing a
fallback reason. This is a static feasibility bound: it does not measure reading time, comprehension,
visual height, or whether the selected reason is the most useful to a human.

M1/M3 is a post-core expansion over frozen T traces only; it launches no drafts and uses no random
seed. Pair drafts by `(derived_seed, format_fixture)` and decision states by ordered test-team turn.
Require identical pair/state counts and pick numbers before computing exact primary match, top-four
Jaccard, and per-candidate stored-ADP support. Report by `qb_mode`, `slot_band`, and the first/middle/
final third of each draft's recommendation sequence. Every subgroup and denominator is reported;
there is no acceptance threshold, multiplicity claim, or outcome-quality interpretation. The sole
decision is whether a missing-ADP UI fallback must be tested uniformly or especially hard in a named
slice.

N0 is a post-07 usability-catalog audit over the frozen U0/U1 traces and the already selected
54-state catalog. It launches no drafts and does not select replacement stimuli. Resolve every
locator back to one exact U0 state and its paired U1 state, then report candidate-position coverage,
stored-ADP completeness, primary-change rate, top-four overlap, objective-disagreement counts, and
evidence presentation states by format, slot band, and phase. Also compare catalog summaries with
the full U population to make the intentional stress-selection shift visible. There is no pass
threshold or human-performance inference. The sole decision is whether the stress catalog is
sufficient by itself or requires separately selected representative/control and degraded-data
stimuli before a local usability study.

O0 is a post-07 feasibility audit over the frozen T0/T1/T3 traces. It launches no drafts and
selects no stimuli. Within every format × slot-band × round phase cell (rounds 1–5, 6–10, and 11+),
count candidate sets with four, one-to-three, and zero stored ADPs for each arm; separately count K
and DST candidate appearances/states. Require exact paired draft/state locators and four legal
candidates before aggregation. Report all empty cells. There is no pass threshold or usability
claim. The sole decision is whether the preregistered degraded-data sampling rule is feasible as
written or must declare a deterministic constraint-relaxation order before stimulus selection.

U0/U1 is authorized only if a test-first, opt-in bridge trace can reuse the single existing scorer
result without changing default bridge output or live policy behavior. It records the test seat's
top four at each turn, structured explanation state, score, and stored market ADP. Preregistered outputs
are primary-pick match rate, top-four set overlap, market-versus-model primary disagreement,
degraded-explanation frequency, and the share of unchosen alternatives that survive to the user's
next turn in the synthetic field. These are decision-surface and generator-sensitivity diagnostics,
not proof that any recommendation was correct or that survival probabilities are calibrated.

## Usability evaluation boundary

Offline policy outcomes and UI usefulness are separate families. Existing automated tests can
verify that the board produces four alternatives, explanations reflect actual score components,
degraded fields are disclosed, controls are reachable, and reduced-motion/static behavior remains
available. They cannot establish that users decide faster, understand uncertainty, or make better
picks. Those claims require a consented local study using task time, comprehension, confidence,
NASA-TLX or a shorter preregistered workload instrument, and counterbalanced board variants.

For this campaign, “usability evidence” means only information hierarchy, contract fidelity,
accessibility behavior, missing-data fallback, computational readiness, and avoidance of misleading
claims. It is integration-readiness evidence, not human-performance evidence.

## Results

### Baseline verification

The inherited experiment seams passed 48 targeted engine tests in 28.07 seconds. The draft-board
and explanation surface passed 216 frontend tests across 17 files, with four intentional skips, in
33.23 seconds. Coverage includes behaviorally model-field-insensitive market picks, seeded replay, legal and
duplicate-free draft invariants, candidate-pool completion, structured explanation fidelity,
roster-health calculations, and superflex bench shape. This is code-contract evidence, not a human
usability result.

After the formatter-unit audit, a fresh E0-focused baseline passed 31/31 tests across reason chips,
the structured explanation interface, live scoring, and the single-scorer integration contract.
This freezes the current ambiguous string as a known failing product semantic for a test-first E0
change; it does not make that wording correct.

The repository's installed Playwright/Chromium path was rechecked after the static audit. A direct
development-server probe loaded the `/draft` route at 375×812 and 1280×720 with no console or page
errors. With no backend keys it correctly rendered only the empty state: zero player rows and no
recommendation, table, or search control. Axe returned zero definite violations, 25 passes, and one
manual/incomplete gradient contrast item at both sizes; the 375 px shell had no horizontal
overflow. This verifies the no-key shell only. It neither contradicts the static populated-component
findings nor closes the populated keyboard/screen-reader/mobile gate.

A later disposable populated-route probe used a localhost PostgREST-shaped server with 96 explicitly
synthetic players, an empty signed-out league list, and no external credentials or vendor data. No
fixture route or product code was added. Playwright 1.61.1/Chrome for Testing 145.0.7632.6 loaded the
board without console/page errors; `Sim to my pick` advanced five legal intervening picks and
updated the heading to `RECOMMENDED · YOUR PICK`. At 375 CSS px, however, the 484 px table expanded
the document to 506 px, producing 131 px of page overflow; at 320 px the overflow was 186 px. The
single recommendation began about 3,409 px below the top and 155 visible tabbables followed source
order before its first control, including 60 player links and 60 assign buttons. The first table
action measured about 93.5×24.4 CSS px and the on-the-clock recommendation action about 56.4×18.4
CSS px, both below the product's 44×44 goal. Axe-core 4.12.1 found four serious unsupported-label
violations on status-dot spans, one minor empty table header, and one moderate heading-order defect;
four uncertainty-wrapper labels and contrast computation remained manual/incomplete. This is
automated synthetic-fixture development evidence, not VoiceOver, human-usability, contrast, or WCAG
conformance evidence. The disposable servers were stopped.

The dense recommendation region measured about 873 px high in the overflow-expanded 375 px layout
and 1,028 px high in the 340 px desktop rail; its four candidate blocks were about 187–242 px each.
Both exceed the corresponding 812/720 viewport height. E0a owns source order/reflow without hiding
evidence; E1 owns compact density and must measure its decision region separately after E0a.

The populated details also expose raw identifiers such as
`accepted_c02_c03_have_no_candidate_transaction_evidence` and `missing_league_key`. E0 now maps
known degradation codes to plain limitations and any unknown nonempty code to one generic honest
fallback, while retaining the raw structured payload for auditability. This is usability/copy
repair only; it does not promote unsupported evidence.

An exact `jq` count over the immutable U0/U1 receipts shows identical per-arm prevalence across
11,400 displayed candidates: 11,400 candidate-transaction codes, 5,760 `unsupported_evidence`,
5,640 `missing_league_key`, and six existing plain-text depth-order limitations. Thus every traced
candidate would expose at least one implementation code in the current expanded renderer. U0/U1
evidence hashes are `3a2ca8b1…`/`16421499…`; no new draft or outcome analysis was run.

The linked worktree does not contain its own pipeline virtual environment. The first relative-path
command failed before collection; the same tests passed using the existing root-checkout venv. No
code was changed to obtain the pass.

The later repository-wide wave passed all 63 frontend files: 584 tests passed and four intentional
skips. Frontend typecheck and production build passed; lint reported zero errors and one inherited
`react-hooks/exhaustive-deps` warning in `lib/useEspnSync.ts`. Pipeline passed 157 tests.

Full engine pytest is not green in this authoritative dirty research worktree: 3,911 tests passed,
one skipped, and 20 authority/promotion tests failed because the command lacked the recorded
`C05_PROD_ROOT` fixture and/or the harness correctly requires a clean committed tooling tree.
Supplying the clean C05E fixture to the focused 46-test authority set produced 37 passes and nine
failures; all nine are the current dirty-tree provenance refusal occurring before the tests' deeper
expected error. The dirty state is authoritative and was not reset, committed, or copied into a fake
clean receipt to make this gate pass. This is a verification limitation, not a waived green gate.

Artifact-local Python analyzers pass Ruff, formatting, and bytecode compilation; TypeScript
analyzers pass an explicit Node-typed `tsc` check. Forty-seven engine campaign/analysis receipts
recomputed their timing-independent evidence hashes with no mismatches. Twenty-nine compact summary
files correctly reference their parent campaign hashes rather than self-hashing, and all six
TypeScript compact/load/run diagnostic receipts match their own insertion-order canonical JSON hash
contract. A blanket Python canonical-hash check is invalid for those two receipt classes; separating
the contracts found zero mismatches across all 82 hashed JSON files. The 21-entry input/code hash
manifest also verifies with no mismatches.

The input manifest is content-valid but not directly portable through generic `shasum -c`: two
external entries use the literal portable prefix `$HOME`, which `shasum` does not expand. The other
19 entries verify directly, and resolving the two allowlisted path templates explicitly produces
the stored hashes for `weekly_2023.pkl` and `weekly_2024.pkl`, so all 21 still match. Future receipts
should store a logical input ID plus a path template and use a non-`eval` verifier that expands only
declared variables; do not rely on shell interpolation inside a checksum file.

The U0/U1 decision-surface analysis also reproduces byte-for-byte (file SHA-256
`b6f52a9682a63d6b77ea7b8716012c4f83350c355abcf5d71d37bc6e2c5b955d`) when invoked from the
worktree root with the stored repository-relative input strings. Running the same files from
`engine/` with `../artifacts/...` produces identical metrics but a different receipt/evidence hash
because the analyzer serializes and hashes the path strings. Future analyzers should record logical
artifact IDs and the invocation working directory/argv separately so path spelling does not masquerade
as evidentiary change.

The later startability-boundary audit passed 127 focused frontend availability/scorer/full-draft/
live-explanation tests and 74 engine availability/survival/publisher tests. No frontend query test
currently covers `getAvailabilityMap` selection or provenance, so these passes do not establish a
live published-snapshot handoff.

### Current decision-surface audit

- `DraftWarRoom.tsx` calls `scoreBoardWithExplanations` once and keeps four candidates. This is the
  correct reuse seam for compare/presentation work.
- `LiveRecommendations.tsx` currently renders every candidate with rank, link, position, optional
  draft button, all reason chips, equity, every formatted explanation line, and uncertainty. Four
  repeated stacks create high information density at the exact moment the user is on the clock.
- The current chip list is not fidelity-clean as a compact selector. `DraftWarRoom.tsx` sets the
  `vona` reason when `equityImpact >= 10`, but `equityImpact` is lineup gain versus the current
  roster, while the chip claims value over the player available next turn. The VONA-like quantity
  is the explanation's `immediate_lineup` component from `marginalStarterValue`. Separately,
  `run-risk` says “get ahead” although only recent concentration is observed, `upside` says median
  although the code compares ceiling to mean, and `ADP value` has no source/as-of contract. E1 must
  not blindly promote `reasons[0]`; reason fidelity is a prerequisite or a structured-claim fallback
  must be used.
- The view buttons are native buttons, global focus styles exist, and the recommendation list is an
  ordered list. However, the view group has no tab/listbox semantics or selected-state attribute,
  search relies on placeholder text, and no draft-specific Playwright/axe or keyboard-flow test was
  found. Those are release gaps, not confirmed accessibility defects.
- Static markup does establish several concrete accessible-name/state gaps: the player search has no
  label, view and position-filter buttons expose no `aria-pressed` state, repeated draft actions do
  not name the player, and the player table uses data cells rather than row headers for names. These
  need only native labels/attributes/semantics in `DraftWarRoom.tsx`, not a component library.
- `Auto-draft all` is a primary-row action beside clock controls. It may remain a test/manual-mode
  convenience, but future hierarchy should demote it behind a secondary disclosure so the product's
  default path stays human-controlled. No usage evidence exists to justify removing it outright.
- The optional repository browser-skill helper still requires a one-time setup and was not
  installed. Direct repository Playwright was sufficient for a disposable populated-route probe.
  It confirmed source-order, page-reflow, target-size-goal, heading, table-header, and unsupported
  ARIA defects while also confirming the basic manual simulation transition. No screen-reader,
  200%-zoom, connected-feed, light-theme, human-time, or conformance pass is claimed.
- `PlayerValue` carries `adp` and `rank` without a source or as-of field. `getAvailabilityMap`
  selects season/week but collapses the result to `player_id -> p_startable`. Repository-wide
  call-site inspection found no live caller: `app/draft/page.tsx` does not fetch it,
  `DraftWarRoom` does not pass `AIContext.availability`, and `candidatePool` cannot accept the
  published map. The board therefore falls back to player-row injury/team/depth metadata even
  though nearby comments describe the engine-published value as truth. A truthful data-
  freshness badge therefore needs a provenance contract before UI work; the current fields cannot
  support vendor or timestamp claims.
- `expectedReplacementAtNextTurn` is a deterministic projection-depletion heuristic. It does not
  return a survival probability and must not be relabeled as one.
- The draft page explicitly reads the `vorp` engine, while `LiveRecommendations` passes only its
  value row to `playerUncertainty(..., null, "pts")`. That adapter maps VORP floor VOR, shaped
  ranking value, and ceiling VOR to P10/median/P90 projected points. The active fields do not support
  those probability or unit labels. Suppress this strip on the draft path and show one calibrated-
  range-unavailable group limitation; audit shared player surfaces separately.

A fresh focused baseline passed 18/18 shared uncertainty adapter tests and 3/3 live integration
tests. The adapter suite explicitly accepts the three-field fallback, so green tests document the
reproducible semantic defect rather than validating its use on the VORP draft path.

Negative and null results remain in this report; passing a development gate does not grant
production authority.

### Primary opponent-profile result

A0/A1 completed 1,080 drafts and 25,920 season trajectories. All 1,080 drafts were legal and
duplicate-free. The homogeneous evidence hash is
`06a0031d580e46bcb6b7ce2b9a7fc7da0819da290477c25e23fac1dd8521bac5`; the wide-mixture hash is
`60b1680ea6d8a027441f7e050ebb646699f28f2a1cc7ff11c35ae27142ba4747`; paired analysis is
`b07d966c75b605a90b393125e35f0ca77355e78e722ac0bb633c4826af3d75b6`.

| Wide `(1,4,8,12)` minus homogeneous `(8)` | Mean | Paired 95% interval |
|---|---:|---:|
| H2H | -0.00155 | -0.01105 to +0.00803 |
| Starter strength vs median | +0.00110 | -0.00647 to +0.00907 |
| Playoff delta | -0.01026 | -0.03888 to +0.01968 |
| Finish rank | -0.037 | -0.363 to +0.298 |

The wide field **misses** the preregistered H2H noninferiority gate because -0.01105 is below the
-0.01 margin. The miss is narrow and the mean is close to zero, but thresholds are not moved after
seeing results. This is negative evidence against selecting the widest mixture as the smallest
adequate default.

The two smaller mixtures were evaluated under the same 540 paired cells:

| Treatment minus homogeneous `(8)` | Mean H2H | H2H 95% interval | Mean changed pick slots | Decision |
|---|---:|---:|---:|---|
| `(4,8,12)` | -0.00002 | -0.00845 to +0.00774 | 7.87 | passes |
| `(4,8)` | -0.00200 | -0.009887 to +0.00557 | 7.10 | passes by 0.000113 |

A2 hash is `824f950b57ba34b737054915b4f00c9c9d4b650dd60a23ba28933d207ffddbc4` and its analysis is
`c9caac68b760d222504a446177f0c01db3be4927bfd79d789712a6d1d5183340`. A3 hash is
`24868877ade4754f8a9248348b9b892de270ceed9f6adb4ef7a78b7f61e8534d` and its analysis is
`9bdcc764156aba18a30145b484632adce2b9340f8fde8c1e79a1d0f304d8aaad`.

Per the pre-inspection ordering, `(4,8)` is the smallest adequate mixture on the primary seed and
advances to the preregistered alternate-seed check. Its margin
is too close for integration: alternate-seed replay and future real-draft validation remain
mandatory. The result supports the sufficiency of the existing `topK` mixture seam for the *first
experiment*, not the adequacy of `topK` as a complete opponent model.

The alternate-seed result does **not** replicate that adequacy. B0 hash is
`74e8176040457e9dfad09f85e78e3e53d8a33483a3ae1173409a02164a26f130`; B1 hash is
`08110b728c11cf1758ba2f981a185a232e2d18a1bb20e6bab8d5a59ce79945b4`; analysis is
`65516e7a9b0706801f491e2ff7131b2701f5cabdaa4825761c9150497a7ac3b1`. On 360 paired drafts,
`(4,8)` mean H2H was -0.00512 with interval -0.01448 to +0.00444, failing noninferiority.
Starter strength remained near zero (+0.00126, -0.00601 to +0.00887), so the honest conclusion is
seed-sensitive uncertainty rather than broad harm. `(4,8)` is not adequate for integration.

B2 found that `(4,8,12)` is the more stable fallback. Against the same alternate-seed B0 cells,
its mean H2H delta was +0.00010 with interval -0.00979 to +0.00993; starter strength was +0.00049
(-0.00774 to +0.00922), and playoff delta was -0.00642 (-0.03855 to +0.02518). All 360 treatment
drafts were legal and duplicate-free. Its campaign hash is
`19d4c1769c2b436c49b43e6c300287e34e5a3571c059666c6f7aa9de16dd8af6`; paired analysis is
`12655ef9ab057f17d5d00ee9186b90530233dcbb1b52e340ab0f6fb14a1c9120`.

Receipt audit recovered an omitted analysis parameter: B2 reproduces byte-for-byte only with
`analyze_campaigns.py --seed 2026082918`; the stored file SHA-256 is
`cd8440e302632dcefa9edfe27f5a0cf77ece6055f8612c30387f5018385035e5`. The current default
analysis seed changes bootstrap interval endpoints but not paired point estimates or the underlying
campaigns. B1 reproduces byte-for-byte with the current default, and the six-seed aggregate also
reproduces byte-for-byte from its 12 source campaigns. The B2 report is internally hash-valid, but
it does not store its analysis seed. Future receipts must serialize campaign seed, analysis seed,
resample count, confidence level, and analyzer hash; a command reconstructed after the fact is not
sufficient provenance. The authoritative stored B2 artifact was not overwritten.

This passes the preregistered alternate-seed gate, but B2 was added sequentially after B1 failed
and both seeds remain draws from the same synthetic picker family. `(4,8,12)` is therefore the
preferred bounded profile for the next offline experiment, not an integration-ready learned model
or live survival authority. It changed 8.22 pick slots per roster on average; first picks matched
75.28% and mean roster Jaccard was 0.552. Those changes are large enough to stress the user-facing
choice set while staying reproducible and bounded.

Exploratory subgroups prevent a universal-profile conclusion. On the alternate seed, combined 2QB
cells show H2H -0.01811 (-0.03211 to -0.00405), including the 10-team 2QB fixture at -0.02286
(-0.04375 to -0.00209), while 1QB is +0.01642 (+0.00038 to +0.03237). The primary seed did not
replicate this split: 2QB was -0.00435 (-0.01686 to +0.00848). These were not separately powered
or multiplicity-adjusted gates, so they are hypothesis-generating rather than a format-specific
effect claim. They do show why one pooled mixture must not drive a live probability across 1QB,
2QB, and superflex; future opponent and survival calibration must stratify by league format and
report per-format reliability before pooling.

The post-core S0-S5 expansion added 864 homogeneous and 864 `(4,8,12)` drafts across six new base
seeds; all were legal and duplicate-free. The profile's 864 paired H2H deltas average +0.00642 with
a seed-cluster interval of -0.00284 to +0.01596. Artifact hash:
`29f8766f4daafbbf1b1f13cbf8bedda12909dbae226e26d45d3733660422d5dc`.

| Base seed | Mean H2H delta | Within-seed 95% interval |
|---:|---:|---:|
| 2026083001 | +0.00199 | -0.01492 to +0.01931 |
| 2026083002 | +0.02038 | +0.00420 to +0.03636 |
| 2026083003 | +0.00598 | -0.00912 to +0.02141 |
| 2026083004 | -0.00801 | -0.02493 to +0.00844 |
| 2026083005 | -0.00451 | -0.02093 to +0.01201 |
| 2026083006 | +0.02267 | +0.00550 to +0.04032 |

No seed mean crossed -0.01, but four within-seed intervals cross it. The earlier alternate-seed
2QB negative does not reproduce: across S0-S5, 2QB is +0.00957 with cluster interval -0.00131 to
+0.01875. Superflex remains the least stable slice at -0.00337 (-0.01750 to +0.01139), with seed
means from -0.02951 to +0.02721. The test roster changes materially—7.99 pick slots on average,
2.20% exact matches, 73.73% first-pick matches, and 0.567 mean Jaccard.

This is stronger evidence that `(4,8,12)` is a useful, bounded stress profile. It is still not
evidence that its weights represent real managers: only six seed clusters, one generator family,
one inspected season proxy, and no behavior-fit labels are present. The proper integration is the
offline experiment seam and its replay/diagnostics, not a live probability or opponent persona.

The same-family stop rule is now active: do not add more `topK` tuples or synthetic seeds merely to
narrow these intervals. The next uncertainty is behavioral realism, which this generator cannot
answer about itself. Further opponent work requires lawful point-in-time choice histories and starts
with rank-only behavior fit/QB-format auditing; absent those data, retain `(4,8,12)` as stress only.

Two independent invocations of the reduced `(4,8)` replay cell produced the identical
timing-independent hash `47e0dd2cd5d62aebf8a114b77cbbb524f170c727751d45dc563d18494318a8bd`.
Each contained 36 legal, duplicate-free drafts and 144 trajectories. This establishes exact seed
replay for the current code/input snapshot; it does not validate the realism of that snapshot.

Opponent assumptions changed the actual path materially even when aggregate roster quality was
similar: only 0.37% of paired test rosters matched exactly; first picks matched 46.30%; mean roster
Jaccard was 0.480; and 9.99 pick slots changed per roster. Position-count deltas were near zero,
which means the field usually changed *which* players were available rather than gross roster
shape. This is strong development evidence for a decision-support surface with alternatives and
tradeoffs, not evidence for an unattended optimizer.

Secondary paired diagnostics found bench/bye coverage -0.00154 (-0.00803 to +0.00488),
replacement quality -0.00955 (-0.02021 to +0.00102), and championship proxy -0.01404 (-0.03086 to
+0.00294). These secondary intervals are exploratory and do not add a new gate; they reinforce the
decision not to treat the wide mixture as harmless merely because primary mean H2H was near zero.

Synthetic market-alternative survival also moved enough to reject a single fixed opponent
assumption for future probability claims. Across eventually drafted top-four market alternatives,
survival was 19.30% in the homogeneous field and 15.49% in the wide field. At a 6-12 pick horizon,
the rates were 8.31% and 2.38%; at a 1-5 pick horizon, 64.45% and 56.49%. These are circular
generator diagnostics, not live calibration: candidates exclude undrafted players and are market
alternatives rather than BlitzBoard's top four.

### Missing-market degradation

D0/D1/D3 completed 1,080 legal, duplicate-free drafts under the `(4,8)` stress profile. The
control, 10%-dropout, and 30%-dropout campaign hashes are
`efe4ae5f097a40fdf1ff92c26c0737db2447ce02989f0c1513349f379dca30a4`,
`a4185a0adefbb762cfeaddf1876d6c808a9fb7402049c3c41371b7972c2b3f43`, and
`3ab3709b03870168cabe922c46584964970eeb571b20d95efd89a7c05d64b052`; paired analysis is
`494a7c33e29d40b9bec066cf01c44ae2753cd3a73007cacf11f9c5cf8663d060`.

| Treatment minus complete-market control | ADP-supported opponent picks | Extreme early reaches | First-pick match | Changed test picks | Mean H2H delta (95% interval) |
|---|---:|---:|---:|---:|---:|
| 10% market metadata removed | 88.91% vs 92.61% | 0.00% vs 0.00% | 82.50% | 11.17 | +0.08212 (+0.07025 to +0.09340) |
| 30% market metadata removed | 74.76% vs 92.61% | 9.09% vs 0.00% | 63.61% | 13.67 | +0.17372 (+0.16078 to +0.18577) |

The large apparent outcome gains are a simulator failure signal: removing ADP makes rivals choose
less realistically, leaving stronger players to BlitzBoard. At 30% dropout, the opponent
ADP-supported-pick rate falls 17.85 percentage points, extreme early reaches appear, and the test roster changes
nearly everywhere (mean Jaccard 0.177). Consequently, no degraded-field league outcome may be used
as recommendation-quality evidence. A live board should retain the current recommendation only
when its own required inputs remain valid, mark market comparisons unavailable or partial, and
never silently turn missing ADP into favorable evidence. Future evaluator reports should make
field-realism diagnostics first-class gates before showing league-outcome summaries.

The false favorable signal is systemic rather than isolated to one favorable slice. D1's apparent
H2H delta is positive in every QB mode (+0.05284 to +0.10625) and every slot band (+0.07321 to
+0.08904); D3 is likewise positive in every QB mode (+0.16747 to +0.18050) and slot band (+0.16035
to +0.18618). These are not robustness wins. Consistent improvement when opponent information is
destroyed is a stronger indication that the test team is exploiting a weakened field. Missing-source
gates must therefore precede outcome interpretation at aggregate and subgroup levels.

T0/T1/T3 then traced 1,140 decision states per arm to test the presentation boundary directly.
All 216 drafts remained legal and duplicate-free, and every state retained four candidates.
Stored-market-ADP support and recommendation stability degraded sharply:

| Surface | Candidate rows with ADP | States with any ADP | States with all four ADPs | Primary match vs control | Top-four Jaccard vs control |
|---|---:|---:|---:|---:|---:|
| Complete input control | 76.16% | 90.88% | 59.91% | — | — |
| 10% source dropout | 48.79% | 81.14% | 13.86% | 32.11% | 0.348 |
| 30% source dropout | 18.57% | 42.98% | 1.58% | 15.35% | 0.176 |

The immutable T/U JSON retains legacy metric keys such as
`candidate_market_rank_available_rate`, but the bridge field those metrics inspect is
`market_adp`. Interpret these results as ADP coverage. Do not rewrite the stored receipts; rename
the keys in the next schema version and keep an explicit compatibility map.

The T1/T3 analysis hashes are
`92b034921d16d45a2d689a6d22643d4562f48d1899005cbe7663ccfb3e71c9c3` and
`7fbc9ef9fee70f086a9afb747c5bafc28ca9eb50be63e85de002831abf1e7846`.
The combined D report and both T reports reproduce byte-for-byte from their checked-in analyzers
when invoked from the worktree root with the stored treatment ordering and relative path strings;
file SHA-256 values are `9ca2282a…`, `e05c5189…`, and `7e5d7a97…`, respectively. D3's bootstrap
offset comes from being the second treatment in the combined invocation, another reason to serialize
ordered argv rather than only a generic analyzer name.
The dropout is applied to the opponent market board, so it changes intervening picks and cascades
into a different available pool; the low match rates are not a controlled estimate of deleting one
ADP value from a fixed state. They are a realistic failure-mode stress for the whole room.
The current v5 scorer itself does not read ADP, so dropout changes its candidate identity indirectly
through that altered draft path while directly changing whether an ADP comparison can be displayed.
Do not describe T1/T3 as an ADP feature-weight ablation.

The usable fallback is now concrete: keep the BlitzBoard candidate list when its model inputs are
valid, show market cells individually as known/unknown, summarize source coverage once (for example,
“stored market ADP available for 2 of 4”), and disable market-derived disagreement/survival language when
support is insufficient. Do not drop candidates with missing ADP, fill ADP from future snapshots, or show
a stable-looking aggregate when only one candidate has a source value.

M1/M3 then paired all 72 drafts and 1,140 decision states per treatment without launching new
drafts. QB-mode and slot-band results are uniformly unstable rather than exposing one safe segment:
T1 primary match ranges 28.52–39.06% by QB mode and 29.74–33.68% by slot; T3 ranges 14.06–16.18%
and 12.11–17.63%. The stronger pattern is draft stage:

| Normalized test-team stage | Control candidate ADP support | T1 candidate ADP support | T1 primary / top-four Jaccard | T3 candidate ADP support | T3 primary / top-four Jaccard |
|---|---:|---:|---:|---:|---:|
| first third | 99.02% | 73.10% | 54.90% / 0.560 | 40.07% | 28.92% / 0.334 |
| middle third | 84.48% | 51.55% | 22.58% / 0.262 | 10.89% | 5.11% / 0.074 |
| final third | 41.67% | 18.40% | 16.11% / 0.197 | 2.15% | 10.56% / 0.104 |

These are ordered-turn thirds, not fixed round bins, and have no inferential intervals. They show
that a missing-ADP fallback cannot be treated as a late-draft edge case: even the first third has
only 4.41% all-four ADP support under T3, while the middle/final thirds have none. Test the coverage
summary and mixed known/unknown cells in every stage. Do not interpret the middle-versus-late match
ordering as a behavioral effect; the candidate pools are different and late pools are smaller.

M1/M3 evidence hash is `54c8c1cdd6b228ebfb1b82cae329413d46aed4a9014de7674d3ebee32c17d1ce`;
file SHA-256 is `9a94b6047c7dc59ae5731fb1fcaede42a3064fb2848f1c1a937d479622b87a3b`.
Analyzer SHA-256 is `a08ea3136a83fcf45a5266391b34768c1cf8c170df5cc8b9d57823a3cc7813ac`.
The analyzer passes Ruff, format, and compile checks; a second invocation reproduces the file
byte-for-byte, and a mismatched-draft fixture is rejected without writing output. It stores logical
artifact names rather than path spellings.

### Strict market-field isolation correction

The poison tests prove **behavioral non-use**, not the stricter required non-receipt boundary.
`pickHumanAdp` reads only ADP, identity, position, roster, and RNG, and poisoned projection/VOR/
availability fields leave picks byte-identical. However, `draft-eval.mjs` constructs every player
as a full `PlayerWithValue` and passes those objects in the market arm's `ctx.pool`. The function
therefore receives hidden BlitzBoard fields at runtime even though it does not read them. All
campaigns in this report are behaviorally isolated stress tests, not structurally source-isolated
opponent evidence.

Before another opponent or next-turn campaign, pass a narrow market-only player/context object at
the bridge boundary and add a structural test that forbidden keys are absent, while retaining the
poison test. This is a small hardening of the existing picker seam, not a new opponent framework.
Existing campaign point estimates remain valid as generator-sensitivity diagnostics, but they do
not satisfy the product acceptance criterion that market-only opponents never receive hidden
fields.

### Preliminary homogeneous decision-surface trace

The opt-in U0 bridge trace records one zero-jitter `scoreBoardWithExplanations` result for the four
displayed candidates while separately preserving the existing seeded-jitter synthetic selected
pick. The new contract was written test-first: the first test failed with
missing `recommendations`, the implementation passed, a trace-isolation test then failed when a
human arm was traceable, and the bridge was tightened to reject that request. The post-change
targeted suites pass 51 engine tests plus 77 frontend contract tests with four intentional skips;
TypeScript typecheck also passes. Default bridge output is still opt-out.

U0 produced 180 legal, duplicate-free drafts, 720 outcome trajectories, 2,850 decision states, and
11,400 candidate rows under homogeneous `topK=8`. Its hash is
`3a2ca8b155c1a3c34b78718fd8c3f4b45257fb5f4afe428b0a8714716d0224e0`. The trace now scores the
live-board view at zero randomness while the synthetic outcome policy retains its existing seeded
5% jitter; an executable control proves tracing does not alter picks. The two primaries matched in
85.37% of states, quantifying why synthetic policy traces must not be silently described as the
exact live board.

Reusing the production `formatDraftExplanation` formatter against all U0 states quantifies the
default text surface before names, positions, chips, equity, or uncertainty are counted. Four
candidates emit a mean 21.10 explanation lines and 1,033 characters per decision state (median 20
lines; p90 28; maximum 32). A mean 13.98 lines are exact duplicates within the same four-candidate
state. U1 independently gives 21.07 lines, 1,032 characters, and 13.97 exact duplicates. Static
load-analysis hashes are `b9ce57ba88b185aae7169fb798261fe12f58f1c4743b35c49816b90892c7df45`
and `0fd4330c17600bcdd0fafaf37b7d21ff4965edbd5289fd8d96a47ebc0b3b3d38`.
These are information-load counts, not proof of cognitive load or faster decisions; they establish
the exact density and duplication that E1 must reduce without deleting faithful detail.

Every candidate had at least one degraded explanation input. Across candidates, 5,760 league
evidence states were `unsupported`, 5,640 were `fallback`, and none were `measured`; candidate-level
waiver/replacement churn had 0% numeric support. The current formatter therefore has no evidentiary
basis for repeating detailed league-status and churn degradation lines under all four candidates on
the default clock-pressure surface. Fidelity still requires disclosure, but a single compact
“limited evidence” signal with details on demand is more usable than repeated zero/unsupported
claims.

Within the displayed four, the model primary differed from the lowest stored-ADP candidate 61.82%
of the time. That is rank disagreement only, not probability or vendor advice. Unchosen displayed
alternatives survived to the next test-team turn 75.01% of the time in this synthetic homogeneous
field. The four candidates spanned more than one position in only 48.25% of states and averaged
1.57 distinct positions, so four adjacent score ranks are not automatically four meaningfully
different objectives. Early primary QB rates were 24.44% in 1QB, 100% in 2QB, and 33.33% in
superflex; the 1QB allocation concern remains visible and is not repaired by adding a comparison
panel. U1 is required before interpreting field sensitivity.

Existing explanation components often identify a different displayed candidate than the primary.
Immediate-lineup value varied within the top four in 72.00% of states and its maximum differed from
the primary in 51.22% of informative states. Bye/absence coverage varied in 58.21% and differed in
42.37%; breakout value varied in every state and differed in 45.05%; redundancy cost varied in
15.86% and differed in 46.02%. This directly supports user-selected comparative lenses because the
lenses surface real tradeoffs already present in the payload. It does **not** validate ranking
players by one component or authorize hidden objective rewrites; the first release should present
these differences side by side while preserving the v5 primary.

An evidence-qualified Pareto check reaches the same product conclusion without collapsing the
components into a new score. Across immediate-lineup, bye/absence, and breakout values (all numeric
and non-unsupported for every displayed candidate), U0 has multiple nondominated choices in 47.05%
of states and U1 in 46.98%; mean frontier size is 1.57 in both. Hashes are
`c9e41432c9f3e76b9357af3cf2bdeb757465c0abd253af23f560597bd2afe970` and
`21ec34f8aad5fa96552b3cbc048aa4d9834456ed10e19a124f1834d8bcf16395`.

The v5 primary is dominated on those three displayed components in 26.84%/25.26% of states. That
does not make it the wrong recommendation: v5 includes legacy residual, constraints, and other
terms outside this diagnostic. It does show that a single asserted choice hides real component
tradeoffs and that alternatives 2-4 are sometimes the sole nondominated displayed option. E2 should
show these component relationships, never relabel Pareto status as global quality or rerank by it.

U1 repeated the same 2,850 deterministic decision states against `(4,8)` opponents. Its hash is
`1642149962ab93a90c02a362f198ba24369866cf291cac992f06578525776843`; the paired decision-surface
analysis hash is `b60c03c7726ab354a1fde7cbe3f8fb2ba4c3645c2d546e2122094ae9dd26a9ce`.

Across paired turns, the exact primary recommendation matched only 63.12%, while top-four set
Jaccard was 0.647 and same-rank agreement across four slots was 54.33%. The alternative set is more
stable than the asserted first choice, so the UI should preserve several defensible candidates and
explain why field assumptions change priority. Unchosen-alternative survival was almost unchanged
(75.01% homogeneous, 75.26% `(4,8)`), but this broad aggregate hides player/horizon variation and
is not a probability forecast.

The usability conclusions replicated: every candidate had degraded inputs, no league evidence was
measured, waiver/churn numeric support was 0%, top-four position diversity remained low (1.56
positions; 47.40% spanning multiple positions), and model-versus-market primary disagreement was
62.91%. These data support compact provenance once per recommendation group, progressive detail,
and user-controlled component comparison. They do not support four repeated full explanations.

Stored-market-ADP coverage is incomplete even before the explicit dropout stress: 77.32% of U0 and
76.80% of U1 candidate rows have an ADP, and all four ADPs are present in only 61.33% and
60.35% of states. At least one rank exists in roughly 91.7%. A compare surface must therefore
support mixed known/unknown cells within the same state; it cannot require complete market rows or
silently remove candidates. The 62% disagreement statistic is conditional on at least one ranked
candidate and must be labeled accordingly.

The existing `detectRuns` heuristic was also replayed against the exact pick prefixes for every U0
and U1 decision state. It detected at least one hot position in 66.32% and 65.33% of synthetic
states; the primary was at a hot position in 32.28% and 32.21%, while any displayed candidate was
hot in 40.56% and 40.11%. Run-context hashes are
`a65d4824683a5069e00f167f516a205c74c140c10bb2d42338ae08272684a559` and
`91afbf74f4a4c0e790b1cfe8dd13d8515ed9c513101267e8f2d74d33a425674f`.
This supports a compact descriptive “recent room pace” view because the state is available and
often relevant to displayed options. It does not support “this run will continue”: the opponent
picker has no explicit run-reaction factor, and the detector is a fixed threshold rather than a
calibrated continuation model. UI copy should report observed counts/window only until a lawful
history can test predictive value.

The 2023-identity coverage audit exposes a separate evaluator blind spot. Of 34,320 U0 draft picks,
7,283 (21.22%) lack a 2023 weekly identity; 3,025 (8.81% of all picks) are offensive players, with
578 QB, 972 RB, 1,304 WR, and 171 TE selections. Yet none of the 11,400 displayed offensive
candidate rows lacks prior identity: all 1,440 missing-history candidates are K/DST, and they occur
late enough to be the primary in 360 states. Artifact hash:
`ade5aa5becaf7b341ebee364bd899b8ebb1d6c9b6ef74c1efbc7eee412a5b508`.

An absent weekly identity is not a verified rookie label; it can mean rookie, full-season absence,
ID mismatch, or archive omission. The result is therefore a coverage failure in this 2024 proxy,
not evidence that live v5 ignores rookies. It does mean the blind-market harness cannot honestly
score recommendation quality for rookie/incomplete-history offensive candidates: market opponents
draft them, the evaluator gives market-only identities zero proxy performance, and the traced board
never displays them. Future rookie tests need an explicit point-in-time prior/projection fixture and
an “insufficient history” UI state; they must not fill missing projections with realized outcomes.

A deterministic catalog now identifies 54 future usability-test states: one high-disagreement state
for every six-format × three-slot-band × early/middle/late cell. It stores locators and candidate
IDs rather than duplicating full payloads. Its hash is
`2fe4100341173556396402ef93eaadf499bab698c5c26afc09fc882a92f5d435`. Fifty-three of 54 selected
states change primary across opponent assumptions by design; mean top-four Jaccard is 0.129. This
catalog is a stress set, not a prevalence sample, and must not be used to claim users usually see
that much disagreement. It is suitable for deterministic component tests, design prototypes, and a
counterbalanced consented local study.

N0 resolved all 54 locators back to the frozen U0 state and exact paired U1 state, then compared
them with all 2,850 U pairs. The intended selection pressure is large: 53/54 catalog primaries
change versus 1,051/2,850 (36.88%) in the full population, while mean top-four Jaccard is 0.129
versus 0.647. Forty-seven of 54 catalog states have two or more displayed-component winners that
differ from the primary. This is useful challenge material, but not an ordinary-use control set.

The catalog also under-stresses missing data. Stored market ADP is present for 87.96% of its
candidate appearances versus 77.32% in the full population; 39/54 states have all four ADPs and
only 1/54 has none, compared with 1,748/2,850 and 236/2,850 respectively. It contains fallback and
unsupported league-evidence states but no measured/interpolated state, no DST candidate, and only
eight K appearances. Those are properties of the frozen stimuli, not estimates of live prevalence.

Decision: the 54-state catalog cannot stand alone for a human study. Keep it as the
high-disagreement stratum; freeze a separately sampled representative/control stratum from U0; and
select a distinct degraded-data stratum from T0/T1/T3. Do not fabricate measured evidence—add that
condition only after a valid point-in-time fixture exists. Report strata separately and include
unchanged-primary controls plus late K/DST cases. N0 launched no drafts. Its evidence hash is
`bbdbc71e450c8cfcf5a67b1fa41dbffbd7d35291ac9d820b9da1fde7534a4ec2`; file SHA-256 is
`8406cf8de62ea0df350a70b5a998c460d68dbcdfedc87ed28b565f6130a9c662`; analyzer SHA-256 is
`712594db480043a19f126ff72b2a6b0b5d2b29b61b047acfa1cb78b1227fe312`. The analyzer passes Ruff,
format, and compile checks, reproduces byte-for-byte, and rejects a valid but incompatible artifact
without writing output.

O0 confirms that a degraded-data stratum is feasible, but not as a complete three-way factorial.
Both T1 and T3 contain 1,140 exactly paired four-candidate states across all 54 format × slot ×
phase cells. At 10% dropout, 158 states have four known ADPs, 767 have one-to-three, and 215 have
none; at 30%, the counts are 18, 472, and 650. A mixed-known state exists in every one of the 54
cells across the two arms. A no-ADP state is absent only for 12-team 2QB/front/early and 14-team
superflex/middle/early; a four-known state is absent in 20 cells, predominantly middle/late.

The degraded traces also contain ample boundary fixtures: T1 has K in 116 states and DST in 96;
T3 has K in 112 and DST in 100. Therefore the study freeze rule should obtain complete-support
controls from U0, mixed-known degraded cases in every exact cell, and no-ADP cases with a declared
relaxation for the two empty early cells. Relax slot first within the same format and phase; if no
state exists, use a mixed-known state and retain an explicit gap flag. Do not relax format/QB mode
silently. Treat each selected T state as a fixed UI task across variants; do not interpret T-arm
differences as a presentation effect because dropout changed the intervening draft path.

O0 launched no drafts and selected no stimuli. Its evidence hash is
`62c896b9e048ce2cf80bcd8fd9523c79e57c4c597323a6adb9ded4ea1a99f9f4`; file SHA-256 is
`c3f45dcba9a4f21005d5ed98aaeca677327146c8ec1c4c498194b7e6169e73c4`; analyzer SHA-256 is
`601fc1c8fe7f78803acdcd2ebd24de7360a7d8829f1faa4a7eeda19985ccf128`. The analyzer passes Ruff,
format, and compile checks, reproduces byte-for-byte, and rejects mismatched draft keys without
writing output.

### Compact-hierarchy feasibility

Q2/Q3 apply the preregistered five-row default model to all 2,850 U0 and 2,850 U1 states. Every one
of the 11,400 candidates per arm has at least one existing candidate-specific, nonzero formatted
claim; every state also has a shared evidence limitation. The modeled default is therefore five
rows in every state versus current means of 21.10/21.07, a mean 75.4% row reduction in both arms,
while the modeled details retain every existing formatter line byte-for-byte. Hashes are
`bb7ba9c5db0d612f5b6cb9dec599755150ccd94db06f50315565a7d67743dd97` and
`d4435c37b13a79f040d31e2d9c33393ce77b1f645e173c0fdc88d984921c6222`.

The deterministic first-claim rule is not merely one repeated upside label: U0 selects 4,906
immediate-lineup, 2,706 bye/absence-coverage, and 3,788 breakout claims; U1 selects 4,929, 2,696,
and 3,775. This establishes that the E1 density target is mechanically feasible with existing
payloads and no second scorer call. The offline trace does not retain `Recommendation.reasons`, so
Q2/Q3 does not validate any live-chip wording or priority; it establishes a
structured-claim fallback and a row-count bound. It also does not measure pixels or assistive-
technology output or prove faster decisions. E1 should test its actual selector with focused live-
shape fixtures and preserve native details; the local study must decide whether the reason order is
useful.

### Regret measurement boundary

No retrospective “primary regret” number is reported from the U traces. The season fixture contains
weekly points for each candidate, but comparing candidate season totals would ignore roster slots,
replacement, later picks, and whether the player would start. Replaying an alternative pick and then
letting the same synthetic field finish would instead measure a counterfactual under an uncalibrated
generator. Neither is an honest user-decision label.

The next valid development experiment must force each of the current top-four actions into identical
cloned states, continue with preregistered opponent seeds, and evaluate roster-aware started points/
H2H; the confirmation experiment must use lawful out-of-time rooms and outcomes. Report regret only
within the contemporaneous reasonable top four, with the primary's distribution and weak-candidate
cases retained. Do not compare against an omniscient full-season board. This is experiment-first and
does not block the E0q/E0/E0a/E1/E2 presentation sequence.

### Trace performance boundary

P0 ran five alternating control/trace pairs, 36 drafts per arm and 570 traced decision states per
pair. Every non-trace draft field—including pick path and evaluated outcomes—was identical within
each pair, every roster was legal and duplicate-free, further confirming that the zero-randomness
trace consumes no policy RNG. Artifact hash:
`4ce65620c9d817881fcf5f5153109fe941420b7e94438c1e50271134bf9ffe22`.

Opting into full structured traces increased full-campaign elapsed time by a mean 42.09% (pair range
39.21% to 44.93%) and compact JSON size by 6.02×. Five pairs under non-isolated system load are only
a descriptive bridge benchmark. The paired difference is about 6.65 ms and 7.9 KB per traced
decision state, but it combines scoring, object construction, Python/Node bridge work, and final
serialization. It does not estimate the live board's single-state React latency.
The integration implication is nevertheless clear: keep trace capture opt-in and offline, and let
E1/E2 consume the recommendation objects the live war room already computes. Do not serialize every
structured state to the client or add a second live scorer call for presentation work.

## Integration map

| Decision | Exact seam and reuse | Evidence and missing data | Cost / authority | Required pre-release test |
|---|---|---|---|---|
| **Build now:** reason fidelity repair | `DraftWarRoom.tsx` existing explanation component, `reasons.ts`, and the current structured formatter; no second scorer | current VONA trigger is current-lineup equity, run copy overreaches observed evidence, rank/ADP has no source/date, `Immediate lineup contribution` omits its next-turn comparator/unit, and expanded details expose raw snake-case reason codes | O(4) presentation/explanation only; no score/rank change | VONA component fixture; descriptive run copy; unknown-source market copy; truthful expanded label; known/unknown degradation humanization with raw-payload parity; exact component value/state, score/order, and single-scorer parity |
| **Build now first:** suppress false draft quantiles (E0q) | `LiveRecommendations.tsx` plus existing live-integration contract; leave shared adapter for a separately scoped audit | active draft is VORP; floor VOR/shaped value/ceiling VOR are currently presented as P10/median/P90 points without a quantile/target/calibration contract | presentation only; one group limitation; no score/order change | no value-row/null-projection uncertainty call on draft path; no P10/P50/P90/points range; one visible calibrated-range-unavailable state; exact four IDs/scores/order/actions and scorer parity |
| **Build now after E0q, before compaction:** populated-board native semantics and reflow | `DraftWarRoom.tsx`, the existing status/sidebar components, and focused source/browser checks; no new dependency or fixture route | 320/375 px page overflow, 60-row/155-tab-stop barrier before recommendations, four serious unsupported status-dot labels, empty action header, heading skip, and sub-44 px consequential actions are directly observed on a 96-player synthetic local route | presentation/native CSS only; no score/order/pick change | zero page overflow at 320/375; table-local named scrolling only; recommendation precedes table actions; zero listed axe violations; keyboard/VoiceOver/200%/themes/feed states; exact scorer/order and sim-transition parity |
| **Build now:** compact default recommendation hierarchy | `LiveRecommendations.tsx`; keep `Recommendation`, `recommendationClaims`, and the four `recs` from `DraftWarRoom.tsx` | 100% of traced candidates have degraded inputs; no measured league evidence; waiver/churn unsupported; current repeated lines consume clock-pressure space | O(4) presentation only; no score/rank change | primary + three alternatives remain keyboard reachable; one compact group-level evidence signal; native details disclose every faithful claim; mobile 375 px, zoom, screen-reader, and reduced-motion QA |
| **Build now:** side-by-side compare for two to four existing candidates | same `recs`; `DraftExplanationPayload.components`; `equity`; player `adp`/`rank` only when semantics are labeled | top-four primary changes across field assumptions while the set is more stable; components often favor different displayed players; only the next-turn edge is projected lineup points, while coverage/breakout/redundancy are weighted score terms | O(4 × components), presentation only; invoke scorer once | source-contract test still sees one scorer call; missing metrics render “unavailable”; no generic points header across unlike terms; rank disagreement never renders as probability; keyboard row/column headers announced |
| **Experiment first:** user-selected component lens | highlight immediate lineup, coverage, breakout, or redundancy within compare; do not sort initially | component maxima differ from primary in roughly 42–51% of informative U0 states; standalone component ranking is unvalidated | O(4); view-only first | log/view-test disagreement without mutating `scoreBoard`; human task comprehension and workload study on catalog states |
| **Experiment first:** descriptive draft-room dynamics | reuse `detectRuns`, current `allPicks`, and candidate positions; display observed recent counts/window, never continuation probability | a hot position exists in about 65–66% of synthetic states and intersects the displayed set about 40%; opponents do not explicitly react to runs | O(recent 1.5 rounds), presentation only | exact prefix replay, count/window fidelity, no causal/probability copy, stress-test K/DST late-run noise, human comprehension study |
| **Experiment first:** next-turn survival | after strict market-row isolation, add a pure module beside `draftAI.ts`; reuse `pickHumanAdp`, snake math, `allPicks`, roster state, and seeded bridge; never reuse health availability type | synthetic market-alternative survival changes materially by opponent profile; no real 2026 labels and no calibrated forecast exist; current market bridge fails structural non-receipt | bounded rollouts can be expensive; worker/debounce only after timing evidence; must not change v5 ranking initially | narrow runtime forbidden-key gate, exact replay, convergence, legal rollouts, calibration/Brier/reliability on lawful real histories, honest missing-data fallback, visible sample/model timestamp |
| **Experiment first:** provenance-bearing live `p_startable` handoff | existing `player_availability` table, `getAvailabilityMap`, `AIContext.availability`, and publisher; no new table or pipeline | schema already stores season/week/source/updated_at, but the query discards provenance and the live page has no caller; focused frontend fallback/optional-map suites pass 127/127 and engine model/publisher suites pass 74/74, while no frontend query-selection test exists | separate shadow unit; no E0q/E0/E0a/E1/E2 dependency and no C05 promotion; reconcile candidate prefilter and final score under one immutable snapshot before authority | typed provenance fixture, neutral missing-data behavior, same-snapshot prefilter/scorer test, no duplicate discount, exact score/order under missing map, legality/full-draft gates, paired availability-only no-regression campaign |
| **Experiment first:** `(4,8,12)` opponent mixture | `pickHumanAdp` plus `_draft_configuration`/`opponent_profile`; first add a narrow market-only runtime row/context; no new framework | passes two seeds while `(4,8)` fails its alternate seed; exact recommendations remain field-sensitive and all evidence shares one generator family; B2 analysis seed was recoverable but omitted from its receipt; current bridge is behaviorally insensitive to hidden fields but still passes full `PlayerWithValue` objects | offline only; zero production authority; strict source-isolation gate currently fails | next canonical season, real point-in-time draft labels, subgroup bounds, retained poison test plus runtime forbidden-key assertion, no hidden projection fields received; serialize campaign/analysis seeds, resamples, confidence, and analyzer hash |
| **Experiment first:** market/source comparison | `PlayerWithValue`, `getAllPlayersByValue`, future point-in-time snapshot contract | live `adp`/`rank` has no source/as-of/type; no vendor parity evidence | presentation cheap, acquisition/legal work dominant | lawful license/provenance review; immutable as-of/source/type; rank-vs-ADP-vs-projection labels; stale/missing state |
| **Experiment first:** local usability study | three separately reported strata: 54-state disagreement stress catalog, frozen representative U0 controls, and T-derived degraded-data states; E0q/E0/E0a-repaired dense versus compact versus compare prototypes, with advice order reserved for a later separate pilot | no participant evidence exists; N0 confirms the catalog strongly oversamples primary changes, under-samples missing ADP, and contains no DST candidate; adjacent time-pressure research does not establish the correct draft advice order | human time, not runtime | consent, counterbalanced order, predefined task correctness/comprehension/time/workload endpoints, accessibility accommodations; no measured-evidence condition until a valid fixture exists; agreement/reliance is not a success metric |
| **Experiment first:** rookie/incomplete-history assistance | new point-in-time fixture and explicit provenance state; reuse current candidate contract only after values exist | 8.81% of synthetic draft picks are offensive identities absent from prior weekly data, but none appears in traced offensive top-four candidates | data acquisition dominates; no realized-outcome imputation | distinguish rookie/absence/ID mismatch, lawful preseason prior, weak-candidate honesty, missing-state UI, temporal holdout |
| **Reject/defer:** change 1QB policy in this unit | no live change to `DEFAULT_POLICY.overfillDepth.QB` | repeated 1QB QB overcapitalization is real development evidence, and a depth-2 shadow was promising, but no untouched season confirms it | would alter recommendations | authoritative 2025/2026 point-in-time fixture and unchanged preregistered gate |
| **Reject/defer:** learned agents, MCTS/POMDP, regret optimizer | none | a two-policy existing seam already produces meaningful stress; training data and holdout remain absent | high complexity/latency | only reconsider after simple mixture and rollout models fail on real labels |

The most defensible first integration is E0q: suppress the confirmed false draft quantile strip and
show one honest unavailable-range state without changing score/order. The six-file bounded E0 reason-
fidelity repair follows before one reason becomes prominent. The
populated-board accessibility/reflow repair follows as an independent native-markup unit before E1:
otherwise compaction would be reviewed on a page that still puts 60 rows and 155 tabbables ahead of
the decision aid. Compact presentation then follows to address measured density; compare remains a
separate E2 unit.
