# v6 orchestration state

- state: running
- phase: C01 correction required
- branch: `v6/bench-portfolio-review`
- worktree: runtime-local `.worktrees/v6-review` (uncommitted parent location)
- green base SHA: `01f01d3c5f9c00a046edd43707db75ce1426c0e8`
- reviewed predecessor SHA: `c2968ed02047370329b0cc64683e60a3358afffa`
- current attempt: 3
- failure signature: resolved by per-pick event-loop yields in heavy test drivers; synchronous
  production driver remains behavior-identical
- blockers: C01 public bye result/template handling and contingent-role valuation contract
- verification: focused gate green; build/typecheck/lint green; pipeline 146 passed; engine Ruff
  green and 4,123 passed / 1 skipped / 1 expected failure
- next action: await immutable C01A production checkpoint and independently re-review corrections
- external authority: no push, merge, PR, release, protected-branch edit, or branch deletion

The 25 files between the reviewed predecessor and baseline belong to the separately landed
intelligence subsystem. They do not overlap the v6 bench surfaces.
