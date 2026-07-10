# Animation Placement Map (v4 E11)

> An audit of **where motion should (or could) live** in BlitzBoard, keyed to **real
> components and routes** that exist today. This is the companion index for
> [`ANIMATION_PROMPTS.md`](./ANIMATION_PROMPTS.md): every individual prompt names a target
> from the tables below. It is a **map, not an instruction to build** — E11 ships prompts, not
> components.

Sources this map is grounded in (do not re-derive):

- **Motion language + neon register** → `docs/design-system/NORTH_STAR.md` §Motion language,
  §Primitives, §Neon palette, §Do / Don't (F1 North Star).
- **Toolkit, performance budget, reduced-motion contract** → `docs/design-system/MOTION.md`.
- **Component reality** → `frontend/components/` (every name below resolves to a file there)
  and `frontend/app/**/page.tsx` routes.

## Legend

- **Register** — the motion class from `NORTH_STAR.md` §Motion language / `MOTION.md` toolkit:
  *ignite* (glow ramp into live/selected), *reveal* (entrance), *loop* (ambient/marquee),
  *rerank* (layout/FLIP), *instrument* (Rive state machine).
- **Kind** — **functional** (encodes state → must carry a non-color cue) vs **decorative**
  (ambience → silent, cheap, skippable). Per `NORTH_STAR.md` §Motion language.
- **Still state** — the reduced-motion resting frame. Every row has one; if a cell says
  "already stilled", the component's existing CSS contract handles it (verified in the
  component source), and a new animation must preserve that contract.

## Priority tiers (where to spend the motion budget)

- **P0 — signature surfaces** the North Star exists to make sing: hero, value dial, engine
  toggle, draft pick-confirm, trending ticker. These appear in `MOTION.md` §Signature motion
  specs and are the first prompts to run.
- **P1 — instrument readouts** that benefit from an *ignite* or Rive pass but already render
  correctly static: distribution ridge, predictability meter, tier badges, sparkline.
- **P2 — ambient / connective tissue**: nav, cursor, scroll cue, empty states, footer. Motion
  here is decorative and must stay nearly invisible.

---

## Route surfaces

