# BlitzBoard v3 — Orchestrator Prompt (thin main session)

> Paste everything below the line into a fresh Claude Code session in the `blitzboard`
> repo. Design: the main session never ingests epic detail — it reads the spec **once** to
> fan out per-epic handoff files, then only launches agents and collects short statuses.
> All verbose work lives in subagent contexts + the handoff files on disk.

---

You are the **orchestrator** for the BlitzBoard v3 build. Keep your own context minimal:
you fan out work to subagents and collect short statuses. Do **not** pull epic detail, file
contents, or build output into this chat — that lives in handoff files and subagent
contexts.

**Setup (once):**
1. Activate Serena on this project; run `onboarding` once. RTK is hook-active (shell
   auto-proxied) — leave it.
2. Read `docs/phases/v3/V3_RALPH_HANDOFF.md` in full **one time**, only to produce the
   artifacts below. After this step, don't re-read it into chat.

**Fan-out (write files, don't echo them):**
3. Generate a PRD with `ralph-skills:prd`, convert with `ralph-skills:ralph` to `prd.json`
   (epics → tasks in Phase A→E order from the doc).
4. For **each epic**, write a self-contained `docs/phases/v3/handoffs/<epic-id>.md`
   containing only what that epic's agent needs: the epic spec, the §1 Definition-of-Done
   bar, §3 blocker policy, branch/commit rules, and local repo pointers
   (`../portfolio-website`, `../soundcheck`). Each file standalone — an agent reads its file
   and nothing else from the spec.
4a. Hold the **dependency map** (below) in this chat — which upstream `.done.md` notes each
   epic needs. You keep only this map + short statuses, never note bodies.

**Loop (this is your steady state):**
5. Run `/ralph-loop:ralph-loop` on `prd.json`. For each task, dispatch a subagent whose
   entire brief is: *"Read `docs/phases/v3/handoffs/<epic-id>.md`. [If the map lists upstream
   deps, also read these outcome notes: `<dep>.done.md` …]. Execute the task; follow its DoD
   + blocker policy. Commit, push, open the PR per §1. **Before returning, write a compressed
   outcome note to `docs/phases/v3/handoffs/<epic-id>.done.md`** — ≤15 lines: what shipped,
   new/changed files, key decisions, gotchas for dependents. Return ONLY: task id, status
   (done/blocked), branch, PR link, ≤2-line note."*
5a. **Carry-forward rule**: when dispatching a dependent epic, append only its upstream
   `.done.md` **paths** (per the map) to the brief — never paste note bodies into this chat;
   the agent reads the files itself. Independent epics get no notes. Polish epics (15–17)
   work off the live repo — inject no notes (attaching every page note would re-flood you).
6. Standing constraints for every agent (§1–§3): phase branch `v3` off `main`, one segment
   sub-branch per epic, autonomous commit/push/PR, never touch `main`; full DoD gate
   (`npm run build`, `tsc --noEmit`, `vitest`, reduced-motion, RLS+policies on new tables,
   no client-bundle secrets, a11y, idempotent pipeline; UI tasks get a Playwright/screenshot
   check); on blocker → mark blocked, log, move to next independent task, never halt the
   loop. Supabase keys are in `frontend/.env.local` + GitHub secrets — source, never
   print/commit.
7. Keep only the short statuses in this chat. If an agent returns verbose output, summarize
   to one line and drop the rest.

## Dependency map (epic → upstream `.done.md` to inject)

Inject only the listed notes; if an upstream epic is blocked/missing its note, proceed and
log it (the agent falls back to discovering prior work from the committed repo via Serena).

| Epic | Inject upstream notes |
|------|-----------------------|
| 1 — pipeline minutes | none |
| 3.1 — publish snapshot | `1` |
| 6 — login | none |
| 7 — signup | `6` (+ read `../portfolio-website`) |
| 3.2 — tooltip primitive | none |
| 2 — homepage | `3.2` |
| 4 — draft (unauth) | `3.1` |
| 5 — league auth-gate | `6`, `7` |
| 9 — waiver (unauth) | `3.1` |
| 10 — trades (unauth) | `3.1` |
| 8 — authenticated section | `3.1`, `6`, `7`, `4`, `9`, `10` |
| 11 — player page | `3.1`, `3.2`, `12` |
| 13 — header | `6`, `7` |
| 12 — models (VORP/MC) | `1`, `3.1` |
| 14 — footer | `12` (+ read `../soundcheck`) |
| 15/16/17 — SEO/mobile/perf | none (work off live repo) |

**End:** post the final report — blockers, branches + PRs opened — and `rtk gain`.

---

## Notes

- **Context discipline is only as good as the agents' returns.** Step 5's "return ONLY …"
  clause is what keeps the main window thin — if an agent ignores it, step 7 is the backstop.
- The `<epic-id>.md` files double as durable checkpoints — if the loop dies overnight, a
  fresh orchestrator re-reads `prd.json` + the handoffs dir and resumes without re-deriving
  anything.
- Full spec lives in `docs/phases/v3/V3_RALPH_HANDOFF.md`; per-epic briefs land in
  `docs/phases/v3/handoffs/`.
