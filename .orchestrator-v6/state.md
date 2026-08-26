# v6 orchestration state — production (Claude-owned)

- state: running
- phase: C00A correction (post-BLOCK)
- branch: `v6/bench-portfolio`
- worktree: `.worktrees/v6-prod` (runtime-local, uncommitted parent location)
- green base SHA: `01f01d3c5f9c00a046edd43707db75ce1426c0e8` (immutable baseline)
- review counterpart: `.worktrees/v6-review` on `v6/bench-portfolio-review` (reviewer-owned; never edited from here)
- current attempt: 2
- blockers: none open on Claude side; C00 BLOCK corrections applied (see checkpoints/C00A-claude.md) — awaiting re-review
- verification: C00 receipts frozen in `.orchestrator-v6/receipts/`; DoD run recorded in `checkpoints/C00-claude.md`
- next action: await independent C00 verdict; C01 implementation only after PASS
- external authority: no push, merge, PR, release, protected-branch edit, or branch deletion

Ownership (from wishlist-v6-bench-portfolio.md):
- Claude: production TypeScript, engine behavior, canonical generated artifacts, product docs,
  checkpoint claims, integration.
- Reviewer: adversarial tests, independent gates/experiments, checkpoint verdicts,
  `v6/bench-portfolio-review` branch and its `.orchestrator-v6/`.
