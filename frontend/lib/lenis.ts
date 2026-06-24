import type Lenis from "lenis";

// Shared handle to the live Lenis instance. SmoothScroll registers it on mount
// (and clears it on unmount / under reduced motion, when Lenis never starts).
// Scaffolding for the homepage scroll story: the SCROLL cue drives it now, and
// the v2.1.3 GSAP/ScrollTrigger story will sync against the same instance rather
// than spinning up a second smooth-scroll. Null whenever momentum scroll is off.
let instance: Lenis | null = null;

export function setLenis(l: Lenis | null): void {
  instance = l;
}

export function getLenis(): Lenis | null {
  return instance;
}
