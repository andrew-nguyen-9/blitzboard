// Builds a PlayerUncertainty from the shapes the frontend already has (the value
// row + ensemble projection), so the uncertainty strip works TODAY and lights up
// further as the engine snapshot ships richer quantiles/mc_probs. Additive: it
// reads an optional `mc_probs` bag if a value row carries one, otherwise derives
// what's honestly computable and leaves the rest undefined (→ badge omitted).
import { bustProbability, gaussianQuantiles, asProbability } from "./quantiles";
import type { PlayerUncertainty, QuantilePoint } from "./types";

// Loose input types: the detail page reads `value`/`projection` as `any` from
// Supabase, so we accept the fields we use and tolerate the rest.
export interface ValueLike {
  value?: number | null;
  boom?: number | null; // P90 outcome
  bust?: number | null; // P10 outcome
  adp?: number | null;
  rank?: number | null;
  replacement?: number | null;
  // Forward-compatible: the engine snapshot's mc_probs, if published onto the row.
  mc_probs?: { bust?: number | null; top5?: number | null; beats_adp?: number | null } | null;
}
export interface ProjectionLike {
  mean?: number | null;
  stdev?: number | null;
  floor?: number | null;
  ceiling?: number | null;
}

const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);

export function playerUncertainty(
  value: ValueLike | null | undefined,
  projection: ProjectionLike | null | undefined,
  unit = "",
): PlayerUncertainty | null {
  const mean = num(projection?.mean);
  const stdev = num(projection?.stdev);
  const floor = num(projection?.floor);
  const ceiling = num(projection?.ceiling);

  let quantiles: QuantilePoint[] = [];
  if (mean != null && stdev != null && stdev > 0) {
    // Full distribution from the stored projection mean + spread.
    quantiles = gaussianQuantiles(mean, stdev);
  } else {
    // Fall back to whatever discrete quantiles exist: floor/mean/ceiling from the
    // projection, or the value row's bust(P10)/value(P50)/boom(P90) band.
    const p10 = floor ?? num(value?.bust);
    const p50 = mean ?? num(value?.value);
    const p90 = ceiling ?? num(value?.boom);
    quantiles = [
      p10 != null ? { p: 0.1, value: p10 } : null,
      p50 != null ? { p: 0.5, value: p50 } : null,
      p90 != null ? { p: 0.9, value: p90 } : null,
    ].filter((q): q is QuantilePoint => q != null);
  }

  const replacement = num(value?.replacement);
  const mc = value?.mc_probs ?? null;

  // bust%: prefer a published mc_probs.bust; else compute P(X < replacement) from
  // the projection gaussian (a real, meaningful probability, not a fabrication).
  const bust =
    asProbability(mc?.bust) ??
    (mean != null && stdev != null ? bustProbability(mean, stdev, replacement) : null);

  const probs = {
    bust,
    top5: asProbability(mc?.top5), // awaits engine mc_probs → undefined omits the badge
    beatsAdp: asProbability(mc?.beats_adp),
  };

  // Nothing to draw at all → let the caller render its empty state.
  if (quantiles.length === 0 && bust == null && probs.top5 == null && probs.beatsAdp == null) {
    return null;
  }

  return { quantiles, probs, replacement, unit };
}
