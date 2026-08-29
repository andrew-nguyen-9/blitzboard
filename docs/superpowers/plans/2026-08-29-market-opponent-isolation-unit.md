# Market Opponent Strict-Isolation Experiment Unit

**Status:** research design only, not implemented. This is a prerequisite to new opponent or
next-turn campaigns, not a production feature or policy promotion.

**Goal:** Ensure a market-only opponent's choice code receives only lawful market ADP, player ID,
position, its own roster positions, public league constraints, and seeded randomness—never
BlitzBoard projections, values, availability, metadata, explanations, or realized outcomes.

## 1. Verified defect and retained evidence

Current protections are valuable but incomplete:

- `pickHumanAdp` reads only nested ADP, ID, position, roster slots, round/rounds remaining, and RNG.
- poison tests adversarially mutate projection, VOR, replacement, boom, bust, rank, injury, and
  metadata; picks remain byte-identical.
- the bridge strips `availability_by_arm` from human arms and rejects recommendation tracing for a
  human arm.
- the bridge avoids `candidatePool`, so projection sorting does not shrink the market board.

However, `draft-eval.mjs` first builds full player objects containing projection/VOR/replacement/
boom/bust/rank/metadata, adds market ADP, and then passes those objects in `ctx.pool` to
`pickHumanAdp`. The choice function does not use the hidden values, but it receives them. This fails
the stronger non-receipt requirement.

The existing 7,056 campaign drafts remain reproducible behavioral-sensitivity evidence. They are
not structurally source-isolated evidence and cannot calibrate a production survival percentage.

## 2. Minimal design

### 2.1 Narrow runtime object

Define one opponent-only runtime interface beside `pickHumanAdp`:

```ts
export interface MarketDraftPlayer {
  readonly id: string;
  readonly position: string | null;
  readonly marketAdp: number | null;
}
```

Do not include full name, NFL team, bye, age, experience, injury, status, metadata, `value`, rank,
projection, availability, explanation, or future outcome. None is needed by the current reach-
tolerance/roster-capacity policy. Future stack, recognizable-name, or home-team factors may add one
lawful timestamped field only after their own experiment passes; do not pre-authorize them here.

Define a narrow context containing only:

```ts
export interface HumanAdpContext {
  readonly pool: readonly MarketDraftPlayer[];
  readonly teamPicks: readonly MarketDraftPlayer[];
  readonly roster: readonly RosterSlot[];
  readonly round: number;
  readonly totalRounds: number;
  readonly rng?: () => number;
}
```

The current picker does not need bench size, other teams' player objects, projected picks-until-next,
randomness multiplier, availability, or recommendation state. Do not copy `AIContext` and omit a
few fields; allow only the fields above.

### 2.2 Sanitizer remains outside the opponent

Add a pure adapter that consumes a full evaluator player before the opponent boundary and returns
the three-field object:

```ts
export function toMarketDraftPlayer(player: PlayerWithValue): MarketDraftPlayer {
  const adp = player.value?.adp;
  return {
    id: player.id,
    position: player.position ?? null,
    marketAdp: typeof adp === "number" && Number.isFinite(adp) ? adp : null,
  };
}
```

This adapter is infrastructure, not opponent logic. `pickHumanAdp` sorts `marketAdp`, not a nested
`value` object.

### 2.3 Bridge maps choice ID back outside the boundary

In the human-arm branch only:

1. map available full players to `MarketDraftPlayer`;
2. map that team's already selected full players to `MarketDraftPlayer`;
3. call `pickHumanAdp` with the narrow context;
4. resolve the returned ID against the full `available` array;
5. append the resolved full evaluator player to the shared pick trace.

The opponent never needs the full object. The evaluator and model seat retain their existing full
rows after the choice boundary. Failure to resolve a returned ID is an invariant error, not a
fallback to `available[0]`.

### 2.4 Entry guard

At `pickHumanAdp` entry in experiment/development builds, reject any pool or owned row with keys
outside `id`, `position`, and `marketAdp`. A sanitizer unit test alone could pass while a bridge call
still supplies the old object. The entry guard makes that wiring error fail before a choice is made.

Keep the allowed-key set next to the interface and guard. Do not use a schema dependency. The pool
is already traversed for filtering/sorting, so a small experiment-only key check is acceptable;
record its timing and remove/relax only with equivalent structural proof.

## 3. Test-first tasks

### Task 1 — narrow type, adapter, and rejection guard

**Files:**

- modify `frontend/lib/draftAI.ts`;
- modify `frontend/lib/blindDraft.test.ts`.

Write failing tests that assert:

- the adapter returns exactly `id`, `position`, and `marketAdp`;
- finite ADP is retained; missing, NaN, and infinity become null;
- the picker accepts only sanitized pool and owned rows;
- adding `value`, `projection`, `metadata`, `injury_status`, `availability`, `explanation`, or an
  unknown key causes an explicit forbidden-market-field error before RNG is called;
- topK=1, bounded top-heavy draws, starter-capacity preservation, K/DST caps, missing-ADP stable
  tie-break, exact seeds, and legal 10/12/14-team drafts retain their current behavior.

Adapt the existing poison test rather than delete it:

1. poison the full source rows;
2. sanitize original and poisoned rows;
3. assert sanitized rows and seeded choices are byte-identical;
4. separately assert direct full-row passage is rejected.

