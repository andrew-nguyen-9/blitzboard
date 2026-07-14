import { describe, expect, test } from "vitest";
import {
  sortQuantiles,
  quantileAt,
  rangeFromQuantiles,
  gaussianQuantiles,
  normCdf,
  bustProbability,
  asProbability,
} from "./quantiles";
import { playerUncertainty } from "./fromValue";
import type { QuantilePoint } from "./types";

const QS: QuantilePoint[] = [
  { p: 0.1, value: 4 },
  { p: 0.5, value: 10 },
  { p: 0.9, value: 22 },
];

describe("sortQuantiles", () => {
  test("sorts ascending and drops non-finite", () => {
    const s = sortQuantiles([
      { p: 0.9, value: 22 },
      { p: 0.1, value: 4 },
      { p: NaN, value: 1 },
      { p: 0.5, value: Infinity },
    ]);
    expect(s.map((q) => q.p)).toEqual([0.1, 0.9]);
  });
});

describe("quantileAt", () => {
  test("returns null on empty", () => {
    expect(quantileAt([], 0.5)).toBeNull();
  });
  test("hits exact knots", () => {
    expect(quantileAt(QS, 0.5)).toBe(10);
  });
  test("linear-interpolates between knots", () => {
    // halfway between p=0.1 (4) and p=0.5 (10) → p=0.3 → 7
    expect(quantileAt(QS, 0.3)).toBeCloseTo(7, 6);
  });
  test("clamps outside the sampled range", () => {
    expect(quantileAt(QS, 0)).toBe(4);
    expect(quantileAt(QS, 1)).toBe(22);
  });
});

describe("rangeFromQuantiles", () => {
  test("floor/median/ceiling from the configured pair", () => {
    expect(rangeFromQuantiles(QS, 0.1, 0.9)).toEqual({ floor: 4, median: 10, ceiling: 22 });
  });
  test("null when a quantile can't be resolved", () => {
    expect(rangeFromQuantiles([], 0.1, 0.9)).toBeNull();
  });
});

describe("gaussianQuantiles", () => {
  test("median ≈ mean and symmetric spread", () => {
    const qs = gaussianQuantiles(100, 10, [0.1, 0.5, 0.9]);
    const at = (p: number) => qs.find((q) => q.p === p)!.value;
    expect(at(0.5)).toBeCloseTo(100, 0);
    expect(at(0.9) - 100).toBeCloseTo(100 - at(0.1), 0); // symmetric
    expect(at(0.9)).toBeGreaterThan(at(0.5));
  });
  test("degenerate sigma collapses to a point mass", () => {
    expect(gaussianQuantiles(50, 0).every((q) => q.value === 50)).toBe(true);
  });
});

describe("normCdf / bustProbability", () => {
  test("CDF at the mean is 0.5", () => {
    expect(normCdf(0, 0, 1)).toBeCloseTo(0.5, 6);
  });
  test("CDF is monotonic and bounded", () => {
    expect(normCdf(-3)).toBeLessThan(0.01);
    expect(normCdf(3)).toBeGreaterThan(0.99);
  });
  test("bust% = P(below the replacement line)", () => {
    // line at the mean → 50%
    expect(bustProbability(100, 15, 100)).toBeCloseTo(0.5, 6);
    // line one sigma below → ~15.9%
    expect(bustProbability(100, 15, 85)).toBeCloseTo(0.159, 2);
  });
  test("null when the line is missing", () => {
    expect(bustProbability(100, 15, null)).toBeNull();
  });
});

describe("asProbability", () => {
  test("clamps and passes null through", () => {
    expect(asProbability(1.4)).toBe(1);
    expect(asProbability(-0.2)).toBe(0);
    expect(asProbability(null)).toBeNull();
    expect(asProbability(undefined)).toBeNull();
  });
});

describe("playerUncertainty", () => {
  test("builds a full distribution from a projection mean + stdev", () => {
    const u = playerUncertainty(
      { replacement: 80 },
      { mean: 120, stdev: 20 },
    );
    expect(u).not.toBeNull();
    expect(u!.quantiles.length).toBeGreaterThan(3);
    // replacement is 2σ below the mean → bust% small but positive
    expect(u!.probs!.bust).not.toBeNull();
    expect(u!.probs!.bust!).toBeLessThan(0.1);
  });
  test("falls back to the value row's bust/value/boom band", () => {
    const u = playerUncertainty({ bust: 5, value: 12, boom: 25 }, null);
    expect(u!.quantiles.map((q) => q.value)).toEqual([5, 12, 25]);
  });
  test("reads published mc_probs when present", () => {
    const u = playerUncertainty(
      { value: 12, mc_probs: { bust: 0.3, top5: 0.12, beats_adp: 0.6 } },
      null,
    );
    expect(u!.probs).toMatchObject({ bust: 0.3, top5: 0.12, beatsAdp: 0.6 });
  });
  test("returns null with nothing to show", () => {
    expect(playerUncertainty(null, null)).toBeNull();
    expect(playerUncertainty({}, {})).toBeNull();
  });
});
