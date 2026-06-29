# Finish v2 — execution script (v2.2 → v2.7)

A self-contained driver to take the v2 line from **v2.1.0 (shipped)** to the **v2 launch**.
Every phase below already has a detailed plan (`docs/phases/v2/v2.<p>-*.md`); this file is the
**order of operations + the decisions**, so a session can run a phase end-to-end without
stopping to ask. Open questions are not asked here — each is given a **default to proceed**
and is **deferred to the phase that owns it** (see the Deferred-decisions register at the end).

Authoritative process: `docs/workflow/{GIT_WORKFLOW,VERSIONING,DEFINITION_OF_DONE}.md`.
Versioning is `v[phase].[segment].[task]`. Phase order is dependency-driven (`PHASES_OVERVIEW.md`):

```
v2.2 scoring → v2.3 player-data → v2.4 draft → v2.5 auth/security → v2.6 gated/public tabs → v2.7 launch
```

Do **not** reorder: scoring feeds players + draft + trades; data feeds draft; auth precedes the
gated tabs; v2.7 only verifies what the earlier phases built.

---

## The loop (run this for every phase)

### 0. Open the phase
```bash
git switch main && git pull --ff-only
git switch -c v2.<p>                 # phase branch, e.g. v2.2
git push -u origin v2.<p>
```
Read `docs/phases/v2/v2.<p>-*.md` and the spec it points at (modeling/security docs).

### 1. Work each segment (inner loop) — for every `v2.<p>.<s>`
```bash
git switch v2.<p> && git pull --ff-only
git switch -c v2.<p>-<slug>          # e.g. v2.2-predictability
# implement tasks v2.<p>.<s>.1..N — one task ≈ one focused commit:
#   git commit -m "v2.<p>.<s>.<t> <scope>: <summary>"   (NO AI attribution)
```
Then the gates (all must pass before the PR):
```bash
cd frontend
npm run build && npx tsc --noEmit && npm test          # + pipeline selftest where touched
cd ..
# QA vs the segment's acceptance + the cross-cutting DEFINITION_OF_DONE checklist:
#   responsive 360/768/1280/1920 · reduced-motion (OS + in-app) · axe light+dark ·
#   keyboard+focus · themes · empty/loading/error w/o keys · RLS on new tables ·
#   no secrets in client bundle · no clipped numerals · CLS≈0
# Browser QA with chrome-devtools/playwright where there's UI; Lighthouse where there's a route.
```
```bash
/code-review            # on the segment diff; resolve findings, re-verify
gh pr create --base v2.<p> --head v2.<p>-<slug> \
  --title "v2.<p>.<s> <scope>: <summary>" \
  --body-file <filled .github/PULL_REQUEST_TEMPLATE.md>
# wait for CI green (build·typecheck·lint, no-personal-identity, axe smoke), then:
gh pr merge <#> --merge --delete-branch
git fetch origin --prune
```
Repeat for every segment. The phase branch always reflects "everything done so far."

### 2. Finish the phase (the 8-step ritual — `GIT_WORKFLOW.md`)
1. **QA** the whole phase (every acceptance, mobile+desktop, light/dark, reduced-motion, keyboard).
2. **`/code-review`** the whole-phase diff (`main...v2.<p>`); resolve everything.
3. **Close-out commit** on `v2.<p>`: archive the phase plan to `docs/archive/v2/` with an
   **"As shipped"** delta, flip `PHASES_OVERVIEW.md` status to **Shipped (v2.<p>.0)** + repoint
   its link to the archive, and write `docs/brainstorming/v2.<p>-ideas.md`. Fix any doc drift.
