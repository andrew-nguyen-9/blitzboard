# Draft-Assistance Expansion Plan

**Prepared from:** the checkpointed deep experiment campaign started 2026-08-29 04:30 CDT

**Authority:** planning and development evidence only. Shipped v5 remains production authority,
C05 remains closed, and no result here authorizes a scoring, deployment, or vendor-access change.

## Outcome

Expand BlitzBoard as a fast, honest decision-support board. The user should see a primary candidate,
several defensible alternatives, the consequential tradeoff, and the limits of the evidence without
reading a full analytics report while the clock runs.

The experiment campaign changes the roadmap in four ways:

1. Truthful copy and native populated-board usability move ahead of compaction and new modeling.
   Every traced candidate had degraded inputs, no league-evidence row was measured, and candidate
   waiver/churn value was unsupported. Repeating those details four times is faithful but unusable,
   but the current populated mobile page also overflows and puts 60 rows/155 tabbables ahead of the
   recommendation. E1 must not paper over those defects.
2. A comparison view is justified. Existing component maxima often favor a different displayed
   candidate, and the primary changes more than the top-four set when opponent assumptions change.
3. A small `topK` mixture is useful for stress testing but not ready to integrate. `(4,8)` passed one
   seed narrowly and failed another; `(4,8,12)` cleared both development seeds and is the preferred
   next offline profile, but it is still one synthetic generator family rather than a calibrated
   belief.
4. Next-turn survival needs its own data/model program. Synthetic survival changes under opponent
   assumptions, so the current deterministic replacement heuristic cannot be relabeled as a
   probability.

## Decision ledger

### Build now

#### E0. Recommendation-reason fidelity repair

Before making one reason visually dominant, correct the existing semantic mismatches: VONA must be
driven by the structured `marginalStarterValue` component rather than current-lineup equity; run
copy must describe observed recent picks; upside must say mean rather than median/probability; the
rank/ADP gap must disclose unknown source/date; and the fallback must not assert “best value.” This
also relabels the expanded immediate-lineup sentence as projected lineup points over estimated
next-turn replacement and translates raw degraded-input identifiers into bounded user-facing
limitations while preserving the structured codes. This is a six-file presentation/explanation unit with no
score or order change. See
[`2026-08-29-reason-fidelity-unit.md`](2026-08-29-reason-fidelity-unit.md).

#### E0q. Suppress false draft quantiles

The active draft reads VORP values, but `LiveRecommendations` passes floor VOR, shaped ranking
value, and ceiling VOR to a loose adapter that labels them P10/median/P90 projected points. Those
fields do not share the declared probability/target/unit contract. Remove the strip from the draft
path and show one visible group limitation, `Calibrated projection range unavailable`, without
changing any candidate, score, order, action, or scorer call. Audit player table/detail uncertainty
separately; do not broaden this small repair into a new model. See
[`2026-08-29-draft-uncertainty-semantics.md`](2026-08-29-draft-uncertainty-semantics.md).

#### E0a. Populated-board native semantics and reflow

**User question:** “Can I reach, understand, and act on the recommendation before navigating the
entire player table?”

A disposable 96-player local route found 131 px of page-level overflow at 375 CSS px and 186 px at
320. The recommendation started about 3,409 px down and its first control followed 155 tabbables,
including 60 player links and 60 assign actions. Axe found four serious unsupported status-dot
labels, plus an empty table header and heading-order defect. The on-the-clock recommendation action
was about 56×18 CSS px, below the product's 44×44 consequential-action goal. Basic manual simulation
still worked and no console/page error occurred.

Fix those bounded presentation defects after E0q and E0, before E1. Reuse native labels, pressed buttons,
row/column headers, semantic status text, one recommendation instance, CSS grid sizing, and one
table-local overflow region. Do not add a component framework, fixture route, scorer call, rank
fallback, or persistent state. Exact interactions/files/acceptance live in
[`2026-08-29-draft-board-native-semantics.md`](2026-08-29-draft-board-native-semantics.md).

**Gate:** zero page-level overflow at 320/375; recommendation precedes table actions in source and
focus order; no confirmed populated-route axe violation; 24×24-or-spacing criterion and separate
44×44 product goal assessed honestly; keyboard, VoiceOver/equivalent, 200% zoom, themes, empty/
filtered/complete/stalled states; exact scorer/order/pick-transition parity. Automated checks do not
substitute for the later participant study.

