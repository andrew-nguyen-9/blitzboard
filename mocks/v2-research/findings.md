# v2 Design Research — Reference Site Teardown

Method: Playwright DOM/script scan (fonts, color palettes, animation libraries, CSS
custom properties) + targeted screenshots. Run 2026-06-24. Raw screenshot:
`sportcover.jpeg`. 9 of 12 sites captured cleanly (ESPN feature template is anti-bot /
lazy-loaded; Wolverine + FreeGameMgmt deprioritized as lower-signal corporate).

## Per-site teardown

| Site | Stack detected | Type system | Base / Accent | Read |
|------|----------------|-------------|---------------|------|
| **sportcover.co** | GSAP+ScrollTrigger, Lenis, Three/WebGL, SplitText, **Rive** | Funnel Sans 100px display, DM Mono, Lausanne | Black / electric blue `#0000EE` | Broadcast editorial; mono nav, blur→sharp media reveal, custom SCROLL reticle |
| **memorial.fcporto.pt** | AOS | GT Super Display serif 120px | **OKLCH** cream `oklch(.87 .02 88)` / near-black navy `oklch(.117 .026 250)` | Cinematic editorial memorial; wide-gamut color science |
| **kern.uprock.pro** | GSAP+ScrollTrigger, Swiper | Inter | White / electric blue `#0000EE` | Clean light editorial portfolio; same hyperlink-blue accent |
| **lacoste ace-breaker** | **Three+WebGL**, **Rive** | Mona Sans | Deep green `rgb(0,80,60)` / cream + yellow `#FCD757` | WebGL 3D interactive *game* under a fashion brand skin |
| **nivisgear.com** | GSAP+ScrollTrigger, Three, Swiper, **Rive**, Shopify | Neue Montreal + lores-12 (pixel-mono) | Near-black `rgb(13,11,20)` / grayscale | Technical-apparel premium; mono accents on dark |
| **podium.global** | Lenis, Three | Futura + **Univers Condensed** | Pure black / grayscale | Sports video studio; condensed broadcast type, restrained |
| **xnrgyclub.com** | Swiper, **Rive** | Space Mono + Neue Helvetica Pro 187px | Light gray `rgb(235,235,235)` / deep navy `rgb(25,43,136)` | Padel club; massive display + mono labels |
| **thegrind.nl** | GSAP+ScrollTrigger, **Lenis, Locomotive**, SplitText, **Rive**, Marquee, Parallax (Webflow) | Formula Condensed 92px + Helvetica Neue | Warm paper `rgb(231,230,226)` / red `rgb(250,49,57)` on green-black | **Richest athletic-kinetic reference** — the full motion stack |
| **dcd.org.ae/events** | Three, Swiper, **Rive**, **Next.js** | Metropolis/Standerd/Resonate/Neue Montreal | Black / grayscale | Events index on Next.js — proves Rive+Three render cleanly in our framework |

## Cross-cutting patterns (what makes them "scream professional")

### 1. Animation stack — the consensus toolkit
- **Rive appeared on 7 of 9 sites** — the single biggest signal. Lightweight vector
  state-machine animation (`.riv` files), GPU-cheap, designer-authored, runs in React/Next.
  This is the modern replacement for heavy Lottie/hand-coded canvas for *interactive* UI
  motion (dials, toggles, micro-states, bursts).
- **GSAP + ScrollTrigger** for scroll-choreographed sequences (5/9).
- **Lenis** (we already ship it) / Locomotive for momentum smooth-scroll (3/9).
- **SplitText** for kinetic per-character headline reveals (3/9).
- **Three.js / WebGL** for hero 3D / spatial moments (6/9) — used sparingly, one hero moment.
- **Swiper** for carousels; **Marquee** for broadcast tickers.

### 2. Type — two poles, always with mono
- **Display:** oversized (90–190px) in either *condensed athletic grotesk* (Formula
  Condensed, Univers Condensed, Neue Helvetica) OR *editorial serif* (GT Super Display).
- **Body:** premium neutral grotesk (Neue Montreal, Mona Sans, Hanken Grotesk).
- **Mono everywhere for labels/metadata/stats** (DM Mono, Space Mono) — the "instrument"
  signal. This directly validates v1's mono-for-numbers instinct.

### 3. Color — disciplined
- A single base pole: **near-black** (`#0A0B0D`-ish, or near-black navy) OR **warm paper**
  (`#E7E6E2` / `#F3F2E1`). Never mid-gray.
- **Exactly one charged accent** (electric blue, brand green, signal red, deep navy).
- **OKLCH wide-gamut color is emerging** (fcporto) — richer accents on modern displays,
  perceptually-uniform lightness ramps. Worth adopting for v2 tokens.

### 4. Interaction polish (the "subtle pro" details)
- Custom cursor (reticle / contextual label) — we already have `Cursor.tsx`.
- Blur→sharp or mask-wipe media reveals on scroll-in.
- Full-bleed imagery/video with edge-to-edge bleed (no visible container seams — directly
  relevant to the v2 homepage "hero has visible edges" complaint).
- Magnetic CTAs, condensed/mono nav, a deliberate "SCROLL" affordance.

## Concrete recommendations for v2 (carried into the design guideline)
1. **Adopt Rive** for interactive instrument motion: value dials, engine toggle, draft
   pick-confirm burst, sentiment pulse, K/DEF "low-value" indicators. Replaces ad-hoc
   canvas/Framer work, cuts bundle, designer-tunable. Confirmed to run in Next.js (dcd).
2. **Keep Lenis** (already shipped) + add **GSAP ScrollTrigger** for the homepage scroll story.
3. **Move color tokens to OKLCH** with perceptually-uniform light/dark ramps.
4. **Lock the type system**: condensed athletic display + editorial serif accent + mono for
   all numerals/labels + neutral grotesk body. (Refines v1's Bricolage/Anton/Hanken set.)
5. **Fix full-bleed**: hero media must bleed past safe-area with mask-based reveals, killing
   the "visible edges / vibe-coded" seams called out for the v2 homepage.
6. Every motion technique ships with a `prefers-reduced-motion` static fallback (non-negotiable).
