import { quantileAt, rangeFromQuantiles } from "./quantiles";
import type { QuantilePoint } from "./types";

// Floor–median–ceiling range bar driven by the snapshot quantiles. The full
// whisker spans the configurable outer pair (default P10–P90); an emphasised
// inner band marks the interquartile "likely" core (P25–P75) when those quantiles
// exist. Meaning is carried by POSITION + labels, never colour alone (colourblind-
// safe, ACCESSIBILITY.md). Pure static markup → no animation, so it is trivially
// reduced-motion safe. Server component.
export default function RangeBar({
  quantiles,
  low = 0.1,
  high = 0.9,
  mid = 0.5,
  innerLow = 0.25,
  innerHigh = 0.75,
  decimals = 0,
  unit = "",
  label = "Projected outcome range",
}: {
  quantiles: QuantilePoint[];
  low?: number;
  high?: number;
  mid?: number;
  innerLow?: number;
  innerHigh?: number;
  decimals?: number;
  unit?: string;
  label?: string;
}) {
  const range = rangeFromQuantiles(quantiles, low, high, mid);
  if (!range) {
    return (
      <div className="text-label text-ink-muted" role="img" aria-label={`${label}: no data`}>
        No range yet
      </div>
    );
  }

  const { floor, median, ceiling } = range;
  const span = ceiling - floor || 1;
  const pct = (v: number) => Math.max(0, Math.min(100, ((v - floor) / span) * 100));
  const medianPct = pct(median);

  const q1 = quantileAt(quantiles, innerLow);
  const q3 = quantileAt(quantiles, innerHigh);
  const hasInner = q1 != null && q3 != null && q3 > q1;
  const fmt = (v: number) => `${v.toFixed(decimals)}${unit}`;
  const pctLabel = (p: number) => `P${Math.round(p * 100)}`;

  const aria =
    `${label}: ${pctLabel(low)} ${fmt(floor)}, median ${fmt(median)}, ${pctLabel(high)} ${fmt(ceiling)}` +
    (hasInner ? `; likely ${fmt(q1!)} to ${fmt(q3!)}` : "");

  return (
    <div role="img" aria-label={aria}>
      <div className="relative h-2.5 w-full rounded-full bg-hairline" aria-hidden>
        {/* full floor–ceiling whisker */}
        <div className="absolute inset-y-0 left-0 right-0 rounded-full bg-accent/25" />
        {/* interquartile "likely" core */}
        {hasInner && (
          <div
            className="absolute inset-y-0 rounded-full bg-accent/55"
            style={{ left: `${pct(q1!)}%`, right: `${100 - pct(q3!)}%` }}
          />
        )}
        {/* median marker */}
        <div
          className="absolute top-1/2 h-4 w-1 -translate-y-1/2 rounded bg-accent"
          style={{ left: `calc(${medianPct}% - 2px)` }}
        />
      </div>
      <div className="mt-2 flex justify-between font-mono text-label text-ink-muted">
        <span>
          {pctLabel(low)} {fmt(floor)}
        </span>
        <span className="text-accent">μ̃ {fmt(median)}</span>
        <span>
          {pctLabel(high)} {fmt(ceiling)}
        </span>
      </div>
    </div>
  );
}
