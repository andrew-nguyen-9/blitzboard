import { ridgePath, distributionSummary, formatStat } from "@/lib/viz";

// Monte-Carlo boom/bust viz. The smooth ridgeline (violin) is the rich state; a
// static range bar (min..max with a median marker) is the reduced-motion
// fallback. Server Component — both render, CSS swaps them (.ridge-curve /
// .ridge-bar in globals.css). Distribution is encoded by SHAPE + a labelled
// median tick, never colour alone (colourblind-safe per ACCESSIBILITY.md).
const VB_W = 120;
const VB_H = 40;

export default function DistributionRidge({
  samples,
  label = "Outcome distribution",
  decimals = 1,
  className,
}: {
  samples: number[];
  label?: string;
  decimals?: number;
  className?: string;
}) {
  const summary = distributionSummary(samples);

  if (!summary) {
    return (
      <div
        className={`grid h-10 place-items-center rounded-[var(--radius)] border border-line text-label uppercase text-ink-2 ${className ?? ""}`}
        role="img"
        aria-label={`${label}: no data`}
      >
        No distribution yet
      </div>
    );
  }

  const { min, max, median, mean } = summary;
  const span = max - min || 1;
  const xOf = (v: number) => ((v - min) / span) * VB_W;
  const { d } = ridgePath(samples, { width: VB_W, height: VB_H, bins: 24, domain: [min, max] });
  const medianX = xOf(median);

  const aria =
    `${label}: median ${formatStat(median, { decimals })}, ` +
    `mean ${formatStat(mean, { decimals })}, ` +
    `range ${formatStat(min, { decimals })} to ${formatStat(max, { decimals })}`;

  return (
    <svg
      viewBox={`0 0 ${VB_W} ${VB_H}`}
      preserveAspectRatio="none"
      className={`h-10 w-full overflow-visible ${className ?? ""}`}
      role="img"
      aria-label={aria}
    >
      {/* baseline */}
      <line x1="0" y1={VB_H} x2={VB_W} y2={VB_H} stroke="var(--line)" strokeWidth="0.5" />

      {/* rich state: violin curve */}
      <g className="ridge-curve">
        <path className="ridge-curve__path" d={d} fill="var(--accent-soft)" stroke="var(--accent)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
        <line x1={medianX} y1="0" x2={medianX} y2={VB_H} stroke="var(--ink-1)" strokeWidth="1" strokeDasharray="2 2" vectorEffect="non-scaling-stroke" />
      </g>

      {/* reduced-motion fallback: static range bar + median tick */}
      <g className="ridge-bar">
        <rect x="0" y={VB_H * 0.35} width={VB_W} height={VB_H * 0.3} fill="var(--accent-soft)" stroke="var(--accent)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
        <line x1={medianX} y1={VB_H * 0.2} x2={medianX} y2={VB_H * 0.8} stroke="var(--ink-0)" strokeWidth="2" vectorEffect="non-scaling-stroke" />
      </g>
    </svg>
  );
}
