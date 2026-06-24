import { useEffect, useState } from "react";

// Single source of truth for "should motion be suppressed?". Two signals matter:
//   1. the OS setting    → prefers-reduced-motion media query
//   2. the in-app toggle → A11ySettings writes data-motion="reduce" on <html>
// Framer's own useReducedMotion() reads only (1), so any JS-driven motion must
// use this hook to also honor (2). Mirrors the resting-frame logic in
// RiveInstrument (which imports the same hook).

/** Pure decision so the OS/attribute combination is unit-testable. */
export function isReducedMotion(prefersReduced: boolean, motionAttr: string | null): boolean {
  return prefersReduced || motionAttr === "reduce";
}

function read(): boolean {
  if (typeof window === "undefined") return false;
  return isReducedMotion(
    window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    document.documentElement.getAttribute("data-motion"),
  );
}

export function useReducedMotion(): boolean {
  // Synchronous initial read so the first client render already reflects the
  // preference (no flash of motion before an effect corrects it).
  const [reduced, setReduced] = useState(read);
  useEffect(() => {
    const update = () => setReduced(read());
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    mq.addEventListener("change", update);
    // React to the in-app toggle flipping data-motion at runtime.
    const obs = new MutationObserver(update);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-motion"] });
    return () => {
      mq.removeEventListener("change", update);
      obs.disconnect();
    };
  }, []);
  return reduced;
}