4. **Merge to main**: `gh pr create --base main --head v2.<p>` → CI green → `gh pr merge --merge`.
5. **Tag + Release**: `git tag -a v2.<p>.0 -m "..." && git push origin v2.<p>.0` → `gh release create v2.<p>.0`.
6. **Delete branches** (phase + any stragglers, local + remote).
7. Confirm `main` tip is the merge, tag points at it, only `main` remains.
8. Stop and report. (`v2.1` is the worked example of all of the above — PRs #8–#11, tag v2.1.0.)

> **Reference template:** the entire v2.1 phase (hero/bands/perf + finish) is the canonical
> example of this loop. Mirror its commit style, PR bodies, QA evidence, and archival.

---

## Per-phase script

Each line is a segment → its sub-branch; build it in task order. Acceptance is in the phase doc.
**Decisions** are the defaults to proceed with now; **Defer** marks what is intentionally not
asked and where it gets resolved.

### v2.2 — Scoring & Value-Engine (`v2.2`) · spec `docs/modeling/{SCORING,VALUE_ENGINE}.md`
- `v2.2-predictability` — add `ρ∈[0,1]` to the Projector; persist to `player_value`; expose in queries.
- `v2.2-vorp` — `adj_value = replacement + raw_VORP·f(ρ)`; K/DEF replacement = weekly-streamer percentile; bounded league signal.
- `v2.2-mc` — predictability-aware Monte-Carlo distributions; reliability/calibration check.
- `v2.2-ui` — `PredictabilityMeter` into the player card; engine-toggle viz morph.
- **Decisions:** ship `f(ρ)` and exponent `k` as a **config constant with a sane default**
  (monotone-decreasing discount, e.g. `f(ρ)=ρ^k`, `k≈1`); K/DEF replacement = **top-streamer
  (waiver-available) weekly percentile**; predictability = blend of YoY positional-rank
  stability + own variance + TD/turnover share, **shrunk toward the positional prior** for
  low-sample players.
- **Defer:** final numeric tuning of `k`/weights/percentile → **v2.4.3** (backtest is the gate).
  Do not hand-tune to taste in v2.2; just make them configurable and unit-tested for monotonicity.

### v2.3 — Player Data Layer & Players tab (`v2.3`) · spec `docs/architecture/DATA_TRANSFER.md`
- `v2.3-snapshot` — `pipeline/publish_snapshot.py` (brotli, content-hashed, CDN, immutable cache) + `manifest.json`; wire format vs 60KB.
- `v2.3-client` — fetch manifest→snapshot→in-memory table; virtualized rows; local sort/filter/search; remove the 500 cap + keyset helper.
- `v2.3-ui` — rebuild `PlayerTable` on `StatTable` + virtualization; instant filters; lazy detail + intent prefetch; instrument player card.
- **Decisions:** wire format = **minified-JSON + brotli first** (the doc's stated fallback);
  only go columnar/typed-array if the 60KB budget is missed. Virtualization = **`@tanstack/react-virtual`**.
  Snapshot storage/CDN = **Supabase Storage** (already in the stack) with immutable cache headers.
  Reuse the v2.1 intent-prefetch (`usePrefetchOnIntent`) for the detail route — **no over-fetch on touch**.
- **Defer:** columnar upgrade → within v2.3 only if budget fails (don't pre-optimize).

### v2.4 — Draft Logic + Backtesting 2021–2025 (`v2.4`) · spec `docs/modeling/DRAFT_LOGIC.md`
- `v2.4-harness` — 2021–2025 actuals under league rules; deterministic 12-team superflex sim; weekly-optimal-lineup evaluation w/ CIs.
- `v2.4-policy` — `marginal_starter_value`; bench-upside model; K/DEF cap + positional caps + superflex QB-run model.
- `v2.4-tune` — tune `f(ρ)`/bench weights/scarcity on the backtest; ablations; `docs/modeling/backtest-report.md`.
- `v2.4-boards` — manual + synced boards consume the **shared** policy (parity, D7); UI surfaces the *why*.
- **Decisions:** ADP pool from a **free/redistributable source** (nflverse/derived), **sensitivity-tested**;
  tuning = **grid search first**, Bayesian only if grid is insufficient; **hold out the latest
  season (2025) for validation**; report **CIs, not point wins**; prefer simple explainable terms.
- **Defer:** none that needs the user — this is where v2.2's tunables get **finalized**.

### v2.5 — Auth, Accounts & Security (`v2.5`) · spec `docs/security/{SECURITY,MULTI_LEAGUE}.md`
- `v2.5-auth` — Auth.js (Google OAuth + email/password), httpOnly/Secure/SameSite cookies; Argon2id hashing; reset + verify; `accounts` + prefs.
- `v2.5-rls` — RLS on every user table keyed to `auth.uid()`; A-vs-B isolation test; service-role key absent from client.
- `v2.5-vault` — `credential_vault` AES-256-GCM envelope encryption; write-once server action; transient server-side decrypt for the pipeline; disconnect = hard delete.
- `v2.5-leagues` — `user_leagues` + multi-tenant `league_rules`; league switcher; Sleeper/ESPN import → confirm/edit screen; manual editor fallback.
- `v2.5-headers` — HSTS/CSP/secure headers, CSRF, zod on server boundaries, rate limits.
- **Decisions:** stack is **already specified** (Auth.js on Supabase Postgres, Argon2id) — build to it.
  Encryption **master key = server-only env var** with documented rotation (KMS-upgrade-ready).
  Transactional email (verify/reset) via **Resend** (Vercel-native) — code against an adapter so
  the provider is swappable. RLS is the **source of truth** for isolation (never app-checks alone).
- **Defer (secrets/provider — needs the user, but does NOT block design):**
  - **Google OAuth client id/secret** → user provisions into env at v2.5 setup; until then,
    email/password path is fully testable.
  - **Email provider account + sending domain** → default Resend; **confirm provider/domain in v2.5**;
    stub the email transport behind `lib/email.ts` so flows are testable without a live key.
  - **Production master key / move to managed KMS** → env var now; managed-KMS decision → **v2.7** hardening.

### v2.6 — Gated + Public League/Waivers/Trades (`v2.6`) · spec `DECISIONS_V2.md` D17
- `v2.6-gate` — route guards (`/league`, auth `/waivers`/`/trades` need session + connected league); helpful connect/login prompts (never a dead end); reconnect on expired creds.
- `v2.6-private` — league Overview/Waivers(FAAB)/Trades tailored to the active league's rules; RLS-isolated.
- `v2.6-public` — public trending Waivers + public Trade tester from the anon snapshot; non-naggy upsell to connect.
- **Decisions:** public surfaces read **only the anon snapshot** (the v2.3 public payload) — the
  private/public data boundary gets its **own code-review + RLS test**. Public trade tester uses
  the **example superflex half-PPR profile** as the default generic scoring profile.
- **Defer:** none needing the user.

### v2.7 — Optimization & Launch hardening (`v2.7`) · spec `SECURITY.md` (verify) + budgets
- `v2.7-perf` — site-wide bundle/code-split/image-font audit; Lighthouse ≥95 (Perf/A11y/Best-Practices) on Home, Players, Draft, public Waivers/Trades; DB/query audit (no N+1, indexes, keyset everywhere).
- `v2.7-sec` — **Go/No-Go**: RLS A-vs-B across all user tables; bundle-secret + header + TLS/HSTS scans; auth/vault audit (session fixation, CSRF, OAuth state/nonce, logout, rate limits); inspector-isolation proof.
- `v2.7-a11y` — full axe + manual SR (VoiceOver/NVDA), keyboard-only, 200% zoom, every a11y mode; real-device matrix.
- `v2.7-launch` — error monitoring/logging (no PII/secrets), uptime, rollback plan, env/secret audit; final docs/README/VISION "as shipped".
- **Decisions:** error monitoring = **Sentry** (PII/secret scrubbing on); apply the v2.1 perf
  playbook (per-route split, font preload trimming, static LCP) to every key route; carry the
  RLS + inspector-isolation tests from v2.5 (verify here, don't first-discover).
- **Defer (needs the user at launch — does NOT block the work):**
  - **Production domain** → `blitzboard.an9.dev` (set as `metadataBase` in the v2.8 rebrand).
  - **Sentry/monitoring account** → user provisions DSN into env at **v2.7.4**; code against the
    SDK now so it's a config flip.

### v2 release (end of v2.7)
Per `v2.7-*` DoD: finish v2.7 → tag `v2.7.0` → the v2 line is shipped → final doc consolidation
+ `docs/brainstorming/v2.7-ideas.md` **and a v2 retrospective**.

---

## Deferred-decisions register

Nothing here is asked now; each has a default so execution proceeds, and a phase that owns the
real call. Surface these to the user **at the named phase**, not before.

| # | Decision | Default to proceed | Resolved in | Needs user? |
|---|----------|--------------------|-------------|-------------|
| 1 | `f(ρ)` discount form + exponent `k` | configurable `ρ^k`, `k≈1` | **v2.4.3** (backtest) | no |
| 2 | K/DEF replacement percentile | weekly top-streamer (waiver-available) | tuned v2.4.3 | no |
| 3 | Predictability weights | YoY-stability + variance + TD/TO, prior-shrunk | calibrated v2.2.3 | no |
| 4 | Snapshot wire format | minified-JSON + brotli (columnar only if >60KB) | v2.3.1 | no |
| 5 | Virtualization lib | `@tanstack/react-virtual` | v2.3.2 | no |
| 6 | Snapshot storage/CDN | Supabase Storage + immutable cache | v2.3.1 | no |
| 7 | ADP source + tuning method | free/derived ADP, grid-first, hold out 2025 | v2.4 | no |
| 8 | Email (verify/reset) provider + domain | Resend, behind `lib/email.ts` adapter | **v2.5.1** | **yes (provider/domain + key)** |
| 9 | Google OAuth credentials | email/password testable without them | **v2.5.1** setup | **yes (secret)** |
| 10 | Encryption master key / KMS | server env var now; managed-KMS later | v2.5.3 / hardened v2.7 | **yes (secret)** |
| 11 | Public generic scoring profile | example superflex half-PPR | v2.6.3 | no |
| 12 | Error-monitoring provider | Sentry (scrubbed) | **v2.7.4** | **yes (DSN)** |
| 13 | Production domain | `blitzboard.an9.dev` (resolved, v2.8 rebrand) | **v2.7.4** launch | resolved |

**Rule:** for the "needs user" rows, build to the default + adapter, keep the secret/provider out
of the repo, and prompt the user **only** when that phase reaches the step — never block earlier
phases on them.

---

## Carry-forwards already on the books (fold in opportunistically)
From `docs/brainstorming/v2.0-ideas.md` + `v2.1-ideas.md`: finish the legacy-alias migration
(v2.3 touches `PlayerTable`; v2.6 touches league/waivers/trades), flip the axe-smoke CI job to a
blocking gate, add required status checks to branch protection, the **Nav** XL-overflow +
touch-prefetch fixes, route-scope Lenis + the GSAP scroll-story, and a bespoke homepage Rive
instrument. Address each in whichever phase already opens that file.
