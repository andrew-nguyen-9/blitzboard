import type { CSSProperties } from "react";

// Kinetic split-text headline — a Server Component, so it ships ZERO JavaScript
// and the words are real, static text in the SSR HTML (this is the hero's LCP
// element; it never waits on hydration). The per-word rise is pure CSS keyframes
// (.hero-word in globals.css), staggered via a --w index, and collapses to a
// static headline under reduced motion through the same CSS contract the kit
// uses. Whitespace tokens are kept as plain (breakable) text so the line still
// wraps normally on small screens — no clipping.

type Line = { text: string; accent?: boolean };

export default function HeroHeadline({ lines, className }: { lines: Line[]; className?: string }) {
  let w = 0;
  return (
    <h1 className={className}>
      {lines.map((line, li) => (
        <span key={li} className={`hero-line${line.accent ? " text-accent" : ""}`}>
          {line.text.split(/(\s+)/).map((tok, ti) =>
            /\s/.test(tok) || tok === "" ? (
              tok
            ) : (
              <span key={ti} className="hero-word" style={{ "--w": w++ } as CSSProperties}>
                {tok}
              </span>
            ),
          )}
        </span>
      ))}
    </h1>
  );
}
