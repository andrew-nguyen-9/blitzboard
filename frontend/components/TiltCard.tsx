"use client";

import Link from "next/link";
import { useRef } from "react";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";

// 3D tilt card with a cursor-tracking glare. The section tiles on the homepage.
// Pointer position → rotateX/Y (springed) + a radial highlight that follows the cursor.
export default function TiltCard({
  href, label, desc, index = 0,
}: {
  href: string; label: string; desc: string; index?: number;
}) {
  const ref = useRef<HTMLAnchorElement>(null);
  const mx = useMotionValue(0.5);
  const my = useMotionValue(0.5);
  const rx = useSpring(useTransform(my, [0, 1], [7, -7]), { stiffness: 150, damping: 15 });
  const ry = useSpring(useTransform(mx, [0, 1], [-7, 7]), { stiffness: 150, damping: 15 });
  const glareX = useTransform(mx, (v) => `${v * 100}%`);
  const glareY = useTransform(my, (v) => `${v * 100}%`);

  function onMove(e: React.PointerEvent) {
    const r = ref.current?.getBoundingClientRect(); if (!r) return;
    mx.set((e.clientX - r.left) / r.width);
    my.set((e.clientY - r.top) / r.height);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 26 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-10% 0px" }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1], delay: index * 0.06 }}
      style={{ perspective: 900 }}
    >
      <Link
        ref={ref}
        href={href}
        data-cursor="open"
        onPointerMove={onMove}
        onPointerLeave={() => { mx.set(0.5); my.set(0.5); }}
        className="group relative block"
      >
        <motion.div
          style={{ rotateX: rx, rotateY: ry, transformStyle: "preserve-3d" }}
          className="glass relative overflow-hidden p-6"
        >
          {/* cursor glare */}
          <motion.div
            aria-hidden
            className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
            style={{ background: useTransform([glareX, glareY], ([x, y]) => `radial-gradient(380px circle at ${x} ${y}, var(--accent-soft), transparent 60%)`) }}
          />
          <div className="flex items-center justify-between" style={{ transform: "translateZ(40px)" }}>
            <h3 className="font-display text-heading link-wipe">{label}</h3>
            <span className="text-label text-accent opacity-0 transition group-hover:opacity-100">↗</span>
          </div>
          <p className="mt-2 text-body text-ink-muted" style={{ transform: "translateZ(20px)" }}>{desc}</p>
        </motion.div>
      </Link>
    </motion.div>
  );
}
