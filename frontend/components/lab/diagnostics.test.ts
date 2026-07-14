import { describe, it, expect } from "vitest";
import {
  rhatStatus,
  essStatus,
  divergenceStatus,
  overallStatus,
  expectedCalibrationError,
  byWorstFirst,
} from "./diagnostics";

describe("MCMC diagnostic thresholds", () => {
  it("grades R̂ against the 1.01 / 1.05 convergence bands", () => {
    expect(rhatStatus(1.004)).toBe("ok");
    expect(rhatStatus(1.03)).toBe("warn");
    expect(rhatStatus(1.2)).toBe("bad");
    expect(rhatStatus(null)).toBe("unknown");
  });

  it("grades ESS against the 400 / 100 bands", () => {
    expect(essStatus(1200)).toBe("ok");
    expect(essStatus(250)).toBe("warn");
    expect(essStatus(40)).toBe("bad");
    expect(essStatus(undefined)).toBe("unknown");
  });

  it("flags any divergence, escalates past a handful", () => {
    expect(divergenceStatus(0)).toBe("ok");
    expect(divergenceStatus(3)).toBe("warn");
    expect(divergenceStatus(50)).toBe("bad");
  });
});

describe("overallStatus", () => {
  it("reports the worst signal across params + divergences", () => {
    expect(
      overallStatus({
        params: [
          { name: "a", rhat: 1.0, ess: 900 },
          { name: "b", rhat: 1.2, ess: 900 }, // bad R̂ dominates
        ],
        divergences: 0,
      }),
    ).toBe("bad");
    expect(
      overallStatus({ params: [{ name: "a", rhat: 1.0, ess: 900 }], divergences: 0 }),
    ).toBe("ok");
    expect(overallStatus({ params: [{ name: "a" }], divergences: null })).toBe("unknown");
  });
});

describe("expectedCalibrationError", () => {
  it("is 0 on the diagonal and count-weights off-diagonal bins", () => {
    expect(
      expectedCalibrationError([
        { predicted: 0.2, observed: 0.2 },
        { predicted: 0.8, observed: 0.8 },
      ]),
    ).toBe(0);
    // one bin off by 0.1 with 3x the weight of an on-diagonal bin → 0.075
    expect(
      expectedCalibrationError([
        { predicted: 0.5, observed: 0.5, count: 1 },
        { predicted: 0.5, observed: 0.6, count: 3 },
      ]),
    ).toBeCloseTo(0.075, 6);
    expect(expectedCalibrationError([])).toBeNull();
  });
});

describe("byWorstFirst", () => {
  it("floats problem params to the top, unknowns to the bottom", () => {
    const sorted = byWorstFirst([
      { name: "ok", rhat: 1.0, ess: 900 },
      { name: "unknown" },
      { name: "bad", rhat: 1.3, ess: 900 },
      { name: "warn", rhat: 1.03, ess: 900 },
    ]);
    expect(sorted.map((p) => p.name)).toEqual(["bad", "warn", "ok", "unknown"]);
  });
});
