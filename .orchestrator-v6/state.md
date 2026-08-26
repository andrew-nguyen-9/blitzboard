# v6 orchestration state

- state: running
- phase: C00 blocked remediation
- branch: `v6/bench-portfolio-review`
- worktree: runtime-local `.worktrees/v6-review` (uncommitted parent location)
- green base SHA: `01f01d3c5f9c00a046edd43707db75ce1426c0e8`
- reviewed predecessor SHA: `c2968ed02047370329b0cc64683e60a3358afffa`
- current attempt: 1
- failure signature: frontend Vitest passes 449/449 assertions, then exits nonzero with
  `[vitest-worker]: Timeout calling "onTaskUpdate"`; reproduced twice
- blockers: frontend harness exit remains non-green; C01 map omits `draftAI.ts::byeCover`;
  promotion v1 does not freeze exact boards/seats or explicit scoring configurations
- verification: focused gate green; build/typecheck/lint green; pipeline 146 passed; engine Ruff
  green and 4,123 passed / 1 skipped / 1 expected failure
- next action: Claude writes a new C00 correction checkpoint; reviewer re-audits without overwriting
  either immutable C00 record
- external authority: no push, merge, PR, release, protected-branch edit, or branch deletion

The 25 files between the reviewed predecessor and baseline belong to the separately landed
intelligence subsystem. They do not overlap the v6 bench surfaces.
