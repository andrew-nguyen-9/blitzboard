# C06A roster-legality recovery — producer checkpoint

Producer disposition: **READY FOR INDEPENDENT REVIEW**

C06A corrects the deterministic blockers recorded by C06 while preserving the authorized boundary:
C05 promotion is excluded, C05 remains parked, shipped v5 remains production authority, and no fit,
confirmation, calibration, auxiliary bridge, merge, push, PR, release, or real-league mutation ran.

## Durable producer tree

- branch: `v6/c06a-roster-legality`
- base: `39563c373265790461e18f388b3c7cd3e31d58d0`
- implementation baseline: `a1ff108b846aa4b51a3266918603609f16ad9886`
- final producer SHA: recorded by the following checkpoint-record commit

The correction is deliberately small: the existing browser draft policy reserves the final safe
picks for missing required starters and never selects a second K or DST; the existing CP-SAT roster
solver uses one search worker so exact seeded replay cannot vary across tied FLEX assignments.
Existing generators, fixtures, evaluators, validators, and bridges were reused.

## Draft evidence

The committed synthetic artifact contains 100 CPU-local drafts and two season trajectories per
draft. It covers front/middle/back seats; 10-, 12-, and 14-team formats; 1QB, superflex, and 2QB;
4-, 6-, and 8-player benches; and degraded ADP/injury/contingent-role metadata.

- artifact: `.orchestrator-v6/prep/C06-draft-realism.json`
- SHA-256: `75e8ccce211475797435163ee9bf96fe70107fe8a8b9d77756775ef8b28cf7d9`
- legal and starter-complete: 100/100
- duplicate-free: 100/100
- classifications: 46 ACCEPTABLE, 45 BORDERLINE, 9 UNACCEPTABLE
- modeled winnability: 76 true, 24 false
- deterministic diversity: 100 unique derived seeds and 100 unique primary rosters

The final extended temporary batch completed 500 drafts in 427.9363 seconds: 500/500 legal,
500/500 duplicate-free, 220 ACCEPTABLE, 245 BORDERLINE, and 35 UNACCEPTABLE. Its SHA-256 is
`761ae30cd2b5b324484a8b985ec411b57723672cf77bd940eb456c5d179365db`; it is intentionally not
committed as a large raw dump. Different seeds produced 500 distinct primary rosters while exact
first-100 replay matched after removing elapsed-time fields.

All simulation evidence is labeled synthetic/non-authoritative. Winnability is cohort-relative and
uncertain, never a guarantee and never C05 promotion evidence. The evaluator reports legality,
starter strength versus median, bench/replacement coverage, bye/absence coverage, contingent-role
limitations, scarcity/redundancy, paired H2H, playoff/championship proxies, degraded inputs, and a
95% interval. The deliberately invalid-team test mutates a legal roster and proves it is classified
UNACCEPTABLE and not winnable.

## Completed live-equivalent draft

No safe configured external draft room was available without account or external-state risk. The
authorized fallback completed the application’s real browser `/draft` flow against recorded local
2024 data in a disposable, hashed overlay.

- format: 12-team superflex, 16 rounds, user team at slot 6
- pick log: 192/192 picks, 192 unique players
- roster: every QB/RB/RB/WR/WR/TE/FLEX/OP/DST/K starter filled and bench 6/6
- displayed result: 2,194 projected starter points, league median 2,307.5, grade C, rank 11/12
- honest classification: BORDERLINE; modeled winnability not proven by the browser result
- overlay SHA-256: `f66050406d3b58c0a0024eb7a50b45be9013d28213a2313a16bb5cd8493b34d5`

The overlay was never committed and its worktree was removed. No account was created, no paid
contest entered, no message/invitation sent, no credential exposed, and no real league changed.

## Final producer verification

All final commands ran against implementation baseline `a1ff108b846aa4b51a3266918603609f16ad9886`:

| Check | Result |
|---|---|
| Frontend build | passed; 25 static pages; one existing hook warning |
| Frontend typecheck | passed |
| Frontend lint | 0 errors, 1 warning |
| Frontend tests | 61 files; 554 passed, 4 skipped |
| Pipeline pytest | 157 passed |
| Full engine Ruff | passed |
| Full engine pytest | 3,890 passed, 1 skipped |
| Promotion plus every C05 test | 127 passed |
| Exact five immutable probes | 8 passed; hashes unchanged |
| Golden draft generator | 16 rows byte-identical |
| Bench-shape artifact parity | exact |
| Client-bundle secret audit | 61 chunks, zero hits |
| Frozen C05 files | empty diff against `39563c3` and `9d71428` |
| Portable-path audit | no username-specific committed path |
| `git diff --check` | passed |

The five immutable probe hashes remain:

- harness authority: `33e759b954799d112d88793c43cc1937b097a42ec92907ac7d42ff18909e3551`
- C05A verdict: `4b10d92a332b005e2d08bcafbd1040639d70ff2cd300640e20c7c8e9a04e6194`
- C05B analysis: `45e8abe1db228d34af2cb2aa73d74dffb51eb127e7ee6f5b7b9b7bc332b1a137`
- C05C auxiliary authority: `cd4e8c62ae2124743b6e0c79a33a27385b6f7a7d4d79b67a0d298ba38049bb30`
- C05D provenance: `5bdcbc27b1bef84c836a9c38efd5f3a1ed5edd9944e18e70326f769aeb461b81`

## Changed-path ownership

Producer owns the two C06A records, the regenerated C06 simulation summary, the shared draft-policy
and solver corrections, their invariant/adversarial tests, the regenerated golden drafts, the exact
Ruff exceptions for hash-frozen probes, and portable normalization of five historical receipt paths.
No frozen experiment, promotion runner, evaluator, immutable probe, or C05 authority artifact changed.

## Handoff

End the producer phase after committing this checkpoint. Independent review must distrust this
record, inspect the actual final diff and hashes, reproduce the deterministic boundary from the
reviewer worktree or an exact commit export, and record PASS, BLOCK, or INCONCLUSIVE on the reviewer
branch. No landing action is authorized by this producer disposition.
