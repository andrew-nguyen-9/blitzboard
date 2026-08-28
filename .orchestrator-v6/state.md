# v6 orchestration state

- state: deployed_and_verified
- phase: C08 land and deploy PASS; C00–C07 complete
- reviewer branch: `v6/bench-portfolio-review`
- reviewed producer branch: `v6/c06a-roster-legality`
- reviewed producer SHA: `ea706a393d50fbb328131cea5ec532436303e922`
- landed main SHA: `f26a6838ddc83e5780980fb464d67a526d8efdf1`
- rehearsed merge tree: `a888a9fe5b1502e1858d50552bf50cbd15407c2e`
- rehearsal object: `10748fbd1473a2ac1e0ff05acf485cd3b676845f` (unattached; no ref moved)
- C05 disposition: promotion excluded and parked; no fit or confirmation run
- verification: conflict-free three-way tree; engine 3,890 passed/1 skipped; frontend 554 passed/4
  skipped; pipeline 157 passed; full Ruff/build/typecheck/lint passed; C05 authority 127 passed;
  immutable probes 8 passed and byte-identical; generators, secret scan, and portable paths passed;
  final landing diff check passed after the C08 whitespace-only cleanup documented in its checkpoint
- deployment: Vercel production `6149025208`; canonical `https://blitzboard.an9.dev` live and verified
- deterministic blockers: none
- operational remainder: optional release/tag decision, as-shipped archive/brainstorming consolidation,
  and later branch/worktree cleanup after preserving user-owned checkout changes
- next action: preserve v5 authority and keep C05 promotion parked; no promotion inference is authorized
- external result: PR `#113` merged to `main`; production deployed; GitHub homepage corrected to canonical URL

The original checkout remains at `9192163b5be121e645e5574d7e04855725b4895f` with its pre-existing
user-owned changes untouched. See C08 for the final clean-tree and remote-state evidence.
