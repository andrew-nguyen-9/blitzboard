"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { motion, useInView, useMotionValue, useSpring, animate } from "framer-motion";

const EASE = [0.22, 1, 0.36, 1] as const;

// ── Reveal: mask-up entrance on scroll-into-view ─────────────────────────────
export function Reveal({ children, delay = 0, y = 28, className }: {
  children: ReactNode; delay?: number; y?: number; className?: string;
}) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-12% 0px" });
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.7, ease: EASE, delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// ── SplitText: per-character kinetic reveal (the hero entrance) ──────────────
export function SplitText({ text, className, delay = 0, stagger = 0.03 }: {
  text: string; className?: string; delay?: number; stagger?: number;
}) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });
  return (
    <span ref={ref} className={className} style={{ display: "inline-block" }}>
      {/* Accessible name for screen readers; the animated glyphs are decorative. */}
      <span className="sr-only">{text}</span>
      <span aria-hidden style={{ display: "inline-block" }}>
        {text.split(/(\s+)/).map((word, wi) => (
          <span key={wi} style={{ display: "inline-block", whiteSpace: "pre", overflow: "hidden", verticalAlign: "top" }}>
            {word.split("").map((ch, ci) => (
              <motion.span
                key={ci}
                style={{ display: "inline-block", willChange: "transform" }}
                initial={{ y: "115%", rotate: 6 }}
                animate={inView ? { y: 0, rotate: 0 } : {}}
                transition={{ duration: 0.85, ease: EASE, delay: delay + (wi * 3 + ci) * stagger }}
              >
                {ch}
              </motion.span>
            ))}
          </span>
        ))}
      </span>
    </span>
  );
}

// ── Magnetic: element drifts toward the cursor on hover ──────────────────────
export function Magnetic({ children, strength = 0.4, className }: {
  children: ReactNode; strength?: number; className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const x = useSpring(useMotionValue(0), { stiffness: 200, damping: 15 });
  const y = useSpring(useMotionValue(0), { stiffness: 200, damping: 15 });
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
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (!inView) return;
    const controls = animate(0, to, {
      duration: 1.2, ease: EASE,
      onUpdate: (v) => setVal(v),
    });
    return () => controls.stop();
  }, [inView, to]);
  return (
    <span ref={ref} className={className}>
      {val.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}
      {suffix}
    </span>
  );
}
