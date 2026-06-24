"use client";

import { useEffect, useState } from "react";
import { useRive } from "@rive-app/react-canvas";

// Wrapper for Rive "instrument" animations. Honors reduced motion (OS pref or
// the A11ySettings data-motion override) by loading the artboard but pausing on
// its resting frame instead of playing. Renders a graceful fallback if the .riv
// fails to load (ship-with-no-assets principle).

function readReduced() {
  return (
    window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
    document.documentElement.getAttribute("data-motion") === "reduce"
  );
}

function useReducedMotion() {
  // Synchronous first-render value so autoplay is correct from the start (no
  // flash of motion before snapping to rest).
  const [reduced, setReduced] = useState(() =>
    typeof window === "undefined" ? false : readReduced(),
  );
  useEffect(() => {
    const update = () => setReduced(readReduced());
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    mq.addEventListener("change", update);
    const obs = new MutationObserver(update);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-motion"] });
    return () => {
      mq.removeEventListener("change", update);
      obs.disconnect();
    };
  }, []);
  return reduced;
}

export default function RiveInstrument({
  src,
  ariaLabel,
  className,
  stateMachines,
  animations,
  fallback = null,
}: {
  src: string;
  ariaLabel: string;
  className?: string;
  stateMachines?: string | string[];
  animations?: string | string[];
  fallback?: React.ReactNode;
}) {
  const reduced = useReducedMotion();
  const [failed, setFailed] = useState(false);

  const { rive, RiveComponent } = useRive({
    src,
    stateMachines,
    animations,
    autoplay: !reduced,
    onLoadError: () => setFailed(true),
  });

  // React to a live motion-preference change after load.
  useEffect(() => {
    if (!rive) return;
    reduced ? rive.pause() : rive.play();
  }, [rive, reduced]);

  if (failed) return <>{fallback}</>;
  return <RiveComponent role="img" aria-label={ariaLabel} className={className} />;
}
