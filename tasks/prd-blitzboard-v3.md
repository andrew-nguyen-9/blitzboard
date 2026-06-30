# PRD: BlitzBoard v3 — Autonomous Build

Generated from the v3 32-question requirements pass (`docs/phases/v3/V3_RALPH_HANDOFF.md`).
Self-contained per-epic specs live in `docs/phases/v3/handoffs/<epic-id>.md`. This PRD is the
ordered task queue; each epic is one Ralph segment (own sub-branch off `v3`, commit/push/PR).

## Introduction

v3 turns BlitzBoard from a data-light shell into a working NFL fantasy war room: real
published snapshot, Supabase Auth, fleshed-out draft/waiver/trades/player pages, VORP + Monte
Carlo models, and SEO/mobile/perf polish. Next.js 15 App Router + Supabase + Python pipeline.

## Goals

- Publish a real player snapshot (kill "No snapshot published yet"); cut daily CI minutes.
- Ship Supabase Auth (email + TOTP), login/signup with bot defense + app-layer field encryption.
- Build/flesh out homepage, draft, waiver, trades, player, header, footer pages.
- Land VORP (backtested 2015–2025) + net-new Monte Carlo season-distribution model.
- SEO, mobile-responsive, and performance polish on key routes.

## Definition of Done (every story)

- [ ] `npm run build` clean, `tsc --noEmit` clean, `vitest` green
- [ ] prefers-reduced-motion honored with static fallback (any animation)
- [ ] RLS enabled + explicit policies on any new table; no secrets in client bundle
- [ ] accessibility checks pass; pipeline scripts idempotent
- [ ] **[UI stories]** Playwright/screenshot check
- [ ] Ponytail: reuse `frontend/lib` + `components/` first; native/CSS over deps; `// ponytail:` on shortcuts

## Build order (dependency-topological)

`1 → 3.1 → 6 → 7 → 3.2 → 2 → 4 → 9 → 10 → 12 → 5 → 8 → 11 → 13 → 14 → 15 → 16 → 17`

---

## User Stories

### US-001: Epic 1 — Pipeline minutes cut
**Description:** As a maintainer, I want the daily ETL workflow to run in fewer minutes so CI stays cheap.
**Depends on:** none
**Acceptance Criteria:**
- [ ] `.github/workflows/etl_daily.yml`: cache pip + nflverse data
- [ ] Gate `history_ingest.py` to run once then skip when cached; re-run only on `workflow_dispatch` or new season
- [ ] Skip steps when upstream unchanged; keep `ubuntu-latest` (win via caching/conditionals, not hardware)
- [ ] Do NOT add the 11-season model backtest to daily CI
- [ ] Workflow idempotent; DoD met

### US-002: Epic 3.1 — Publish real snapshot
**Description:** As a user, I want the players page to show a real published snapshot, not the empty state.
**Depends on:** 1
**Acceptance Criteria:**
- [ ] Run `value_engine_run.py --engine vorp` → `publish_snapshot.py` against live Supabase (source `frontend/.env.local`, never print/commit keys)
- [ ] Manifest + snapshot read confirmed on the players page (screenshot)
- [ ] Unblocks players/draft/trades; DoD met

### US-003: Epic 6 — Login page
**Description:** As a user, I want to log in via Supabase Auth with forgot-password and optional TOTP 2FA.
**Depends on:** none
**Acceptance Criteria:**
- [ ] Login route; header **profile icon** → login route
- [ ] Forgot-password via email OTP/reset
- [ ] 2FA = TOTP opt-in at sign-in (no SMS; wire SMS interface but leave provider unconfigured)
- [ ] Builds on existing v2.5 accounts/credential_vault/multi_league migrations
- [ ] DoD met; Playwright check

### US-004: Epic 7 — Signup page
**Description:** As a new user, I want to sign up with bot defense and encrypted sensitive fields.
**Depends on:** 6
**Acceptance Criteria:**
- [ ] Signup page (First, Last, Email, Phone, Password, Confirm); linked from login
- [ ] Bot defense = replicate `../portfolio-website` hCaptcha + Vercel BotID + rate-limit on auth routes
- [ ] App-layer envelope-encrypt sensitive fields (phone/credentials) client→server; reuse `lib/crypto/` + `pipeline/vault.py`
- [ ] Passwords hashed server-side (argon2/bcrypt via Supabase), never decrypted, only verified
- [ ] DoD met; Playwright check

