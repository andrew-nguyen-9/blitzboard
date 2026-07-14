import RangeBar from "./RangeBar";
import MiniDistribution from "./MiniDistribution";
import ProbabilityBadges from "./ProbabilityBadges";
import type { PlayerUncertainty } from "./types";

// The composed uncertainty surface for one projection row: probability badges +
// floor–median–ceiling range bar + mini-distribution. Every piece degrades on its
// own, and the whole strip renders a compact empty state when there is no snapshot
// data — so a fully-loaded WR and a keyless empty state both render cleanly.
// Server component; reused by player rows, the draft board (E8-draft-room) and the
// lineup. `low`/`high` pick the outer quantile pair the range bar spans.
export default function UncertaintyStrip({
  data,
  low = 0.1,
  high = 0.9,
  decimals = 0,
  showDistribution = true,
  showBadges = true,
  label = "Projection uncertainty",
  className,
}: {
  data: PlayerUncertainty | null | undefined;
  low?: number;
  high?: number;
  decimals?: number;
  showDistribution?: boolean;
  showBadges?: boolean;
  label?: string;
  className?: string;
}) {
  const hasRange = !!data && data.quantiles.length > 0;
  const hasProbs =
    !!data?.probs && (data.probs.bust != null || data.probs.top5 != null || data.probs.beatsAdp != null);

  if (!hasRange && !hasProbs) {
    return (
      <p
        className={`text-label text-ink-muted ${className ?? ""}`}
        role="status"
      >
        No uncertainty data yet — publish the engine snapshot.
      </p>
    );
  }

  const unit = data?.unit ?? "";

  return (
    <div className={`flex flex-col gap-3 ${className ?? ""}`} aria-label={label}>
      {showBadges && hasProbs && <ProbabilityBadges probs={data!.probs} />}
      {hasRange && (
        <RangeBar
          quantiles={data!.quantiles}
          low={low}
          high={high}
          decimals={decimals}
          unit={unit}
        />
      )}
      {showDistribution && hasRange && (
        <MiniDistribution quantiles={data!.quantiles} decimals={decimals} unit={unit} />
      )}
    </div>
  );
}
