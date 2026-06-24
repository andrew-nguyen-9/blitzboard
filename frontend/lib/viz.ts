// Pure geometry/format helpers for the instrument primitives. No DOM, no React —
// kept here so the math is unit-testable in isolation (see viz.test.ts).

function clamp01(n: number): number {
  // NaN-safe: anything that isn't a finite number reads as empty.
  if (!Number.isFinite(n)) return 0;
  return n < 0 ? 0 : n > 1 ? 1 : n;
}

/**
 * Geometry for the radial ValueDial: a 270° arc (gap at the bottom) whose fill
 * tracks `fraction` (0..1). Returns SVG `stroke-dasharray` strings so the
 * component is pure markup over these values.
 */
export function dialGeometry(fraction: number, radius: number, arcFraction = 0.75) {
  const f = clamp01(fraction);
  const circumference = 2 * Math.PI * radius;
  const arcLen = circumference * arcFraction;
  return {
    circumference,
    arcLength: arcLen,
    filledFraction: f,
    trackDasharray: `${arcLen} ${circumference}`,
    fillDasharray: `${arcLen * f} ${circumference}`,
    // Offset that reveals exactly `f` of the arc when dasharray = trackDasharray.
    // Animating from `arcLen` (empty) to this value sweeps the fill in.
    fillOffset: arcLen * (1 - f),
  };
}

const round = (n: number) => Math.round(n * 100) / 100;

export interface RidgeBox {
  width: number;
  height: number;
  bins: number;
  domain?: [number, number];
}

/**
 * Bins Monte-Carlo `samples` into a normalized density curve and returns a
 * closed SVG area path (baseline at the bottom). The modal bin reaches full
 * height; empty input degrades to a flat baseline. Never emits NaN.
 */
export function ridgePath(samples: number[], box: RidgeBox) {
  const { width, height, bins } = box;
  const clean = samples.filter(Number.isFinite);
  const counts = new Array(bins).fill(0);

  if (clean.length > 0) {
    const [lo, hi] = box.domain ?? [Math.min(...clean), Math.max(...clean)];
    const span = hi - lo;
    for (const v of clean) {
      // Zero-width domain (all-equal samples) collapses to the first bin.
      const idx = span === 0 ? 0 : Math.min(bins - 1, Math.floor(((v - lo) / span) * bins));
      counts[idx] += 1;
    }
  }

  const peak = Math.max(...counts);
  const densities: number[] = counts.map((c) => (peak === 0 ? 0 : c / peak));

  const points = densities.map((dens, i) => ({
    x: round(((i + 0.5) / bins) * width),
    y: round(height - dens * height),
  }));

  const line = points.map((p) => `L${p.x},${p.y}`).join(" ");
  const d = `M0,${height} ${line} L${width},${height} Z`;

  return { d, densities, points };
}

export interface DistributionSummary {
  min: number;
  max: number;
  mean: number;
  median: number;
}

/**
 * Five-number-ish summary used by the static (reduced-motion) ridge fallback:
 * a range bar from min..max with a median marker. Null when there's nothing to
 * summarize. Ignores non-finite samples.
 */
export function distributionSummary(samples: number[]): DistributionSummary | null {
  const clean = samples.filter(Number.isFinite).sort((a, b) => a - b);
  if (clean.length === 0) return null;
  const mid = Math.floor(clean.length / 2);
  const median = clean.length % 2 === 0 ? (clean[mid - 1] + clean[mid]) / 2 : clean[mid];
  return {
    min: clean[0],
    max: clean[clean.length - 1],
    mean: clean.reduce((a, b) => a + b, 0) / clean.length,
    median,
  };
}

export type PredictabilityTier = "Volatile" | "Variable" | "Reliable";

export interface PredictabilityBand {
  lit: number;
  total: number;
  tier: PredictabilityTier;
  tone: "pos" | "warn" | "neg";
}

/**
 * Maps a 0..1 predictability score (the f(ρ) of D13) to a segmented meter + a
 * tier label. Low predictability surfaces as "Volatile" — the human-readable
 * reason a streaming-level K/DEF carries a discounted value. Thresholds are
 * even thirds by default; tune against the v2.2/v2.4 backtest.
 */
export function predictabilityBand(score: number, total = 5): PredictabilityBand {
  const s = clamp01(score);
  const lit = Math.round(s * total);
  const tier: PredictabilityTier = s < 1 / 3 ? "Volatile" : s < 2 / 3 ? "Variable" : "Reliable";
  const tone = tier === "Volatile" ? "neg" : tier === "Variable" ? "warn" : "pos";
  return { lit, total, tier, tone };
}

export interface StatFormat {
  decimals?: number;
  sign?: boolean;
  suffix?: string;
}

/**
 * Formats a stat for a tabular cell. With `tabular-nums` every glyph is 1ch, so
 * the returned string's length is exactly the ch-width the cell must reserve to
 * guarantee digits never clip (the named v1 homepage bug). Missing values render
 * an em dash; negatives use a true minus (U+2212) for column alignment.
 */
export function formatStat(value: number | null | undefined, opts: StatFormat = {}): string {
  const { decimals = 0, sign = false, suffix = "" } = opts;
  if (value == null || !Number.isFinite(value)) return "—";
  // Decide the sign from the value as it will actually display: rounding -0.3 at
  // 0 decimals collapses to -0, and `-0 < 0` is false, so we never print "−0".
  const rounded = Number(value.toFixed(decimals));
  const neg = rounded < 0;
  let s = Math.abs(rounded).toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  if (neg) s = `−${s}`;
  else if (sign && rounded > 0) s = `+${s}`;
  return `${s}${suffix}`;
}
