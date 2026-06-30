"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { Reveal } from "@/components/motion";
import { useReducedMotion } from "@/lib/reducedMotion";
import { usePrefetchOnIntent } from "@/lib/usePrefetchOnIntent";

// 3D tilt card with a cursor-tracking glare — the homepage section tiles.
// The scroll-in entrance is delegated to Reveal (SSR-visible, reduced-motion
// safe, armed only below the fold). The tilt itself is purely additive: it only
// engages after mount on a fine pointer with motion allowed, so the card renders
// flat and static on the server, for no-JS, on touch, and under reduced motion —
// at rest the tilted and flat cards are identical, so enabling it is seamless.
export default function TiltCard({
  href, label, desc, index = 0,
}: {
  href: string; label: string; desc: string; index?: number;
}) {
  const reduced = useReducedMotion();
  const prefetch = usePrefetchOnIntent(href);
  const [enabled, setEnabled] = useState(false);
  useEffect(() => {
    setEnabled(!reduced && window.matchMedia("(pointer: fine)").matches);
  }, [reduced]);

  const ref = useRef<HTMLAnchorElement>(null);
  const mx = useMotionValue(0.5);
  const my = useMotionValue(0.5);
  const rx = useSpring(useTransform(my, [0, 1], [7, -7]), { stiffness: 150, damping: 15 });
  const ry = useSpring(useTransform(mx, [0, 1], [-7, 7]), { stiffness: 150, damping: 15 });
  const glareX = useTransform(mx, (v) => `${v * 100}%`);
  const glareY = useTransform(my, (v) => `${v * 100}%`);
  const glareBg = useTransform([glareX, glareY], ([x, y]) =>
    `radial-gradient(380px circle at ${x} ${y}, var(--accent-soft), transparent 60%)`);

  function onMove(e: React.PointerEvent) {
    if (!enabled) return;
    const r = ref.current?.getBoundingClientRect(); if (!r) return;
    mx.set((e.clientX - r.left) / r.width);
    my.set((e.clientY - r.top) / r.height);
  }

  return (
    <Reveal delay={index * 0.06} className="h-full [perspective:900px]">
      <Link
        ref={ref}
        href={href}
        prefetch={false}
        data-cursor="open"
        onPointerMove={onMove}
        onPointerEnter={prefetch.onPointerEnter}
        onFocus={prefetch.onFocus}
        onPointerLeave={() => { mx.set(0.5); my.set(0.5); }}
        className="group relative block h-full"
      >
        <motion.div
          style={enabled ? { rotateX: rx, rotateY: ry, transformStyle: "preserve-3d" } : undefined}
          className="glass relative flex h-full flex-col overflow-hidden p-6"
        >
          {/* cursor glare — only present when the tilt is engaged */}
          {enabled && (
            <motion.div
              aria-hidden
              className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
              style={{ background: glareBg }}
            />
          )}
          <div className="flex items-center justify-between" style={enabled ? { transform: "translateZ(40px)" } : undefined}>
            <h3 className="font-display text-heading link-wipe">{label}</h3>
            <span className="text-label text-accent opacity-0 transition group-hover:opacity-100">↗</span>
          </div>
          <p className="mt-2 text-body text-ink-2" style={enabled ? { transform: "translateZ(20px)" } : undefined}>{desc}</p>
        </motion.div>
      </Link>
    </Reveal>
  );
}
