import { describe, expect, test } from "vitest";
import { dialGeometry, ridgePath, formatStat, distributionSummary, predictabilityBand } from "./viz";

describe("dialGeometry", () => {
  const r = 84;
  const C = 2 * Math.PI * r;

  test("circumference is 2*pi*r", () => {
    expect(dialGeometry(0.5, r).circumference).toBeCloseTo(C, 6);
  });

  test("track dasharray spans the full 270-degree arc", () => {
    expect(dialGeometry(1, r).trackDasharray).toBe(`${C * 0.75} ${C}`);
  });

  test("fill at half scales the visible arc, not the whole circle", () => {
    // 0.5 of a 270-degree arc, NOT 0.5 of the full circumference
    expect(dialGeometry(0.5, r).fillDasharray).toBe(`${C * 0.75 * 0.5} ${C}`);
  });

  test("clamps fraction below 0 to an empty fill", () => {
    expect(dialGeometry(-3, r).fillDasharray).toBe(`0 ${C}`);
    expect(dialGeometry(-3, r).filledFraction).toBe(0);
  });

  test("clamps fraction above 1 to the full arc", () => {
    expect(dialGeometry(99, r).fillDasharray).toBe(`${C * 0.75} ${C}`);
    expect(dialGeometry(99, r).filledFraction).toBe(1);
  });

  test("treats NaN as empty rather than emitting NaN into the DOM", () => {
    expect(dialGeometry(Number.NaN, r).fillDasharray).toBe(`0 ${C}`);
  });
});

describe("ridgePath", () => {
  const box = { width: 120, height: 40, bins: 24 };

  test("produces a closed area path starting at the baseline", () => {
    const { d } = ridgePath([1, 2, 3, 4, 5], box);
    expect(d.startsWith("M")).toBe(true);
    expect(d.trimEnd().endsWith("Z")).toBe(true);
  });

  test("never emits NaN, even for a single repeated value (zero-width domain)", () => {
    const { d } = ridgePath([7, 7, 7, 7], box);
    expect(d).not.toMatch(/NaN/);
  });

  test("empty samples degrade to a flat baseline, not a crash", () => {
    const { d, densities } = ridgePath([], box);
    expect(d).not.toMatch(/NaN/);
    expect(densities.every((v) => v === 0)).toBe(true);
  });

  test("normalizes so the modal bin reaches full height (density 1)", () => {
    const { densities } = ridgePath([5, 5, 5, 5, 1, 9], box);
    expect(Math.max(...densities)).toBeCloseTo(1, 6);
  });

  test("a left-skewed sample puts its peak in the left half", () => {
    const samples = [1, 1, 1, 1, 1, 2, 9];
    const { densities } = ridgePath(samples, box);
    const peak = densities.indexOf(Math.max(...densities));
    expect(peak).toBeLessThan(box.bins / 2);
  });
});

describe("formatStat", () => {
  test("reserves no-clip width via a stable digit count (the v1 cell bug)", () => {
    // tabular-nums => 1ch per glyph; the formatted string's length is the
    // minimum ch the cell must reserve so digits never clip.
    expect(formatStat(1234.5, { decimals: 1 })).toBe("1,234.5");
    expect(formatStat(1234.5, { decimals: 1 }).length).toBe(7);
  });

  test("applies fixed decimals so columns align", () => {
    expect(formatStat(8, { decimals: 1 })).toBe("8.0");
    expect(formatStat(8.25, { decimals: 1 })).toBe("8.3");
  });

  test("supports an explicit sign for deltas", () => {
    expect(formatStat(4, { decimals: 0, sign: true })).toBe("+4");
    expect(formatStat(-4, { decimals: 0, sign: true })).toBe("−4"); // U+2212 minus
    expect(formatStat(0, { decimals: 0, sign: true })).toBe("0");
  });

  test("appends a suffix without breaking the width count", () => {
    expect(formatStat(50, { decimals: 0, suffix: "%" })).toBe("50%");
  });

  test("never renders a negative zero when a small negative rounds to 0", () => {
    expect(formatStat(-0.3, { decimals: 0, sign: true })).toBe("0");
    expect(formatStat(-0.02, { decimals: 1 })).toBe("0.0");
  });

  test("renders an em-dash placeholder for missing values", () => {
    expect(formatStat(null, { decimals: 1 })).toBe("—");
    expect(formatStat(Number.NaN, { decimals: 1 })).toBe("—");
  });
});

describe("distributionSummary", () => {
  test("returns null for empty input (drives the empty state)", () => {
    expect(distributionSummary([])).toBeNull();
  });

  test("computes min, max, mean and median for an odd count", () => {
    expect(distributionSummary([5, 1, 3, 2, 4])).toEqual({ min: 1, max: 5, mean: 3, median: 3 });
  });

  test("averages the middle pair for an even count", () => {
    expect(distributionSummary([1, 2, 3, 4])?.median).toBe(2.5);
  });

  test("ignores non-finite samples", () => {
    expect(distributionSummary([Number.NaN, 2, 4, Infinity])).toEqual({
      min: 2, max: 4, mean: 3, median: 3,
    });
  });
});

describe("predictabilityBand", () => {
  test("low predictability reads as Volatile (explains a discounted K/DEF, D13)", () => {
    const b = predictabilityBand(0.1);
    expect(b.tier).toBe("Volatile");
    expect(b.tone).toBe("neg");
    expect(b.lit).toBe(1);
  });

  test("mid predictability reads as Variable", () => {
    const b = predictabilityBand(0.5);
    expect(b.tier).toBe("Variable");
    expect(b.tone).toBe("warn");
  });

  test("high predictability reads as Reliable and lights the whole meter", () => {
    const b = predictabilityBand(0.95);
    expect(b.tier).toBe("Reliable");
    expect(b.tone).toBe("pos");
    expect(b.lit).toBe(b.total);
  });

  test("clamps out-of-range and non-finite scores", () => {
    expect(predictabilityBand(5).lit).toBe(predictabilityBand(1).total);
    expect(predictabilityBand(-1).lit).toBe(0);
    expect(predictabilityBand(Number.NaN).lit).toBe(0);
    expect(predictabilityBand(Number.NaN).tier).toBe("Volatile");
  });
});
