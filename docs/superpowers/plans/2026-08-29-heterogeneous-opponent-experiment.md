# Heterogeneous Opponent Experiment Plan

**Status:** post-core planning expansion. No opponent profile is calibrated for live probability.

**Authority:** opponents are offline stress generators for human decision support. They do not
autodraft for the user, change shipped v5, reopen C05, or receive hidden BlitzBoard projections.

## 1. Decision and current evidence

Reuse `pickHumanAdp` and the existing draft harness. The current seam rotates bounded `topK` values
by seat, changing reach tolerance while remaining deterministic for a seed.

Observed development evidence:

- wide `(1,4,8,12)` misses the primary noninferiority gate narrowly;
- `(4,8)` passes one seed and fails another;
- `(4,8,12)` clears two core seeds;
- a six-seed expansion of `(4,8,12)` has mean H2H +0.00642 with seed-cluster interval
  -0.00284 to +0.01596, but format directions remain mixed;
- test rosters change about eight pick slots and exact primary recommendations are field-sensitive;
- metadata dropout weakens opponents and creates misleading league-outcome gains;
- the current picker has no explicit response to runs, own roster need, stacks, or other teams.

Conclusion: `(4,8,12)` is a bounded offline stress profile and the correct starting control. It is
not a realistic population estimate. Add factors only when lawful histories supply behavior targets.
Do not run another `topK` grid or seed sweep: the current campaign already answers whether the seam
can create bounded sensitivity. More draws from the same family cannot establish human realism.

## 2. Source-isolation contract

An opponent may observe only information a manager could lawfully observe at that pick:

- the opponent's assigned point-in-time market/ADP/rank source;
- pick number, round, snake geometry, league rules, and roster constraints;
- public prior pick history and public drafted rosters;
- public player identity, NFL team/position, and role tags when timestamped;
- its own seeded profile parameters.

It may not observe:

- BlitzBoard projection, VOR, boom/bust, explanation components, availability model, or score;
- realized target-season outcomes;
- future picks, later source snapshots, or post-draft depth charts;
- another manager's private preferences or identity unless the dataset lawfully includes consented,
  pseudonymized repeated-manager linkage;
- a vendor “recommendation” inferred from an ADP/rank list.

Keep the existing poison test: perturb hidden model fields and require market-only opponent picks to
remain byte-identical.

That poison test is necessary but not sufficient. The current bridge passes full `PlayerWithValue`
objects to `pickHumanAdp`; projection/VOR/boom/bust/rank/metadata are present at runtime even though
the function does not read them. Before the next campaign, define a narrow market-player/context
type containing only identity, position/team fields needed for roster legality, lawful market ADP,
own roster, visible picks, league rules, and RNG. Sanitize at the bridge boundary and assert that
forbidden keys are absent from every market pool and owned-player row. Do not claim structural
source isolation for the existing deep artifacts.
The test-first boundary is specified in
[`2026-08-29-market-opponent-isolation-unit.md`](2026-08-29-market-opponent-isolation-unit.md).

## 3. Reproducible persona representation

A profile is data, not a class hierarchy. Conceptually:

```text
OpponentProfile {
  profileId
  marketSourceId
  topK
  marketTemperature
  positionPreference
  rosterTemplate
  qbTiming
  ownNeedWeight
  publicNeedReaction
  recentRunReaction
  clockPressureReaction
  stackPreference
  handcuffPreference
  recognizableNameBias
  homeTeamBias
  riskPreference
  sophisticationLevel
  seed
  evidenceReceipt
}
```

Do not scaffold this type until a second factor passes its experiment. The current tuple is enough
for reach-tolerance experiments.

Every numeric factor requires:

- bounded range and default zero/off;
- evidence source and as-of date;
- deterministic application order;
- candidate window that prevents chaotic reaches;
- legality fallback;
- exact replay test;
- behavior metric it is intended to match;
- ablation and missing-data behavior.

## 4. Factor ladder

Add one factor at a time in this order. Stop when behavior fit is sufficient.

### F0. Reach tolerance / random utility

Control: discrete `topK` mixture `(4,8,12)`.

Small alternative: sample within the bounded market window using a Plackett-Luce/softmax random
utility based only on market rank or ADP distance. Temperature controls adherence. Estimate it from
real pick-minus-market distributions by format/round; do not hand tune it from test-team outcomes.

### F1. Early/late QB behavior by format

Targets: QB-by-round distribution, first-QB pick, final QB counts, and legal starter completion for
1QB, 2QB, and superflex. A single pooled QB coefficient is prohibited. Current v5 test-team QB
overcapitalization is a policy concern, not evidence for opponent QB weights.