#### E1. Compact clock-pressure recommendation hierarchy

**User question:** “Who should I seriously consider right now, and what is the one tradeoff I cannot
ignore?”

**Scope:** presentation only. Preserve the four candidates and their order from the existing single
`scoreBoardWithExplanations` call.

**Default hierarchy:**

1. primary player, position, and draft action;
2. one concise evidence-backed reason;
3. one consequential tradeoff or limitation;
4. three compact alternatives with one-line reasons;
5. one group-level data state such as “limited evidence” plus native details on demand.

Do not print zero-valued unsupported redundancy text or the same league-evidence sentence under all
four candidates. Do not hide the limitation: consolidate it at the group level and retain every
structured claim in an expandable details region.

The measured baseline is 21.10 formatted explanation lines and 1,033 explanation characters per
four-candidate U0 state before names, chips, equity, and uncertainty; 13.98 lines are exact
duplicates within a state. U1 reproduces the result. E1 should cut default explanation rows by at
least 50% on those frozen states while preserving byte-equivalent expanded claims. That is an
information-density contract, not a claim that workload or decision time improved.

The preregistered Q2/Q3 dry run demonstrates headroom without editing the renderer: four existing
candidate-specific structured claims plus one shared limitation reduce formatted rows by 75.4% in both arms,
cover all 11,400 candidates per arm, and preserve all expanded lines. The chosen claim categories
span immediate lineup, bye/absence coverage, and breakout value. This passes the static feasibility
gate only. Offline traces do not retain the live `Recommendation.reasons` chips, so focused live-
shape UI fixtures must first reject or repair the current VONA/run/source-fidelity defects; the
consented study then determines whether the resulting reason is understandable and useful.

**Exact files:**

- `frontend/components/draft/LiveRecommendations.tsx`;
- `frontend/lib/v6DraftExplanation.ts` only if a pure compact-summary selector is needed;
- `frontend/lib/v6DraftLiveIntegration.c04.test.ts`;
- one focused renderer/summary test beside the component or formatter.

**Acceptance:**

- candidate order and scorer invocation count are unchanged;
- primary plus three alternatives remain visible without expansion;
- frozen U0/U1 states show at least 50% fewer default explanation rows, while expanded details
  contain every current `formatDraftExplanation` claim;
- missing/unsupported evidence is visible once and fully discoverable;
- no unsupported numeric claim is created;
- keyboard focus order follows visual order;
- buttons retain accessible names and 44 CSS-pixel target sizing where layout permits;
- when the decision region itself is scrolled to the top at 375×812, the primary, three alternatives,
  group evidence, and full-evidence summary fit in that viewport; global route chrome is not counted;
- 375 px width, 200% zoom, high contrast, reduced motion, and screen-reader structure are manually
  verified on the populated route. Direct repository Playwright is already available; the optional
  gstack helper need not be installed to satisfy this gate;
- existing explanation-contract, draft-integration, typecheck, lint, test, and build gates pass.

**Rollback:** revert the renderer/summary change. The scorer, schema, database, and stored data are
unchanged.

#### E2. Presentation-only compare panel

**User question:** “Why would I take A instead of B, C, or D?”

**Scope:** consume the current four candidates; do not rerank them and do not add simulations.

The exact interaction, mixed-evidence fixtures, responsive contract, file boundary, and rollback are
in [`2026-08-29-player-compare-unit.md`](2026-08-29-player-compare-unit.md).

The frozen U0/U1 traces provide a direct presentation rationale: 47.05%/46.98% of states have more
than one nondominated displayed choice across the three universally supported numeric components
(immediate-lineup, bye/absence, and breakout), with mean frontier size 1.57. The v5 primary is
dominated on those three components in 26.84%/25.26% of states, but that is not a policy-error label
because the shipped score includes residual and constraint terms outside the diagnostic. The panel
may expose the tradeoff; it must not badge “Pareto winners,” infer global quality, or reorder players.

**Initial columns:** player/position, current BlitzBoard order, market rank or ADP when source type is
known, immediate-lineup contribution, bye/absence coverage, breakout option, redundancy cost, and
evidence state. Market fields without source/type/as-of display as “source unavailable,” not as an
implied vendor opinion.

