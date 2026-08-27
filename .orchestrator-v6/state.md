# v6 orchestration state

- state: running
- phase: C05 promotion-v4 exec-v2 freeze PASS; bounded harness implementation authorized
- branch: `v6/bench-portfolio-review`
- worktree: runtime-local `.worktrees/v6-review` (uncommitted parent location)
- green base SHA: `01f01d3c5f9c00a046edd43707db75ce1426c0e8`
- reviewed predecessor SHA: `c2968ed02047370329b0cc64683e60a3358afffa`
- current attempt: 3
- failure signature: resolved by per-pick event-loop yields in heavy test drivers; synchronous
  production driver remains behavior-identical
- blockers: authoritative execution remains prohibited pending v4 harness review and a new accepted
  calibration report passing every inherited threshold
- verification: exec-v2 and all predecessor hashes exact; focused suite 47 passed; frozen Ruff scope
  passed; exec-v2 provenance probe passed; diff and clean-tree checks passed
- next action: implement only the frozen v4 draft/measurement harness, run non-authoritative
  rehearsals, and stop for independent harness freeze review
- external authority: no push, merge, PR, release, protected-branch edit, or branch deletion

The 25 files between the reviewed predecessor and baseline belong to the separately landed
intelligence subsystem. They do not overlap the v6 bench surfaces.
