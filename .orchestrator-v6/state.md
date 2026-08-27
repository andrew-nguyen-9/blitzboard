# v6 orchestration state

- state: running
- phase: C05D auxiliary authority BLOCK; provenance and calibration authority remain caller-owned
- branch: `v6/bench-portfolio-review`
- worktree: runtime-local `.worktrees/v6-review` (uncommitted parent location)
- green base SHA: `01f01d3c5f9c00a046edd43707db75ce1426c0e8`
- reviewed producer SHA: `36d395aefb4bb4683e9e8d7186d65c7f6fbbda47`
- C05A base SHA: `ce0758bf4b94885d1df580a55cef679c6dd4d1eb`
- C05B base SHA: `2b0ae60ca2f61623597abf9cccc75a257e55210f`
- C05C base SHA: `37ed8b361f882abf09f6bdbcedf2ae4e24ca0b23`
- current attempt: 6
- failure signature: caller-added accepted calibration identity plus fabricated receipts produces
  and confirms `pass`; fabricated tooling provenance admits deterministic and runtime evidence
- blockers: mutable caller `effective` state creates calibration authority and the embedded report
  is not hashed; any truthy `produced_by_tooling` value is accepted as mechanical provenance
- verification: four immutable reviewer probes were byte-identical and their 6 tests passed;
  focused suite 125 passed; full engine 3876 passed, 2 skipped; Ruff/frozen/diff/tree green; two
  independent C05D authority probes fail as expected
- next action: bounded C05E canonical-effective and provenance correction, then re-review; C05 stays
  parked and v5 preserved with no authoritative execution or policy bridge
- external authority: no push, merge, PR, release, protected-branch edit, or branch deletion

The 25 files between the reviewed predecessor and baseline belong to the separately landed
intelligence subsystem. They do not overlap the v6 bench surfaces.
