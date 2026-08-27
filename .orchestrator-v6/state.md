# v6 orchestration state

- state: running
- phase: C05 promotion-v4 freeze BLOCK; design accepted but exec-v1 evidence is contradictory
- branch: `v6/bench-portfolio-review`
- worktree: runtime-local `.worktrees/v6-review` (uncommitted parent location)
- green base SHA: `01f01d3c5f9c00a046edd43707db75ce1426c0e8`
- reviewed predecessor SHA: `c2968ed02047370329b0cc64683e60a3358afffa`
- current attempt: 3
- failure signature: resolved by per-pick event-loop yields in heavy test drivers; synchronous
  production driver remains behavior-identical
- blockers: v4 exec-v1 names `bc11f54` as receipt-generation tooling while receipts prove
  `278f50e`; roster “partition the board” validation is impossible as written; Ruff scope is
  overstated because the immutable second reviewer probe retains E501
- verification: both earlier reviewer probes pass; focused suite 47 passed; C05-owned Ruff scope
  passes; full scope including the immutable second probe fails E501; new v4 provenance probe fails
- next action: append-only promotion-v4-exec-v2 correction and freeze re-review before harness work
- external authority: no push, merge, PR, release, protected-branch edit, or branch deletion

The 25 files between the reviewed predecessor and baseline belong to the separately landed
intelligence subsystem. They do not overlap the v6 bench surfaces.
