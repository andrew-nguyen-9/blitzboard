// Minimal SVG sparkline for a player's season-points history.
export default function Sparkline({
  points,
  width = 280,
  height = 64,
}: {
  points: number[];
  width?: number;
  height?: number;
}) {
  if (points.length < 2) {
    return <div className="text-label text-ink-muted">Not enough history</div>;
  }
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const pad = 4;
  const coords = points.map((p, i) => {
    const x = pad + (i / (points.length - 1)) * (width - 2 * pad);
    const y = height - pad - ((p - min) / span) * (height - 2 * pad);
    return [x, y] as const;
  });
  const path = coords.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const [lx, ly] = coords[coords.length - 1];
  return (
    <svg width={width} height={height} className="overflow-visible">
      <path d={path} fill="none" stroke="var(--accent)" strokeWidth="2" />
      <circle cx={lx} cy={ly} r="3.5" fill="var(--accent)" />
    </svg>
  );
}
