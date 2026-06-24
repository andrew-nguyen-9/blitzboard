# Design Direction

> Status: **proposed — confirm before UI build.** Built with the `creative-dev` skill in
> mind (Awwwards-caliber, motion-forward, validated for the artifact/CDN stack).

## The concept: "Broadcast Deck"

**Dark athletic luxury meets a broadcast instrument panel.** A fantasy war room you'd
see on a premium sports broadcast: deep matte black base, one charged accent that the
*league/team sets* (mirroring festival-analyzer's runtime `accent_color`), data presented
like precision instruments — readouts, dials, tickers — not flat dashboard cards.

### Why this, from the inspiration set
- **bastioncycles.com / vostok-europe** → matte premium materials, titanium/instrument
  detailing, technical-luxury restraint. Player cards = machined instrument readouts.
- **redbull / hoverair** → kinetic energy, bold full-bleed motion, velocity. Used on draft
  picks and "trending" surges, not everywhere.
- **GQ "extraordinary lab"** → editorial, cinematic storytelling, generous type scale.
  Homepage + player profiles get the editorial treatment.
- **sportcover / coachsportif** → clean sports-data legibility under the cinematic skin.
- **dribbble dashboard video** → the live, glassy data-panel feel for the draft board.

## Theming: dark / light / system

The "Broadcast Deck" is **dark-native** (that's the signature look), but ships with a full
**dark / light / system** toggle:
- **System** (default) — follows OS via `prefers-color-scheme`.
- **Dark** — the signature broadcast deck (deep matte black, glow accents).
- **Light** — a "daytime broadcast" adaptation: warm off-white/paper base, charcoal ink,
  same accent, glass becomes frosted-white, glows become soft shadows. Same layout, retuned tokens.
- Implemented as **CSS custom properties** swapped by a `data-theme` attribute (no per-component
  branching); accent color stays runtime-derived in both modes. Preference persisted in
  localStorage (a `"use client"` ThemeToggle). Respects `prefers-reduced-motion` independently.

## Visual system (dark tokens shown; light mode retunes the same tokens)

| Token | Direction |
|-------|-----------|
| **Base** | Near-black (`#0A0B0D`), layered charcoal panels, subtle grain/noise · *light:* warm paper (`#F4F2EC`) |
| **Accent** | Runtime-derived per league/team (`accent_color`), e.g. electric volt-green, or team primary |
| **Surfaces** | Frosted glass panels (inherited glassmorphism), thin hairline borders, soft inner glow |
| **Type** | Editorial display serif *or* tight grotesk for headlines; mono for stats/numbers (instrument feel) |
| **Data viz** | Instrument-style: radial dials for value, ridgeline/violin for Monte Carlo distributions, sparkline tickers for trending |
| **Motion** | Framer Motion default; GSAP + ScrollTrigger for homepage scroll story; canvas for the draft "pick" burst |

## Signature moments (where we spend the "wow" budget)
1. **Homepage hero** — cinematic scroll story: the league, the season, the war room. Split-text reveals, parallax, a kinetic accent.
2. **Draft board** — the centerpiece. Live ticker of picks, best-available recomputing with animated reorder (Framer layout animations), value dials updating, a satisfying pick-confirm burst.
3. **Player card** — instrument readout: radial value gauge, distribution curve (boom/bust), trending sparkline, sentiment pulse.
4. **Trending ticker** — broadcast lower-third style scroller blending news sentiment + Sleeper add/drop velocity.

## Motion & accessibility rules
- Respect `prefers-reduced-motion` (inherited convention) — every signature animation has a static fallback.
- Server Components by default; `"use client"` only for the interactive/animated surfaces.
- Fixed free CDN stack per `creative-dev` (GSAP, no paid plugins); validate every technique against the artifact environment before shipping.

## Open design questions
- Confirm "Broadcast Deck" over a lighter/cleaner ESPN-like dashboard.
- Accent model: single league accent, or per-NFL-team theming on player views?
- How heavy is the homepage scroll story vs. getting users into tools fast?
