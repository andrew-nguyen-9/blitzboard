// Pure quantile / probability geometry for the uncertainty primitives. No DOM, no
// React — the math is unit-tested in isolation (quantiles.test.ts) and reused by
// the range bar, mini-distribution and probability badges.
import { gaussianSamples } from "@/lib/viz";
import type { QuantilePoint } from "./types";

// Drop non-finite entries, sort ascending by cumulative probability.
export function sortQuantiles(qs: QuantilePoint[]): QuantilePoint[] {
  return qs
    .filter((q) => Number.isFinite(q.p) && Number.isFinite(q.value))
    .sort((a, b) => a.p - b.p);
}

// Linear-interpolate the outcome at cumulative probability `p` from a sorted set;
// clamps to the endpoints outside the sampled range. Null when there's nothing.
export function quantileAt(qs: QuantilePoint[], p: number): number | null {
  const s = sortQuantiles(qs);
  if (s.length === 0) return null;
  if (p <= s[0].p) return s[0].value;
  if (p >= s[s.length - 1].p) return s[s.length - 1].value;
  for (let i = 1; i < s.length; i++) {
    if (p <= s[i].p) {
      const a = s[i - 1];
      const b = s[i];
      const t = (p - a.p) / (b.p - a.p || 1);
      return a.value + t * (b.value - a.value);
    }
  }
  return s[s.length - 1].value;
}

export interface Range {
  floor: number;
  median: number;
  ceiling: number;
}

// floor–median–ceiling from a configurable quantile pair (default P10/P90). Null
// unless all three interpolate to finite outcomes.
export function rangeFromQuantiles(
  qs: QuantilePoint[],
  low = 0.1,
  high = 0.9,
  mid = 0.5,
): Range | null {
  const floor = quantileAt(qs, low);
  const median = quantileAt(qs, mid);
  const ceiling = quantileAt(qs, high);
  if (floor == null || median == null || ceiling == null) return null;
  return { floor, median, ceiling };
}

// Quantile points of N(mean, stdev) at the requested cumulative probabilities,
// reusing viz.gaussianSamples (deterministic probit sampling → SSR-safe, no RNG,
// no hydration drift). Degenerate σ collapses to a point mass at the mean.
export function gaussianQuantiles(
  mean: number,
  stdev: number,
  ps: number[] = [0.1, 0.25, 0.5, 0.75, 0.9],
): QuantilePoint[] {
  if (!(stdev > 0) || !Number.isFinite(mean)) return ps.map((p) => ({ p, value: mean }));
  const n = 1000;
  const samples = gaussianSamples(mean, stdev, n); // sorted asc at (i+0.5)/n
  return ps.map((p) => {
    const idx = Math.min(n - 1, Math.max(0, Math.round(p * n - 0.5)));
    return { p, value: samples[idx] };
  });
}

// Standard-normal CDF via the Abramowitz & Stegun 7.1.26 erf approximation
// (|error| < 1.5e-7). Degenerate σ → a step at the mean.
export function normCdf(x: number, mean = 0, stdev = 1): number {
  if (!(stdev > 0)) return x < mean ? 0 : x > mean ? 1 : 0.5;
  const z = (x - mean) / (stdev * Math.SQRT2);
  const t = 1 / (1 + 0.3275911 * Math.abs(z));
  const y =
    1 -
    ((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) * t + 0.254829592) *
      t *
      Math.exp(-z * z);
  const erf = z >= 0 ? y : -y;
  return 0.5 * (1 + erf);
}

// P(outcome < line) under N(mean, stdev): the "bust below the replacement line"
// probability we can compute from a stored projection even before mc_probs ship.
export function bustProbability(mean: number, stdev: number, line: number | null | undefined): number | null {
  if (line == null || !Number.isFinite(line) || !Number.isFinite(mean)) return null;
  return normCdf(line, mean, stdev);
}

// Clamp a raw fraction to a displayable [0,1] probability; null passes through.
export function asProbability(v: number | null | undefined): number | null {
  if (v == null || !Number.isFinite(v)) return null;
  return v < 0 ? 0 : v > 1 ? 1 : v;
}
