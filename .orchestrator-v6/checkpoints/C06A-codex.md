# C06A roster-legality recovery — independent review

Official verdict: **PASS**

- reviewer branch: `v6/bench-portfolio-review`
- reviewer predecessor: `c29fbbaf3ad788e09e592ad5be0e645b540f2053`
- reviewed producer branch: `v6/c06a-roster-legality`
- reviewed producer base: `39563c373265790461e18f388b3c7cd3e31d58d0`
- reviewed producer commit: `ea706a393d50fbb328131cea5ec532436303e922`
- review window: Friday, 2026-08-28 10:40:42–10:54:19 AM CDT (`-0500`)

C05 promotion remains excluded. C05 is parked and shipped v5 is production authority. The review
ran no fit, confirmation, calibration, auxiliary bridge, merge, push, PR, release, protected-branch
edit, real-league mutation, account creation, invitation, or payment.

## Verdict basis

The reviewer inspected the actual `39563c3..ea706a3` diff and reproduced the corrected boundaries
from a detached worktree at the exact producer commit. The required-starter guard is in the shared
browser draft policy, not a simulation-only bridge; a second K or DST is always capped. The existing
roster solver uses one CP-SAT search worker so tied FLEX assignments replay exactly.

No deterministic defect, authority bypass, frozen-file drift, secret exposure, portable-path defect,
duplicate roster, invalid roster, or required-suite failure remains. The exact Ruff exceptions are
limited to four hash-frozen reviewer files whose bytes cannot be formatted; they do not suppress any
production or mutable-test scope. No reviewer-owned test was needed because existing adversarial
tests plus direct independent replay resolved every boundary.

## Independent simulation and roster reproduction

The reviewer did not trust producer summaries. It reran the first 18 jobs from the exact commit and
compared every result field except elapsed time against the committed artifact.

- exact-without-elapsed comparison: true
- independent first-18 canonical SHA-256:
  `fd6b3780b25294cf47fce9dec9cd0583e597edf73110c5c7a9e37b4ee11eb3da`
- first-18 results: 18/18 legal; 18/18 duplicate-free; 9 ACCEPTABLE, 9 BORDERLINE
- coverage: all six mandatory fixtures and front/middle/back bands

A separate reviewer script rebuilt the recorded player pools and independently passed every one of
the committed 100 drafts through `validate_rosters`:

- 100/100 league drafts legal and starter-complete
- 100/100 draft-wide duplicate-free
- K count range across every roster: 1–1
- DST count range across every roster: 1–1
- 100 unique derived seeds and 100 unique primary rosters
- classifications: 46 ACCEPTABLE, 45 BORDERLINE, 9 UNACCEPTABLE
- modeled winnability: 76 true, 24 false
- artifact SHA-256: `75e8ccce211475797435163ee9bf96fe70107fe8a8b9d77756775ef8b28cf7d9`

The seeded local evidence is reproducible and its different seeds create bounded meaningful roster
variation without irrational special-team accumulation. Every row remains explicitly synthetic and
non-authoritative. The evaluator reports legality, starter completeness and strength versus median,
bench/replacement and bye/absence coverage, unavailable contingent-role evidence, scarcity and
redundancy, paired H2H, playoff/championship proxies, degraded inputs, and uncertainty. Existing
tests independently prove an intentionally invalid team is UNACCEPTABLE, has zero replacement
quality, and is not forced to winnable.

## Independent live-equivalent browser reproduction

No safe external sandbox was configured. The reviewer independently recreated the producer's exact
disposable overlay—SHA-256
`f66050406d3b58c0a0024eb7a50b45be9013d28213a2313a16bb5cd8493b34d5`—on the final producer commit
and drove the real `/draft` `DraftWarRoom` through the browser.

- completed 12-team superflex draft, 16 rounds
- pick log: 192 rows, 192 unique players, zero duplicates
- user team at slot 6: every QB/RB/RB/WR/WR/TE/FLEX/OP/DST/K starter filled, bench 6/6
- independent UI result: 2,280 projected starter points, grade C+, rank 9/12
- producer UI result: 2,194 projected starter points, grade C, rank 11/12

The UI intentionally uses live randomness, so exact selections differ while the legality and
uniqueness invariants reproduce. Neither roster is claimed guaranteed to win; the browser evidence
alone does not prove modeled winnability. The two ordinary middling results are reported honestly
rather than upgraded. The local-data overlay was never committed and the disposable review worktree
was removed after the run.

