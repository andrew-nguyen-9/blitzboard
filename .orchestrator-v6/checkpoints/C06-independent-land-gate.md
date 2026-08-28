# C06 independent land gate — producer checkpoint

Producer disposition: **LAND GATE FAILED**

C05 promotion remains excluded. No fit, confirmation, calibration, auxiliary bridge, promotion
manifest, or frozen evaluator was run or changed. Shipped v5 remains production authority.

## Deterministic blocker

The real TypeScript v5 draft policy was exercised through the existing `draft-eval.mjs` bridge,
then every selected roster was checked by the existing engine roster solver. In the canonical
10-team 1QB standard, four-bench fixture, the seeded test team drafted 13 players but no kicker:

```text
fixture: t10-1qb-std-te0.0-b4-ir0
base seed: 20260828
derived seed: 1428192669
draft position: 3
solver result: illegal roster: no pool player can fill starter slot 'K' (index 7)
classification: UNACCEPTABLE
winnable: false
```

Exact replay reproduced the selections. This is not isolated: only 6 of 18 completed league drafts
had every roster legal. All 18 were duplicate-free. Missing required K/DST slots occurred across
10- and 12-team 1QB/2QB fixtures and front/middle/back seats. Both sampled 14-team fixtures were
legal, which does not cure the mandatory-slice failures.

Changing the policy's K/DST timing would change shipped v5 strategy; ignoring K/DST would bypass the
explicit roster-legality requirement. Both are outside C06. Scale-up stopped because more samples
cannot turn a replayable illegal roster into a valid one.

## Reality evidence

- local draft/season evaluations: 18 drafts × 2 season trajectories
- required format coverage: 10/12/14 teams; 1QB/superflex/2QB; 4/6/8 bench
- seat coverage: front, middle, back
- classification totals: 8 ACCEPTABLE, 2 BORDERLINE, 8 UNACCEPTABLE
- duplicate prevention: 18/18 drafts
- fully legal league drafts: 6/18
- evaluator: shipped `draftAI.DEFAULT_POLICY` plus `season_eval.evaluate_rosters`
- uncertainty: local historical corpus, degraded ADP/injury/contingent-role metadata, proxy
  playoffs/championships, two trajectories per draft; no roster is claimed guaranteed to win
- synthetic artifact: `.orchestrator-v6/prep/C06-draft-realism.json`, SHA-256
  `e035f4e463d29b9f3a5badcb533aa96da21e014a34022c5ba586eceb3a0bfe83`

The safe no-network live-equivalent fallback replayed the same `candidatePool`/`pickForTeam` path
used by the application against the checked-in 12-team superflex mock. Its 216-pick artifact was
byte-identical at SHA-256 `104edd7a0619e0ae69c1a1c13ecae1702eff335d06e9f1d1088642f40cd605de`.
External live access was unavailable without relying on an uncontrolled external draft ID or
credentials, so no account, login bypass, invitation, real league, payment, or network mutation was
attempted.

## Verification at checkpoint

- focused C06 tests: 9 passed
- focused Ruff: passed
- local mock generator `--check`: passed, one row byte-identical
- frozen C05 experiment/promotion/evaluator diff against `9d71428`: empty
- `git diff --check`: passed
- pre-commit promotion/C05 suite: 118 passed, 9 expected dirty-tree refusals; must be rerun against
  the committed clean producer tree
- full engine Ruff: pre-existing four immutable-probe formatting findings
- portable-path audit: pre-existing committed user-home paths in four C05/npm receipt files

Post-commit verification against `1526540f2c790839dd547089edad0d7c3787deb9`:

- promotion plus every C05 test: 127 passed
- full engine pytest with required producer-root binding: 3,888 passed, 1 skipped
- frontend build/typecheck/lint/tests: exit 0; tests 553 passed, 4 skipped; lint has one warning
- pipeline pytest: 157 passed
- client bundle secret audit: passed; no service-role or secret token
- frozen-file comparison and hashes: passed
- browser/canonical bench-shape parity: exact
- `git diff --check`: passed
- full engine Ruff: failed only on four pre-existing immutable-probe formatting findings
- portable-path audit: failed on five pre-existing user-home strings in historical C05/npm receipts
- original checkout: unchanged from the recorded dirty `main` state

## Required disposition

C06 cannot PASS. Independent review must reproduce the committed defect and record **BLOCK**. C05
remains parked, v5 remains production authority, and no merge, push, PR, release, or branch deletion
is authorized.
