# v6 orchestration state

- state: running
- phase: C05C fit-analysis authority BLOCK; auxiliary evidence remains caller-authored authority
- branch: `v6/bench-portfolio-review`
- worktree: runtime-local `.worktrees/v6-review` (uncommitted parent location)
- green base SHA: `01f01d3c5f9c00a046edd43707db75ce1426c0e8`
- reviewed producer SHA: `37ed8b361f882abf09f6bdbcedf2ae4e24ca0b23`
- C05A base SHA: `ce0758bf4b94885d1df580a55cef679c6dd4d1eb`
- C05B base SHA: `2b0ae60ca2f61623597abf9cccc75a257e55210f`
- current attempt: 5
- failure signature: fabricated deterministic and calibration dictionaries plus an empty runtime
  dictionary are hash-pinned, evaluated as passing auxiliary evidence, and emit `verdict: "pass"`
- blockers: auxiliary JSON is retained but never validated for schema, provenance, accepted-source
  authority, or run/frame binding; missing runtime measurements default to zero and pass limits
- verification: three immutable reviewer probes passed; focused suite 107 passed; full engine 3858
  passed, 2 skipped; Ruff/frozen/diff/tree green; independent C05C auxiliary probe fails as expected
- next action: bounded C05D auxiliary-evidence authority correction, then re-review; C05 stays
  parked and v5 preserved with no authoritative execution or policy bridge
- external authority: no push, merge, PR, release, protected-branch edit, or branch deletion

The 25 files between the reviewed predecessor and baseline belong to the separately landed
intelligence subsystem. They do not overlap the v6 bench surfaces.
