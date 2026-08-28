# C01A-claude — response to C01-codex BLOCK (bench-logic corrections only)

## Identity

- base: `48ae46c14f23b72ee99a05900c9841d424b0ed35` (C01 head, the reviewed commit)
- branch: `v6/bench-portfolio`; head = the commit containing this file
- review responded to: `C01-codex.md` at review commit `caac6af` (verdict: BLOCK)
- scope: EXACTLY the five required corrections from C01-codex, plus their specified
  adversarial tests. The accepted player-value corrections (ceiling/raw conversion,
  redraft-age removal, `search_rank` removal, full-QB OP allocation) are untouched, as is
  `C01-claude.md` (immutable). No coefficient was tuned (see "Coefficients" below).
- git identity: Andrew; no assistant attribution; date 2026-08-26

## Correction 1 — coverage returns expected starts + covered records

`ByeCoverage` is now `{ expectedStarts, covered: ByeCoverRecord[], degraded }` with
`ByeCoverRecord = { week, slot, starterId }` (`frontend/lib/contingency.ts`).

The matching core (`matchAssign`) now returns the winning hole assignment instead of
discarding it. The records are read off that assignment, not re-derived: bodies are placed
in input order and a placed body never becomes unmatched, so the first `|usable|`
placements reproduce the baseline matching exactly and a strictly larger matching means
the candidate body itself holds a hole — that hole's `(week, slot, starterId)` is the
record. Deterministic by construction (no randomness, stable iteration order), ascending
by week. `expectedStarts = covered.length` (a candidate occupies at most one slot per
week, so covered weeks = expected bye-driven starts). Marginal semantics unchanged — all
13 pre-existing coverage tests still pass, now asserting through the record shape.

