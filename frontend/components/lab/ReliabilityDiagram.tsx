import { expectedCalibrationError } from "./diagnostics";
import type { ReliabilityPoint } from "./types";

// Reliability diagram (calibration plot) from E7's reliability_curve. Hand-rolled
// SVG — no chart lib (ponytail: the geometry is a diagonal + a polyline). A
// perfectly calibrated model traces the y = x diagonal; bins above it are
// under-confident, below it over-confident (the dangerous direction). Static SVG →
// reduced-motion safe by construction. Shape + the ECE readout carry the meaning,
// not colour alone (colourblind-safe).
const VB = 100;
const PAD = 8;

export default function ReliabilityDiagram({
  points,
  label = "Reliability diagram",
  className,
}: {
  points: ReliabilityPoint[];
  label?: string;
  className?: string;
}) {
  const pts = points
    .filter((p) => Number.isFinite(p.predicted) && Number.isFinite(p.observed))
    .map((p) => ({
      predicted: Math.max(0, Math.min(1, p.predicted)),
      observed: Math.max(0, Math.min(1, p.observed)),
      count: p.count,
    }))
    .sort((a, b) => a.predicted - b.predicted);

  const ece = expectedCalibrationError(points);

  if (pts.length === 0) {
    return (
      <div
        className={`grid h-40 place-items-center rounded-[var(--radius,0.5rem)] border border-line text-label uppercase text-ink-2 ${className ?? ""}`}
        role="img"
        aria-label={`${label}: no data`}
      >
        No calibration data yet
      </div>
    );
  }

  const inner = VB - PAD * 2;
  const x = (v: number) => PAD + v * inner;
  const y = (v: number) => VB - PAD - v * inner; // invert: 0 at bottom
  const curve = pts.map((p) => `${x(p.predicted)},${y(p.observed)}`).join(" ");

  const aria =
    `${label}: ${pts.length} bins, ` +
    (ece != null ? `expected calibration error ${(ece * 100).toFixed(1)}%. ` : "") +
    pts.map((p) => `predicted ${(p.predicted * 100).toFixed(0)}% → observed ${(p.observed * 100).toFixed(0)}%`).join("; ");

  return (
    <figure className={className}>
      <svg
        viewBox={`0 0 ${VB} ${VB}`}
        className="w-full max-w-sm rounded-[var(--radius,0.5rem)] border border-line bg-surface"
        role="img"
        aria-label={aria}
      >
        {/* plot frame */}
        <rect x={PAD} y={PAD} width={inner} height={inner} fill="none" stroke="var(--line)" strokeWidth="0.4" />
        {/* perfect-calibration diagonal */}
        <line
          x1={x(0)}
          y1={y(0)}
          x2={x(1)}
          y2={y(1)}
          stroke="var(--ink-2)"
          strokeWidth="0.5"
          strokeDasharray="2 2"
        />
        {/* observed-vs-predicted polyline */}
        <polyline points={curve} fill="none" stroke="var(--accent)" strokeWidth="1.2" vectorEffect="non-scaling-stroke" />
        {pts.map((p, i) => (
          <circle key={i} cx={x(p.predicted)} cy={y(p.observed)} r="1.4" fill="var(--accent)" />
        ))}
      </svg>
      <figcaption className="mt-2 flex justify-between text-label uppercase text-ink-2">
        <span>predicted → observed</span>
        {ece != null && (
          <span className={ece > 0.1 ? "text-neg" : "text-pos"}>ECE {(ece * 100).toFixed(1)}%</span>
        )}
      </figcaption>
    </figure>
  );
}
