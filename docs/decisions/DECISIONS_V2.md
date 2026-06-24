# Locked Decisions — v2

Extends the v1 record (`docs/archive/v1/DECISIONS.md`, D1–D9), which remains in force except
where superseded here. ADR-style: decision + why.

---

### D10 — Versioned phase/segment/task workflow
`v[phase].[segment].[task]`. Phase = branch, segment = sub-branch (build→test→QA→/code-review
→commit→push to parent), phase finish = the 8-step ritual (QA→review→commit→merge→delete→doc
review→archive→brainstorm). See `docs/workflow/`.
**Why:** the project lacked structure; this mirrors how disciplined teams ship and makes every
unit of work addressable, reviewable, and reversible.

---

### D11 — v1 is frozen as v1.0.0; v2.0.0 starts fresh
All P0–P7 work archived under `docs/archive/v1/`, untouched. New structured docs supersede it.
**Why:** a clean baseline without losing the "why"; v1 history stays readable.

---

### D12 — Auth.js (NextAuth) + Supabase Postgres (supersedes D4's "no auth in v1")
Google OAuth + email/password via Auth.js; data + RLS on Supabase. Encrypted credential vault
for ESPN/Sleeper. **Supersedes D4** ("one ESPN league, no auth") — v2 is genuinely multi-user.
**Why:** v2's gated tabs, saved credentials, and multi-league require real accounts; Auth.js
gives finer session control while keeping the Supabase data layer we already run.

---

### D13 — Predictability-discounted VORP; streamer-level K/DEF replacement
Value discounted by a per-player predictability score; K/DEF replacement set at weekly
streamer level. Bounded league-specific signal (distance-K, yardage-D/ST) retained.
**Why:** K/DEF are over-valued because v1 ranks on point total without penalizing low
predictability and free waiver availability. (`docs/modeling/SCORING.md`)

---

### D14 — Draft policy = starting-lineup marginal value + explicit bench-upside model
Replace "best available by VORP" with marginal-to-optimal-lineup value + a bench model
(upside/handcuff/cover) + a K/DEF cap, **backtested on 2021–2025**.
**Why:** v1 autodraft hoards K/DEF and builds weak benches; the bench is where leagues are won.
(`docs/modeling/DRAFT_LOGIC.md`)

---

### D15 — Player data shipped as precomputed, CDN-cached, compressed snapshots
The daily-static, read-only value layer is published per `(profile×engine)` as immutable,
content-hashed, brotli-compressed columnar blobs; the client virtualizes + sorts/filters
locally; detail is lazy + prefetched. **Supersedes** the v1 row-API path that capped at ~500.
**Why:** the data is identical per profile and changes once/day — a static artifact + CDN is
faster and cheaper than paginating a row API, and removes the cap. (`docs/architecture/DATA_TRANSFER.md`)

---

### D16 — Design system "Broadcast Instrument": OKLCH tokens + Rive-led motion
Locked type stack, OKLCH light/dark tokens, Rive for interactive instrument motion + GSAP/
Lenis/SplitText for the homepage story; mobile-excellent, accessible by construction.
**Why:** validated by a teardown of 12 premium sites (`mocks/v2-research/findings.md`); Rive
appeared on 7/9 and is GPU-cheap + Next-compatible; OKLCH keeps light/dark perceptually matched.
(`docs/design-system/`)

---

### D17 — Two-plane access: public vs. authenticated
Public plane (anon, RLS public-read + snapshots): Home, Players, generic Waivers/Trades.
Auth plane (Auth.js session, per-user RLS): My League, my Waivers, my Trades, Draft-with-
my-rules, credential vault. **Supersedes** v1's single-plane anon-read model.
**Why:** league/waivers/trades must be private to the connected user; a generic public surface
still lets anyone try trending + the trade tester. (Requirements #5, #6)

---

### D18 — Remove all "Andrew-ification"
No personal names, personal league branding, or "my league" framing in the product UI;
"Smores 2025" becomes a seed/example, not a hardcoded identity. The personal league lives
behind auth like any other user's.
**Why:** v2 is a product for anyone, not a personal tool. (Requirement #8)

---

### D19 — Accessibility + performance are acceptance criteria
WCAG 2.2 AA baseline, in-app a11y controls (text size, reduced motion, colorblind, high
contrast), and per-segment perf budgets (LCP ≤2.5s, CLS ≤0.05, Lighthouse ≥95) gate "done."
**Why:** "high-end and effortless" is unachievable if it's slow or excludes users; bolting
these on later never works. (`docs/workflow/DEFINITION_OF_DONE.md`, `design-system/ACCESSIBILITY.md`)

---

## Still open (revisit during the relevant phase)

- Exact wire format for snapshots: columnar/typed-array vs. minified-JSON-first (decide in v2.3
  against the 60KB budget).
- Argon2id vs bcrypt by runtime support (decide in v2.5).
- Predictability `f(ρ)` shape + streamer percentile (tuned by v2.2/v2.4 backtest).
- Per-team accent theming on player views vs. single league accent (decide in v2.1).
