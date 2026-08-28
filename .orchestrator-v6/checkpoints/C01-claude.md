# C01-claude — bench logic + player-value deterministic correctness (amended scope)

## Identity

- base: `b8ce3e76c0ae4dea8d655db09c9b36bd7d912c49` (C00B, independent PASS)
- branch: `v6/bench-portfolio`; head = the commit containing this file
- scope: original C01 (candidate-aware coverage, structured contingent roles) + the
  2026-08-26 player-rating amendment (`.orchestrator-v6/C01-scope-amendment.md`,
  reviewer amendment `player-calibration-v1.md` at review commit `bc4cec0`)
- excluded, per contract: numerical fitting of ELITE_PREMIUM / CLIFF_W / UPSIDE_W /
  predictability / bench weights; the calibration report and promotion-v3.json (C02)
- git identity: Andrew; no assistant attribution; date 2026-08-26

## Original C01 — what was built

### 1. Candidate-aware maximum-matched weekly bye coverage (consolidated)

`frontend/lib/contingency.ts::weeklyByeCoverage` is the ONE public implementation, consumed
by BOTH `draftAI.benchValue` (replacing the deleted `byeCover`) and `benchScore.byeCoverage`.
Per week, starter byes open (week, slot) holes; owned bench bodies plus the candidate are
max-matched (augmenting-path bipartite matching) onto holes they can legally start in
(FLEX/OP aware) and are not themselves absent for. A week is credited only when ADDING the
candidate grows that week's matching, so:
- a shared bye earns nothing; a missing candidate bye earns nothing and degrades;
- one candidate never covers two simultaneous holes; two same-week holes never double-count;
- a hole an owned body already covers earns the candidate nothing (marginal semantics);
- slot eligibility is enforced (WR cannot cover a dedicated RB slot; QB covers OP only in
  superflex templates).

The marginal semantics matter beyond correctness: a naive all-holes count inflated late-round
skill bench values ~65% and the greedy policy then NEVER drafted K/DST in full sims (empty
starting slots). Marginal matching restores the draft-end invariant with zero weight changes.

### 2. Structured contingent-role evidence (replaces the handcuff boolean)

`contingency.ts::contingentRole`: RB succession (same NFL team + authoritative
depth_chart_order = 2); QB only with authoritative feed depth (= 2); WR/TE only with explicit
role-transfer evidence (`metadata.role_transfer`, non-empty source string). Same-roster
positional depth — the v5 inference — is NOT evidence. Status is explicit
(supported / no-evidence / ambiguous-depth / missing-metadata / not-applicable);
`benchScore.handcuffValue` pays the (unchanged) contingent formula only on `supported` and
flags ambiguous/missing as degraded; `draftAI` amplifies injuryCover only on `supported`.
Coefficients untouched.

### 3. Retired gate, documented

The frontend "v4 ≥ v3 raw points-for" fixture gate is retired: the metric is bye-blind, and
under corrected coverage the tuned bye terms trade ~0.11% raw projection in that synthetic
pool without buying measurable coverage there (probe: uncovered holes v4 26 vs v3 24 of 120).
Fixture-level evidence for the v5 tuning is therefore inconclusive → v5 values PRESERVED
unchanged; re-adjudication belongs to the preregistered C05/C02 experiments. The replacement
test asserts what stays deterministically true: legal lineups in both arms and a bounded
(<0.5%) perturbation. This is a documented evidence retraction, not a tuning change.

## Amendment — player-value deterministic correctness

### A1/A2. Explicit unit contracts; mixed comparisons banned

- Pipeline `PlayerValue` (pipeline/models/value_engine.py) now carries the written contract
  plus derived `projection_mean` / `projection_ceiling` properties: `boom` IS ceiling VOR
  (= projection ceiling − replacement), `bust` floor VOR; `value` is a unitless board score.
- Frontend `lib/valueUnits.ts` (projectionMean / projectionCeiling / ceilingVor) is the one
  conversion point; `lib/types.ts` documents the wire contract; missing boom/replacement
  degrade to null explicitly.