### F2. Own-roster starter/bench need

Use only slot feasibility and already drafted positions. Targets: probability of selecting a
position conditional on open starter, round, and format; bench diversification; K/DST timing. Need
may tilt choices within the market window, never force an illegal or unbounded reach.

### F3. Positional preference / roster-construction template

Examples: RB-heavy, WR-heavy, balanced, early-TE, late-TE. Estimate mixture prevalence and bounded
effects from histories. A template describes tendencies, not a claim about sophistication or skill.

### F4. Recent positional-run reaction

The existing `detectRuns` window can supply an observable state, but its predictive/behavioral value
is unvalidated. Estimate whether managers select the running position more or less often after
conditioning on market rank, round, need, and format. Report observed-count response; do not infer a
run-continuation probability from the current heuristic.

### F5. Reaction to other teams' public needs

Summarize only intervening teams between the current and next seat: feasible open starters and
position counts. Estimate a small public-need effect. Avoid a full belief model or hidden manager
state.

### F5b. Time remaining, only as an observed room state

Spiliopoulos, Ortmann, and Zhang found reduced opponent-payoff lookup and a shift toward simpler
heuristics under a 20-second deadline in 148 laboratory participants playing one-shot normal-form
games ([DOI](https://doi.org/10.1037/xlm0000535)). This is adjacent evidence, not a fantasy-draft
coefficient. Keep the factor off unless a lawful draft event archive records remaining clock time or
a timeout state for each pick. Then preregister a small interaction—such as weaker public-need/run
response near the deadline—fit it only on training rooms, and compare held-out pick log loss and
survival calibration. Never infer clock state from response order, call fast drafters unsophisticated,
or hand-tune the effect from BlitzBoard outcomes.

### F6. Stack and handcuff preferences

Require point-in-time NFL team and role/depth metadata. Define stack types before analysis (for
example QB-WR/TE) and handcuff eligibility from lawful role data. Do not infer handcuffs from realized
season touches. Targets are conditional selection rates within a market window.

### F7. Recognizable-name and home-team bias

These require measurable proxies and, for home-team bias, consented location/affiliation data. They
are likely defer/reject items because privacy cost may exceed product value. Never guess a manager's
home team from IP or personal data.

### F8. Risk preference and sophistication

Risk preference requires a point-in-time, semantically valid uncertainty input. ADP disagreement is
not uncertainty, and season-total quantiles are not ceiling-week boom/bust. Sophistication should be
an observed behavior cluster, not a personal label exposed in UI. Defer until the data contract
exists.

## 5. Data and labeling

The minimum lawful real-draft event archive mirrors the next-turn plan:

- timestamped pick sequence and league rules;
- remaining pick-clock time and timeout/autopick state when the platform lawfully exposes it;
- point-in-time market source/type/as-of;
- public rosters before each pick;
- candidate identities and positions;
- source/identity-map receipts;
- censoring and correction events.

For one-step behavior fit, each observed pick creates a choice set from the bounded market window at
that time. Record the chosen candidate and public features. Do not build the choice set from a later
final player universe.

Platform autopicks and clock expirations are a separate mechanism. Exclude them from human-policy
coefficient fitting or model them as an explicitly labeled platform fallback only when the source
documents its behavior; never let them masquerade as fast human market adherence.

Repeated manager linkage is optional and privacy-sensitive. The first model should treat picks as
draft-clustered observations without identifying managers across drafts.

## 6. Evaluation hierarchy

### Primary: one-step behavior fit

- negative log likelihood/log loss of the observed pick within the lawful choice set;
- top-k choice coverage;
- pick-minus-market distribution and extreme reaches;
- position-by-round distribution;
- QB timing and final roster-count distributions by format;
- K/DST timing;
- conditional own-need response;
- run-response calibration after confounder adjustment;
- clock-state interaction with declared support counts, when the archive contains it;
- missing-source and rookie/history slices.

Use temporal/provider holdouts and cluster uncertainty by draft. A lower log loss against a broad
choice set is useful only if legality and reach tails remain plausible.

### Secondary: trajectory realism

- duplicate-free and legal rosters;
- positional run length/frequency;
- distribution of starter completion rounds;
- roster construction diversity;
- intervening-pick and next-turn player/tier survival calibration;
- exact replay and different-seed bounded variation.

### Diagnostic only: BlitzBoard outcomes

Starter strength, H2H, playoff proxies, and regret remain sensitivity diagnostics. They cannot select
an opponent factor because a weaker field can improve the test team's results, as the dropout
experiment demonstrated.

## 7. Model sequence

1. homogeneous `topK=8` control;
2. `(4,8,12)` bounded stress control;
3. rank-only Plackett-Luce/random-utility baseline;
4. one accepted factor plus rank utility;
5. smallest accumulated factor mixture;
6. optional online mixture-weight update from the current room's public pick history.

The online update, if reached, should be a simple Bayesian/likelihood update over a few fixed
profiles. Report posterior weights as model state, not manager diagnoses. Use a prior learned from
training rooms, update only with observed picks, and regularize toward the population when history is
short.

Level-k/cognitive hierarchy may be tested only as credible adjacent theory: define what “levels”
mean in this product and show that they improve held-out choice likelihood beyond the simple mixture.
Do not assign hidden BlitzBoard reasoning to higher levels. Quantal response is already represented
by bounded random utility; prefer that small method before a richer game-theoretic label.

## 8. Preregistered matrix

For every accepted factor:

| Dimension | Cells |
|---|---|
| arm | homogeneous, `(4,8,12)`, single factor, accumulated mixture |
| split | train, temporal validation, untouched time/provider test |
| teams | 10, 12, 14 |
| QB | 1QB, 2QB, superflex |
| bench | shallow, canonical, deep |
| seat | front, middle, back |
| round | early, middle, late |
| source | complete, partial, stale, absent |
| room | no run, RB/WR/QB/TE run, late K/DST noise |
| player | returning, verified rookie, prior absence, unresolved ID |
| replay | identical seed and multiple prelisted seeds |

Freeze the factor target, coefficient-estimation method, accumulation rule, and acceptance threshold
before the test split. Publish every cell, including weak candidate and null results.

## 9. Acceptance and stop rules

Accept a factor into the offline stress mixture only if it:

- improves out-of-time behavior fit against the current smallest model by a frozen meaningful amount;
- does not create implausible reach tails or illegal/duplicate rosters;
- improves the intended conditional behavior target in the same direction across the supported
  formats, or is explicitly format-specific with adequate support;
- remains behaviorally model-field-insensitive under poison tests;
- proves structural non-receipt with a runtime forbidden-key assertion on market pool and owned
  rows; behavioral poison invariance alone does not pass;
- replays exactly and varies within frozen different-seed bounds;
- serializes campaign and analysis/bootstrap seeds, resample count, confidence level, and analyzer
  hash in the receipt; the deep B2 audit showed that an internally valid report can omit the
  nondefault analysis seed required for byte reproduction;
- degrades honestly when its required metadata are missing.

Reject or defer when behavior benefit appears only in league-outcome proxies, a coefficient is not
identifiable, the factor requires private/retrospective data, or complexity exceeds the simple
mixture's out-of-time gain.

## 10. Product integration boundary

An accepted offline opponent model can support:

- what-if rollouts;
- next-turn survival experiments after calibration;
- explanation of field-assumption sensitivity;
- deterministic stress fixtures for UI studies.

It does not automatically change v5 ranking. The default board should show one primary and
alternatives; if assumptions materially alter order, present that as model sensitivity, not certainty
or a claim about a particular manager.

No opponent persona name should stigmatize a user. Prefer neutral labels such as “market-tight,”
“market-broad,” “early-QB tendency,” and “roster-need responsive.”

## 11. Likely repository seams

Before a second factor passes, change only experiment artifacts and the existing
`opponent_profile`/`pickHumanAdp` seam. If a second factor is accepted, likely files are:

- `frontend/lib/draftAI.ts` for the narrow market-player/context type and existing picker;
- `frontend/scripts/draft-eval.mjs` for runtime row sanitization and serialized public factor configuration;
- `engine/blitz_engine/backtest/draft_realism.py` for experiment orchestration;
- `engine/blitz_engine/backtest/blind_market.py` for paired reports;
- `frontend/lib/blindDraft.test.ts` and focused engine bridge tests for forbidden-key non-receipt,
  poison invariance, bounds, replay, and legality.

Do not add a generic agent framework, policy registry, database table, or live UI abstraction until
the existing seam is proven insufficient.

## 12. Rollback and next action

Rollback removes the factor arm/config and returns experiments to `(4,8,12)`; no production score,
schema, or stored roster changes.

The next action is data readiness, not another hand-tuned factor: define the lawful choice-set event
schema and calculate whether available real histories support format/round targets. If they do, fit
only F0 rank random utility and F1 QB timing against held-out choice likelihood. If they do not, keep
`(4,8,12)` as a synthetic stress profile and stop.
