"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { motion, useInView, useMotionValue, useSpring, animate } from "framer-motion";
import { useReducedMotion } from "@/lib/reducedMotion";

const EASE = [0.22, 1, 0.36, 1] as const;

// Motion is enhancement, never the substrate. Every primitive here renders its
// resting (visible) state on the server and first client paint, then layers
// animation on AFTER mount and only when motion is allowed (OS + in-app toggle,
// via useReducedMotion). That keeps SSR markup identical to the client's first
// paint (no hydration drift, no flash) and guarantees content is present even if
// JS never runs — see lib/reducedMotion.ts.

/** False on the server and first client paint, true after mount. */
function useMounted() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return mounted;
}

// ── Reveal: mask-up entrance on scroll-into-view ─────────────────────────────
export function Reveal({ children, delay = 0, y = 28, className }: {
  children: ReactNode; delay?: number; y?: number; className?: string;
}) {
  const reduced = useReducedMotion();
  const mounted = useMounted();
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-12% 0px" });
  // Hidden only when enhancing AND not yet on screen. Until mounted (SSR + first
  // paint) and under reduced motion the element sits at rest, fully visible.
  const enhance = mounted && !reduced;
  const hidden = enhance && !inView;
  return (
    <motion.div
      ref={ref}
      className={className}
      initial={false}
      animate={{ opacity: hidden ? 0 : 1, y: hidden ? y : 0 }}
      transition={{ duration: 0.7, ease: EASE, delay }}
    >
      {children}
    </motion.div>
  );
}

// ── Magnetic: element drifts toward the cursor on hover ──────────────────────
// Pointer-driven, so there is no entrance to reconcile — it just renders a plain
// span until it is safe to enhance (mounted, motion allowed, fine pointer). A
// motion.span at rest is visually identical to the plain span, so the post-mount
// swap is seamless.
export function Magnetic({ children, strength = 0.4, className }: {
  children: ReactNode; strength?: number; className?: string;
}) {
  const reduced = useReducedMotion();
  const mounted = useMounted();
  const [fine, setFine] = useState(false);
  useEffect(() => {
    setFine(window.matchMedia("(pointer: fine)").matches);
  }, []);
  const ref = useRef<HTMLSpanElement>(null);
  const x = useSpring(useMotionValue(0), { stiffness: 200, damping: 15 });
  const y = useSpring(useMotionValue(0), { stiffness: 200, damping: 15 });

  if (!(mounted && !reduced && fine)) {
    return <span className={className}>{children}</span>;
  }

  function onMove(e: React.PointerEvent) {
    const el = ref.current; if (!el) return;
    const r = el.getBoundingClientRect();
    x.set((e.clientX - (r.left + r.width / 2)) * strength);
    y.set((e.clientY - (r.top + r.height / 2)) * strength);
  }
  return (
    <motion.span
      ref={ref}
      onPointerMove={onMove}
      onPointerLeave={() => { x.set(0); y.set(0); }}
      style={{ x, y, display: "inline-block" }}
      className={className}
    >
      {children}
    </motion.span>
  );
}

// ── CountUp: scoreboard number that tallies up when scrolled into view ───────
export function CountUp({ to, decimals = 0, className, suffix = "" }: {
  to: number; decimals?: number; className?: string; suffix?: string;
}) {
  const reduced = useReducedMotion();
  const mounted = useMounted();
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (reduced || !mounted || !inView) return;
    const controls = animate(0, to, { duration: 1.2, ease: EASE, onUpdate: (v) => setVal(v) });
    return () => controls.stop();
  }, [reduced, mounted, inView, to]);
  // Show the final number on the server, for no-JS, and under reduced motion;
  // only the live animation drives the intermediate value.
  const display = mounted && !reduced ? val : to;
  return (
    <span ref={ref} className={className}>
      {display.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}
      {suffix}
    </span>
  );
}