Because this unit already touches `draftAI.ts` and `blindDraft.test.ts`, correct their ADP-as-rank
comments/test names in the same reviewable diff (`provider ADP`, not `provider ranking` or `market
rank`). Do not rename immutable artifact fields in place or broaden this into a provider schema
refactor.

### Task 2 — bridge sanitization

**Files:**

- modify `frontend/scripts/draft-eval.mjs`;
- modify `engine/tests/test_blind_market_benchmark.py`.

Write the bridge test first. It must prove:

- a market arm completes only after sanitization;
- model/player overrides and availability maps change the v5 candidate arm but leave the sanitized
  market arm byte-identical;
- recommendation tracing a market arm remains rejected;
- unknown chooser remains rejected;
- every selected market ID resolves to one current full evaluator row;
- complete 10/12/14-team 1QB/2QB/superflex rosters stay legal and duplicate-free.

In the same bounded edit, replace the current overclaiming bridge comments (“Market arms never
receive model fields” / “source-independence contract”) with wording that describes the now-tested
narrow-row boundary. Comments are not evidence, but leaving a contradicted assertion beside the
adapter invites the defect to recur.

Do not add the narrow keys to bridge output just for testing. The entry guard is the runtime proof;
the bridge test fails automatically if it passes full rows.

### Task 3 — replay and bounded overhead

**Files:**

- no product files beyond Tasks 1–2;
- ignored verification receipt under `artifacts/draft-assistance-deep/`;
- append results to `docs/modeling/draft-assistance-deep-experiments.md`.

Run the previously frozen R1/R2 inputs before and after hardening. Compare:

- ordered pick IDs/teams/positions;
- roster IDs;
- legality and duplicate flags;
- recommendation trace for the v5 seat;
- non-timing evaluation fields.

The code/input receipt must change because the bridge changed. Pick/evaluation payloads should
remain identical; if they do not, stop and explain the behavioral difference rather than accepting
it as cleanup.

Benchmark at least five alternating old/new bridge pairs on the reduced replay fixture. Report
whole-campaign elapsed ratio and per-market-decision delta descriptively. Do not infer live UI
latency.

### Task 4 — campaign authority reset

Do not relabel old A/B/S/D/U/T campaigns. Mark them pre-hardening behavioral-isolation evidence.
Every new opponent/survival campaign must record:

- market runtime contract version;
- allowed and forbidden keys;
- structural-guard pass;
- poison-test pass;
- campaign and analysis seeds;
- resample count/confidence/analyzer hash;
- bridge/picker/input hashes;
- legality and duplicate-free results.

A small parity replay can authorize reuse of historical behavioral conclusions. Calibration or
promotion evidence still requires new lawful point-in-time rooms after hardening.

## 4. Edge cases

| Case | Required behavior |
|---|---|
| all market ADP missing | stable ID ordering inside bounded topK; explicit degraded receipt; no projection fallback |
| one ranked player | ranked player precedes missing rows when legal |
| required starter at last turn | position-only capacity forces a legal filler |
| duplicate K/DST already owned | position-only cap still applies |
| DEF versus DST | existing normalized position behavior retained |
| extra market-only rookie | only ID/position/ADP enters opponent; evaluator limitations remain explicit |
| player selected between sanitize and resolve | impossible in synchronous draft step; unresolved ID throws |
| forged hidden key | guard throws before RNG/choice |
| availability map supplied to human arm | remains stripped; narrow context has no field for it |
| trace requested for human arm | remains rejected |

## 5. Exact non-goals

- changing topK profiles, distribution, roster rules, or missing-ADP behavior;
- adding QB/run/stack/handcuff/name/home-team/risk factors;
- a generic agent framework, policy registry, schema library, or runtime dependency;
- changing v5 ranking, live draft behavior, recommendation UI, or production authority;
- rerunning the broad parameter grid before narrow replay parity passes;
- calling behavioral poison invariance structural isolation.

## 6. Acceptance criteria

1. `pickHumanAdp` choice logic receives only the narrow context and three-field player rows.
2. Direct passage of a full player or any forbidden key fails before RNG is consumed.
3. Original-versus-poisoned source rows sanitize and replay identically.
4. Frozen replay pick/evaluation payloads remain identical after hardening; changed code receipts are
   expected and recorded.
5. Market arms receive no availability, recommendation trace, model rank, projection, VOR,
   replacement, boom/bust, metadata, injury, or realized outcome.
6. All tested league formats and seeds are legal and duplicate-free.
7. Missing ADP degrades to stable market-only behavior and never projection order.
8. Focused frontend/engine tests, typecheck, lint, and diff checks pass; full repository authority
   limitations remain reported honestly.
9. No dependency, schema, product UI, score, or authority change.

## 7. Rollback and ordering

Rollback removes the adapter/guard/bridge branch and returns to the behaviorally isolated seam; no
database or stored roster migration exists. Retain failed/parity receipts for audit.

Ordering:

1. E0 reason-fidelity remains the next product implementation unit.
2. This strict-isolation unit is the next experiment-harness prerequisite.
3. After parity, run point-in-time data readiness; then heterogeneous behavior fit and next-turn
   calibration.
4. Do not run another large synthetic opponent grid before this unit passes.