| Route | Surface / component (real) | Register | Kind | Animation opportunity | Still state | NORTH_STAR § |
|-------|----------------------------|----------|------|-----------------------|-------------|--------------|
| `/` (home) | `HeroHeadline.tsx` | ignite + reveal | decorative→functional | Accent line ("war room.") already `.neon-text` (F1 proof). Add a one-shot *ignite* on first paint: glow ramps up after LCP. | Fully-lit `.neon-text`, no ramp (already stilled) | §Motion language, §Proof |
| `/` | `BlitzField.tsx` | loop | decorative | Full-formation blitz behind hero; defenders rush along `.bp-route` self-drawing paths. Neon-tint the rush lines as ambient shimmer. | Fully-drawn still SVG (already stilled via `.bp-route`) | §Primitives → Texture, §Motion language |
| `/` | `ScrollCue.tsx` | loop | decorative | Foot-of-hero "SCROLL" travel pulse; drives shared Lenis on click. | Pulse stilled, jump instant (already stilled) | §Motion language |
| `/` | `Marquee.tsx` / `Ticker.tsx` | loop | decorative | Broadcast lower-third trending ticker at ~40px/s; pause on hover/focus. | Static horizontally-scrollable list (already stilled via `.ticker`) | §Do / Don't (ration) |
| `/` | `TiltCard.tsx` | ignite | decorative | Feature cards; neon-edge *ignite* on hover/focus (raise glow, not lift geometry). | Static `.neon-edge` rim, no ramp | §Primitives → Elevation/edge |
| `/players` | `ValueDial.tsx` | ignite (CSS `.dial-fill`) | functional | 270° gauge sweep to `fraction`; neon-tint the lit arc as the "charged" readout. | Static filled arc + centered text/sr-only (already stilled via `.dial-fill`) | §Motion language, §Neon palette |
| `/players` | `EngineToggle.tsx` | rerank | functional | VORP⇄MC switch → board re-ranks; toggled engine *ignites* (glow marks the live engine). | Values/positions swap instantly; lit engine still-glowing | §Motion language, §Do / Don't |
| `/players` | `DistributionRidge.tsx` | reveal/instrument | functional | Monte-Carlo ridgeline; dial→ridge morph (Rive) on engine toggle. Shape carries meaning. | Static range bar `.ridge-bar` + median tick (already stilled) | §Motion language |
| `/players` | `PredictabilityMeter.tsx` | ignite | functional | Segmented signal-strength meter; lit segments *ignite* left-to-right. Segment count + tier word carry signal. | All lit segments static (component is already static) | §Motion language, §Neon palette |
| `/players` | `Sparkline.tsx` | reveal | decorative | Season-points trace draws in via stroke-dashoffset. | Fully-drawn static line | §Primitives → Texture |
| `/players/[id]` | `StatTable.tsx` / `PlayerTable.tsx` | reveal/rerank | functional | Row enters + value re-rank on sort/engine change (Framer `layout`). | Rows appear, list reorders instantly | §Motion language |
| `/players/[id]` | `TierBadge.tsx` | ignite | functional | Tier chip *ignites* when it is the player's live tier; shape/label carry tier, glow reinforces. | Static badge, glow present not ramped | §Do / Don't |
| `/draft` | `DraftRoom.tsx` | reveal/rerank | functional | Board is the war room; picks insert (Framer `layout`), best-available reorders via FLIP. | Row appears, list reorders instantly | `MOTION.md` §Signature specs |
| `/draft` | `DraftEndCard.tsx` | ignite + reveal | functional | Fires the moment a draft fills; grade/finish reveal, best-pick *ignites*. Celebration, ≤600ms. | Card + grade render instantly, no burst | §Motion language |
| `/draft/analysis` | `DraftAnalysis.tsx` | reveal | functional | Grade breakdown reveals section-by-section on scroll (GSAP ScrollTrigger, home-route pattern). | All sections visible, no pin | `MOTION.md` §Performance |
| `/league` | `AllTeamsBoard.tsx` | rerank | functional | League-wide value board; standings/value re-rank (Framer `layout`). | Instant reorder | §Motion language |
| `/league` | `FootballPit.tsx` / `BlueprintField.tsx` | loop/instrument | decorative | Field/blueprint backdrop; route sketches draw in (`.bp-route`), Rive swap-in point noted in source. | Fully-drawn still SVG (already stilled) | §Primitives → Texture |
| `/trades` | `TradeCalculator.tsx` / `TradeFinder.tsx` | rerank + ignite | functional | Trade value delta re-ranks both sides; the favored side *ignites* (glow marks value-add). | Instant delta, favored side still-glowing | §Motion language, §Do / Don't |
| `/waivers` | `WaiverBoard.tsx` / `WaiverScope.tsx` | rerank + ignite | functional | Waiver priority board; top target *ignites* as the live pickup signal. | Instant sort, target still-glowing | §Do / Don't |
| all | `Nav.tsx` | ignite | decorative | Active-route link carries a neon underline that *ignites* on navigate; label is the real cue. | Static neon underline on active link | §Do / Don't |
| all | `Cursor.tsx` / `CursorTooltip.tsx` | loop | decorative | Custom broadcast cursor + context tooltip; magnetic radius on CTAs (`Magnetic`). | Native cursor, no magnet (client-gated) | `MOTION.md` §Signature specs |
| all | `EmptyState.tsx` / `ConnectPrompt.tsx` | loop | decorative | Empty surfaces host the `.neon-grid` ambient wash so an offline board still reads as "live". | Static grid texture (paint-only, inert) | §Primitives → Texture |
| all | `Footer.tsx` | loop | decorative | Faint neon-grid or drifting glow; nearly invisible. | Static | §Primitives → Texture |

## The Rive seam (do not bypass)

`RiveInstrument.tsx` is the **single wrapper** for `.riv` state machines: it honors reduced
motion (loads the artboard, pauses on the resting frame) and renders a graceful fallback when
the asset is missing (ship-with-no-assets principle). Any *instrument*-register prompt (value
dial → ridge morph, draft pick-confirm burst, sentiment pulse) must target `RiveInstrument`
with a static component fallback (`ValueDial`, `DistributionRidge`, `BlueprintField`), **not**
a raw canvas. `BlueprintField.tsx` already documents the swap-in seam in its source.

## Coverage note

Every animation-bearing surface currently shipped in `frontend/components/` is accounted for
above. Static-by-design components with **no** motion opportunity are intentionally omitted:
`A11ySettings`, `AccountSettings`, `SignupForm`, `LeagueImport`, `LeagueManager`,
`LeagueSelector`, `ThemeToggle`, `ThemeScript`, `MotionProvider`, `PrefetchLink`,
`SmoothScroll`, `DistributionBar`, `Tooltip`, `Footer` (form/plumbing/settings surfaces where
motion would violate `NORTH_STAR.md` §Do / Don't rationing).
