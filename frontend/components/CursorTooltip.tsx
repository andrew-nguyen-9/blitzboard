"use client";

import { Fragment, useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { useReducedMotion } from "@/lib/reducedMotion";
import type { TipRow } from "@/lib/playerTooltip";

// Shared floating info card that renders AT the cursor and FOLLOWS it (fixed,
// pointer-tracked) — distinct from the CSS group-hover green Tooltip.tsx. f2 owns
// only the chrome + pointer plumbing; consumers pass content (reuse
// lib/playerTooltip.ts `playerTooltipRows` → TipRow[]). Mirrors Cursor.tsx: one
// pointermove listener, fixed translate, guarded by (pointer: fine). The card is
// decorative (aria-hidden) — the consumer's row cells already expose the data to AT.

export interface TipContent {
  title: string;
  rows: TipRow[];
}

// Same markup PlayerTable's hover card uses, so the look is identical.
const BASE =
  "fixed left-0 top-0 z-[60] pointer-events-none w-max max-w-[15rem] rounded-lg border border-line bg-surface-elevated px-3 py-2 text-left text-[0.8rem] normal-case leading-snug tracking-normal text-ink shadow-[var(--glow)]";

/** Pure: fade only when motion is allowed; position itself is never transitioned. */
export function cursorTipClass(reduced: boolean): string {
  return reduced ? BASE : `${BASE} transition-opacity duration-150`;
}

/** Pure: keep the card on-screen — down-right of the cursor, flipped at the right/bottom edge. */
export function cursorTipOffset(
  x: number, y: number, w: number, h: number, vw: number, vh: number, gap = 14,
): { x: number; y: number } {
  return {
    x: x + gap + w > vw ? Math.max(0, x - gap - w) : x + gap,
    y: y + gap + h > vh ? Math.max(0, y - gap - h) : y + gap,
  };
}

/** Pure: absent/empty rows render nothing (null-safe `show`). */
export function cursorTipContent(c: TipContent | null): TipContent | null {
  return c && c.rows.length > 0 ? c : null;
}

export function useCursorTooltip(): {
  show: (c: TipContent) => void;
  hide: () => void;
  element: ReactNode;
} {
  const [content, setContent] = useState<TipContent | null>(null);
  const [fine, setFine] = useState(false);
  const reduced = useReducedMotion();
  const card = useRef<HTMLDivElement>(null);

  useEffect(() => setFine(window.matchMedia("(pointer: fine)").matches), []);

  const active = cursorTipContent(content); // stable ref: === content or null

  useEffect(() => {
    if (!fine || !active) return;
    const onMove = (e: PointerEvent) => {
      const el = card.current;
      if (!el) return;
      const { x, y } = cursorTipOffset(
        e.clientX, e.clientY, el.offsetWidth, el.offsetHeight, window.innerWidth, window.innerHeight,
      );
      el.style.transform = `translate(${x}px, ${y}px)`;
      el.style.opacity = "1"; // hidden until first move positions it
    };
    window.addEventListener("pointermove", onMove);
    return () => window.removeEventListener("pointermove", onMove);
  }, [fine, active]);

  const show = useCallback((c: TipContent) => setContent(c), []);
  const hide = useCallback(() => setContent(null), []);

  const element = fine && active ? (
    <div ref={card} aria-hidden className={cursorTipClass(reduced)} style={{ opacity: 0 }}>
      <p className="mb-1.5 font-semibold text-ink">{active.title}</p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-0.5 font-mono tabular-nums">
        {active.rows.map((r) => (
          <Fragment key={r.label}>
            <dt className="text-ink-muted">{r.label}</dt>
            <dd className="text-right text-ink">{r.value}</dd>
          </Fragment>
        ))}
      </dl>
    </div>
  ) : null;

  return { show, hide, element };
}