**Interaction:** native checkboxes or compare buttons select two to four candidates. On mobile,
render candidate cards or a horizontally scrollable table with persistent row labels; do not shrink
text into an unreadable matrix. Every color encoding has text/icon redundancy.

**Exact files:**

- `frontend/components/draft/LiveRecommendations.tsx` for entry controls;
- new `frontend/components/draft/PlayerCompare.tsx` only after the E1 hierarchy is stable;
- a focused `PlayerCompare.test.tsx`;
- `frontend/components/draft/DraftWarRoom.tsx` only to hold local selection/open state if the child
  cannot own it cleanly.

No database, engine, or scoring file should change in this unit.

**Acceptance:**

- scorer still runs once per board update;
- compare opens/closes without changing recommendation order;
- null values say “unavailable” and preserve evidence state;
- mixed support is summarized once (“stored market ADP available for N of 4”); comparison remains usable
  when only one or no candidate has a rank, without dropping an unranked candidate;
- rank disagreement is a signed/ordinal difference, never probability, confidence, or variance;
- table headers and candidate names form valid screen-reader relationships;
- escape/back behavior and focus restoration are tested;
- mobile layout does not conceal the draft action;
- rollback is component removal with no data migration.

The first compare test fixture should include one state with multiple nondominated candidates, one
state where the primary is dominated on the three displayed components, and one mixed-market state.
Assertions must prove faithful values and unchanged order, not assert that a participant ought to
pick a particular player.

### Integration order and collision ledger

| Unit | Must follow | Exact overlap that forces sequencing | Independent seams | Rollback proof |
|---|---|---|---|---|
| E0q false-quantile suppression | current v5/C04 contracts | touches `LiveRecommendations.tsx`; establishes the honest no-range baseline inherited by later UI units | shared player-surface audit stays separate | component/test revert is diagnostic only; safe fallback is no range |
| E0 reason fidelity | E0q | establishes the truthful reason/expanded-claim baseline consumed by every later UI variant; shares the live-integration test | no CSS, query, schema, opponent, or study-stimulus change | six-file revert restores identical scores/order |
| E0a native semantics/reflow | E0 | touches `DraftWarRoom.tsx` and heading markup in `LiveRecommendations.tsx`; landing concurrently with E0/E1 would blur semantic and hierarchy review | status-dot semantics and grid/table CSS do not touch the scorer | bounded markup/test revert; no persisted data |
| E1 compact hierarchy | E0a | rewrites `LiveRecommendations.tsx` after its honest-range, heading, source-order, and target-size baseline is green | consumes the same four recommendation objects; no board scoring change | renderer/test revert returns expanded post-E0q/E0/E0a surface |
| E2 compare | E1 | adds compare entry/state around the compact renderer; must inherit E1 focus/disclosure rules | new compare component remains read-only over existing payload | remove component/entry; E1 survives |
| Strict market-opponent isolation | none of E0–E2 for code, but required before another opponent/survival campaign | changes the experiment bridge/picker input shape and invalidates prior campaign comparability until replayed | engine/offline harness only; can be planned while UI units land | restore old bridge only for historical replay; never promote old full-row path |
| Point-in-time acquisition readiness | legal/source approval first | source receipt/schema must precede collectors; no UI may invent source/as-of | archival tooling and manifests; no v5 score path | disable source; immutable receipts stay |
| Draft-clock/advice-order experiments | strict market isolation plus lawful clock/autopick labels for opponent work; E0q/E0/E0a common baseline for UI work | clock state must remain an observed room field, not a profile diagnosis; platform autopicks stay separate | opponent and UI studies have separate outcomes and may fail independently | remove optional factor/study variant; C0 and default hierarchy survive |
| `p_startable` shadow handoff | provenance contract and separate preregistration | `DraftWarRoom.tsx` overlap means do not land beside E0/E0a/E1; candidate prefilter/scorer must share one snapshot | existing table/query/publisher; independent of next-turn survival | remove shadow read/flag; neutral fallback retained |

This order is about reviewability and rollback, not a mandate to implement everything. UI work may
stop after any green unit. Strict isolation and data readiness can proceed as separately authorized
experiments, but no new campaign should start until the runtime opponent input no longer contains
forbidden model fields.

### Experiment first

