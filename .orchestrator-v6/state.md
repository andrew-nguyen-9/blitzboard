# v6 orchestration state

- state: running
- phase: C00A blocked remediation
- branch: `v6/bench-portfolio-review`
- worktree: runtime-local `.worktrees/v6-review` (uncommitted parent location)
- green base SHA: `01f01d3c5f9c00a046edd43707db75ce1426c0e8`
- reviewed predecessor SHA: `c2968ed02047370329b0cc64683e60a3358afffa`
- current attempt: 2
- failure signature: production Vitest with `maxWorkers: 4` passes 441/441 assertions, then exits
  nonzero with `[vitest-worker]: Timeout calling "onTaskUpdate"`; independent correction run 90.99s
- blockers: frontend harness correction is not robust under concurrent machine load
- verification: focused gate green; build/typecheck/lint green; pipeline 146 passed; engine Ruff
  green and 4,123 passed / 1 skipped / 1 expected failure
- next action: Claude produces a lower-concurrency or structurally isolated harness correction and
  writes a new immutable correction checkpoint; reviewer reruns plain `npm test`
- external authority: no push, merge, PR, release, protected-branch edit, or branch deletion

The 25 files between the reviewed predecessor and baseline belong to the separately landed
intelligence subsystem. They do not overlap the v6 bench surfaces.
