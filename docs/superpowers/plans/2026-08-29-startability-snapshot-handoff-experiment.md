# Startability Snapshot Handoff Experiment Plan

**Status:** planning and preregistration only. No live query, score, schema, or authority change is
authorized. Shipped v5 remains production authority and C05 promotion remains closed.

**User question:** Can BlitzBoard truthfully show a current health/role startability signal during a
draft, and can that signal ever inform ranking, without confusing it with next-pick survival or
discounting a season-long value by an incompatible weekly probability?

## 1. Why this experiment exists

Repository inspection found a mismatch between intended and actual architecture:

- `engine/blitz_engine/survival/availability.py` defines `p_startable(player, week)` as the
  probability that the player is on an active NFL roster, dresses, and plays at least 10% of his
  team's offensive snaps, given that the team plays that week.
- `db/migrations/20260825_v5.2_player_availability.sql` stores `season`, `week`, `p_startable`,
  `roster_status`, `source`, and `updated_at`.
- `engine/blitz_engine/snapshot/publish_availability.py` publishes those weekly rows.
- `frontend/lib/queries.ts:getAvailabilityMap` orders the rows by season/week and collapses them to
  `player_id -> p_startable`, discarding week, source, and update time.
- `frontend/app/draft/page.tsx` does not call that query. `DraftWarRoom` supplies no
  `AIContext.availability`, and `candidatePool` accepts no published map. The live draft board
  therefore uses the local player-row status/team fallback.
- `docs/design/v5-architecture.md` and comments beside the frontend seam say the database value is
  live scoring truth. Those statements describe intent, not the current call graph.
- `scoreBoard` is season-valued, while the stored probability is explicitly player-week-valued.
  The repository does not document a valid transformation from one selected weekly row to a
  season-long discount.

Focused tests currently pass 127/127 across the local fallback, optional map behavior, scorer, full
draft legality, and live explanation integration. This proves the optional seam behaves when a map
is supplied. Engine survival, availability, and publisher suites also pass 74/74. Repository-wide
test search found no frontend test of `getAvailabilityMap` or `player_availability` query selection.
The missing test layer is therefore the point-in-time database-to-frontend contract, not the pure
model/publisher or optional score behavior. None of these green suites proves freshness,
calibration, horizon compatibility, or live wiring.

## 2. Decision ledger

### Selected: provenance-bearing offline shadow

Preserve the stored row's season, week, source, and update time; select a point-in-time row without
future leakage; compare it with the current local fallback in an offline shadow; and keep both
ranking and UI unchanged. This is the smallest experiment that can resolve whether the signal is
usable.

### Build now: truthful documentation only

Correct capability maps and, when an authorized code unit next touches the affected comments,
state that the published map is optional and not currently loaded. Do not add a fetch merely to
make the old comments true.

### Rejected: wire the current flat map directly into the live score

This loses provenance, silently chooses the numerically latest week, can select a future or stale
row, gives `candidatePool` and `scoreBoard` different health information, and applies an unresolved
weekly quantity to season value. It also bypasses the closed component experiment authority.

### Deferred: ranking or automatic risk-objective change

Even a calibrated startability display does not authorize a score multiplier. A ranking arm needs
its own paired development screen, lawful point-in-time confirmation, explanation-fidelity check,
and explicit C05-independent product authority.

## 3. Semantic boundary

Three concepts must remain different in type, label, receipt, and test:

| Concept | Exact question | Unit/horizon | Allowed current evidence |
|---|---|---|---|
| `injury_status` / roster facts | What current designation or team fact is observed? | categorical, as of a timestamp | player row and lawful dated roster/injury source |
| `p_startable` | Will this player be on the active roster, dress, and play at least 10% of offensive snaps in the named week, conditional on his team playing? | probability for one player-week | engine snapshot only when source, effective week, model/input version, and update time are present |
| `next_pick_survival` | Will this player remain unselected until the user's next pick? | probability over intervening draft picks | separately calibrated draft-room model; never the availability table |

The UI must not shorten either probability to a bare “availability.” A season-long draft value may
not be multiplied by a single weekly `p_startable` unless a separately validated horizon contract
defines why that operation is meaningful.

## 4. Questions and preregistered hypotheses

1. **Call-path truth:** Does any production route currently consume the published rows? Expected
   answer from static inspection: no. A later discovery must identify the exact call site and
   invalidate this finding explicitly.
2. **Snapshot selection:** Can a reader choose the latest row known at or before the draft decision
   for a named effective week without future leakage or silent cross-season fallback?
3. **Coverage:** What fraction of displayed offensive candidates has a valid, fresh snapshot?
4. **Calibration:** On lawful subsequent outcomes, does the published signal improve Brier score
   and reliability over the local status proxy and neutral 1.0 baseline?
5. **Horizon:** Is the useful product signal Week-1 startability, a documented season schedule of
   weekly probabilities, or status-only presentation? No season-score transformation is assumed.
