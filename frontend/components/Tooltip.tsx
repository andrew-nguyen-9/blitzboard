import { type ReactNode } from "react";

// Opaque, theme-aware tooltip bubble. CSS-only enter/leave: the nearest ancestor
// marked `group` (and acting as the positioning context — `relative`, or already
// `absolute`) drives visibility via group-hover / group-focus-within. The bubble is
// pointer-events-none, so when it overlays a sibling (e.g. the next table row) the
// pointer falls through to that sibling — the hovered ancestor changes, this bubble
// hides and the new one shows. No JS state, no flicker, clears on row change even
// when overlapping the next row. Reduced motion: globals.css drops the fade
// (`[data-tooltip]`) for both the OS query and the in-app `data-motion` toggle.
//
// `decorative` (default false): set true when the content only duplicates data the
// host already exposes to assistive tech (e.g. the player row's value/VOR/ρ cells),
// so the bubble is aria-hidden. Otherwise pass an `id` and point the trigger's
// `aria-describedby` at it.
export default function Tooltip({
  content,
  id,
  side = "top",
  decorative = false,
  className = "",
}: {
  content: ReactNode;
  id?: string;
  side?: "top" | "bottom";
  decorative?: boolean;
  className?: string;
}) {
  const place = side === "bottom" ? "top-full mt-2" : "bottom-full mb-2";
  return (
    <span
      id={id}
      role={decorative ? undefined : "tooltip"}
      aria-hidden={decorative || undefined}
      data-tooltip
      className={`pointer-events-none absolute left-1/2 z-30 -translate-x-1/2 ${place} w-max max-w-[15rem] rounded-lg border border-line bg-surface-elevated px-3 py-2 text-left text-[0.8rem] normal-case leading-snug tracking-normal text-ink opacity-0 shadow-[var(--glow)] transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100 ${className}`}
    >
      {content}
    </span>
  );
}
