# Next-Turn Availability Experiment Plan

**Status:** planning only, prepared from the 2026-08-29 deep draft-assistance campaign.

**Authority:** no current field is a calibrated “available at my next pick” probability. Shipped v5
remains production authority. This plan does not reopen C05 or authorize collection from a platform
without a lawful access basis.

## 1. Product question and semantic boundary

The model answers one question:

> Given the room state immediately before my pick, what is the probability this player remains
> undrafted immediately before my next scheduled pick?

It does not answer whether the player will be healthy, active, startable, on an NFL roster, or
available on waivers during the season. Keep these types and labels separate:

- `p_survives_to_next_draft_turn`: sequential draft-allocation event;
- `p_startable`: health/role availability from the existing availability pipeline;
- `expectedReplacementAtNextTurn`: current deterministic projection-depletion heuristic;
- market rank/ADP: ordinal or average-pick source data, not a probability;
- uncertainty interval: model uncertainty, not player performance variance.

No UI or schema may reuse the word `availability` without the qualifier `draft turn` or `startable`.

## 2. Why this is experiment-first

The synthetic campaign proves the software need but not the probability:

- top-four market-alternative survival changes materially with opponent assumptions;
- exact primary recommendations match only 63% across homogeneous and heterogeneous synthetic
  fields while the top-four set is more stable;
- 10%/30% market dropout cascades through the room and reduces top-four overlap to 0.348/0.176;
- the current human picker does not explicitly react to position runs;
- no lawful, point-in-time 2026 real-draft labels are archived;
- rookies and incomplete histories are not honestly represented in the 2024 proxy.

Therefore synthetic rollouts can validate replay, latency, monotonicity, and fallback. They cannot
validate calibration or justify a live percentage.

## 3. Point-in-time observation contract

For every eligible real draft decision, archive an immutable event snapshot before the user's pick:

| Field family | Required fields | Reason |
|---|---|---|
| draft identity | provider, provider draft ID hash/pseudonym, retrieval timestamp, event timestamp | clustering, ordering, deduplication |
| league | teams, scoring, roster slots, bench, IR, 1QB/2QB/superflex, snake/linear | format stratification |
| seat/turn | user seat, current pick number, next scheduled pick number, intervening-pick count | exact horizon label |
| public history | prior picks with pick number, team, player ID, position | room pace and partial opponent state |
| public rosters | each seat's drafted positions and slot feasibility | bounded need features |
| candidate | point-in-time player ID, position, team, market source/type/value/as-of | prediction row |
| BlitzBoard state | model/version hash and displayed candidate IDs only | replay and selection-bias audit |
| source receipt | acquisition basis, raw hash/reference, identity-map version, unresolved rows | licensing and provenance |

Do not archive platform credentials, private chat, personally identifying manager names, or fields
unnecessary for the event label. Pseudonymize draft/team identifiers with a project-held keyed hash
when cross-event linkage is needed; otherwise use per-draft random IDs. Define retention and deletion
before collection.

### Label

For candidate `c` at decision state `t`:

```text
y(c,t) = 1 if c is still undrafted immediately before the user's next scheduled pick
       = 0 if c is selected by any intervening pick
```

Store `selected_at_pick` when `y=0`. Exclude or mark censored when the draft log ends before the
next turn, the next turn does not exist, the room skips/rewinds ambiguously, or identity resolution
changes after the point-in-time snapshot. Do not convert censoring to `0`.

Create player-level rows for the displayed four and tier-level labels for each displayed player's
predeclared tier. Tier survival means at least one interchangeable member survives; it must not be
substituted for player survival.

### Selection-bias audit

The displayed four are policy-selected and do not cover the full board. Archive a bounded evaluation
set at each state—recommended four plus the next market-ranked players needed to cover positions and
rank gaps—without showing them to the user. Report calibration separately for displayed candidates
and the evaluation set. Never claim global calibration from only policy-selected rows.

## 4. Smallest model ladder

Use the first model that passes out-of-time calibration and usefulness gates.

Do not compare methods on mismatched targets:

| Method | What it estimates | Primary validation | Product role |
|---|---|---|---|
| fixed `topK` picker | bounded synthetic opponent choices | legality, replay, reach/roster realism; real pick fit when available | stress generator only |
| rank-only Plackett–Luce/random utility | probability of the next observed opponent choice within a lawful choice set | held-out pick log loss and reach distribution | opponent model feeding rollouts |
| M1 empirical table | player/tier survival to the user's next turn | held-out Brier/log loss and reliability | smallest direct forecast |
| M2 logistic/discrete hazard | conditional next-turn survival or per-pick selection hazard | held-out Brier/log loss, calibration, subgroup/fallback | direct forecast if M1 is insufficient |
| M3 rollout | survival implied by a validated opponent generator | real-history calibration plus seed convergence/latency | what-if and comparator |
| MCTS/POMDP/approximate dynamic programming | action policy over longer futures | regret/utility under a validated transition model | deferred; not a survival estimator |