6. **Recommendation stability:** In a shadow only, how often would an authorized, same-snapshot
   application change the primary and top four? This is a sensitivity measure, not a promotion
   metric.
7. **Comprehension:** Can users distinguish startability from next-pick survival under draft-clock
   pressure?

The signal is considered display-capable only if coverage and calibration pass and the usability
study's factual-confusion rate stays below its preregistered threshold. Ranking remains separately
deferred even when display passes.

## 5. Point-in-time snapshot contract to test

Use the existing table. Do not create another availability table or publisher. The reader under
test must preserve, at minimum:

```text
player_id
effective_season
effective_week
p_startable
roster_status
source
updated_at_utc
requested_as_of_utc
model_version
input_snapshot_ids
degraded_reason
```

`model_version`, `input_snapshot_ids`, and `degraded_reason` are required for a future durable
forecast receipt but are not present in the current table. The experiment must first determine
whether they can be joined from the existing immutable publish manifest. Additive schema work is
allowed only after that audit; do not guess a migration now.

Selection rule under test:

1. name the draft decision time and desired effective season/week;
2. reject any row with `updated_at > requested_as_of_utc`;
3. prefer an exact effective season/week match;
4. never substitute a future effective week;
5. if an exact row is absent, return a typed degraded state rather than silently taking another
   week or season;
6. clamp nothing silently—out-of-range probabilities are invalid data and degrade to the local
   factual proxy with an internal receipt;
7. ensure every candidate in one recommendation calculation sees the same snapshot receipt.

## 6. Experiment stages

### S0 — contract and documentation audit

Read the migration, publisher, query, page route, `DraftWarRoom`, `candidatePool`, final scorer, and
all availability tests. Record contradictions between comments/docs and call sites. This stage is
complete for the 2026-08-29 audit and must be repeated immediately before execution because the
worktree is active.

**Exit:** exact call graph and unchanged HEAD recorded; no live caller claimed without evidence.

### S1 — pure snapshot-selection tests

Test a pure reader/selector outside the live route. The unit must consume synthetic database rows
and return either one provenance-bearing snapshot per player or a typed degradation reason.
This is the first executable stage because no current query-level fixture covers this behavior.
Follow the existing `queries.boxstats.test.ts` pattern: keep one pure exported selector in
`queries.ts` and exercise it without a Supabase-chain mock. Do not create a repository, service,
hook, or query framework for one row-selection rule.

Required fixtures:

- exact week and as-of match;
- two revisions of the same player-week;
- future update for the same effective week;
- future effective week;
- prior week only;
- prior season only;
- missing player;
- unknown source;
- `p_startable` below 0, above 1, null, and nonnumeric;
- mixed complete/missing candidates;
- rookie or identity not yet present;
- duplicate rows that violate the expected primary key in a mocked response;
- offline Supabase client.

**Exit:** exact replay, no future leakage, provenance retained, neutral/local degradation explicit.

### S2 — offline shadow bridge

Reuse the existing optional `AIContext.availability` seam only in a test or experiment bridge.
Generate paired recommendation states from identical pool, roster, all-picks, and seed inputs:

- A: current live-equivalent local fallback;
- B: published snapshot supplied to final scoring only, reproducing the existing optional seam;
- C: published snapshot supplied consistently to both candidate prefilter and final scoring;
- D: missing/stale published snapshot, which must equal A exactly.

Arm B is diagnostic because it exposes the current prefilter/scorer inconsistency. Arm C is the
only coherent sensitivity arm, but it still has no production authority. Market-only opponents
must not receive `p_startable` or any BlitzBoard field.

Measure primary match, top-four Jaccard, rank displacement, weak-candidate cases, legality,
duplicate-free rosters, starter strength, bench/absence coverage, paired H2H/playoff proxies, and
runtime. Retain cases where the signal makes recommendations worse.

**Exit:** exact replay; D equals A byte-for-byte; every roster legal/duplicate-free; no hidden-field
leakage; all outcome statements labeled development-only.

### S3 — lawful calibration

Use archived point-in-time 2026+ weekly snapshots collected before the effective week and the
later observed active/dressed/snap-threshold outcome. Do not substitute historical appearance maps
as live inputs. Use them only as realized labels when the identity, schedule, and snap threshold
are valid.

Report Brier score, log loss with bounded epsilon, reliability bins with counts, calibration
intercept/slope when sample size permits, sharpness, coverage/abstention, and Brier skill versus:

- neutral 1.0;
- current local status/team proxy;
- a simple position/base-rate baseline.

Stratify by position, rookie/incomplete history, roster state, injury designation, week range,
snapshot age, source completeness, and model version. Use rolling-origin or later-season holdout;
never random-split player-weeks across time.

**Exit:** no display authority without held-out reliability and sample-count reporting. No ranking
authority follows automatically.

### S4 — usability-only prototype

Test a non-ranking presentation on the 54-state usability catalog plus dedicated health/survival
confusion states. Every arm uses the E0-fidelity copy baseline.

