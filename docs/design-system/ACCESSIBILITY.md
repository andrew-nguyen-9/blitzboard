# Accessibility — built into the process

Accessibility is an **acceptance criterion**, checked in every segment's QA (not a
retrofit). Target **WCAG 2.2 AA** baseline, AAA for body-text contrast where feasible.

## User-facing controls (a settings panel, persisted to localStorage + account)

The product ships explicit, discoverable accessibility controls — not just OS inheritance:

1. **Text size** — a UI scale control (S / M / L / XL) that scales the fluid type ramp via a
   root `--type-scale` multiplier. Layout reflows; nothing clips.
2. **Reduce motion** — a toggle that forces the reduced-motion path regardless of OS (and a
   "Sync with system" default). Collapses motion tokens to 0ms, swaps animated viz for
   static.
3. **Colorblind modes** — deuteranopia/protanopia/tritanopia-aware palettes: value/risk
   encoded with **shape + label + position**, not hue alone. Distribution/heat viz ship a
   colorblind-safe ramp (e.g. viridis-class) as an option.
4. **High contrast** — a high-contrast theme variant (boost `--ink`/`--line` lightness
   deltas, remove low-contrast glass, thicken borders).
5. **Underline links / focus-always-visible** — optional stronger affordances.

These map to data attributes on `<html>` (`data-motion`, `data-contrast`, `data-cvd`,
`data-type-scale`) consumed by token CSS — no per-component branching.

## Non-negotiables (every component)

- **Keyboard**: full operability, logical tab order, visible focus ring (≥3:1 against
  adjacent), no keyboard traps. Draft board, tables, toggles all keyboard-driven.
- **Semantics**: real landmarks (`header/nav/main/footer`), headings in order, tables use
  `<th scope>`, controls are real buttons/links or have correct `role`+`aria`.
- **Color independence**: never encode meaning in color only — pair with icon/shape/label
  (e.g. value = dial fill + number; trend = arrow + sparkline direction).
- **Contrast**: text ≥ 4.5:1 (AA), large text ≥ 3:1, UI components/graphics ≥ 3:1. Verified
  in both themes with the OKLCH ramps.
- **Motion safety**: `prefers-reduced-motion` honored; no parallax/auto-play that can't be
  paused; no flashing > 3Hz.
- **Forms**: labels tied to inputs, errors announced (`aria-live`), instructions not
  placeholder-only.
- **Images/canvas/Rive**: meaningful alt text / `aria-label`; decorative marked
  `aria-hidden`. Data viz has a text/table equivalent.
- **Targets**: ≥ 44×44px touch; spacing prevents mis-taps.
- **Screen-reader announcements** for live regions: draft picks, trade results, value
  recompute (`aria-live="polite"`).

## Verification per segment

- Automated: **axe** (via Playwright) + Lighthouse a11y ≥ 95.
- Manual: keyboard-only pass; VoiceOver/NVDA spot-check on the changed surface; reduced-motion
  pass; 200% zoom with no loss of content/function; each colorblind mode visually checked.
- Numeric-cell check (the v1 bug): digits never clip at any breakpoint or text scale.