A generator can have plausible rosters and still produce miscalibrated survival. A direct hazard can
calibrate survival without being realistic enough for rich what-if trajectories. Advance each only
for the user question it actually answers.

### M0. Unconditional horizon baseline

Empirical survival by intervening-pick bucket and league format. This establishes whether any richer
model adds value. It is not a product candidate.

### M1. Shrunk empirical market-gap table

Estimate survival by:

- `market_rank - current_pick` bucket;
- exact/bucketed intervening picks;
- position;
- league format (1QB, 2QB, superflex);
- team-count/bench-depth bucket.

Use beta-binomial or equivalent count shrinkage toward the broader horizon/format cell. Publish cell
counts and fallback path. This dependency-free baseline is preferred if calibration is competitive.

### M2. Regularized discrete-time hazard/logistic model

Candidate features are point-in-time observable only:

- market gap and source kind;
- pick horizon;
- position and league format interactions;
- recent position counts in the existing 1.5-round window;
- bounded counts of intervening teams with open/fragile starters at the position;
- candidate tier size;
- current round and seat/turn geometry;
- missing-source indicators and freshness age.

Start with regularized logistic regression for the next-turn event. If modeling each intervening pick,
use a discrete-time hazard with a complementary-log-log/logit link and aggregate survival. Do not add
neural embeddings, manager IDs, realized NFL outcomes, hidden BlitzBoard projection fields, or
post-draft data.

The binary next-turn event is the default target because it exactly matches the product question and
does not require a separate model for every pick in the interval. Escalate to the per-pick hazard only
if a preregistered what-if question needs the selection-time distribution and the extra rows improve
held-out calibration or scenario fidelity. Continuous-time Cox and competing-risk models are deferred:
the event clock is an ordered pick index, there is only one relevant absorbing event for a candidate,
and proportional-hazard assumptions add complexity without solving the missing-label problem.

### M3. Seeded rollout comparison

Run the existing `pickHumanAdp` harness with the `(4,8,12)` stress profile only after the bridge
projects full player rows into a narrow market-only runtime contract and a forbidden-key test
passes. Then use the source-isolated public state as a model-based comparator only. The six-seed
campaign supports bounded variation; it does not estimate mixture weights. A rollout percentage
cannot ship without real-history
calibration and format-specific reliability.
The prerequisite is specified in
[`2026-08-29-market-opponent-isolation-unit.md`](2026-08-29-market-opponent-isolation-unit.md).

Stop the ladder when a smaller model meets the gate. Do not start MCTS, POMDP, learned opponents, or
approximate dynamic programming because they exist mathematically. Do not fit a discrete hazard merely
because it is a familiar survival-analysis tool; M1 or the direct next-turn logistic model wins when it
is equally calibrated and materially easier to explain, replay, and maintain.

## 5. Splits and preregistered evaluation

Use forward-chaining time splits. No draft, league, or repeated manager cluster may straddle train
and test when linkage exists. The final release gate must be a later, untouched time block from the
same intended product population plus a provider/format transport slice.

Report:

- Brier score and log score;
- calibration intercept and slope;
- reliability table/plot with counts and cluster-aware intervals;
- sharpness/distribution of predictions;
- AUROC only as secondary discrimination evidence;
- player- and tier-level metrics;
- coverage/missingness/fallback rate;
- format, teams, seat band, bench depth, horizon, round, position, source, freshness, rookie/history,
  and positional-run slices;
- exact-seed replay and different-seed rollout variation;
- calibration drift by weekly snapshot date.

Bootstrap by draft/league cluster. Do not bootstrap candidate rows independently.

### Gates to freeze after the sample audit, before test outcomes

The sample audit may set minimum support and binning because current row counts are unknown; it may
not inspect survival outcomes. Then freeze:

1. minimum drafts/clusters and observations per release format;
2. primary Brier/log noninferiority margin against M1;
3. calibration intercept/slope and reliability-error bounds;
4. maximum fallback/stale rate for showing a percentage;
5. inference latency and rollout sample budget;
6. subgroup harm rule and multiple-comparison handling.

If sample support cannot justify numeric thresholds, the product remains descriptive (“recent room
pace,” “stored market ADP available for N of 4”) rather than showing a probability.

## 6. Stress matrix

Every candidate model is exercised across:

