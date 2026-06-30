"use client";

import { LazyMotion, domAnimation } from "framer-motion";

// Loads only the `domAnimation` feature set (animations + gestures, ~half the
// weight of the full `motion` build) and only as an async chunk — so framer's
// DOM features stay out of every route's First Load JS and arrive after paint.
// `strict` forbids the heavy `motion.*` components (which would re-pull the full
// bundle): all animated elements use the lightweight `m.*` from framer-motion.
export default function MotionProvider({ children }: { children: React.ReactNode }) {
  return (
    <LazyMotion features={domAnimation} strict>
      {children}
    </LazyMotion>
  );
}