### US-005: Epic 3.2 — Shared tooltip primitive
**Description:** As a user, I want one consistent opaque tooltip across the deck and player table.
**Depends on:** none
**Acceptance Criteria:**
- [ ] One opaque, theme-aware tooltip reused on the deck + `PlayerTable.tsx`
- [ ] Proper enter/leave: clears on row change even when overlaying the next row
- [ ] Meaningful content; DoD met; Playwright check

### US-006: Epic 2 — Homepage
**Description:** As a visitor, I want a polished homepage with correct copy, a card carousel, tooltips, and a Rive background.
**Depends on:** 3.2
**Acceptance Criteria:**
- [ ] `app/page.tsx:108` copy `seven tools` → `six tools` (match 6 cards)
- [ ] Equal-size cards in a CSS scroll-snap carousel (no dep)
- [ ] Opaque shared tooltip primitive (Epic 3.2)
- [ ] Rive blueprint background animation (football-play sketches, right-column weighted, reduced-motion static fallback); author a `.riv`, mount via existing `RiveInstrument.tsx` — if Rive authoring blocked, ship static fallback + log
- [ ] DoD met; Playwright check

### US-007: Epic 4 — Draft (unauth)
**Description:** As a drafter, I want a league-rules editor, bye weeks, schedule import, and fixed auto-draft.
**Depends on:** 3.1
**Acceptance Criteria:**
- [ ] League-rules editor before draft, default = superflex 2QB (`leagueRules.ts` superflex-aware); import rules from existing league
- [ ] Bye weeks column (4.2) from schedule; import NFL schedule nflverse/Sleeper so byes affect drafting (4.5)
- [ ] Fix auto-draft freeze — root-cause (likely empty-snapshot path from Phase A; verify after A lands)
- [ ] Soft VORP penalty on K/DEF so QB/RB/WR/TE backups fill first (4.6)
- [ ] Move Sleeper ID input from Manual → Sleeper Live option (4.7)
- [ ] Full-analysis section = a full page of real detail (4.4)
- [ ] DoD met; Playwright check

### US-008: Epic 9 — Waiver (unauth)
**Description:** As a visitor, I want a waiver page with an all-NFL-players RSS feed.
**Depends on:** 3.1
**Acceptance Criteria:**
- [ ] RSS = all-NFL-players feed
- [ ] DoD met; Playwright check

