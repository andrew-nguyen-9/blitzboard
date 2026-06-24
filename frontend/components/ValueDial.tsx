import { dialGeometry } from "@/lib/viz";

// Radial value gauge (instrument readout). A 270° arc fills to `fraction` (0..1).
// Server Component: the fill animates via a pure CSS stroke-dashoffset sweep
// (.dial-fill in globals.css), which the global reduced-motion rules collapse to
// the static final state — no client JS, no motion library, 0 KB added.
//
// Accessibility: the SVG is aria-hidden decoration; the real value lives in the
// centered text and an sr-only sentence, so screen readers get a text equivalent
// of the gauge (per ACCESSIBILITY.md "data viz has a text equivalent").
export default function ValueDial({
  fraction,
  label,
  value,
  sub,
  size = 200,
  srText,
}: {
  fraction: number;
  label: string;
  value: string;
  sub?: string;
  size?: number;
  /** Optional fuller sentence for assistive tech; defaults to `value`, `label`. */
  srText?: string;
}) {
  const r = size * 0.42;
  const cx = size / 2;
  const g = dialGeometry(fraction, r);
  const pct = Math.round(g.filledFraction * 100);

  return (
    <div
      className="relative grid place-items-center"
      style={{ width: size, height: size }}
      role="img"
      aria-label={srText ?? `${value} ${label}, ${pct}% of scale`}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="-rotate-[135deg]"
        aria-hidden
        focusable="false"
      >
        {/* track */}
        <circle
          cx={cx}
          cy={cx}
          r={r}
          fill="none"
          stroke="var(--line)"
          strokeWidth={size * 0.064}
          strokeDasharray={g.trackDasharray}
          strokeLinecap="round"
        />
        {/* fill — rests at fillOffset; .dial-fill sweeps from empty (--dial-arc) */}
        <circle
          className="dial-fill"
          cx={cx}
          cy={cx}
          r={r}
          fill="none"
          stroke="var(--accent)"
          strokeWidth={size * 0.064}
          strokeDasharray={g.trackDasharray}
          strokeDashoffset={g.fillOffset}
          strokeLinecap="round"
          style={{ "--dial-arc": `${g.arcLength}` } as React.CSSProperties}
        />
      </svg>
      <div className="absolute text-center" aria-hidden>
        <div className="font-mono text-[clamp(1.75rem,3.5vw,3rem)] font-semibold leading-none tabular-nums text-ink">
          {value}
        </div>
        <div className="mt-1 text-label uppercase text-ink-2">{label}</div>
        {sub && <div className="mt-0.5 text-label uppercase text-accent">{sub}</div>}
      </div>
    </div>
  );
}
