# C06A roster-legality recovery timebox log

Append-only execution record. Actual wall-clock times are CDT (`-0500`). C06A is a narrow
correction unit based exactly on the failed C06 producer commit. C05 promotion remains excluded,
C05 remains parked, and shipped v5 remains production authority.

## Recovery charter and start

- actual start: Friday, 2026-08-28 09:31:15 AM CDT (`-0500`)
- predecessor: `39563c373265790461e18f388b3c7cd3e31d58d0`
- branch: `v6/c06a-roster-legality`
- isolated producer worktree: runtime temporary root; no earlier worktree changed
- deadline amendment: hard stop extended by Andrew to 5:00 PM CDT; product scope unchanged
- hardware: 11 logical CPUs, 19,327,352,832 bytes physical memory
- worker ceiling: `min(8, 11 - 2) = 8`; selected one simulation/evaluator process because the
  measured batch completed with ample deadline headroom and avoided nondeterministic merge risk

### Requirement ledger

| ID | Requirement | Producer evidence | Status |
|---|---|---|---|
| R1 | Preserve v5 authority and exclude C05 promotion | frozen diff, immutable hashes, 127-test authority slice | proven |
| R2 | Complete, legal, duplicate-free rosters | shared live-policy guard, solver checks, 100- and 500-draft batches | proven |
| R3 | Deterministic seeded replay and bounded variation | exact tied-solver replay, 100/500 unique derived seeds and test rosters | proven |
| R4 | Required format/seat/bench coverage | six canonical fixtures; 10/12/14 teams; 1QB/SF/2QB; front/middle/back | proven |
| R5 | Honest quality and winnability classification | cohort metrics, uncertainty interval, weak/invalid-team test | proven |
| R6 | Completed live/mock draft | real browser draft room against local recorded data | proven by fallback |
| R7 | Required suites and land audits | final verification bound to durable producer commit | proven |

### Decision ledger

- roster correction options: waive K/DST legality; add a separate simulation-only patch; enforce
  required starters in the shared shipped draft policy
- selected: the shared policy guard. Waiving legality violates the gate, and a simulation-only
  patch would not repair the browser path.
- special-team options: retain the late duplicate K/DST exception; add complex need-aware caps;
  hard-cap a second K or DST in every round
- selected: hard-cap the second special-team player. It is the smallest reversible invariant and
  removes the irrational K/DST distributions observed in the first 500-draft pilot.
- solver options: accept interchangeable tied FLEX assignments; canonicalize after solving; run
  the existing CP-SAT model with one search worker
- selected: one search worker. It preserves the existing objective and makes exact replay stable
  without a new solver or post-processing abstraction.
- live options: external account/sandbox; public no-account mock; application browser fallback
- selected: the real local browser draft flow because no safe configured external room was
  available. No account, payment, invitation, credential, real league, or network mutation occurred.

## TDD and implementation checkpoint

- actual end: Friday, 2026-08-28 10:17:27 AM CDT (`-0500`)
- producer implementation commit: `1d2a26cd02b60e504f67d9a9f23a330420542c04`
- shared TypeScript completion regression first failed with final picks `WR,K` instead of `K,DST`,
  then passed after the required-starter guard
- duplicate-special-team probes first failed under the old late-round exception, then passed after
  the hard cap
- tied roster-solver replay produced three assignment signatures in 40 runs before the worker
  correction and one afterward
- corpus invariant first exposed ten stale golden rows with missing required K/DST starters; all 16
  golden rows were regenerated through the existing generator and verified byte-identical on replay
- focused frontend: 108 passed; focused engine/C06/solver/corpus: 40 passed; focused Ruff: passed
- immutable probe bytes unchanged; full Ruff debt resolved only with exact per-file ignores for
  hash-frozen probe formatting
- five historical username-specific path literals normalized to `$HOME` without changing authority
  evidence

## Simulation checkpoint

- pilot: 18 drafts, 18/18 legal and duplicate-free, about 16.7 seconds
- first 500-draft scale run exposed up to three kickers and two defenses on a roster; evidence was
  rejected and the hard cap added
- second 500-draft run exposed nondeterministic tied solver assignments when replayed independently;
  evidence was rejected and the solver worker correction added
- final committed artifact: 100 drafts × two season trajectories, SHA-256
  `75e8ccce211475797435163ee9bf96fe70107fe8a8b9d77756775ef8b28cf7d9`, 740,087 bytes
- committed results: 100/100 league drafts legal; 100/100 duplicate-free; 46 ACCEPTABLE,
  45 BORDERLINE, 9 UNACCEPTABLE; 76 classified winnable and 24 not winnable
