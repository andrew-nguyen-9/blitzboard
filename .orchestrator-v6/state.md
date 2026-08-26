# v6 orchestration state — production (Claude-owned)

- state: running
- phase: C01 bench + player-value correctness (amended scope)
- branch: `v6/bench-portfolio`
- worktree: `.worktrees/v6-prod` (runtime-local, uncommitted parent location)
- green base SHA: `01f01d3c5f9c00a046edd43707db75ce1426c0e8` (immutable baseline)
- review counterpart: `.worktrees/v6-review` on `v6/bench-portfolio-review` (reviewer-owned; never edited from here)
- current attempt: 2 (C01A — response to C01-codex BLOCK)
- blockers: C01-codex BLOCK (review commit caac6af) — five bench-logic corrections implemented in C01A
- verification: C00 receipts frozen in `.orchestrator-v6/receipts/`; DoD run recorded in `checkpoints/C00-claude.md`
- next action: stop at C01A-claude.md; awaiting independent C01A verdict; no merge, no C02
- external authority: no push, merge, PR, release, protected-branch edit, or branch deletion

Ownership (from wishlist-v6-bench-portfolio.md):
- Claude: production TypeScript, engine behavior, canonical generated artifacts, product docs,
  checkpoint claims, integration.
- Reviewer: adversarial tests, independent gates/experiments, checkpoint verdicts,
  `v6/bench-portfolio-review` branch and its `.orchestrator-v6/`.
