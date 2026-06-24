"use client";

import Link from "next/link";
import type { ComponentProps } from "react";
import { usePrefetchOnIntent } from "@/lib/usePrefetchOnIntent";

// A next/link that prefetches on intent (fine-pointer hover or keyboard focus)
// instead of eagerly on viewport entry — see usePrefetchOnIntent. Use for the
// homepage's primary CTAs so desktop/keyboard navigation is instant without
// over-fetching on touch. Forwards all Link props (className, data-*, etc.).
export default function PrefetchLink({
  href,
  children,
  ...rest
}: ComponentProps<typeof Link>) {
  const intent = usePrefetchOnIntent(typeof href === "string" ? href : href.toString());
  return (
    <Link href={href} prefetch={false} onPointerEnter={intent.onPointerEnter} onFocus={intent.onFocus} {...rest}>
      {children}
    </Link>
  );
}
