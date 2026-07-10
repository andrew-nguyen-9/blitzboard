# Animation Prompt Library (v4 E11)

> **This is a prompt deliverable, not a built animation board.** You (the user) paste these
> prompts into **Claude Design**, run them, and feed the results back. E11 owns *the prompts* —
> no component code ships from this unit.

Every prompt below is **self-contained** (readable without the others), **North-Star-aligned**
(it cites the narrowest relevant `docs/design-system/NORTH_STAR.md` section — never the whole
file, per §How to cite this), **names its target component** from
[`ANIMATION_PLACEMENT_MAP.md`](./ANIMATION_PLACEMENT_MAP.md), and **specifies a reduced-motion
static fallback** (the non-negotiable rule in `NORTH_STAR.md` §Motion language).

## How to use this file

1. Pick a prompt (start with the **Board prompt**, then P0 items).
2. Paste the whole prompt block into Claude Design — each block is standalone by design; do not
   stitch two together.
3. Bring the generated `.riv` / CSS / motion spec back into the repo behind the seams named in
   the prompt (`RiveInstrument.tsx` for state machines; a global CSS keyframe for paint-only
   motion). Feed results back for a placement pass (E10/E12 own broad application).

**Shared contract every prompt inherits** (stated once, true for all):

- Animate **compositor-only** properties — `transform`, `opacity`, `box-shadow` — never layout
  props; never block LCP. (`MOTION.md` §Performance rules; `NORTH_STAR.md` §Do / Don't.)
- Neon is the *charged* state of the existing accent, derived from `--accent-h`; **never**
  hardcode a neon hex or a second hue. (`NORTH_STAR.md` §Neon palette.)
- Any animating neon element MUST null its animation under **both**
  `@media (prefers-reduced-motion: reduce)` **and** `[data-motion="reduce"]`, resolving to the
  **fully-lit static frame** (resting state is the lit element, not the dark one).
  (`NORTH_STAR.md` §Motion language — Reduced-motion rule.)
- A glow that **encodes state** is functional → it must carry a non-color cue
  (label/shape/position). A glow that is pure ambience is decorative → silent, cheap,
  skippable. (`NORTH_STAR.md` §Motion language — Decorative vs functional.)

---

## Board prompt — the animation showcase page

> **Prompt 0 · Motion Board** — target: a new showcase route (model it on the existing
> `frontend/app/kit/page.tsx` design-kit page) rendering each instrument below.

```
Design a single-page "Motion Board" for BlitzBoard — a night-broadcast NFL fantasy war room.
It is an internal gallery that shows every signature animation resting and playing, so the team
can QA the motion language in one place. Model the layout on our existing design-kit page
(frontend/app/kit/page.tsx): a dark base, sectioned cards, mono numerals.

Visual language — "Neon Broadcast" (NORTH_STAR.md §The idea, §Neon palette): one dark base, one
charged accent given a lit-tube neon glow derived from --accent-h. Neon marks the live / the
selected / the signal — ration it; a neon that lights everything lights nothing (§Do / Don't).

The board shows, each as its own labelled card with a "resting / playing" toggle:
  1. Hero ignite (the HeroHeadline accent line lighting up)
  2. Value dial sweep (ValueDial)
  3. Engine toggle re-rank (EngineToggle → board)
  4. Draft pick-confirm burst (DraftRoom / DraftEndCard)
  5. Trending ticker loop (Ticker / Marquee)
  6. Predictability meter ignite (PredictabilityMeter)

Motion register (NORTH_STAR.md §Motion language): the signature transition is *ignite* — an
element crossing into its live/selected state ramps its glow up via box-shadow/opacity only,
over --dur with --ease-out. The resting still-state is the FULLY-LIT element.

Reduced-motion fallback (NORTH_STAR.md §Motion language, non-negotiable): a global toggle on the
board flips every card to its fully-lit static frame — no ramps, no loops — mirroring
prefers-reduced-motion / [data-motion="reduce"]. Ship this state first; motion is additive.

Accessibility: every functional glow pairs with a text/shape cue; AA contrast rides on the solid
--neon / --neon-ink color, never the glow (NORTH_STAR.md §Contrast / a11y). Cards are keyboard
reachable with the global focus ring.

Deliver: a responsive layout spec + the per-card resting and playing frames. Do NOT invent new
colors — use the neon token ladder (--neon, --neon-ink, --neon-dim, --neon-soft, --neon-glow).
```

---

## Individual animation prompts

### P0 — signature surfaces

> **Prompt 1 · Hero ignite** — target: `HeroHeadline.tsx` (home `/`).

```
Design the first-paint "ignite" for the hero headline of a night-broadcast NFL fantasy war room.
The accent line ("war room.") already renders as charged neon text (.neon-text: --neon fill +
static halo). Add a ONE-SHOT ignite: after the LCP text paints, the glow ramps from 0 to full
over --dur with --ease-out (box-shadow/opacity only — the solid --neon color is there from frame
one, so nothing pops in).

North Star: NORTH_STAR.md §Motion language (ignite register) + §Proof (HeroHeadline is the F1
neon proof; resting state is the fully-lit word).

Reduced-motion: under prefers-reduced-motion / [data-motion="reduce"], NO ramp — the word is
fully lit from first paint (already its resting state). LCP text stays static HTML/CSS; the ramp
hydrates after first paint, purely additive (MOTION.md §Performance).

Deliver the keyframe (glow-up) + the static frame. One accent line only — do not neon the whole
headline (§Do / Don't: ration neon).
```

> **Prompt 2 · Value dial sweep** — target: `ValueDial.tsx` (`/players`).

```
Design the fill animation for a radial value gauge in a night-broadcast fantasy war room. A 270°
arc sweeps from empty to `fraction` (0..1) — the instrument readout of a player's value. The lit
arc is charged neon (--neon), the track is --neon-dim; the sweep is a pure CSS stroke-dashoffset
animation (this component uses .dial-fill, zero JS).

North Star: NORTH_STAR.md §Motion language (the lit arc *ignites* into its value) + §Neon palette
(arc = --neon, track = --neon-dim, both derived from --accent-h so the gauge re-tints per league).

Reduced-motion: under prefers-reduced-motion / [data-motion="reduce"] the arc shows its FINAL
filled state instantly (no sweep). The real value already lives in centered text + an sr-only
sentence (aria-hidden SVG), so the gauge always has a text equivalent.

Deliver the sweep timing/easing + the static filled frame. AA contrast rides on the numerals,
not the glow (§Contrast / a11y).
```

> **Prompt 3 · Engine toggle re-rank** — target: `EngineToggle.tsx` → board (`/players`).

```
Design the "the model changed its mind" transition for a VORP ⇄ Monte-Carlo engine toggle in a
fantasy war room. Flipping the toggle re-ranks the player value board; rows glide to new
positions (Framer Motion `layout` / FLIP), and the newly-active engine chip IGNITES — its neon
glow ramps up to mark which engine is live.

North Star: NORTH_STAR.md §Motion language (ignite = crossing into the selected/live state) +
§Do / Don't (the live engine also carries a text label + aria-pressed — glow is reinforcement,
never the only cue).

Reduced-motion: under prefers-reduced-motion / [data-motion="reduce"] values and positions swap
INSTANTLY (no glide), and the active chip is simply already-lit (no ramp). Animate transform +
box-shadow only.

Deliver: the row-reorder motion spec + the chip resting (lit) and igniting frames.
```

> **Prompt 4 · Draft pick-confirm burst** — target: `DraftRoom.tsx` / `DraftEndCard.tsx` (`/draft`).

```
Design a draft pick-confirm celebration for an NFL fantasy draft war room. When a pick is
confirmed, a short neon burst fires keyed to the accent (≤600ms), the new pick row inserts via a
layout animation, and the best-available list reorders beneath it (FLIP). This is the emotional
beat of the draft — charged but disciplined.

North Star: NORTH_STAR.md §Motion language (ignite/burst on the accent) + §Do / Don't (ration —
the burst is a single moment, not a permanent glow on every row).

Reduced-motion: under prefers-reduced-motion / [data-motion="reduce"] the row simply appears and
the list reorders instantly — NO burst. Compositor-only (transform/opacity/box-shadow), ≤600ms,
never blocks interaction.

Deliver: the burst keyframe (accent-tinted, box-shadow/opacity) + the instant static fallback.
Prefer authoring as a Rive state machine behind RiveInstrument.tsx (with a static fallback), not
raw canvas.
```

> **Prompt 5 · Trending ticker loop** — target: `Ticker.tsx` / `Marquee.tsx` (home `/`).

```
Design the broadcast lower-third trending ticker for a night NFL fantasy war room. A "LIVE" tag
pins left; trending items scroll seamlessly right-to-left at ~40px/s on a continuous marquee. The
LIVE tag is the only neon element — a small charged --neon pill that reads as "on air".

North Star: NORTH_STAR.md §Do / Don't (ration neon — the whole strip is NOT neon, only the LIVE
signal) + §Motion language (a decorative ambient loop: silent, cheap, skippable).

Reduced-motion: under prefers-reduced-motion / [data-motion="reduce"] the scroll STOPS and the
strip becomes a static, horizontally-scrollable list — nothing clipped, each item read once by
screen readers (the duplicate track is aria-hidden). The marquee also pauses on hover/focus.

Deliver: the marquee timing + the static list frame + the LIVE pill (resting lit) spec.
```

### P1 — instrument readouts

> **Prompt 6 · Predictability meter ignite** — target: `PredictabilityMeter.tsx` (`/players`, K/DEF).

```
Design the "signal-strength" ignite for a segmented predictability meter (0..1 score) in a
fantasy war room — think a phone signal-bars readout for how predictable a K/DEF is. Lit segments
ignite left-to-right in --neon; unlit segments sit as --neon-dim tracks. The number of lit
segments AND a tier word both carry the score.

North Star: NORTH_STAR.md §Motion language (ignite, left-to-right) + §Neon palette (lit = --neon,
track = --neon-dim) + §Do / Don't (segment count + tier word = the real cue; glow reinforces).

Reduced-motion: under prefers-reduced-motion / [data-motion="reduce"] all lit segments are shown
lit instantly (no left-to-right ramp) — this component is static by default, so the ignite is a
pure enhancement over an already-correct still frame.

Deliver: the stagger/ignite timing + the static lit frame.
```

> **Prompt 7 · Distribution ridge morph** — target: `DistributionRidge.tsx` via `RiveInstrument.tsx` (`/players`).

```
Design the value-dial → boom/bust ridgeline morph for a fantasy war room. When the engine toggles
to Monte Carlo, a radial value gauge morphs into a smooth violin/ridgeline distribution; the
shape (spread, skew) encodes boom/bust, with a labelled median tick. Neon-tint the ridge curve as
the charged --neon signal over a --neon-dim baseline.

North Star: NORTH_STAR.md §Motion language (instrument morph, ease-inout loop) + §Neon palette
(curve = --neon, baseline = --neon-dim, re-tint per league via --accent-h).

Reduced-motion: under prefers-reduced-motion / [data-motion="reduce"] show the static range bar
(min..max + median tick) — the component's existing reduced-motion fallback — NO morph. Meaning
is carried by SHAPE + a labelled median, never color alone (colorblind-safe).

Deliver: the morph as a Rive state machine spec behind RiveInstrument.tsx, with DistributionRidge
(static range bar) as the fallback. Do not author raw canvas.
```

> **Prompt 8 · Tier badge ignite** — target: `TierBadge.tsx` (`/players`, `/draft`).

```
Design the "this is the live tier" ignite for a tier badge chip in a fantasy war room. When a
badge represents the player's current tier, its neon edge ignites (glow ramps up); other tiers
stay as quiet --neon-dim outlines. The tier's shape and label always name it — glow only
reinforces.

North Star: NORTH_STAR.md §Primitives → Elevation/edge (.neon-edge lit-tube rim) + §Do / Don't
(pair the glow with the label/shape cue — never encode tier in glow alone).

Reduced-motion: under prefers-reduced-motion / [data-motion="reduce"] the live badge is simply
already-lit (static .neon-edge), no ramp. Box-shadow/opacity only.

Deliver: the ignite keyframe + the resting lit and unlit (dim) frames.
```

> **Prompt 9 · Sparkline draw-in** — target: `Sparkline.tsx` (`/players/[id]`).

```
Design the draw-in reveal for a player season-points sparkline in a fantasy war room. On entry
the trace draws itself left-to-right via stroke-dashoffset in --neon over a faint --neon-dim
baseline — a quiet instrument coming online.

North Star: NORTH_STAR.md §Primitives → Texture/pattern (paint-driven, low-key) + §Neon palette
(trace = --neon, baseline = --neon-dim). Decorative, not functional — the numbers elsewhere are
the real data.

Reduced-motion: under prefers-reduced-motion / [data-motion="reduce"] the full line is shown
drawn instantly — no draw-in. stroke-dashoffset only; never blocks paint.

Deliver: the draw-in timing + the fully-drawn static frame.
```

### P2 — ambient / connective tissue

> **Prompt 10 · Blitz field ambient shimmer** — target: `BlitzField.tsx` (home `/`).

```
Design the ambient background motion for the homepage hero of a night-broadcast NFL war room. A
full 22-man blitz formation sits on a faint chalk grid; defenders rush the QB along routes that
draw themselves in (stroke-dashoffset loop). Give the rush lines a barely-there neon shimmer so
the field reads as "live" without fighting the hero copy.

North Star: NORTH_STAR.md §Primitives → Texture/pattern (faint, under the text plane,
aria-hidden) + §Do / Don't (this is ambience — keep it nearly invisible, never neon-outline the
whole field).

Reduced-motion: under prefers-reduced-motion / [data-motion="reduce"] the routes show fully drawn
and still (the component's existing .bp-route contract) — NO loop, NO shimmer. Purely decorative,
aria-hidden.

Deliver: the shimmer/draw loop timing + the fully-drawn still frame. Keep alpha low enough that
hero text contrast is unaffected.
```

> **Prompt 11 · Scroll cue pulse** — target: `ScrollCue.tsx` (home `/`).

```
Design the foot-of-hero "SCROLL" affordance motion for a night-broadcast war room. A small neon
travel pulse cues downward scroll; clicking drives a momentum (Lenis) scroll to the next section.
The cue is a real anchor — it works with no JS and is keyboard-operable with the global focus
ring.

North Star: NORTH_STAR.md §Motion language (decorative loop: silent, cheap, skippable) + §Neon
palette (a single --neon accent, rationed).

Reduced-motion: under prefers-reduced-motion / [data-motion="reduce"] the travel pulse is stilled
and the scroll jump is instant (native in-page anchor). Transform/opacity only.

Deliver: the pulse loop timing + the static frame.
```

> **Prompt 12 · Nav active-route underline** — target: `Nav.tsx` (all routes).

```
Design the active-route indicator for the top nav of a night-broadcast fantasy war room. The
current route's link carries a neon underline that ignites on navigate (glow ramps up); the link
label is always the real state cue.

North Star: NORTH_STAR.md §Motion language (ignite on state change) + §Do / Don't (the label/
aria-current is the cue; the neon underline reinforces — never the only signal).

Reduced-motion: under prefers-reduced-motion / [data-motion="reduce"] the active underline is
simply already-lit (static), no ramp. Box-shadow/opacity/transform only.

Deliver: the underline ignite keyframe + the resting lit (active) and unlit (inactive) frames.
```

> **Prompt 13 · Empty-state neon grid wash** — target: `EmptyState.tsx` / `ConnectPrompt.tsx` (all routes).

```
Design the ambient background for empty / offline surfaces in a night-broadcast war room, so a
board with no data still reads as "live equipment, powered on, waiting for signal." Use the faint
neon circuit grid (.neon-grid: --neon at ~0.06 alpha, decorative) with an optional very slow
drift.

North Star: NORTH_STAR.md §Primitives → Texture/pattern (the .neon-grid wash, aria-hidden, kept
under the text plane) + §Do / Don't (ambience only — do not neon-outline the empty card).

Reduced-motion: under prefers-reduced-motion / [data-motion="reduce"] the grid is completely
static (paint-only, no drift) — this is the default and always-safe state. aria-hidden.

Deliver: the (optional) drift timing + the static grid frame. Alpha must keep any overlaid text
above AA.
```

> **Prompt 14 · Trade value-add ignite** — target: `TradeCalculator.tsx` / `TradeFinder.tsx` (`/trades`).

```
Design the value-verdict motion for a trade calculator in a fantasy war room. As pieces are added
to each side, both totals re-rank (layout animation) and the FAVORED side ignites — a neon glow
marks which side wins value, alongside a numeric delta and a "you gain / you lose" label.

North Star: NORTH_STAR.md §Motion language (ignite marks the value-add signal) + §Do / Don't
(pair the glow with the numeric delta + text verdict — glow never carries the verdict alone).

Reduced-motion: under prefers-reduced-motion / [data-motion="reduce"] totals update instantly and
the favored side is simply already-lit (no ramp, no glide). Transform/box-shadow/opacity only.

Deliver: the re-rank + ignite spec and the instant static verdict frame.
```

---

## Prompt inventory

| # | Prompt | Target component(s) | Route | NORTH_STAR § cited |
|---|--------|---------------------|-------|--------------------|
| 0 | Motion Board (board prompt) | new showcase page (model `kit/page.tsx`) | new | §The idea, §Neon palette, §Motion language, §Contrast / a11y |
| 1 | Hero ignite | `HeroHeadline` | `/` | §Motion language, §Proof |
| 2 | Value dial sweep | `ValueDial` | `/players` | §Motion language, §Neon palette |
| 3 | Engine toggle re-rank | `EngineToggle` | `/players` | §Motion language, §Do / Don't |
| 4 | Draft pick-confirm burst | `DraftRoom`, `DraftEndCard`, `RiveInstrument` | `/draft` | §Motion language, §Do / Don't |
| 5 | Trending ticker loop | `Ticker`, `Marquee` | `/` | §Do / Don't, §Motion language |
| 6 | Predictability meter ignite | `PredictabilityMeter` | `/players` | §Motion language, §Neon palette, §Do / Don't |
| 7 | Distribution ridge morph | `DistributionRidge`, `RiveInstrument` | `/players` | §Motion language, §Neon palette |
| 8 | Tier badge ignite | `TierBadge` | `/players`, `/draft` | §Primitives, §Do / Don't |
| 9 | Sparkline draw-in | `Sparkline` | `/players/[id]` | §Primitives, §Neon palette |
| 10 | Blitz field shimmer | `BlitzField` | `/` | §Primitives, §Do / Don't |
| 11 | Scroll cue pulse | `ScrollCue` | `/` | §Motion language, §Neon palette |
| 12 | Nav active underline | `Nav` | all | §Motion language, §Do / Don't |
| 13 | Empty-state grid wash | `EmptyState`, `ConnectPrompt` | all | §Primitives, §Do / Don't |
| 14 | Trade value-add ignite | `TradeCalculator`, `TradeFinder` | `/trades` | §Motion language, §Do / Don't |

**Total: 1 board prompt + 14 individual prompts.** Every target resolves to a real file in
`frontend/components/` and a real entry in [`ANIMATION_PLACEMENT_MAP.md`](./ANIMATION_PLACEMENT_MAP.md).
