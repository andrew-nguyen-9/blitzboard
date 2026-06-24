# Design Tokens — OKLCH, type, space, motion

Tokens are CSS custom properties on `:root`, swapped by `data-theme="dark|light"`. Colors
are **OKLCH** so light/dark and accent derivation stay perceptually uniform (validated as an
emerging best practice on fcporto's memorial site). No per-component color branching.

## Color (OKLCH)

```css
:root[data-theme="dark"] {
  /* base ladder — lightness ramps, constant hue/chroma */
  --bg-0: oklch(0.16 0.012 250);   /* page */
  --bg-1: oklch(0.20 0.014 250);   /* panel */
  --bg-2: oklch(0.25 0.016 250);   /* raised */
  --line: oklch(0.32 0.02 250 / 0.6);
  --ink-0: oklch(0.97 0.01 250);   /* primary text */
  --ink-1: oklch(0.78 0.012 250);  /* secondary */
  --ink-2: oklch(0.58 0.012 250);  /* tertiary/labels */
  /* accent — runtime-derived per league/team; default electric volt */
  --accent: oklch(0.78 0.17 145);
  --accent-ink: oklch(0.18 0.02 145);
  /* semantic */
  --pos: oklch(0.80 0.16 150);     /* good / value-add */
  --neg: oklch(0.65 0.20 25);      /* bad / risk */
  --warn: oklch(0.82 0.16 75);
}
:root[data-theme="light"] {
  --bg-0: oklch(0.96 0.008 90);    /* warm paper */
  --bg-1: oklch(0.99 0.006 90);
  --bg-2: oklch(0.93 0.01 90);
  --line: oklch(0.55 0.02 90 / 0.25);
  --ink-0: oklch(0.22 0.02 250);
  --ink-1: oklch(0.40 0.02 250);
  --ink-2: oklch(0.52 0.02 250);
  --accent: oklch(0.62 0.17 145);  /* same hue, retuned L/C for paper */
  --accent-ink: oklch(0.98 0.01 145);
  --pos: oklch(0.55 0.15 150);
  --neg: oklch(0.55 0.20 25);
  --warn: oklch(0.62 0.15 75);
}
```

Accent derivation: from a league/team hue `H`, set `--accent` to `oklch(L C H)` with
theme-appropriate `L`/`C` — one source hue, two perceptually-matched renderings. Never store
accent as a raw hex; store the hue and derive.

## Type — the locked stack

| Role | Face | Use |
|------|------|-----|
| **Display / scoreboard** | Condensed athletic grotesk (e.g. Anton / a Formula-Condensed-class face) | Hero numerals, big stat bands |
| **Editorial accent** | Editorial serif (e.g. Bricolage Grotesque display / a GT-Super-class serif) | Story/hero headlines, player-profile editorial |
| **Body** | Neutral grotesk (Hanken Grotesk / Neue-Montreal-class) | Prose, UI |
| **Mono** | JetBrains Mono / DM Mono | **All numerals, stats, labels** — the instrument signal |

Numerals always `font-variant-numeric: tabular-nums` in tables. Sizes via `clamp()`:

```css
--step--1: clamp(0.83rem, 0.8rem + 0.15vw, 0.9rem);
--step-0:  clamp(1rem, 0.95rem + 0.25vw, 1.125rem);
--step-1:  clamp(1.33rem, 1.2rem + 0.6vw, 1.6rem);
--step-2:  clamp(1.77rem, 1.5rem + 1.2vw, 2.4rem);
--step-3:  clamp(2.37rem, 1.9rem + 2.2vw, 3.6rem);
--display: clamp(3rem, 2rem + 6vw, 9rem);   /* hero scoreboard */
```

## Space & radii (fluid)

```css
--space-2xs: clamp(0.31rem, 0.3rem + 0.05vw, 0.34rem);
--space-s:   clamp(0.69rem, 0.65rem + 0.2vw, 0.81rem);
--space-m:   clamp(1.13rem, 1.05rem + 0.4vw, 1.35rem);
--space-l:   clamp(1.5rem, 1.35rem + 0.75vw, 2rem);
--space-xl:  clamp(2.25rem, 1.9rem + 1.7vw, 3.5rem);
--radius:    0.75rem; --radius-lg: 1.25rem;
```

## Motion tokens

```css
--ease-out: cubic-bezier(0.16, 1, 0.3, 1);
--ease-inout: cubic-bezier(0.65, 0, 0.35, 1);
--dur-fast: 140ms; --dur: 240ms; --dur-slow: 480ms;
/* reduced-motion: all durations collapse to 0ms, transforms removed */
```

## Elevation / glass

```css
--glass: oklch(from var(--bg-1) l c h / 0.6);
--blur: 14px;          /* backdrop-filter on panels */
--glow: 0 0 0 1px var(--line), 0 8px 40px oklch(0 0 0 / 0.4);  /* dark */
```

All tokens live in `frontend/app/globals.css` (or a `tokens.css` import). Components consume
tokens only — no literal colors/sizes in component CSS.
