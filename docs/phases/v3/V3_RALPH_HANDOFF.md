# BlitzBoard v3 — Autonomous Build Handoff (paste into a cleared chat)

> Generated from a 32-question requirements pass. Paste everything below the line
> into a fresh Claude Code session in the `blitzboard` repo. It is self-contained.

---

## 0. Session setup (do this first)

1. **Activate Serena** on this project and use its symbolic tools (`find_symbol`,
   `get_symbols_overview`, `find_referencing_symbols`, `replace_symbol_body`) for all
   code navigation/edits instead of reading whole files. Run Serena `onboarding` once.
2. **RTK** is active via hook — shell commands are auto-proxied (`git status` →
   `rtk git status`). Don't fight it. Check `rtk gain` at the end.
2a. **Supabase keys are already provisioned** — `frontend/.env`, `frontend/.env.local`,
   and GitHub Actions secrets all carry `NEXT_PUBLIC_SUPABASE_URL` +
   `SUPABASE_SERVICE_ROLE_KEY` (the daily workflow already consumes them). For local
   pipeline/script runs, source `frontend/.env.local`. Do NOT print, echo, or commit
   secret values. Not a blocker.
3. Read before touching code: `docs/workflow/VERSIONING.md`, `GIT_WORKFLOW.md`,
   `DEFINITION_OF_DONE.md`, `docs/architecture/ARCHITECTURE.md`.
4. **Two reference repos are already cloned locally** as siblings of this repo — read
   them directly with file tools (no `add_repo`, no clone, no network):
   - `../portfolio-website` → source for the hCaptcha/offline form security (Epic 7.3).
     Key files: `middleware.ts`, `app/api/contact/route.ts`, `components/Contact/index.tsx`.
   - `../soundcheck` → source for Privacy + Terms page structure (Epic 14.2).
     Key routes: `app/privacy/`, `app/terms/`.
   If a path is missing when you reach the epic: **skip + log it**, keep moving (see §3).

## 1. Workflow + autonomy (non-negotiable)

- **Phase branch `v3`** off `main`; **one segment sub-branch per epic**. Commit + push
  per segment to the `v3` parent branch. **You are authorized to commit, push, and open
  PRs autonomously** this run. Never work directly on `main`.
- **Order = dependency order** (Phase A→E below). Do not jump ahead past a dependency.
- **Done bar per task = full Definition of Done**: `npm run build` clean, `tsc --noEmit`
  clean, `vitest` green, prefers-reduced-motion honored with static fallback, RLS enabled
  + explicit policies on any new table, no secrets in client bundle, accessibility checks
  pass, pipeline scripts idempotent. UI tasks also get a Playwright/screenshot check.
- **Ponytail discipline**: climb the ladder — reuse what's in `frontend/lib` and
  `components/` before writing new; native platform/CSS over deps; shortest correct diff.
  Mark deliberate shortcuts with `// ponytail:` + upgrade path. Non-trivial logic leaves
  one runnable check (assert demo or `test_*`).

## 2. Build plan (dependency-ordered phases → Ralph segments)