## Independent verification matrix

| Check | Reviewer result |
|---|---|
| Full engine pytest | 3,890 passed, 1 skipped in 423.11s |
| Full engine Ruff | passed |
| Promotion plus every C05 test | 127 passed in 19.47s |
| Exact five immutable reviewer probes | 8 passed in 8.05s; hashes match C05E |
| Frontend build | passed; 25 static pages; one existing hook warning |
| Frontend typecheck | passed |
| Frontend lint | 0 errors, 1 warning |
| Frontend tests | 61 files; 554 passed, 4 skipped |
| Pipeline pytest | 157 passed in 4.50s |
| Golden draft generator | 16 rows byte-identical |
| Bench-shape generator parity | exact |
| Client bundle audit | 61 JavaScript chunks; zero service-role/secret-token hits |
| Frozen C05 experiment/promotion/evaluator diff | empty against `9d71428` |
| Portable-path scan | no username-specific committed path |
| Producer diff check | passed |
| Exact detached producer tree | clean before disposable browser overlay |
| Original checkout | unchanged at `9192163`; pre-existing user changes preserved |

Immutable probe SHA-256 values remain:

- `33e759b954799d112d88793c43cc1937b097a42ec92907ac7d42ff18909e3551`
- `4b10d92a332b005e2d08bcafbd1040639d70ff2cd300640e20c7c8e9a04e6194`
- `45e8abe1db228d34af2cb2aa73d74dffb51eb127e7ee6f5b7b9b7bc332b1a137`
- `cd4e8c62ae2124743b6e0c79a33a27385b6f7a7d4d79b67a0d298ba38049bb30`
- `5bdcbc27b1bef84c836a9c38efd5f3a1ed5edd9944e18e70326f769aeb461b81`

## Complete changed-path ownership

Producer-owned implementation and tests:

- `frontend/lib/draftAI.ts`
- `frontend/lib/draftAI.test.ts`
- `frontend/lib/draftAI.fixtures.test.ts`
- `frontend/lib/draftAI.candidatePool.test.ts`
- `frontend/lib/v6DraftIntegration.adversarial.test.ts`
- `engine/blitz_engine/value/roster_solver.py`
- `engine/tests/test_roster_solver.py`
- `engine/tests/test_corpus.py`
- `engine/tests/test_draft_realism.py`
- `engine/pyproject.toml`

Producer-owned generated/evidence paths:

- all 16 tracked rows under `fixtures/golden_drafts/`
- `.orchestrator-v6/prep/C06-draft-realism.json`
- `.orchestrator-v6/prep/C06A-timebox-log.md`
- `.orchestrator-v6/checkpoints/C06A-roster-legality.md`
- portable-only normalization in `.orchestrator-v6/prep/C05-dryrun.md` and
  `.orchestrator-v6/receipts/npm-test-under-load-{1,2,3a}.txt`

Reviewer owns only this checkpoint and `.orchestrator-v6/state.md`. No reviewer implementation or
adversarial test was added. Frozen experiments, promotion execution/runner/manifest/gates/stats,
`season_eval.py`, and all five immutable probes are byte-identical.

## Decision ledger, limitations, and disposition

- options considered: BLOCK because C06 previously failed; INCONCLUSIVE because no external room
  was safely available; PASS because the corrected exact tree independently satisfies every local
  and authorized live-equivalent boundary
- selected: PASS. Prior C06 failures were independently reproduced as resolved. INCONCLUSIVE is not
  warranted because the authorized real browser fallback completed twice and all deterministic
  requirements pass.
- reviewer-test options: add another duplicate/legality test; add a distribution test; rely on the
  existing invariant tests plus direct 100-artifact validation
- selected: no new test. Another tracked probe would duplicate the independently executed boundary.
- limitations: external mock-room access was unavailable; browser picks use bounded live randomness;
  projections come from recorded local 2024 data; simulations use two season trajectories and proxy
  playoff/championship metrics; one pre-existing frontend hook warning remains; no roster is a win
  guarantee.

Official disposition is PASS for C06A only. C05 promotion remains out of scope and parked. The
producer branch and worktree are preserved. No merge, push, PR, release, or branch cleanup is
authorized or performed.
