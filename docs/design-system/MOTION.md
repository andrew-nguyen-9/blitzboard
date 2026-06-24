# Motion System

Motion serves comprehension and feel — never at the cost of speed or access. The reference
teardown (`mocks/v2-research/findings.md`) converged on a small toolkit; v2 adopts it.

## The toolkit (and when each is used)

| Tool | Role | Notes |
|------|------|-------|
| **Rive** | Interactive instrument states & micro-motion: value dial fill, engine toggle, draft pick-confirm burst, sentiment pulse, K/DEF predictability meter. | **The headline adoption** — appeared on 7/9 premium references. GPU-cheap vector state machines, designer-authored `.riv`, small bundle, renders in Next.js (confirmed on dcd.org.ae). Replaces ad-hoc canvas/Framer work. |
| **GSAP + ScrollTrigger** | Homepage scroll story: pinned sections, masked reveals, parallax depth. | Loaded only on the homepage route; lazy/idle-hydrated. |
| **Lenis** | Momentum smooth-scroll. | Already shipped (`SmoothScroll.tsx`). Disabled under reduced-motion. |
| **SplitText (or CSS)** | Kinetic per-character/word hero reveals. | Static fallback = plain text. |
| **Framer Motion** | Component-level layout animations: best-available reorder, value re-rank on engine toggle, list enters. | Already a dep. Prefer `layout` animations for the "model changed its mind" effect. |
| **Marquee** | Broadcast lower-third trending ticker. | Already shipped. Pauses on hover/focus; static under reduced-motion. |

## Performance rules (motion must respect the budget)

- **First paint is sacred.** Hero LCP image/text is static HTML/CSS; heavy motion libraries
  hydrate **after** first paint (dynamic import, `requestIdleCallback`), purely additive.
- **Animate compositor-only properties** (`transform`, `opacity`). No animating layout props.
- **60fps or cut it.** Profile with chrome-devtools performance traces; if a motion drops
  frames on a mid-tier phone, simplify or remove.
- **Bundle discipline**: GSAP/Three load per-route, never globally. Rive runtime is small;
  load `.riv` lazily.
- **Zero CLS**: skeletons match final layout; nothing reflows as motion hydrates.

## Reduced-motion contract

Every animated surface has a designed still state. Under `prefers-reduced-motion: reduce`
(or the in-app toggle): durations → 0, transforms removed, ScrollTrigger pins released,
Lenis off, Rive state machines snap to their resting frame, marquees become static lists,
CountUp shows the final number immediately. This is verified in QA for every segment.

## Signature motion specs (acceptance-level detail)

- **Hero reveal**: mask-wipe (clip-path) over full-bleed media, 480ms `--ease-out`; headline
  SplitText stagger 24ms/word; CTA magnetic radius 60px. Reduced: instant, no magnet.
- **Draft pick-confirm**: Rive burst keyed to accent, ≤ 600ms; row inserts via Framer
  `layout`; best-available reorders with FLIP. Reduced: row appears, list reorders instantly.
- **Engine toggle (VORP⇄MC)**: board re-ranks with `layout` animation; dial → ridgeline morph
  via Rive. Reduced: values/positions swap instantly.
- **Trending ticker**: continuous marquee at ~40px/s, pause-on-interaction. Reduced: static
  scrollable list.
