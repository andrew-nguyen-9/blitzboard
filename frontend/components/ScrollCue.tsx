"use client";

import { useReducedMotion } from "@/lib/reducedMotion";
import { getLenis } from "@/lib/lenis";

// Broadcast "SCROLL" affordance at the foot of the hero. It is a real anchor, so
// it works with no JS (native in-page jump) and is keyboard-operable with the
// global focus ring. With JS it drives the shared Lenis instance for a momentum
// scroll, falling back to scrollIntoView; under reduced motion the travel pulse
// is stilled (CSS) and the jump is instant. `target` is a CSS selector/hash.
export default function ScrollCue({ target, label = "Scroll" }: { target: string; label?: string }) {
  const reduced = useReducedMotion();

  function onClick(e: React.MouseEvent<HTMLAnchorElement>) {
    const el = document.querySelector(target) as HTMLElement | null;
    if (!el) return; // let the native hash navigation handle it
    e.preventDefault();
    const lenis = getLenis();
    if (lenis && !reduced) lenis.scrollTo(el);
    else el.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
  }

  return (
    <a
      href={target}
      onClick={onClick}
      data-cursor="scroll"
      aria-label="Scroll to content"
      className="scroll-cue mt-14 inline-flex flex-col items-center gap-3 text-label uppercase tracking-[0.3em] text-ink-2 transition hover:text-ink"
    >
      <span>{label}</span>
      <span className="scroll-cue__line" aria-hidden />
    </a>
  );
}