| Dimension | Required cells |
|---|---|
| teams | 10, 12, 14 |
| format | 1QB, 2QB, superflex |
| seat | front, middle, back |
| bench | shallow, canonical, deep |
| horizon | 1-5, 6-12, 13-20, 21+ intervening picks |
| room dynamics | no run, RB/WR/QB/TE run, late K/DST noise |
| source | complete, stale, partially missing, absent |
| player | returning, verified rookie, prior absence, unresolved identity |
| role | starter-like, bench/upside, contingent/handcuff where evidence exists |
| execution | exact replay, different-seed bounded variation, interrupted/censored log |

The current six canonical fixtures cover teams/format/seat/bench software paths. They do not cover
real labels, verified rookies, lawful source vintages, or causal run continuation.

## 7. Product output contract

A future typed output should be conceptually separate from `AvailabilityMap`:

```text
DraftTurnSurvival {
  playerId
  nextPickNumber
  probability | null
  tierProbability | null
  modelId
  trainedThrough
  marketSource
  marketAsOf
  sampleSupport
  calibrationSupport | null
  state: measured | fallback | stale | unsupported
  limitations[]
}
```

This is a contract description, not authorization to scaffold a file or migration.

`calibrationSupport` should expose a coarse frozen reliability bin, observed rate, cluster-aware
interval, and draft/cluster count. It is evidence about forecast calibration in similar held-out
cases, not an individual player's outcome interval. Omit it rather than create a narrow-looking
interval from synthetic trials or candidate-row bootstraps.

### UI rules

- Show “72% to next turn” only when the exact next pick, model/as-of, and support gate are valid.
- Prefer bounded language/rounding; do not imply 72.3% is precise.
- Put calibration-bin support and its cluster count in details; if the bin interval is too wide for
  the frozen gate, fall back to tier/descriptive language rather than a confident-looking percent.
- Pair the probability with the consequential alternative: “take now” versus “likely options next.”
- Show tier survival when player-specific support is weak and tier support is valid.
- If source is stale/missing, show `Unavailable` or a labeled broader fallback, not `0%`.
- Never combine `p_startable` and draft-turn survival into one “availability” number.
- Do not rerank v5 initially; first release is a compare/what-if view.
- Make scenario assumptions visible for “RB run” or “QB run”; scenario output is conditional, not a
  forecast that the run will occur.

## 8. Runtime experiment

Benchmark M1/M2 scalar predictions and M3 rollouts on representative mobile/server hardware. Record
median, p95, p99, memory, candidate count, trial count, seed, warm/cold state, and cancellation.

Start with four displayed candidates. For rollouts, measure convergence at 25, 50, 100, 250, and
500 trials against a high-trial offline reference. If 100 trials do not stabilize the displayed
ordering/probability bins within the frozen tolerance, do not hide latency with optimistic caching;
prefer M1/M2 or show no live rollout. Debounce/cancel on each incoming pick and never block the draft
action.

## 9. Likely repository seams after evidence exists

- `frontend/lib/draftNextTurn.ts`: pure typed consumer/inference adapter;
- `frontend/lib/draftNextTurn.test.ts`: missingness, replay, semantic separation, bounds;
- `frontend/components/draft/PlayerCompare.tsx`: optional survival row after compare ships;
- `frontend/components/draft/DraftWarRoom.tsx`: pass public room state; no second v5 scorer call;
- `engine/blitz_engine/backtest/blind_market.py`: label/rollout experiments only if the current seam
  cannot emit them cleanly;
- a point-in-time migration/query only after provenance, privacy, and retention approval.

Do not change `frontend/lib/availability.ts`, overwrite `expectedReplacementAtNextTurn`, or add a
generic “strategy engine.”

## 10. Acceptance and rollback

Offline acceptance requires lawful point-in-time labels, temporal holdout calibration, legal and
duplicate-free replay, honest format/missingness slices, exact reproducibility, and latency within
the frozen budget. UI acceptance additionally requires comprehension testing that distinguishes
draft survival from health and market rank, keyboard/screen-reader behavior, 375 px/200% zoom, and
no change to v5 order in the first release.

Rollback removes the optional presentation row/adapter and falls back to descriptive room pace.
No score, stored roster, production authority, or health-availability field changes. Raw lawful
archives remain immutable subject to their retention policy; derived model artifacts are versioned
and can be deactivated without rewriting history.

## 11. Next bounded action

Write and review the point-in-time event/label schema plus a synthetic contract fixture. Do not fit
a model yet. The fixture must prove exact next-pick geometry, censoring, source freshness,
player-versus-tier labels, rookie/history states, and separation from `p_startable`. Only then begin
lawful 2026 collection and a sample-size audit.
