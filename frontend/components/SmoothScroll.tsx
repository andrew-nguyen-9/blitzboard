"use client";

import { useEffect } from "react";
import type Lenis from "lenis";
import { setLenis } from "@/lib/lenis";

// Site-wide smooth scroll. Lenis is dynamically imported so the motion library
// stays out of the global bundle (loaded client-side, after paint). Honors
// reduced motion (OS pref or the A11ySettings data-motion override) by never
// initializing — native scroll remains.
export default function SmoothScroll() {
  useEffect(() => {
    const reduced =
      window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
      document.documentElement.getAttribute("data-motion") === "reduce";
    if (reduced) return;

    let lenis: Lenis | undefined;
    let raf = 0;
    let cancelled = false;

    import("lenis").then(({ default: Lenis }) => {
      if (cancelled) return;
      lenis = new Lenis({
        duration: 1.05,
        easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
        smoothWheel: true,
      });
      setLenis(lenis); // share with the scroll story (SCROLL cue, GSAP later)
      const loop = (time: number) => {
        lenis?.raf(time);
        raf = requestAnimationFrame(loop);
      };
      raf = requestAnimationFrame(loop);
    });

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      lenis?.destroy();
      setLenis(null);
    };
  }, []);
  return null;
}
