# C06 timebox and decision log

Append-only execution record. Actual wall-clock times are CDT (`-0500`). Commands use runtime-local
paths only in this uncommitted execution narrative; committed configuration remains portable.

## 2:15 checkpoint reconciliation

- actual start: Friday, 2026-08-28 02:13:55 AM CDT (-0500)
- actual end: Friday, 2026-08-28 08:31:07 AM CDT (-0500)
- elapsed: 6h17m12s, dominated by the required sandbox approval for Git ref creation
- status: 2:15, 3:30, 5:30, and 7:30 checkpoints missed; latest safe bounded action started
- authoritative verification:
  - reviewer `HEAD=9033f402cc76e0f02709d73c1e2293abd114e98d`, branch
    `v6/bench-portfolio-review`, clean, exit 0
  - accepted producer `HEAD=9d71428c8dacabd747d21205296b46d5410de3f3`, branch
    `v6/c05e-auxiliary-absent`, clean, exit 0
  - required instruction and checkpoint files read completely, exit 0
  - `git worktree add -b v6/c06-independent-land-gate ... 9d71428...`: sandbox exit 255,
    approved retry exit 0
  - C06 producer `HEAD=9d71428c8dacabd747d21205296b46d5410de3f3`, clean, exit 0
- worktree decision:
  - options: add `.worktrees/` to tracked ignore rules; reuse the unignored repository-local
    directory; create the linked worktree under the writable temporary root
  - selected: temporary-root worktree, because it avoids editing protected `main`, adding another
    untracked repository-local tree, or touching earlier C05 worktrees; branch commits remain durable
- risks: compressed schedule; original checkout already contains unrelated `.serena/project.yml`,
  `AGENTS.md`, `tmp/`, and `.worktrees/` changes that must remain untouched and be reported
- next bounded action: TDD the reuse-only realism harness, pilot it, then select the safe batch

## Frozen execution charter

### Requirement ledger

| ID | Requirement | Evidence | Failure disposition |
|---|---|---|---|
| R1 | C05 promotion excluded; v5 authority preserved | unchanged frozen/C05 hashes and prohibited-command log | BLOCK |
| R2 | deterministic seeded realistic drafts | exact replay tests plus artifact seeds/selections | BLOCK |
| R3 | front/middle/back and 10/12/14 formats | scenario matrix and completed artifact rows | BLOCK |
| R4 | 1QB plus superflex/2QB and bench variation | canonical matrix rows in artifact | BLOCK |
| R5 | degradation, runs, scarcity, late needs | scenario flags and roster/position evidence | BLOCK |
| R6 | no duplicate and every roster legal | existing roster rules plus adversarial tests | BLOCK |
| R7 | honest team quality and winnability | numerical league-relative metrics and weak-team test | BLOCK |
| R8 | at least 100 local drafts if pilot permits | pilot throughput and final count | BLOCK if runtime permits |
| R9 | one safe live/mock draft | repository sandbox/browser flow, else local app-flow fallback | INCONCLUSIVE only if external access unavailable and fallback passes |
| R10 | every required suite and land audit green | command receipts and independent replay | BLOCK |
| R11 | frozen files, secrets, paths, artifacts, original checkout | hashes/diffs/scans | BLOCK |

### Test matrix

| Concern | Test/evidence |
|---|---|
| exact replay | same seed produces byte-identical jobs and selections |
| bounded variation | different seeds change selections/seat while preserving legality and rational rank bounds |
| draft slots | explicit front, middle, back plus seeded primary slots |
| formats | canonical 10-team 1QB, 12-team 1QB half-PPR-like, 12-team 2QB, 14-team superflex |
| bench | 4-, 6-, and 8-slot canonical fixtures |
| metadata | remove optional bye/metadata fields in an isolated input and classify uncertainty |
| roster safety | global uniqueness, exact roster size, legal complete starters |
| scarcity/runs | position-pick concentration and scarce QB/TE tier observations |
| late needs | final-round picks still yield complete legal starters |
| reality | starter strength vs median, bench replacement, bye/absence, upside, scarcity/redundancy |
| honesty | deliberately weak/invalid team cannot be forced to acceptable or winnable |
| authority | all five immutable reviewer probes plus every C05 test remain green and byte-identical |

### Hardware and simulation budget

- logical CPUs: 11 (`getconf _NPROCESSORS_ONLN`, exit 0)
- physical memory: 19,327,352,832 bytes; system-reported free percentage 46%
- load at 2:16 AM: 2.67 / 2.71 / 2.67
- swap: historical cumulative 7,269,902 in / 10,716,344 out; no rapid-growth sample observed yet
- pytest-xdist: unavailable (`pytest --help` exposes no `-n`/`--numprocesses`)
- ceiling from policy: `min(8, 11 - 2) = 8` workers
- selected initial budget: one batched Node draft process and one evaluator process for the pilot;
  scale to at most four workers only if measured throughput needs it and memory remains at least 25%
