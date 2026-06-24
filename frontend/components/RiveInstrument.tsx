"use client";

import { useEffect, useState } from "react";
import { useRive } from "@rive-app/react-canvas";
import { useReducedMotion } from "@/lib/reducedMotion";

// Wrapper for Rive "instrument" animations. Honors reduced motion (OS pref or
// the A11ySettings data-motion override, via the shared useReducedMotion hook)
// by loading the artboard but pausing on its resting frame instead of playing.
// Renders a graceful fallback if the .riv fails to load (ship-with-no-assets
// principle).

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