### Phase A — Data + pipeline foundation (unblocks everything)
- **Epic 1 — Pipeline minutes cut** (`.github/workflows/etl_daily.yml`): cache pip +
  nflverse data; gate `history_ingest.py` to **run once then skip when cached** (past
  seasons don't change — re-run only on `workflow_dispatch` or new season); skip steps
  when upstream unchanged. Keep `ubuntu-latest`; win via caching/conditionals, not
  hardware. Do **not** add the 11-season model backtest to daily CI.
- **Epic 3.1 — Publish real snapshot** (kills "No snapshot published yet"): run
  `value_engine_run.py --engine vorp` → `publish_snapshot.py` against **live Supabase**
  (keys already in `frontend/.env.local` + GitHub secrets — source them, don't prompt the
  user); confirm manifest + snapshot read on the players page. Unblocks players/draft/trades.

### Phase B — Auth + security foundation
- Stack = **Supabase Auth** (builds on existing `v2.5` accounts + credential_vault +
  multi_league migrations). Channels = **Email + TOTP authenticator only** (no SMS;
  wire an SMS interface but leave provider unconfigured).
- **Epic 6 — Login page** + header **profile icon** → login route; **forgot-password**
  via email OTP/reset; **2FA = TOTP** opt-in at sign-in.
- **Epic 7 — Signup page** (First, Last, Email, Phone, Password, Confirm); linked from
  login. **Bot defense = replicate portfolio-website hCaptcha + Vercel BotID + rate-limit
  on auth routes.** Crypto model: TLS in transit (have it) + **app-layer envelope-encrypt
  sensitive fields (phone/credentials) client→server**; passwords hashed server-side
  (argon2/bcrypt via Supabase) and **never decrypted, only verified**. Reuse `lib/crypto/`
  + `pipeline/vault.py` patterns.

### Phase C — Pages (build on data + auth)
- **Epic 2 — Homepage**: change `app/page.tsx:108` copy `seven tools` → **`six tools`**
  (match the 6 cards); equal-size cards in a **CSS scroll-snap carousel** (no dep);
  **opaque shared tooltip primitive** (see Epic 3.2); **Rive blueprint background
  animation** (football-play sketches, right-column weighted, reduced-motion static
  fallback) — author a `.riv` scene, mount via existing `RiveInstrument.tsx`.
- **Epic 3.2 — Shared tooltip primitive**: one opaque, theme-aware tooltip reused on the
  deck + `PlayerTable.tsx`; proper enter/leave so it clears on row change even when it
  overlays the next row; meaningful content.
- **Epic 4 — Draft (unauth)**: league-rules editor before draft, **default = superflex
  2QB** (`leagueRules.ts` is superflex-aware), import rules from existing league; **bye
  weeks column** (Epic 4.2) from schedule; **import NFL schedule** (nflverse/Sleeper) so
  byes affect drafting (Epic 4.5); fix **auto-draft freeze** (root-cause it — likely the
  empty-snapshot path from Phase A; verify after A lands); **soft VORP penalty** on K/DEF
  so backups at QB/RB/WR/TE fill first (Epic 4.6); move **Sleeper ID input from Manual →
  Sleeper Live** option (Epic 4.7); **full-analysis section = a full page of real detail**
  (Epic 4.4).
- **Epic 5 — League page → auth-only**: move behind auth middleware; unauth → redirect to
  login with return-to.
- **Epic 8 — Authenticated section**:
  - Leagues (auth): connect **up to 3** leagues via Sleeper + ESPN
    (`sleeperDraft`/`espnDraft`/`LeagueImport.tsx` + `multi_league` tables, RLS per
    `auth.uid()`).
  - Draft (auth): same as unauth minus the Manual/Sleeper-Live/ESPN-Live selector;
    instead a 2–3 league toggle.
  - Waiver (auth): League Selector; RSS toggle all-NFL vs league/team-specific, default to
    free-agents-on-waivers.
  - Trades (auth): League Selector; RSS on right focuses team-specific feeds for teams on
    screen; **trade calculator (multi-select dropdown) above suggested trades**; on submit,
    RSS refocuses to players-in-trade.
  - Settings (auth): change password/email/phone, toggle 2FA, delete account.
- **Epic 9 — Waiver (unauth)**: RSS = all-NFL-players feed.
- **Epic 10 — Trades (unauth)**: trade calculator with player search — **fast in-memory
  client index (trie/fuzzy), bloom pre-filter as labeled nicety** (small N — don't
  over-engineer), position + NFL-team dropdown filters; RSS all-NFL, refocus to
  players-in-trade on submit.
- **Epic 11 — Player page**: flesh out from **existing pipeline data** (weekly logs,
  splits, trends, VORP + Monte Carlo outputs, `Sparkline.tsx`); more stats, no new source.
- **Epic 13 — Header**: a11y → icon, login/signup → **profile icon**, settings → **gear
  icon** (auth only); **remove `auto` theme, default dark, keep light** (`ThemeToggle.tsx`,
  `ThemeScript.tsx`). Icons via lucide-react if present else inline SVG.
- **Epic 14 — Footer**: About page link, **site-pages nav**, **an9.dev nav link**; About
  describes the models (VORP = replacement value; Monte Carlo = simulated seasons) at
  **methodology depth, no unverified accuracy numbers**; Privacy + Terms mirroring
  **Soundcheck** repo structure.

### Phase D — Models (run locally, upload results online)
- **Epic 12.1 — VORP**: backtest 2015–2025; **Epic 12.2 — Monte Carlo (net-new)**:
  simulate **season-long fantasy-point distributions** per player (injury/usage/variance →
  floor/ceiling/boom-bust), validate vs actual 2015–2025. **Run backtests locally**, not in
  daily CI, but **automate the local run to upload results online** (Supabase). Add a
  separate manual-dispatch workflow if helpful; keep daily minutes low.

### Phase E — Polish
- **Epic 15 — SEO**: per-route metadata/OG, dynamic sitemap, robots.txt.
- **Epic 16 — Mobile**: QA + fix every page responsive.
- **Epic 17 — Perf**: Lighthouse pass on key routes; image/font/bundle trims; minimize
  data per page. Practical/measurable, not exhaustive.

## 3. Blocker policy (autonomous)

On a blocker (missing repo, missing key, ambiguous spec, build you can't fix): **mark the
task blocked, log why, move to the next independent task, summarize all blockers in the
final report.** Reference repos (`../portfolio-website`, `../soundcheck`) are local — read
them directly, not a blocker. Only likely blocker: Rive scene authoring (Epic 2). Supabase
keys are NOT a blocker — already provisioned (§0.2a). Don't halt the whole loop.

## 4. Kickoff

1. Generate a PRD from this doc using the `ralph-skills:prd` skill, then convert with
   `ralph-skills:ralph` to `prd.json` (epics → tasks in the Phase A→E order above).
2. Start the loop: **`/ralph-loop:ralph-loop`** pointed at that `prd.json`, with the
   workflow + autonomy + DoD + blocker rules in §1–§3 as the loop's standing constraints.
3. End of run: post a blocker report + `rtk gain` savings.

## 5. Overnight autonomous run

This run is unattended overnight. The two source repos are **already cloned locally** as
siblings of this repo — read them in place, no `add_repo`/clone/network needed:
- `../portfolio-website` — hCaptcha / offline form-security source (Epic 7).
- `../soundcheck` — Privacy + Terms page structure (Epic 14).
If either path is missing, skip+log and continue. With both local, the only remaining
likely blocker is Rive scene authoring (Epic 2). Never halt the loop — work through every
phase, commit/push/PR autonomously, and leave a full report at the end: blockers,
branches + PRs opened, and `rtk gain`.
