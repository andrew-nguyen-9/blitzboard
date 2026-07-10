# Visual North Star — "Neon Broadcast" (v4 F1)

> The single citable anchor for BlitzBoard's **neon / high-tech / elegant** direction.
> It **extends** the "Broadcast Instrument" system (`DESIGN_GUIDELINE.md`, `TOKENS.md`,
> `MOTION.md`, `ACCESSIBILITY.md`) — it does **not** replace it. Every UI/animation/mobile
> unit (E8, E10, E11, E12, and the UI bits of E2/E5) cites **sections of this file**, not the
> whole thing (see [§How to cite](#how-to-cite-this)).

## The idea (one paragraph)

Take the disciplined broadcast instrument — one dark (or warm-paper) base, one charged accent,
mono numerals rendered like precision gauges — and give the accent a **lit-tube neon glow**:
high-tech, night-broadcast, still elegant and restrained. Neon is the *charged* state of the
existing accent, not a second color. It marks the live, the selected, the signal — never
decoration for its own sake. Rationing is the whole point: a neon that lights everything lights
nothing. **Effortless-and-fast still beats impressive** (`DESIGN_GUIDELINE.md` §Four principles).

## Neon palette (OKLCH, additive)

Neon tokens are **new named tokens that sit on top of** the base ladder and accent. They are
derived from the same `--accent-h` source hue, so neon stays league/team-tinted at runtime and
perceptually matched across themes. They **never rename or override** `--accent`, `--bg-*`,
`--ink-*`, or any shipped token — downstream units and shipped v3 depend on those.

| Token | Dark | Light | Role |
|-------|------|-------|------|
| `--neon` | `oklch(0.86 0.20 H)` | `oklch(0.49 0.18 H)` | Charged accent: signal text, lit edges, active state |
| `--neon-ink` | `oklch(0.20 0.03 H)` | `oklch(0.98 0.01 H)` | Text/icon **on** a solid neon fill |
| `--neon-dim` | `oklch(0.62 0.14 H)` | `oklch(0.50 0.16 H)` | Neon **graphic/edge** (borders, gridlines, gauge tracks) |
| `--neon-soft` | `--neon @ 0.16α` | `--neon @ 0.10α` | Halo / wash fill behind a lit element |
| `--neon-glow` | multi-layer box halo | tight rim + soft drop | Elevation glow (box-shadow) |
| `--neon-glow-text` | soft text halo | barely-there on paper | Text glow (box-shadow-free) |
| `--glass-neon` | `--bg-1 @ 0.55α` | `--bg-1 @ 0.72α` | Frosted panel fill behind a neon rim |

`H` = `var(--accent-h)` (default 145, electric volt). **Where they live:** all tokens are in
`frontend/app/globals.css`, in the `[data-theme="dark"]` and `[data-theme="light"]` blocks —
so they **swap by flipping `data-theme` on `<html>`** (set pre-paint by `ThemeScript`), exactly
like the base tokens. Tailwind exposes them as `neon`, `neon-ink`, `neon-dim`, `neon-soft`
colors and `shadow-neon` (`frontend/tailwind.config.ts`). Light neon is deliberately deepened
(glow is a dark-native effect; on paper neon reads as a rich saturated ink, the halo dialled
almost to nothing).

## Primitives (how each is expressed)

Four primitives, all token-driven and **paint-only** (no animation → inert under reduced
motion). Utilities in `frontend/app/globals.css`:

- **Glow** — `.neon-text` (charged text + static halo, the signature) · `.neon-glow` /
  `shadow-neon` (box halo for a raised or active surface). Contrast is always carried by the
  solid color, never the glow, so stripping the halo never drops below AA.
- **Glass** — `.glass-neon`: frosted `backdrop-filter: blur(var(--blur))` panel with a
  `--neon-dim` rim and the neon box halo. Solid-fill fallback when blur is unsupported;
  `--blur` collapses to 0 under `data-contrast="high"`.
- **Texture / pattern** — `.neon-grid`: a faint neon circuit grid (`--neon @ 0.06α`, 2.5rem
  cell) for empty/hero surfaces. Decorative → always `aria-hidden`; alpha keeps it under the
  text plane.
- **Elevation / edge** — `.neon-edge` (hairline `--neon-dim` border + faint inner wash, the
  "lit tube" rim) layers over the base `--glow` elevation; use for the selected/active tier of
  a surface, not every card.

## Motion language

Extends `MOTION.md` (its toolkit and reduced-motion contract are unchanged and authoritative).
Neon adds one register:

- **Signature transition** — *ignite*: an element crossing into its live/selected state ramps
  its glow up (`box-shadow`/`opacity` only, compositor-safe) over `--dur` with `--ease-out`.
  The resting still-state is the fully-lit element (not the dark one), so reduced motion lands
  correctly lit.
- **Easing** — reuse `--ease-out` (entrances/ignite) and `--ease-inout` (loops); no new easings.
- **Decorative vs functional** — a glow that *encodes* state (live, selected, value-add) is
  **functional** and must also carry a non-color cue (label/shape/position, `ACCESSIBILITY.md`
  §Color independence). A glow that is pure ambience (hero grid shimmer) is **decorative** and
  must be silent, cheap, and skippable.
- **Reduced-motion rule (non-negotiable)** — any neon element that *animates* (pulse, ignite,
  shimmer) MUST null that animation under **both** `@media (prefers-reduced-motion: reduce)`
  **and** `[data-motion="reduce"]`, resolving to the fully-lit static frame — mirroring the
  per-component contract already used by `.hero-word`, `.dial-fill`, `.bp-route`, etc. The
  static neon utilities above need no such guard (they never animate).

## Do / Don't

- **Do** ration neon to the live/selected/value-add signal. **Don't** neon-outline every card
  or panel — that is the "rainbow accenting" `DESIGN_GUIDELINE.md` explicitly forbids.
- **Do** let AA contrast ride on the solid `--neon`/`--neon-ink` color. **Don't** rely on the
  glow for legibility — it is stripped under high-contrast and reduced transparency.
- **Do** keep neon derived from `--accent-h` so it re-tints per league. **Don't** hardcode a
  neon hex or a second fixed hue.
- **Do** pair a neon "live/selected" glow with a label/icon/position cue. **Don't** encode
  meaning in the glow alone.
- **Do** hydrate any neon *motion* after first paint, additive-only (`MOTION.md` §Performance).
  **Don't** animate a glow via `filter`/layout props or block LCP on it.

## Contrast / a11y (WCAG 2.2 AA — verified)

Computed OKLCH→sRGB→WCAG for the new accent-on-surface pairs (default hue H=145), both themes.
All text pairs clear **AA 4.5:1**; all graphic/edge pairs clear **3:1**.

| Pair | Dark | Light | Requirement |
|------|-----:|------:|-------------|
| `--neon-ink` on `--neon` fill (text) | **12.55** | **5.38** | ≥ 4.5 ✓ |
| `--neon` on `--bg-0` (accent text) | **13.54** | **5.06** | ≥ 4.5 ✓ |
| `--neon` on `--bg-1` (accent text) | **12.62** | **5.52** | ≥ 4.5 ✓ |
| `--neon-dim` on `--bg-0` (graphic) | **5.64** | **4.98** | ≥ 3 ✓ |
| `--neon-dim` on `--bg-1` (graphic) | **5.26** | **5.44** | ≥ 3 ✓ |

Non-color encoding, keyboard, and motion safety continue to follow `ACCESSIBILITY.md` — neon
adds no exemptions. Ratios recompute if a league hue `H` is set very differently; the low-chroma
`--neon-ink`/base surfaces keep these stable across the usable hue range, but re-verify a hue
before shipping it as a default.

## Proof (existence proof, F1)

`frontend/components/HeroHeadline.tsx` — the accent line ("war room.") now renders with
`.neon-text` (charged `--neon` + static glow) instead of flat `text-accent`. Server Component,
zero JS, LCP-safe; glow is paint-only so it is inert under reduced motion and AA is carried by
the solid color. This is the **only** component F1 touches — E10 does the broad application pass,
E12 the mobile pass. Do not restyle other components citing "the North Star did the hero."

## How to cite this

Downstream briefs reference **a section anchor**, not the file, e.g.:

- palette / token names → `NORTH_STAR.md §Neon palette`
- a primitive → `NORTH_STAR.md §Primitives → Glass`
- motion register + reduced-motion rule → `NORTH_STAR.md §Motion language`
- a11y ratios → `NORTH_STAR.md §Contrast / a11y`

Rule of thumb: cite the **narrowest** section that answers your question. If you need a base
token (bg/ink/accent/type/space/motion), cite `TOKENS.md` directly — this file only adds the
neon layer on top.