- Fixed mixed-unit consumers: `draftAI.ceilingWeeks` (compared ceiling VOR against a RAW
  starter projection — the audit's headline bug; now raw vs raw), `draftAI.benchValue`'s
  mean/ceiling blend, `components/draft/DraftWarRoom.tsx`'s upside chip. `benchScore`'s
  upside term is documented as intentionally VOR-scale (no mixed comparison there).
- Display surfaces (tooltip, player page band, columns) remain on the internally consistent
  VOR band; noted for C04 explanation work.

### A3. Superflex/2QB replacement demand

`league_rules.starters_per_team`: the OP slot accrues to QB in full; RB/WR/TE receive
nothing from OP; FLEX splits unchanged. 12-team superflex ⇒ QB replacement rank 24 (was
~15 under the equal four-way split), clamped to pool size. Receipt
`receipts/op-usage-measurement.txt` records why the golden-corpus measurement (QB ≈ 30% of
OP slots) is the defect's own artifact and cannot serve as usage evidence, and the
authoritative format-specific rule adopted instead.

### A4. Redraft age single-count

`_youth_factor` / `YOUTH_W` / `PEAK_AGE` removed from BOTH VorpEngine and MonteCarloEngine
shaped value. Age affects redraft value exactly once — inside the projection.

### A5. search_rank out of value

`CONSENSUS_W` and the negative-VOR search_rank branch removed; deep pool orders by
`vor + 0.5·upside` only. `search_rank` annotated as search/display metadata in both trees.
Missing ADP degrades explicitly (`adp: null`), never substituted.

### A6. Tests (mine, not the reviewer's)

- `frontend/lib/contingency.test.ts` — 26 adversarial cases: missing byes (candidate and
  starter), FLEX, superflex/OP, double counting, shared bye, self-cover, marginal matching
  (owned cover, same-week second hole, same-bye body, ineligible body, augmenting path),
  RB/QB/WR/TE evidence rules, false positives, ambiguous depth, missing metadata, K/DST.
- `frontend/lib/valueUnits.test.ts` — 6 unit-contract regressions incl. the exact
  raw-ceiling-vs-bar case and replacement-split invariance of the raw core.
- `pipeline/tests/test_value_units_c01.py` — 11 tests: boom/bust≡ceiling/floor VOR with
  derived raw fields; equal-forecast age invariance; productive-veteran ordering; search
  popularity never changes value; negative-VOR ordering by forecast; superflex QB
  replacement ≥ 24 with RB/WR/TE uninflated and 1QB unchanged; superflex QB VOR rises;
  rookie-without-meta; missing-ADP.
- Updated to corrected semantics: `draftAI.test.ts` (consolidated coverage describe),
  `draftAI.fixtures.test.ts` (retired gate → bounded perturbation + both-arm legality),
  `benchScore` degraded-order preserved.

## Canonical artifacts

`fixtures/golden_drafts/*` (16 rows) regenerated once, after ALL policy-affecting changes
(coverage, contingent roles, ceilingWeeks unit fix) — the byte-for-byte generator check
passes against the engine suite below.

## Verification

| Suite | Result |
|---|---|
| frontend `npm test` | 54 files / **473 passed**, exit 0 |
| frontend build / typecheck / lint | pass / pass / pass (pre-existing `useEspnSync.ts` warning only) |
| pipeline pytest | **157 passed** (146 baseline + 11 new) |
| engine ruff | pass |
| engine full pytest | **4123 passed, 1 skipped, exit 0** (531.75s; regenerated-golden corpus incl. byte-for-byte generator check) — `receipts/engine-pytest-c01.txt` |

C00B hygiene note addressed: `build-under-load-run.txt` trailing whitespace stripped;
`git diff --check` clean.

## Known open items (deferred, tracked)

- C02: calibration report vs frozen ECR/ADP benchmarks, per-player rank decomposition,
  promotion-v3.json (reviewer preregistration `player-calibration-v1.json` acknowledged);
  unfitted ensemble weights (`value_engine_run.py:126`) and hand-authored shaping
  coefficients unchanged pending that evidence.
- Supabase `player_value` rows must be re-materialized by the pipeline before the corrected
  values reach the live UI; no DB write happens in C01.
- Reviewer-side `it.fails` / strict-xfail acceptance tests will flip on the combined tree —
  reviewer to reconcile at the C01 verdict.

## Next

Stopped at C01-claude.md. No merge, no push, no C02 until the independent C01 verdict.