#### E3. User-selected lenses without hidden strategy rewrites

**User question:** “Show me the choice that best matches what I care about.”

Start by highlighting, not sorting. Four explicit lenses are enough:

- lineup now;
- absence coverage;
- upside option;
- roster balance/redundancy.

The traced top four contain informative differences often enough to justify these lenses, but a
single component is not a validated objective. A selected lens may emphasize cells and generate a
faithful one-line summary; it must not silently replace the v5 primary. If later testing supports
sorting, label the alternate order and retain “v5 order” as the default.

**Experiment:** on the frozen 54-state stress catalog, test whether the highlighted component winner
matches the component payload, whether users can identify the tradeoff, and whether the lens causes
them to mistake it for a probability or new global recommendation.

**Gate:** explanation fidelity 100%; no increase in unsupported claims; comprehension improves or
workload falls without a material decision-time regression. Exact thresholds must be set before a
participant study and powered against its intended effect, not chosen here.

#### E3b. Descriptive draft-room dynamics

**User question:** “What has the room actually done recently, and which of my four choices is
affected?”

Reuse `detectRuns(picks, numTeams)` and the existing displayed candidates. The first prototype shows
only observable facts: position, count in the recent 1.5-round window, window size, and which
displayed candidates share that position. Do not write “likely run,” “will be gone,” or any survival
percentage. U0/U1 replay detects a hot position in roughly 65–66% of synthetic states and finds a
hot-position candidate in about 40%, so the data are common enough to test without occupying the
default hierarchy permanently.

The late-round stress set must explicitly include K/DST signals: the current heuristic detected
small K/DST hot-state counts, which may be technically faithful but unhelpful. Acceptance requires
exact count/window fidelity, no score/order mutation, copy-comprehension checks, and a rule for
collapsing strategically irrelevant late-position noise. Predictive continuation or next-turn
survival stays in E5 and requires real labels.

#### E4. Local usability study

The full task battery, state sampling, counterbalancing, endpoint hierarchy, privacy protocol, and
release interpretation are in
`docs/superpowers/plans/2026-08-29-draft-assistance-usability-study.md`.

No human-performance claim exists yet. The 54-state catalog is a deterministic synthetic stress set,
not a representative sample. Use it to preregister a study before recruiting anyone.

**Variants:**

- A: current dense four-card surface after E0q uncertainty suppression, E0 fidelity, and E0a native repair;
- B: compact hierarchy from E1;
- C: compact hierarchy plus optional compare from E2.

E0q/E0/E0a apply to every arm so the study isolates hierarchy/compare usefulness rather than
rewarding a variant for removing known misleading copy, false quantiles, or navigation/reflow defects.

**Design:** within-subject, counterbalanced order. Draw balanced early/middle/late states across
1QB, 2QB, superflex, 10/12/14 teams, and front/middle/back slots. Do not show all 54 to each person
unless pilot evidence says workload is acceptable. Keep the underlying candidate payload fixed
within a state.

**Primary usability outcomes:**

- time from state reveal to committed choice;
- objective comprehension questions derived mechanically from payloads;
- ability to identify missing/unsupported evidence;
- workload using a preregistered instrument;
- confidence calibration: confidence should fall when evidence is explicitly degraded.

**Secondary outcomes:** compare usage, expansion usage, choice reversals, preferred information
density, and whether component disagreement is perceived as useful.

Do not score a subjective player choice as “wrong” merely because it differs from v5. A factual
question can have a payload-derived answer; player preference remains the participant's decision.

**Privacy:** obtain consent; collect the minimum demographic/context fields needed for analysis;
avoid account identifiers and real league data; use synthetic states; define retention/deletion
before collection; publish only aggregates that cannot identify participants.

#### E5. Next-turn survival baseline

The complete preregistration, label contract, calibration ladder, runtime study, and rollback are in
`docs/superpowers/plans/2026-08-29-next-turn-availability-experiment.md`.

**User question:** “If I pass, how likely is this player or tier to survive to my next pick?”

Keep this type and label separate from health/startability availability.

**Label for lawful real histories:** at a user decision time `t`, for each player available at `t`,
`survives_next_turn = 1` when the player is still undrafted immediately before the user's next pick.
Archive league format, team count, slot, current pick, next-pick horizon, roster constraints, board
source/as-of, and all intervening picks as they were known at `t`.

