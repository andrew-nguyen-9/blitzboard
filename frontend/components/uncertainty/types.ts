// The uncertainty contract the frontend consumes from the engine snapshot
// (docs/design/v4-engine-architecture.md → {quantiles, mc_probs}). Prod ships
// quantiles + correlation + Monte-Carlo probabilities, NOT raw draws, so every
// uncertainty surface is driven by these two compact shapes. All fields optional
// so a partial (or empty) snapshot degrades cleanly to "no data" per unit.

// One point of a projection's cumulative distribution: `value` (projected points
// or VOR) is the outcome at cumulative probability `p` ∈ [0,1].
export interface QuantilePoint {
  p: number;
  value: number;
}

// Monte-Carlo outcome probabilities (mc_probs). Each is a fraction in [0,1] or
// null/absent when the snapshot hasn't published it yet → that badge is omitted.
export interface McProbs {
  bust?: number | null; // P(finishes below a replacement-level starter)
  top5?: number | null; // P(positional top-5 finish)
  beatsAdp?: number | null; // P(returns value above its ADP cost)
}

// Everything an uncertainty strip needs for one player row.
export interface PlayerUncertainty {
  quantiles: QuantilePoint[]; // sorted ascending by p
  probs?: McProbs;
  replacement?: number | null; // reference line the bust% is measured against
  unit?: string; // display suffix for range labels ("" points, " VOR", …)
}
