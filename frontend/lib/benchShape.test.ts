import { describe, expect, it } from "vitest";
import { benchMarginalCost, resolveBenchShape, type LeagueConfigKey } from "./benchShape";

describe("C03 bench-shape lookup", () => {
  it("resolves mandatory rows with exact budgets and soft-only costs", () => {
    for (const key of [
      "t10-1qb-half-te0.0-b4-ir0",
      "t10-superflex-half-te0.5-b8-ir1",
      "t12-2qb-half-te0.5-b8-ir1",
      "t14-superflex-ppr-te0.5-b8-ir0",
    ] as LeagueConfigKey[]) {
      const bench = key.includes("-b4-") ? 4 : 8;
      const shape = resolveBenchShape(key, bench);
      expect(Object.values(shape.composition).reduce((a, b) => a + b, 0)).toBe(bench);
      expect(shape.hardCaps).toBeNull();
      expect(Number.isFinite(benchMarginalCost(shape, "RB", bench))).toBe(true);
      expect(shape.evidenceStatus).toBe("unsupported");
      expect(shape.degraded).toBe(true);
      expect(shape.degradedReason).toBe("unsupported_evidence");
    }
  });

  it("keeps the known 14-team 2QB slice explicitly unsupported", () => {
    const shape = resolveBenchShape("t14-2qb-std-te0.5-b4-ir1", 4);
    expect(shape.evidenceStatus).toBe("unsupported");
    expect(shape.degraded).toBe(true);
  });
});