### US-009: Epic 10 — Trades (unauth)
**Description:** As a visitor, I want a trade calculator with fast player search and RSS.
**Depends on:** 3.1
**Acceptance Criteria:**
- [ ] Trade calculator with player search — fast in-memory client index (trie/fuzzy), bloom pre-filter as labeled nicety (small N, don't over-engineer)
- [ ] Position + NFL-team dropdown filters
- [ ] RSS all-NFL, refocus to players-in-trade on submit
- [ ] DoD met; Playwright check

### US-010: Epic 12 — Models (VORP + Monte Carlo)
**Description:** As an analyst, I want a backtested VORP model and a net-new Monte Carlo season-distribution model, run locally and uploaded online.
**Depends on:** 1, 3.1
**Acceptance Criteria:**
- [ ] 12.1 VORP: backtest 2015–2025
- [ ] 12.2 Monte Carlo (net-new): simulate season-long fantasy-point distributions per player (injury/usage/variance → floor/ceiling/boom-bust), validate vs actual 2015–2025
- [ ] Run backtests locally (not daily CI); automate local run to upload results to Supabase; optional separate manual-dispatch workflow; keep daily minutes low
- [ ] DoD met; idempotent upload

### US-011: Epic 5 — League page → auth-only
**Description:** As a user, I want the league page gated behind auth with return-to redirect.
**Depends on:** 6, 7
**Acceptance Criteria:**
- [ ] Move league page behind auth middleware; unauth → redirect to login with return-to
- [ ] DoD met; Playwright check

### US-012: Epic 8 — Authenticated section
**Description:** As an authenticated user, I want leagues/draft/waiver/trades/settings tailored to my connected leagues.
**Depends on:** 3.1, 6, 7, 4, 9, 10
**Acceptance Criteria:**
- [ ] Leagues (auth): connect up to 3 leagues via Sleeper + ESPN (`sleeperDraft`/`espnDraft`/`LeagueImport.tsx` + `multi_league` tables, RLS per `auth.uid()`)
- [ ] Draft (auth): same as unauth minus Manual/Sleeper-Live/ESPN-Live selector; instead a 2–3 league toggle
- [ ] Waiver (auth): League Selector; RSS toggle all-NFL vs league/team-specific, default free-agents-on-waivers
- [ ] Trades (auth): League Selector; RSS focuses team-specific feeds for on-screen teams; trade calculator (multi-select dropdown) above suggested trades; on submit RSS refocuses to players-in-trade
- [ ] Settings (auth): change password/email/phone, toggle 2FA, delete account
- [ ] RLS + policies on new tables; DoD met; Playwright check

### US-013: Epic 11 — Player page
**Description:** As a user, I want a fleshed-out player page from existing pipeline data.
**Depends on:** 3.1, 3.2, 12
**Acceptance Criteria:**
- [ ] Flesh out from existing pipeline data (weekly logs, splits, trends, VORP + Monte Carlo outputs, `Sparkline.tsx`)
- [ ] More stats, no new data source
- [ ] DoD met; Playwright check

### US-014: Epic 13 — Header
**Description:** As a user, I want an icon-based header with theme defaulting to dark.
**Depends on:** 6, 7
**Acceptance Criteria:**
- [ ] a11y → icon; login/signup → profile icon; settings → gear icon (auth only)
- [ ] Remove `auto` theme, default dark, keep light (`ThemeToggle.tsx`, `ThemeScript.tsx`)
- [ ] Icons via lucide-react if present else inline SVG
- [ ] DoD met; Playwright check

### US-015: Epic 14 — Footer
**Description:** As a user, I want a footer with About/Privacy/Terms and site nav.
**Depends on:** 12
**Acceptance Criteria:**
- [ ] About page link, site-pages nav, an9.dev nav link
- [ ] About describes models (VORP = replacement value; Monte Carlo = simulated seasons) at methodology depth, no unverified accuracy numbers
- [ ] Privacy + Terms mirroring `../soundcheck` structure (`app/privacy/`, `app/terms/`)
- [ ] DoD met; Playwright check

### US-016: Epic 15 — SEO
**Description:** As a maintainer, I want per-route SEO metadata, sitemap, and robots.
**Depends on:** none
**Acceptance Criteria:**
- [ ] Per-route metadata/OG, dynamic sitemap, robots.txt
- [ ] DoD met

### US-017: Epic 16 — Mobile
**Description:** As a mobile user, I want every page responsive.
**Depends on:** none
**Acceptance Criteria:**
- [ ] QA + fix every page responsive (Playwright across viewports)
- [ ] DoD met

### US-018: Epic 17 — Perf
**Description:** As a user, I want fast key routes.
**Depends on:** none
**Acceptance Criteria:**
- [ ] Lighthouse pass on key routes; image/font/bundle trims; minimize data per page
- [ ] Practical/measurable, not exhaustive; DoD met

## Non-Goals

- No SMS 2FA provider configured (interface only).
- No 11-season model backtest in daily CI (local + manual-dispatch only).
- No new player data sources for the player page (existing pipeline data only).
- No bloom/over-engineered search for small-N trade calculator beyond a labeled nicety.
- No unverified model accuracy numbers in About copy.

## Technical Considerations

- Phase branch `v3` off `main`; one segment sub-branch per epic; commit/push/PR autonomously; never touch `main`.
- Supabase keys in `frontend/.env.local` + GitHub secrets — source, never print/commit.
- Reference repos local siblings: `../portfolio-website` (Epic 7 bot defense), `../soundcheck` (Epic 14 privacy/terms).
- Reuse `frontend/lib/queries.ts`, `leagueRules.ts`, `lib/crypto/`, `RiveInstrument.tsx`, `PlayerTable.tsx`, `Sparkline.tsx`, `ThemeToggle.tsx`.

## Open Questions

- Rive scene authoring (Epic 2) is the only likely hard blocker → static fallback + log if blocked.
