import { useRouter } from "next/navigation";
import { useCallback, useRef } from "react";

// Anticipatory route prefetch driven by *intent*, not by the viewport. Next's
// default Link prefetch warms every in-view link — which also fires on touch
// devices as cards scroll past, an over-fetch. Pairing `prefetch={false}` with
// this hook warms a route only when a fine pointer hovers it or it receives
// keyboard focus, so navigation feels instant on desktop while touch users fetch
// only what they actually tap. Prefetch is fired at most once per link.
export function usePrefetchOnIntent(href: string) {
  const router = useRouter();
  const warmed = useRef(false);
  const warm = useCallback(() => {
    if (warmed.current) return;
    warmed.current = true;
    router.prefetch(href);
  }, [href, router]);

  return {
    onPointerEnter: (e: React.PointerEvent) => {
      // touch "hover" is a tap-and-hold artefact — skip it so taps don't prefetch.
      if (e.pointerType !== "touch") warm();
    },
    onFocus: warm,
  };
}
