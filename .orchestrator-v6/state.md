# v6 orchestration state

- state: blocked
- phase: C06 independent land gate BLOCK; C05 removed from landing scope, parked, and v5 preserved
- branch: `v6/bench-portfolio-review`
- worktree: runtime-local `.worktrees/v6-review` (uncommitted parent location)
- green base SHA: `01f01d3c5f9c00a046edd43707db75ce1426c0e8`
- reviewed producer SHA: `39563c373265790461e18f388b3c7cd3e31d58d0`
- accepted producer base SHA: `9d71428c8dacabd747d21205296b46d5410de3f3`
- C05A base SHA: `ce0758bf4b94885d1df580a55cef679c6dd4d1eb`
- C05B base SHA: `2b0ae60ca2f61623597abf9cccc75a257e55210f`
- C05C base SHA: `37ed8b361f882abf09f6bdbcedf2ae4e24ca0b23`
- C05D base SHA: `36d395aefb4bb4683e9e8d7186d65c7f6fbbda47`
- current attempt: 8
- failure signature: deterministic shipped-v5 drafts omit required K/DST starters in mandatory
  10/12-team slices; only 6 of 18 sampled league drafts had every roster legal
- blockers: invalid completed rosters; full Ruff has four tracked immutable-probe findings; five
  username-specific paths remain in historical committed records; no browser/external live mock
- verification: independent selection replay matched the committed artifact exactly; 18/18 drafts
  were duplicate-free but only 6/18 fully legal; immutable probes 8 passed; C05 suite 127 passed;
  full engine 3,888 passed and 1 skipped; frontend 553 passed and 4 skipped; pipeline 157 passed;
  frozen diff, bundle-secret audit, artifact parity, diff check, and original-checkout comparison
  passed; required Ruff failed with four findings
- next action: do not land. A separately authorized correction unit must restore required K/DST
  roster legality and resolve land-audit blockers without changing C05 authority.
- external authority: no push, merge, PR, release, protected-branch edit, or branch deletion

The 25 files between the reviewed predecessor and baseline belong to the separately landed
intelligence subsystem. They do not overlap the v6 bench surfaces.