- final extended temporary batch: 500 drafts × two season trajectories in 427.9363 seconds,
  SHA-256 `761ae30cd2b5b324484a8b985ec411b57723672cf77bd940eb456c5d179365db`
- extended results: 500/500 legal; 500/500 duplicate-free; 220 ACCEPTABLE, 245 BORDERLINE,
  35 UNACCEPTABLE; 369 winnable, 131 not winnable; 500 unique derived seeds and primary rosters
- exact first-100 deterministic replay after removing elapsed-time fields:
  `1e881939e4d0439b8232abaf4bfe1bd8e1ded8aa4fd66599f2b7ffac3639fced`
- evaluator: `draftAI.DEFAULT_POLICY(v5) + season_eval.evaluate_rosters`; every row is labeled
  synthetic/non-authoritative and cannot support C05 promotion
- limitations: recorded local historical corpus, degraded ADP/injury/contingent-role metadata,
  two season trajectories per draft, playoff/championship proxies, and no guaranteed-win claim

## Live-equivalent browser checkpoint

- actual window: Friday, 2026-08-28 10:18:51–10:21:34 AM CDT (`-0500`)
- tested producer commit: `1d2a26cd02b60e504f67d9a9f23a330420542c04`
- disposable local-data page overlay SHA-256:
  `f66050406d3b58c0a0024eb7a50b45be9013d28213a2313a16bb5cd8493b34d5`
- browser path: the real `/draft` `DraftWarRoom`, loaded with repository `fixtures/seasons/2024.json`
  half-PPR-like data; the overlay was never committed and its disposable worktree was removed
- completed format: 12-team superflex, 16 rounds, user team in slot 6
- pick log: 192 rows, 192 unique player names; first pick Lamar Jackson, last pick Calvin Austin III
- user roster: complete QB/RB/RB/WR/WR/TE/FLEX/OP/DST/K starters plus 6/6 bench; no duplicates
- displayed starter projection: 2,194 versus 2,307.5 league median; grade C, rank 11/12
- classification: BORDERLINE and not proven winnable. The legal roster is projection-poor relative
  to this cohort; the UI result is not upgraded to ACCEPTABLE or a win claim.

## Final producer verification checkpoint

- actual window: Friday, 2026-08-28 10:24:29–10:38:20 AM CDT (`-0500`)
- first typecheck found one stale test-only `OFFENSIVE` symbol; corrected assertion committed as
  `07cbe84b8b2d5ad4119249672d038dccbe685399`
- first full frontend run then found one stale C04 late-kicker expectation; corrected probe committed
  as `a1ff108b846aa4b51a3266918603609f16ad9886`
- final verification restarted against `a1ff108b846aa4b51a3266918603609f16ad9886`
- frontend build: exit 0, 25 static pages; one pre-existing `useEspnSync` hook warning
- frontend typecheck: exit 0
- frontend lint: exit 0, zero errors and one warning
- frontend tests: 61 files; 554 passed, 4 skipped; exit 0
- bare system `python -m pytest` in `pipeline/`: exit 2, collected none; rejected as evidence
- pipeline repository virtualenv `python -m pytest`: 157 passed in 6.09 seconds; exit 0
- full engine Ruff: passed; exit 0
- full engine pytest with `C05_PROD_ROOT` bound: 3,890 passed, 1 skipped in 423.51 seconds; exit 0
- promotion plus every C05 test: 127 passed in 17.10 seconds; exit 0
- exact five immutable probes: 8 passed in 5.63 seconds; exit 0; all hashes match C05E
- golden draft generator check: 16 rows byte-identical; exit 0
- bench-shape generator parity: exact; canonical source hash
  `58b611f5b768dc0b95867410ccd815be39e390cd2711a4f67f8e8844c43f9e90`
- client bundle: 61 JavaScript chunks, zero service-role/secret-token hits
- frozen C05 experiment/promotion/evaluator diff against both `39563c3` and `9d71428`: empty
- portable-path scan: no username-specific committed home path; documentation placeholders only
- resource end sample: load 4.92/4.82/4.20; no memory-pressure or backoff condition observed
- options: merge/push; discard; retain isolated branch and begin artifact-first review
- selected: retain. The execution charter forbids merge, push, PR, release, or deletion.
- current risk: producer claims remain untrusted until independently reproduced from the final
  durable commit
- next bounded action: commit producer records, end producer phase, and review the exact committed
  tree from `v6/bench-portfolio-review`