**Smallest baselines, in order:**

1. empirical survival table by market-rank gap and pick horizon with shrinkage/fallback;
2. regularized logistic model for the direct next-turn event using market gap, position, horizon,
   league format, recent position counts, and bounded opponent need summaries;
3. Monte Carlo from the existing seeded `pickHumanAdp` mixture only as a model-based comparison.

Escalate the second arm to a per-pick discrete-time hazard only if a validated selection-time or
scenario question needs it and the added structure improves held-out calibration/fidelity. Synthetic
rollouts may validate software and sensitivity before lawful labels exist, but they cannot displace
the real-label empirical baseline or establish a live probability.

Do not start with MCTS, POMDP, a learned agent, or a neural survival model.

**Offline evaluation:** temporal holdout, Brier score, log score, reliability bins with counts,
calibration intercept/slope, sharpness, missingness slices, rookie/incomplete-history slices, and
exact replay. Report both player and tier survival. Use cluster-aware uncertainty by draft/league.

**Product gate:** no probability enters the live board until there is a point-in-time, lawful,
out-of-time validation set and a defined stale/missing fallback. Synthetic U/D results can test
software and sensitivity only.

**Likely files after the data gate:**

- `frontend/lib/draftNextTurn.ts` as a pure typed consumer, not an overloaded health availability
  function;
- `frontend/lib/draftNextTurn.test.ts`;
- `frontend/components/draft/PlayerCompare.tsx` or a small next-turn panel;
- engine experiment code beside `blind_market.py` only if the current seam cannot emit labels and
  predictions cleanly;
- migrations/queries only after the point-in-time schema is approved.

#### E5b. Roster-aware reasonable-alternative regret

**Question:** “How costly was the primary versus the other reasonable choices available then?”

Do not subtract raw season totals. For each frozen state, score once to get the contemporaneous top
four, clone the state four times, force one candidate as the user action, and continue every arm with
identical preregistered opponent/season seeds. Evaluate roster-aware started points, starter strength,
paired H2H/playoff proxies, coverage, and legal completion. Regret is the primary arm's outcome minus
the best of those same four arms, never an omniscient player outside the displayed set.

This remains development evidence until repeated on lawful out-of-time rooms. Report the full regret
distribution, zero/tie rate, tail, candidate rank, format/slot/round, weak-candidate states, and seed
sensitivity. The action-forcing seam must consume no hidden future information and must replay
exactly. Add it to the existing bridge/harness only if a test proves the current state transition
cannot express a forced first action; do not create a counterfactual framework first.

Advance a recommendation change only if the same predeclared policy improves paired reasonable-set
regret without harming legality, primary H2H/starter strength, stability, or explanation fidelity.
The E0q/E0/E0a/E1/E2 presentation sequence does not need this result because it preserves v5 order.

#### E6. Heterogeneous opponent factor ladder

The complete source-isolation contract, factor sequence, behavior-fit hierarchy, partial-history
updating boundary, and stop rules are in
`docs/superpowers/plans/2026-08-29-heterogeneous-opponent-experiment.md`.

The current seam varies only reach tolerance. Its poison tests establish behavioral model-field
insensitivity, but the bridge still passes full player rows; project those rows to the narrow
market-only runtime contract before another campaign. `(4,8,12)` clears both pooled development seeds and
should be the next control, but exploratory alternate-seed 2QB cells are materially negative while
1QB cells are positive; the primary seed does not replicate that split. Treat this as a mandate for
format-stratified diagnostics, not proof of a format effect. After strict non-receipt passes, add one bounded, source-isolated factor
at a time and require a behavior target from lawful histories before choosing a coefficient:

1. early/late QB tendency by league format;
2. positional preference or roster-construction template;
3. reaction to own starter/bench needs;
4. bounded response to a recent positional run;
5. stack/handcuff preference only with observable team/role metadata;
6. recognizable-name or home-team bias only if lawful draft histories can estimate it.

Each factor must be deterministic given seed/profile/state, keep all choices within a bounded market
window, preserve roster legality, and pass the model-field poison test. A factor that cannot be
estimated stays off; it does not receive a plausible-sounding hand-tuned coefficient.

Stop expanding the `topK` grid. The campaign already establishes bounded stress and seed variation;
the next gate is behavior fit on lawful histories, not more self-validation by the same picker.

