import { predictabilityBand } from "@/lib/viz";

// Segmented "signal-strength" meter for a 0..1 predictability score (D13). The
// number of lit segments AND the tier word both carry the signal, so meaning
// survives any colourblind mode (colour is reinforcement, not the only cue).
// Static — no motion. Server Component.
export default function PredictabilityMeter({
  score,
  label = "Predictability",
  className,
}: {
  score: number;
  label?: string;
  className?: string;
}) {
  const band = predictabilityBand(score);
  const toneVar = `var(--${band.tone})`;

  return (
    <div
      role="img"
      aria-label={`${label}: ${band.tier} (${band.lit} of ${band.total})`}
      className={className}
    >
      <div className="flex gap-1" aria-hidden>
        {Array.from({ length: band.total }).map((_, i) => (
          <span
            key={i}
            className="h-1.5 flex-1 rounded-full"
            style={{ background: i < band.lit ? toneVar : "var(--line)" }}
          />
        ))}
      </div>
      <div className="mt-1.5 flex items-center justify-between gap-2" aria-hidden>
        <span className="text-label uppercase text-ink-2">{label}</span>
        {/* tone shown as a swatch (graphic); the tier word stays high-contrast ink */}
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-full" style={{ background: toneVar }} />
          <span className="text-label font-semibold uppercase text-ink">{band.tier}</span>
        </span>
      </div>
    </div>
  );
}
