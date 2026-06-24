# v2 Vision — one page

## What we're building (v2)

The same pipeline-driven NFL fantasy war room, taken from "works for my league, looks
vibe-coded in places" to **a product that feels like a professional team built it** — fast,
accessible, secure, and trustworthy on its numbers. v1 proved the data spine end-to-end
(P0–P7). v2 makes it *good*.

## The five v2 bets

1. **It should feel high-end and effortless.** A real design system (OKLCH tokens,
   locked type, instrument-grade motion via Rive/GSAP) replacing ad-hoc styling — flawless
   on every screen size, accessible by construction, with subtle "how did it know" touches.
   (`docs/design-system/`)
2. **The model should be honest.** Kickers and defenses stop being overvalued; value is
   discounted by predictability; the draft logic is rebuilt and **backtested on 2021–2025**
   so the autodraft stops hoarding K/DEF and starves offense. (`docs/modeling/`)
3. **The data should be effortless to move.** No 500-player ceiling; the whole universe
   ships as a precomputed, CDN-cached, compressed snapshot — instant, paginated,
   virtualized. (`docs/architecture/DATA_TRANSFER.md`)
4. **It should be multi-user and secure.** Google/email accounts, an encrypted vault for
   ESPN/Sleeper credentials, RLS isolation, and a threat model where no network-inspection
   tool can read another user's data. Multi-league per account; import your league's rules.
   (`docs/security/`)
5. **It should welcome everyone, not just me.** All "Andrew-ification" removed; a public
   waivers/trades surface anyone can use; the personal league lives behind auth.

## Guiding constraints (carried from v1, still true)

- **Manual-first, sync-as-accelerator** for drafts (ESPN feed is the most fragile thing).
- **Batch over live** — value + sentiment are precomputed in the pipeline; the frontend
  reads, never computes.
- **Swap, don't rewrite** — the four interfaces (`LeagueRules`/`Projector`/`ValueEngine`/
  `SentimentScorer`) stay; v2 upgrades implementations behind them.
- **Ships with no keys** — builds and renders empty states before any backend exists.
- **Accessibility and performance are acceptance criteria, not afterthoughts.**

## How v2 is sequenced

Foundation → Design/Homepage → Scoring → Player Data → Draft → Auth/Security → Gated+Public
tabs → Hardening. Scoring lands before Players/Draft because everything reads the value
layer; Auth lands before the gated tabs that depend on it. Full map:
`docs/phases/v2/PHASES_OVERVIEW.md`.

## Read next

`docs/decisions/DECISIONS_V2.md` (the why) · `docs/architecture/ARCHITECTURE.md` (the how) ·
`docs/design-system/DESIGN_GUIDELINE.md` (the look) · `docs/workflow/` (how we ship).