**Experiment matrix:** homogeneous control, single-factor arm, smallest accumulated mixture; two
base seeds; six canonical formats; three slot bands; 10/12/14 teams; shallow/deep bench; metadata
dropout; positional-run stress; exact replay. Predeclare 1QB, 2QB, and superflex reliability and
behavior-fit tables before any pooled summary. Primary target is behavior fit/calibration to real
pick patterns, not whether the v5 test team happens to win more against weaker rivals.

#### E7. Point-in-time 2026+ archive

Every acquisition must store:

- provider and lawful acquisition basis;
- retrieval timestamp and effective/as-of timestamp;
- artifact SHA-256 and immutable raw payload reference;
- format, scoring, teams, rank-vs-ADP-vs-projection semantic type;
- player identity mapping version and unresolved rows;
- history-coverage state (`returning`, verified rookie, prior-season absence, unresolved ID), with
  the evidence used to assign it;
- any rookie/incomplete-history prior as its own versioned forecast input, never a value inferred
  from the realized target season;
- observed sample-size metadata when the provider supplies it;
- code/config commit or dirty-state receipt used to transform it;
- license/terms restrictions, retention, and redistribution status.

Never backfill a missing preseason snapshot from later pages. Never merge providers into an
unlabeled “consensus.” Never recover proprietary credentials from client JavaScript. Store only
data the user or project is lawfully entitled to process.

The current 2024 proxy is not an acceptable rookie test: 8.81% of all synthetic picks are
offensive identities absent from the prior weekly archive, yet none appears in the traced offensive
top four. Before E5/E6 claims broad coverage, add a point-in-time fixture that distinguishes actual
rookies from injury/absence and mapping failures, then preregister missing-state and weak-candidate
tests. Until then, the UI fallback is “insufficient history,” not a zero projection or fabricated
confidence interval.

### Reject or defer

#### Learned opponent agents

Defer until a simple factor mixture is demonstrably miscalibrated on a large, current, lawful
history set. A learned policy must beat the empirical/hazard baselines out of time, retain source
isolation, support replay, and provide behavior diagnostics. Outcome performance against its own
training distribution is not sufficient.

#### MCTS, POMDP, and approximate dynamic programming

Defer. The dominant unknown is opponent/data calibration, not search depth. Rollouts through a
misspecified field make precise-looking bad probabilities. Reconsider only after survival and
opponent models are calibrated and the simple one-turn what-if fails measured decision tasks.

#### Regret-minimizing or risk-sensitive global policy

Defer as a recommendation rewrite. A user-facing regret display over reasonable alternatives may be
valuable once counterfactual labels exist, but do not define “regret” as distance from v5 or as a
single simulated season outcome. Preserve conservative/upside/balance as explicit user controls.

#### Direct 1QB policy promotion

The repeated four-QB median and early-QB rate remain a serious development finding. Still, do not
change `overfillDepth.QB` here. The previous depth-2 shadow was promising only on inspected 2024.
Require an unchanged temporal holdout and evaluate whether a UI warning/roster lens helps users
recognize redundancy before changing the primary order.

## Rollback and observability strategy

Presentation units use no migrations and no persistent preference writes in their first version.
Keep the old component behind a local import-level rollback until QA completes; do not add a remote
flag service. If decision time, keyboard behavior, layout, or claim fidelity regresses, revert the
component and retain the experiment artifacts.

Model experiments remain offline and artifact-gated. A failed seed, subgroup, replay, legality,
calibration, or source-isolation gate blocks integration without touching v5. New stored prediction
types, when eventually justified, require a versioned schema and readers that ignore unknown or
stale versions.

## Recommended next independent implementation unit

Implement **E0q draft-only false-quantile suppression** only.

The exact test-first two-or-three-file boundary is in
`docs/superpowers/plans/2026-08-29-draft-uncertainty-semantics.md`.

The unit retains the same four candidates, order, scores, scorer invocation, reasons, and actions.
It removes the incoherent value-row P10/median/P90 points strip and shows one honest group-level
unavailable-range limitation, without rewriting the shared uncertainty system.

This is the smallest safe predecessor. Then execute E0 reason fidelity, E0a native semantics/reflow,
E1 compact hierarchy, and E2 as separate rollback units.
