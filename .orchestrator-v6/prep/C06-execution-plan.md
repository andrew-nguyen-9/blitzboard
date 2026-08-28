# C06 Independent Land Gate Implementation Plan

> **For agentic workers:** Execute inline in this worktree. The primary process is the sole writer;
> read-only investigators may only report evidence.

**Goal:** Prove whether the land-safe, v5-preserving tree supports reproducible realistic drafts
without reopening C05 promotion.

**Architecture:** Add one small Python harness beside the existing backtest tools. It batches jobs
through `frontend/scripts/draft-eval.mjs` so every pick uses shipped TypeScript v5 behavior, then
uses `simulation.season_eval.evaluate_rosters` and existing roster rules for legality and outcome
metrics. One deterministic JSON artifact carries the complete local and local-browser-equivalent
evidence; no frozen promotion or simulation implementation changes.

**Tech Stack:** Python 3.12 stdlib, existing NumPy/engine evaluator, existing TypeScript draft
bridge, pytest, Ruff.

**Spec:** `wishlist-v6-bench-portfolio.md` plus the authorized C06 contract dated 2026-08-28.

## Global Constraints

- C05 promotion is outside scope; C05 fit and confirmation may not run.
- v5 shipped behavior is production authority; candidate evidence is synthetic/non-authoritative.
- No network dependency, paid service, new account, credential use, or real-league mutation.
- Preserve every frozen path byte-for-byte from `9d71428c8dacabd747d21205296b46d5410de3f3`.
- Use existing fixtures, draft bridge, evaluator, roster rules, and stdlib concurrency only.
- Stop large simulation launches at 9:30 AM CDT and all commands at 1:00 PM CDT.

---

### Task 1: Realism contracts

**Files:**
- Create: `engine/tests/test_draft_realism.py`
- Create: `engine/blitz_engine/backtest/draft_realism.py`

**Interfaces:**
- Consumes: `static_fit.run_bridge`, `season_eval.build_players`,
  `season_eval.evaluate_rosters`, and `fixtures/league_matrix.json`.
- Produces: deterministic job construction, roster validation, team evaluation, honest
  acceptability/winnability classification, and a CLI JSON report.

- [ ] Write failing tests for exact seed replay, derived slots, duplicate/illegal rejection,
  bounded cross-seed variation, degraded metadata, irrational-distribution rejection, and honest
  weak-team classification.
- [ ] Run the focused tests and confirm failures name missing production behavior.
- [ ] Implement only the functions required by those tests.
- [ ] Rerun focused tests and Ruff.

### Task 2: Pilot and evidence run

**Files:**
- Create: `.orchestrator-v6/prep/C06-draft-realism.json`
- Update: `.orchestrator-v6/prep/C06-timebox-log.md`

**Interfaces:**
- Consumes: Task 1 CLI.
- Produces: base/derived seeds, format, seat, teams, ordered roster selections, outcome metrics,
  elapsed time, evaluator identity, resource observations, and synthetic/non-authoritative label.

- [ ] Run a five-draft pilot and record elapsed time/resource headroom.
- [ ] Select the largest safe batch that can finish before 9:30, with at least 100 drafts if the
  pilot permits.
- [ ] Run and deterministically merge the evidence artifact.
- [ ] Verify coverage for front/middle/back, 10/12/14 teams, 1QB/superflex/2QB, bench variation,
  degradation, positional runs/scarcity/late needs, legality, duplication, and seed variation.
- [ ] Complete one local application-flow draft as the live-equivalent fallback.

### Task 3: Producer verification and checkpoint

**Files:**
- Create: `.orchestrator-v6/checkpoints/C06-independent-land-gate.md`
- Update: `.orchestrator-v6/prep/C06-timebox-log.md`

- [ ] Run focused draft tests, required C05 tests/probes, full Ruff, full engine pytest, frontend
  build/typecheck/lint/tests, pipeline pytest, diff check, frozen hashes, path/secrets scans, and
  clean-tree checks.
- [ ] Record exact commands, exits, counts, durations, hashes, limitations, and producer SHA.
- [ ] Commit the coherent producer checkpoint.

### Task 4: Artifact-first independent review

**Files:**
- Create on reviewer branch: `.orchestrator-v6/checkpoints/C06-codex.md`
- Update on reviewer branch: `.orchestrator-v6/state.md`

- [ ] Review the committed producer diff and hashes from the reviewer worktree without relying on
  producer notes.
- [ ] Reproduce focused and complete verification plus frozen/original/ownership/parity checks.
- [ ] Add a reviewer-owned adversarial test only if a disputed boundary cannot be decided from
  existing probes and evidence.
- [ ] Record PASS, BLOCK, or INCONCLUSIVE, commit reviewer records, and prove both trees clean.
