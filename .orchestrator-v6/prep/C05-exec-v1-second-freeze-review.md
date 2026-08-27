# C05 promotion-v3-exec-v1 independent second freeze review

Verdict: **BLOCK EXECUTION**

- candidate policy SHA: `7b3fd73578943b992402ad693259a3e92358da69`
- reviewed C05 tooling head: `980f5e305d4d580a9e509030dc8254d0d877b3cc`
- correction commit: `9939179`
- addendum SHA-256: `24e5e50afdad75006ca3a1814317d9254ea98de25bbb97dba4b06bbee7c3b7ad`
- frozen manifest SHA-256: `bbb241603a33697bff376b21a2e57e7e066c3c85186eaaab120485ec6bd941ab`

## Accepted corrections

The second-freeze branch is clean. The frozen manifest/addendum and candidate policy SHA are
unchanged. The new loader hash-verifies both frozen files and applies the frozen candidate SHA and
zero waiver-cost binding only in memory. The runner now maps accepted C02 playoff/championship
samples. Arm execution verifies the actual arm checkout HEAD, isolates imports from the editable
tooling installation, and writes stage-separated receipts without overwriting them.

The unchanged reviewer probe passes 2/2. The focused promotion suite passes 45/45 when invoked with
its documented `C05_PROD_ROOT`. The real two-checkout rehearsal proves distinct baseline/candidate
evaluators ran against an identical board. These findings close the three original execution
blockers, but do not authorize the experiment.

## Remaining deterministic blockers

1. The v5 control evaluator predates `per_season_playoff` and `per_season_champ`; its rehearsal
   receipt necessarily contains null proxies. The frozen manifest requires paired playoff and
   championship gates and lists proxy availability as an execution precondition. Missing control
   samples make the authoritative result structurally inconclusive and preserve v5. Restricting
   those gates or accepting the cap would waive frozen requirements and is rejected.
2. The committed rehearsal receipts claim `produced_by_tooling_head` `4c31f9e...`, but that commit
   does not contain `promotion/execution.py`; the harness first appears at `9939179`. The producer
   passed an unverified caller string while running from a dirty tooling tree. Arm identities are
   proven, but tooling provenance is not. Authoritative receipts must mechanically derive and
   verify their tooling commit, require a clean tooling tree, and record hashes of the execution
   module and effective manifest.
3. The reported Ruff-clean gate is not reproducible. Ruff deterministically reports I001 in the
   committed `engine/tests/test_v6_c05_execution_freeze_adversarial.py` import block. The test
   suite is green, but the stated quality gate is not.

## Required append-only protocol correction

Create `promotion-v4.json` and a matching `promotion-v4-exec-v1.json`; preserve v3 and exec-v1
byte-for-byte. V4 must compare both arms through one frozen accepted C02 measurement evaluator:
each frozen arm produces its policy/draft outputs under the same board, seat, season, and seed,
then the common evaluator replays both outputs to derive started-points, H2H, playoff, and
championship samples. Freeze the measurement-evaluator SHA and file hashes, intermediate receipt
schema, pairing keys, commands, write-once separation, and policy-versus-measurement identity.
This is a material experiment change and must stop for a new freeze review before implementation
or authoritative execution.

Also make tooling provenance mechanical, regenerate only non-authoritative rehearsal receipts from
a committed clean tooling head, and make the full stated Ruff command pass. Do not run the
authoritative fit or confirmation, reinterpret the failed accepted calibration evidence, edit
immutable files, push, merge, or open a PR.