C04 can therefore explain *which starter and slot* a bench body covers without
reimplementing the matcher (the wishlist's "structured candidate-aware coverage replaces
the scalar count").

Consumers updated: `draftAI.benchValue` reads `.expectedStarts` (was `.covered.length`);
`benchScore.byeCoverage` keys off `expectedStarts`.

## Correction 2 — the league's REAL slots reach both consumers

`BenchCtx` gains `rosterSlots?: RosterSlot[]`. Template resolution
(`benchScore.starterTemplate`, exported for direct verification):

1. `ctx.rosterSlots` (explicit),
2. `ctx.config.rosterSlots` (the imported league's actual lineup),
3. only then the hard-coded superflex preset (flag-only callers, e.g. legacy tests).

`deriveSuperflex` now reads the same slots: an explicitly named OP/SF slot **or** any
shape with ≥2 QB-capable slots — so a pure 2QB lineup (QB, QB) activates the superflex
overlay, which the old OP/SF-name rule and draftAI's old
`slot !== "QB" && eligible.includes("QB")` rule both missed.

`draftAI.benchQuality` now passes `rosterSlots: ctx.roster` (the live league definition it
already used for its own coverage call) instead of a locally computed boolean, so both
declared consumers evaluate the same league shape through the same implementation.
`DraftWarRoom` already passes `config` and needs no change (path 2).

Tests: 2QB derivation (explicit slots and via `config.rosterSlots`); a custom no-TE/no-FLEX
shape where a bench TE's ByeCoverage term is 0 against the real template vs the preset's
phantom credit — the score difference is exactly the term weight (5), proving the template
actually reaches the coverage computation; direct `weeklyByeCoverage` 2QB tests (a QB
candidate covers the second dedicated QB slot's bye; a position with no slot in a custom
template covers nothing).

## Correction 3 — missing owned-bench bye metadata degrades

In `weeklyByeCoverage`, an owned bench body with `bye_week == null` is (as before)
excluded from the baseline matching, but now sets `degraded` whenever it could legally
occupy any hole — the marginal verdict is then conditional on missing metadata and must
not present as certain. A bye-less body that can start in no hole slot (e.g. a K against a
WR hole) does not degrade.

Adversarial tests: unknown-bye WR behind a WR hole → credit still computed on the
baseline but `degraded: true`; unknown-bye K behind the same hole → `degraded: false`.

## Correction 4 — one shared structured contingent valuation

`contingency.ts` now exports the single valuation:

- `injuryRisk(status)` — moved verbatim from `benchScore` (identical table; `benchScore`
  imports it for its unrelated SF-RB health term).
- `contingentValuation(cand, starter) → { status, eligible, starterId, evidence,
  inheritanceProb, expectedValue, degradedReason }` where `inheritanceProb =
  injuryRisk(starter)` iff eligible (else 0), `expectedValue = inheritanceProb ×
  projectionMean(cand)` (season points), and `degradedReason` is an explicit string for
  ambiguous-depth / missing-metadata (null for clean negatives and clean positives).
  `starterId` names the proposed relevant starter even for negatives.

Both consumers now take whether, probability, and value from it exclusively:

- `benchScore.handcuffValue`: eligibility and probability come from the valuation; the
  model rescales the shared expected value onto its saturating-VOR upside scale
  (`inheritanceProb × upside`), with the v5 coefficients 0.4 / 1.5 unchanged. Numerically
  identical to C01 for every supported case; degradation now keys off `degradedReason`.
- `draftAI.injuryCover(cand, starter, valuation, params)`: the boolean bridge is gone.
  With evidence, contingent starts = `inheritanceProb × STARTABLE_WEEKS ×
  handcuffAmplify`, capped at the season (a 0.95-risk starter × 1.6 amplification must
  not exceed 17 starts). Without evidence, the generic positional fill-in prior
  (`injuryRate[pos] × STARTABLE_WEEKS`) applies unchanged — that term makes no
  succession claim.

Intentional behavior change (correction, not tuning): an evidenced handcuff behind a
HEALTHY starter now earns `0.1 × 17 × 1.6 ≈ 2.7` contingent starts instead of the v5
blanket `injuryRate[RB] × 17 × 1.6 ≈ 4.9` — succession value now conditions on the
starter's actual status, which is the point of the shared valuation. The draftAI test
asserting handcuff > generic now does so with an ailing starter (the case the term is
for) and a new test pins the season cap.

## Correction 5 — position compatibility + authoritative starter depth

`contingentRole` now rejects:

- **cross-position pairings** (`normPos(starter) !== normPos(cand)` → `no-evidence`) for
  every evidence kind — a depth-2 RB with a same-team WR, and explicit role-transfer
  across positions, are both dead;
- **unverifiable succession order** for QB/RB: the starter must carry authoritative
  `depth_chart_order === 1`; a missing or non-1 starter depth → `ambiguous-depth`
  (degraded, never supported). C01's code marked a depth-2 RB behind a depth-less RB as
  supported — the new missing-starter-depth test fails against that code.

Adversarial tests: cross-position (RB/WR and role-transfer WR/TE), missing starter depth,
ambiguous starter depth (2 vs 2), and both QB variants.

## Coefficients — none tuned

Unchanged: ELITE_PREMIUM/CLIFF_W/UPSIDE_W and all engine constants (no engine/pipeline
file touched); `GENERAL_WEIGHTS`, `SF_*_WEIGHTS`, `SF_MULTIPLIER`, handcuff 0.4/1.5,
`injuryRate`, `handcuffAmplify`, `benchByeWeight`/`benchInjuryWeight`/`benchCeilingWeight`,
the `injuryRisk` table (moved, byte-identical values). New numeric literals introduced:
none beyond the `Math.min(STARTABLE_WEEKS, …)` season cap, which is a bound, not a knob.

## Verification (this worktree)

- `frontend`: `npm run build` clean; `npm run typecheck` clean; `npm run lint` — one
  pre-existing `react-hooks/exhaustive-deps` warning in `lib/useEspnSync.ts` (untouched
  file, present at C01); `npx vitest run` **492 passed, 0 failed** (+19 net new
  adversarial/shape tests across `contingency`, `benchScore`, `draftAI`: 20 added, 1
  replaced — the boolean-bridge handcuff test superseded by the valuation pair).
- `pipeline`: 157 passed (untouched).
- `engine`: run with the worktree-safe form
  `PYTHONPATH="$PWD" <main>/pipeline/.venv/bin/python -m pytest` (main-checkout venv,
  worktree PYTHONPATH): **4123 passed, 1 skipped** (untouched by this correction).
- `git diff --check` clean. No merge, no push, no C02 work, reviewer worktree untouched.

## Stop

Stopping for independent re-review per contract. Next action belongs to the reviewer
(`C01A` verdict); no merge/push/PR from this session.
