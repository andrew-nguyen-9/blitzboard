// Floor / mean / ceiling range bar (the projection-as-distribution, per D5).
export default function DistributionBar({
  floor,
  mean,
  ceiling,
}: {
  floor: number;
  mean: number;
  ceiling: number;
}) {
  const span = ceiling - floor || 1;
  const meanPct = ((mean - floor) / span) * 100;
  return (
    <div>
      <div className="relative h-2.5 w-full rounded-full bg-hairline">
        <div className="absolute inset-y-0 left-0 rounded-full bg-accent/30" style={{ width: "100%" }} />
        <div
          className="absolute top-1/2 h-4 w-1 -translate-y-1/2 rounded bg-accent"
          style={{ left: `calc(${meanPct}% - 2px)` }}
        />
      </div>
      <div className="mt-2 flex justify-between font-mono text-label text-ink-muted">
        <span>floor {floor.toFixed(0)}</span>
        <span className="text-accent">μ {mean.toFixed(0)}</span>
        <span>ceil {ceiling.toFixed(0)}</span>
      </div>
    </div>
  );
}
