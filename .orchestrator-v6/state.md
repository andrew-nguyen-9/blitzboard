# v6 orchestration state — production (Claude-owned)

- state: running
- phase: C02 evaluator realism + player-level calibration (amended scope)
- branch: `v6/bench-portfolio`
- worktree: `.worktrees/v6-prod` (runtime-local, uncommitted parent location)
- green base SHA: `01f01d3c5f9c00a046edd43707db75ce1426c0e8` (immutable baseline)
- review counterpart: `.worktrees/v6-review` on `v6/bench-portfolio-review` (reviewer-owned; never edited from here)
- current attempt: 2 (C02A — response to C02-codex BLOCK)
- blockers: C02-codex BLOCK (review commit d50f757) — six corrections implemented in C02A under frozen waiver-realism-v1 manifest
- verification: C00 receipts frozen in `.orchestrator-v6/receipts/`; DoD run recorded in `checkpoints/C00-claude.md`
- next action: stop at C02A-claude.md; awaiting independent C02A verdict; no integration, no C03, no push, no merge
- external authority: no push, merge, PR, release, protected-branch edit, or branch deletion

Ownership (from wishlist-v6-bench-portfolio.md):
- Claude: production TypeScript, engine behavior, canonical generated artifacts, product docs,
  checkpoint claims, integration.
- Reviewer: adversarial tests, independent gates/experiments, checkpoint verdicts,
  `v6/bench-portfolio-review` branch and its `.orchestrator-v6/`.
