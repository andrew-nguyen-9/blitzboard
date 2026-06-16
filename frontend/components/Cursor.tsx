"use client";

import { useEffect, useRef, useState } from "react";

// Broadcast-reticle custom cursor: a lerped ring + a crisp center dot. Expands and
// labels itself over interactive elements ([data-cursor]). Disabled on touch and
// for reduced-motion. T02, pushed further with a contextual label.
export default function Cursor() {
  const ring = useRef<HTMLDivElement>(null);
  const dot = useRef<HTMLDivElement>(null);
  const [label, setLabel] = useState("");
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    const fine = window.matchMedia("(pointer: fine)").matches;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!fine || reduce) return;
    setEnabled(true);

    let mx = 0, my = 0, rx = 0, ry = 0, raf = 0;
    const onMove = (e: PointerEvent) => {
      mx = e.clientX; my = e.clientY;
      if (dot.current) dot.current.style.transform = `translate(${mx}px, ${my}px)`;
      const hit = (e.target as HTMLElement)?.closest("[data-cursor]") as HTMLElement | null;
      document.body.classList.toggle("cursor-hover", !!hit);
      setLabel(hit?.dataset.cursor || "");
    };
    const loop = () => {
      rx += (mx - rx) * 0.16; ry += (my - ry) * 0.16;
      if (ring.current) ring.current.style.transform = `translate(${rx}px, ${ry}px)`;
      raf = requestAnimationFrame(loop);
    };
    window.addEventListener("pointermove", onMove);
    raf = requestAnimationFrame(loop);
    return () => { window.removeEventListener("pointermove", onMove); cancelAnimationFrame(raf); };
  }, []);

  if (!enabled) return null;
  return (
    <>
      <div ref={ring} className="cursor-ring" aria-hidden>
        {label && <span className="cursor-label">{label}</span>}
      </div>
      <div ref={dot} className="cursor-dot" aria-hidden />
    </>
  );
}