Tasks ask the participant to identify:

- which fact is an observed injury/roster status;
- which percentage refers to named-week startability;
- which percentage refers to surviving until the next draft pick;
- whether either number is stale or unavailable;
- the most consequential candidate tradeoff.

Measure factual accuracy, confusion rate between the two probabilities, decision time, confidence
for factual tasks, task-level workload, keyboard completion, and screen-reader label
comprehension. Preference-only choices have no correctness score.

**Exit:** the signal may be presentation-capable only if it improves factual answers or supplies
new correct information without materially increasing decision time/workload and without an
accessibility blocker.

### S5 — authority decision

Choose exactly one:

- **Display:** show a named-week, sourced probability with timestamp and honest missing state;
- **Facts only:** show injury/roster facts, not a probability;
- **Keep hidden:** insufficient calibration, coverage, freshness, or comprehension.

A separate future preregistration is required for any score or ordering change.

## 7. Stress matrix

| Dimension | Cells | Required behavior |
|---|---|---|
| Time | exact, stale, future update, future week, prior season | no future leakage; explicit stale/missing state |
| League | 10/12/14 teams; 1QB/superflex; bench 4/8/12 | health meaning unchanged across format |
| Draft seat | front/middle/back | same snapshot semantics; no seat-dependent health label |
| Player history | veteran, rookie, ID mismatch, incomplete history | no imputed certainty; reason retained |
| Health/role | healthy, questionable, out, IR/PUP, unsigned, buried role | factual status distinct from modeled probability |
| Market data | complete, 10% missing, 30% missing | market degradation cannot mutate health snapshot |
| Source | known, unknown, mixed versions | no vendor or freshness claim without receipt |
| Draft dynamics | neutral, RB/QB/TE run | next-pick survival changes independently; `p_startable` does not |
| Accessibility | 375 px, 200% zoom, keyboard, screen reader, reduced motion | full meaning available without color/hover/motion |

## 8. Exact existing files in scope if execution is later authorized

- `frontend/lib/types.ts` — provenance-bearing snapshot read type.
- `frontend/lib/queries.ts` — point-in-time selection/read; do not flatten away provenance.
- `frontend/lib/queries.availability.test.ts` — pure selection fixtures following the existing
  `queries.boxstats.test.ts` style; no database/network dependency.
- `frontend/lib/availability.ts` — local fallback and explicit published-snapshot consumption.
- `frontend/lib/availability.test.ts` — fallback, bounds, and mixed-missingness fixtures.
- `frontend/lib/draftAI.ts` and its tests — same-snapshot prefilter/final-score shadow only.
- `frontend/app/draft/page.tsx` and `frontend/components/draft/DraftWarRoom.tsx` — no change until
  S1-S4 authorize a delivery contract.
- `frontend/lib/v6DraftLiveIntegration.c04.test.ts` — single-scorer and exact-order authority guard.
- `engine/blitz_engine/snapshot/publish_availability.py` and
  `engine/tests/test_publish_availability.py` — reuse the existing publisher and receipt seam.
- `engine/blitz_engine/survival/availability.py` and focused tests — model semantics/calibration;
  do not change solely to satisfy frontend expectations.
- `db/migrations/20260825_v5.2_player_availability.sql` — inspect as authoritative history; do not
  edit. Additive future migration only if the manifest cannot supply required provenance.
- `docs/modeling/<dated-startability-handoff-results>.md` and ignored receipt artifacts — results,
  hashes, failures, and authority decision.

No new availability service, state framework, client dependency, agent framework, or duplicate
publisher belongs in this experiment.

## 9. Acceptance and rollback

Contract/shadow acceptance:

1. point-in-time selection never reads a future update/effective week;
2. one recommendation state uses one immutable receipt;
3. missing/stale/invalid published data exactly restores the current local fallback;
4. `p_startable` and `next_pick_survival` are different types and labels;
5. market-only opponents never see health or BlitzBoard fields;
6. exact seeds replay; every simulated draft is legal and duplicate-free;
7. calibration and subgroup failures remain in the report;
8. no production score, order, schema authority, or v5 status changes.

Display acceptance adds lawful held-out calibration, date/source visibility, mobile/accessibility
QA, and demonstrated comprehension. Ranking acceptance is deliberately absent.

Rollback is layer-local: remove the optional read/prototype and retain the existing table/publisher;
the current local fallback remains the product behavior. Immutable experiment receipts remain for
audit. Stop immediately on future leakage, semantic conflation, duplicated discount, inaccessible
copy, or any path that would silently change v5 authority.

## 10. Recommended outcome before data exist

Keep E0 reason fidelity as the next implementation unit. Run this startability work only as an
offline provenance/selection shadow after the point-in-time 2026 archive exists. On today's
evidence, show current observed injury/team facts where lawfully sourced, do not display a bare
startability percentage, do not wire the flat map into ranking, and keep next-pick survival in its
separate experiment.
