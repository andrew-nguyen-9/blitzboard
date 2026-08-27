# v6 orchestration state

- state: running
- phase: C05 second execution freeze BLOCK; common proxy measurement protocol not frozen
- branch: `v6/bench-portfolio-review`
- worktree: runtime-local `.worktrees/v6-review` (uncommitted parent location)
- green base SHA: `01f01d3c5f9c00a046edd43707db75ce1426c0e8`
- reviewed predecessor SHA: `c2968ed02047370329b0cc64683e60a3358afffa`
- current attempt: 3
- failure signature: resolved by per-pick event-loop yields in heavy test drivers; synchronous
  production driver remains behavior-identical
- blockers: v5 control cannot emit frozen playoff/championship metrics; rehearsal tooling provenance
  names a commit without the harness; committed C05 test fails Ruff I001
- verification: original reviewer probe 2 passed; focused C05 suite 45 passed with documented env;
  second reviewer provenance probe fails as expected; C05-focused Ruff fails deterministically
- next action: freeze append-only promotion-v4 common-measurement protocol and matching execution
  addendum, repair provenance/Ruff, and stop for another freeze review before implementation or run
- external authority: no push, merge, PR, release, protected-branch edit, or branch deletion

The 25 files between the reviewed predecessor and baseline belong to the separately landed
intelligence subsystem. They do not overlap the v6 bench surfaces.