- merge rule: derived seeds and output ordering are fixed before execution; workers, if used, write
  isolated temporary shards and the primary process merges by scenario/derived seed

### Design decision ledger

- harness options: extend frozen C05 promotion execution; modify the TypeScript bridge; compose the
  existing bridge and evaluator in a new module
- selected: composition in a new module; it reuses production v5 picks and accepted evaluators while
  keeping frozen C05 behavior byte-identical
- simulation volume options: 100 minimum; 500 preferred; 2,000 upper target
- selected: decide after a five-draft pilot, with 100 as the deadline-safe floor if throughput permits
- live options: configured sandbox integration; signed-in reversible mock room; public no-account
  mock; local application-flow fallback
- selected: first available safe repository-backed option; no account, payment, invitation, real
  league, authentication bypass, or irreversible external state is authorized
- classification options: absolute projection cutoff; cohort-relative percentile; cohort-relative
  metrics with uncertainty
- selected: cohort-relative metrics with an uncertainty interval, because the contract defines
  acceptability and winnability relative to the league and forbids guaranteed-win claims

## Fail-fast producer run

- actual start: Friday, 2026-08-28 08:31:07 AM CDT (-0500)
- actual end: Friday, 2026-08-28 08:49:09 AM CDT (-0500)
- elapsed: 18m02s
- implementation:
  - new reuse-only `draft_realism.py` harness and nine focused tests
  - `static_fit.run_bridge` invokes the installed `tsx` loader through `node --import tsx` because
    the `tsx` CLI's IPC socket is prohibited by the sandbox; focused regression replay passed
  - no frozen C05/promotion/evaluator file changed
- TDD receipts:
  - initial module import: exit 2, expected missing-module failure
  - first focused run: 6 passed, 1 failed from sandbox `tsx` IPC `EPERM`
  - `node --import tsx scripts/draft-eval.mjs` reached JSON parsing, proving the loader path avoids
    IPC; bridge switched at the shared call site
  - focused bridge run: 7 passed
  - required-dimensions test first failed because shipped v5 produced an illegal K-less roster
  - empty-bench regression first failed with `StatisticsError`, then passed after zero-valuing the
    unavailable replacement metric
  - final focused suite: 9 passed in 7.58s; focused Ruff passed
- bounded simulation command: `python -m blitz_engine.backtest.draft_realism --base-seed 20260828
  --count 18 --seasons 2 --output ../.orchestrator-v6/prep/C06-draft-realism.json`, exit 0
- simulation evidence:
  - 18 completed seeded drafts over six canonical formats and front/middle/back strata
  - all 18 duplicate-free; only 6/18 league drafts had every roster legal
  - test-team labels: 8 ACCEPTABLE, 2 BORDERLINE, 8 UNACCEPTABLE
  - 10-team 1QB shallow-bench: 0/3 test teams legal, each missing the required K
  - additional 10/12-team failures missed K or DST; both tested 14-team formats were legal
  - artifact SHA-256 `e035f4e463d29b9f3a5badcb533aa96da21e014a34022c5ba586eceb3a0bfe83`,
    134,787 bytes
- live/mock fallback:
  - no repository browser draft sandbox or offline-populated `/draft` page exists
  - local real-policy mock replay `node --import tsx scripts/gen-golden-drafts.mjs --check --row
    t12-superflex-std-te0.0-b8-ir0`, exit 0, one row byte-identical
  - completed artifact: 216 picks, 12 rosters of 18, SHA-256
    `104edd7a0619e0ae69c1a1c13ecae1702eff335d06e9f1d1088642f40cd605de`
- scale decision:
  - options: rewrite v5 K/DST draft strategy; waive K/DST as required starters; stop scale-up and
    record deterministic BLOCK
  - selected: stop and BLOCK. Strategy change is outside C06/v5-preservation scope; waiving roster
    requirements would bypass an explicit gate. A 100-draft run cannot reverse an invalid roster.
- resource end sample: 41% memory free, load 3.81 / 2.84 / 2.56; no worker backoff triggered
- authority regression pre-commit: 118 passed, 9 failed solely because the promotion harness
  correctly refuses the intentionally dirty tracked producer tree; rerun required after commit
- additional land-gate findings from the independent read-only audit:
  - full engine Ruff flags four pre-existing immutable-probe formatting findings
  - committed username-specific paths remain in one C05 dry-run note and three npm receipts
  - neither was changed or waived because the invalid-roster defect already terminates C06
- current risks: required full frontend/pipeline/engine suites are intentionally not started after
  the deterministic terminal failure; official reviewer reproduction is still required
- next bounded action: commit producer evidence, rerun clean-tree C05 authority tests, then review
  the durable commit from the reviewer worktree
