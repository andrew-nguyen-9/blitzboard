import { ridgePath, distributionSummary, formatStat } from "@/lib/viz";
import { quantileAt } from "./quantiles";
import type { QuantilePoint } from "./types";

// Compact mini-distribution sparkline for a projection row. Reconstructs a
// representative sample set from the snapshot quantiles (evenly spaced in
// probability → the density is exact), then reuses viz.ridgePath for the violin
// curve. The animated curve (.ridge-curve) draws in; under reduced motion the CSS
// (globals.css .ridge-curve/.ridge-bar swap, honouring BOTH the OS query and the
// in-app data-motion toggle) shows a static range bar + median tick instead — so
// this reuses the shipped, information-equivalent reduced-motion fallback without
// adding any global CSS. Server component; distribution encoded by SHAPE + median
// tick, never colour alone (colourblind-safe).
const VB_W = 100;
const VB_H = 28;
const SAMPLES = 160;

export default function MiniDistribution({
  quantiles,
  label = "Outcome distribution",
  decimals = 0,
  unit = "",
  className,
}: {
  quantiles: QuantilePoint[];
  label?: string;
  decimals?: number;
  unit?: string;
  className?: string;
}) {
  // Evenly-spaced-in-p samples reproduce the density; interpolation fills the gaps.
  const samples: number[] = [];
  for (let i = 0; i < SAMPLES; i++) {
    const v = quantileAt(quantiles, (i + 0.5) / SAMPLES);
    if (v != null) samples.push(v);
  }
  const summary = distributionSummary(samples);

  if (!summary) {
    return (
      <div
        className={`grid h-7 place-items-center rounded-[var(--radius)] border border-line text-label uppercase text-ink-2 ${className ?? ""}`}
        role="img"
        aria-label={`${label}: no data`}
      >
        No distribution yet
      </div>
    );
  }

  const { min, max, median } = summary;
  const span = max - min || 1;
  const medianX = ((median - min) / span) * VB_W;
  const { d } = ridgePath(samples, { width: VB_W, height: VB_H, bins: 20, domain: [min, max] });
  const fmt = (v: number) => `${formatStat(v, { decimals })}${unit}`;
  const aria = `${label}: median ${fmt(median)}, range ${fmt(min)} to ${fmt(max)}`;

  return (
    <svg
      viewBox={`0 0 ${VB_W} ${VB_H}`}
      preserveAspectRatio="none"
      className={`h-7 w-full overflow-visible ${className ?? ""}`}
      role="img"
      aria-label={aria}
    >
      <line x1="0" y1={VB_H} x2={VB_W} y2={VB_H} stroke="var(--line)" strokeWidth="0.5" />

      {/* rich state: violin curve that draws in */}
      <g className="ridge-curve">
        <path
          className="ridge-curve__path"
          d={d}
          fill="var(--accent-soft)"
          stroke="var(--accent)"
          strokeWidth="1"
          vectorEffect="non-scaling-stroke"
        />
        <line
          x1={medianX}
          y1="0"
          x2={medianX}
          y2={VB_H}
          stroke="var(--ink-1)"
          strokeWidth="1"
          strokeDasharray="2 2"
          vectorEffect="non-scaling-stroke"
        />
      </g>

      {/* reduced-motion fallback: static range bar + median tick */}
      <g className="ridge-bar">
        <rect
          x="0"
          y={VB_H * 0.35}
          width={VB_W}
          height={VB_H * 0.3}
          fill="var(--accent-soft)"
          stroke="var(--accent)"
          strokeWidth="1"
          vectorEffect="non-scaling-stroke"
        />
        <line
          x1={medianX}
          y1={VB_H * 0.2}
          x2={medianX}
          y2={VB_H * 0.8}
          stroke="var(--ink-0)"
          strokeWidth="2"
          vectorEffect="non-scaling-stroke"
        />
      </g>
    </svg>
  );
}
