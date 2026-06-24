# v2 Design Guideline — "Broadcast Instrument"

> Supersedes v1 `docs/archive/v1/DESIGN.md`. Grounded in a teardown of 12 reference sites
> (`mocks/v2-research/findings.md`). This is the contract every UI segment is reviewed
> against.

## The concept

**A premium sports broadcast's instrument panel.** Dark-native athletic luxury: a
disciplined base (near-black *or* warm paper), exactly one charged accent, and data
rendered like precision instruments — dials, ridgelines, tickers — not flat cards. It must
feel *fast and effortless first*, cinematic second. Motion serves comprehension; it never
taxes usability.

The research validated this register: every high-end reference paired an **oversized
display face** with **mono labels** over a **single-pole base + one accent**, animated with
a small consensus toolkit (Rive, GSAP/ScrollTrigger, Lenis, SplitText). v2 adopts that
toolkit deliberately.

## Four principles

1. **Effortless beats impressive.** The fastest path to the answer wins. Anticipate the
   next action (prefetch the player the cursor is heading toward, preselect the likely
   filter, keep the draft "best available" one glance away). Never make motion a tax on
   speed.
2. **Instrument, don't decorate.** Numbers are the product. Mono numerals, aligned
   columns, dials/ridgelines that *mean* something. No ornament that doesn't carry data.
3. **One base, one accent, infinite restraint.** Color is rationed. The accent marks
   value/action/trend — never "because it looked empty."
4. **Accessible by construction.** Every signal has a non-color encoding; every motion has
   a still; every control is reachable by keyboard. (See `ACCESSIBILITY.md`.)

## Visual system (tokens defined in `TOKENS.md`)

| Token group | Direction |
|-------------|-----------|
| **Base** | Dark: near-black `oklch(0.16 0.01 250)` layered charcoals + subtle grain. Light ("daytime broadcast"): warm paper `oklch(0.96 0.01 90)`, charcoal ink. |
| **Accent** | One charged hue, runtime-derived per league/team (`accent_color`), defined in OKLCH so light/dark stay perceptually matched. Default: electric volt. |
| **Surfaces** | Frosted-glass panels, hairline borders, soft inner glow (dark) / soft shadow (light). No hard 1px box seams. |
| **Type** | Display: condensed athletic grotesk (scoreboard) + an editorial serif for hero/story moments. Mono for **all** numerals, stats, and labels. Neutral grotesk for body. (See `TOKENS.md` for the locked stack.) |
| **Data viz** | Radial dial = value/VORP; ridgeline/violin = Monte Carlo distribution (boom/bust); sparkline ticker = trending; tier bands; predictability meter for K/DEF. |
| **Motion** | Rive for interactive instrument states; GSAP+ScrollTrigger for the homepage story; Lenis momentum scroll; SplitText for hero reveals. All reduced-motion-aware. (`MOTION.md`) |

## Responsive — works *very well* at every size

Not "mobile-friendly" — **mobile-excellent**. Design mobile-first, enhance up.

- **Fluid everything**: type via `clamp()`, space via a fluid scale, grids via
  `minmax()`/`auto-fit`. No fixed pixel layouts that break between breakpoints.
- **No clipped cells** (a named v1 homepage bug): numeric cells use `tabular-nums`, fixed
  min-column widths, and `clamp()` font sizing so digits always fit. Tables become stacked
  "stat rows" under 640px, never horizontal-scroll-of-shame.
- **Full-bleed without seams** (the v1 "hero has visible edges" bug): hero media bleeds
  edge-to-edge with `100vw` and mask-based reveals; no container background showing through;
  gradients meet the viewport edge, not a panel edge.
- **Touch targets ≥ 44px**, hover affordances degrade to tap, the custom cursor disables on
  touch.
- Breakpoint intents: ≤640 single column / stacked stats; 641–1024 two-column tool layouts;
  ≥1025 the full war-room multi-pane. Test 360/768/1280/1920 every segment.

## The "professional team built this" details (subtle, high-signal)

These are where we spend the polish budget — small, felt, never flashy:

- **Anticipatory prefetch**: hovering/focusing a player warms its detail route + data.
- **Optimistic, reversible actions**: draft picks, trade adds apply instantly with a quiet
  undo; never a spinner where an optimistic update will do.
- **Custom cursor reticle** with a contextual label (already `Cursor.tsx`) — broadcast feel,
  off on touch + reduced-motion.
- **Mask-wipe / blur→sharp media reveals** on scroll-in (seen on SportCover, The Grind).
- **Magnetic primary CTAs**; condensed mono nav; a deliberate "SCROLL" affordance on the hero.
- **Number transitions**: values `CountUp` and re-rank with a layout animation when the
  engine toggles VORP⇄Monte Carlo — you *see* the model change its mind.
- **Live broadcast ticker** (lower-third) for trending — sentiment + Sleeper add/drop.
- **Pick-confirm burst** (Rive) on the draft board; **sentiment pulse** on player cards.
- **Skeletons that match final layout** (zero CLS), not generic gray blocks.
- **Sound-off by default**, optional subtle audio cue on draft pick (respects OS settings).

## Signature moments (the "wow" budget)

1. **Homepage hero** — cinematic but cheap: a masked, full-bleed reveal; kinetic split-text
   headline; magnetic CTAs; a scoreboard stat band that counts up. Loads fast (LCP ≤ 2.5s);
   the heavy motion hydrates after first paint and is purely additive.
2. **Draft board** — the centerpiece. Best-available recomputes with animated reorder; value
   dials update; a satisfying Rive pick-confirm burst; positional-scarcity heat.
3. **Player card** — instrument readout: radial value gauge, ridgeline distribution
   (boom/bust), trending sparkline, sentiment pulse, **predictability meter** (new — explains
   why a K/DEF is low-value).
4. **Engine toggle** — VORP⇄Monte Carlo flips the whole board with a layout animation; the
   distribution viz morphs from point to ridgeline.

## What we explicitly avoid

Generic SaaS dashboard cards; rainbow accenting; motion that blocks reading; carousels that
hide data; hover-only information; fixed-pixel layouts; anything that ships > the perf budget.

## Process

Build with the `frontend-design` skill in mind; validate motion techniques against the
free-CDN stack; review every screen with the `ce-design-implementation-reviewer` /
`ce-design-iterator` agents and a Lighthouse + axe pass before a segment is "done."
