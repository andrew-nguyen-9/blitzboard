import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolveBenchShape, type LeagueConfigKey } from "./benchShape";
import {
  BENCH_SHAPE_CANONICAL_SOURCE_HASH,
  BENCH_SHAPE_ROWS,
} from "./generated/benchShape.generated";

interface TraceSpec {
  fixture_status: string;
  schema_version: number;
  cases: {
    id: string;
    league: { teams: number; qb_mode: string; bench_slots: number; ir_slots: number; te_premium: number };
    starting_slots: Record<string, number>;
    required: string[];
    dependency: string;
  }[];
}

const fixture = JSON.parse(
  readFileSync(new URL("../../fixtures/noncanonical/v6_c04_draft_traces.json", import.meta.url), "utf8"),
) as TraceSpec;

describe("C04 producer-blind trace specifications", () => {
  it("is explicitly noncanonical and uniquely keyed", () => {
    expect(fixture.fixture_status).toBe("noncanonical-producer-blind-c04-specification");
    expect(new Set(fixture.cases.map((row) => row.id)).size).toBe(fixture.cases.length);
  });

  it("covers 1QB, superflex, pure 2QB, and a custom roster shape", () => {
    expect(new Set(fixture.cases.map((row) => row.league.qb_mode))).toEqual(new Set(["1qb", "superflex", "2qb", "custom"]));
    expect(fixture.cases.some((row) => row.starting_slots.WRTE === 2 && row.starting_slots.K === undefined)).toBe(true);
  });

  it("covers four/eight benches, TE premium, and IR/no-IR", () => {
    expect(new Set(fixture.cases.map((row) => row.league.bench_slots))).toEqual(new Set([4, 6, 8]));
    expect(fixture.cases.some((row) => row.league.te_premium > 0)).toBe(true);
    expect(new Set(fixture.cases.map((row) => row.league.ir_slots))).toEqual(new Set([0, 1]));
  });

  it("records rather than hides every unfinished dependency", () => {
    for (const row of fixture.cases) expect(row.dependency).toMatch(/^c03|c02/);
  });
});

describe("C04 accepted C03 trace resolutions", () => {
  it.each(fixture.cases)("resolves $id without measured-evidence overclaim", (spec) => {
    const canonical = spec.league.qb_mode !== "custom" && [10, 12, 14].includes(spec.league.teams) &&
      [4, 8].includes(spec.league.bench_slots);
    const key = canonical
      ? `t${spec.league.teams}-${spec.league.qb_mode}-half-te${spec.league.te_premium.toFixed(1)}-b${spec.league.bench_slots}-ir${spec.league.ir_slots}`
      : `unsupported:${spec.id}`;
    const shape = resolveBenchShape(key as LeagueConfigKey, spec.league.bench_slots);
    expect(shape.evidenceStatus).toBe("unsupported");
    expect(shape.degraded).toBe(true);
    expect(shape.hardCaps).toBeNull();
    expect(Object.values(shape.softMarginalCosts).flat().every(Number.isFinite)).toBe(true);
    expect(shape.degradedReason).toBe(canonical ? "unsupported_evidence" : "missing_league_key");
  });

  it("matches canonical and browser-safe shape source hashes byte-for-byte", () => {
    const canonical = JSON.parse(
      readFileSync(new URL("../../fixtures/bench_shape.json", import.meta.url), "utf8"),
    ) as { canonical_source_hash: string; rows: Record<string, unknown> };
    expect(BENCH_SHAPE_CANONICAL_SOURCE_HASH).toBe(canonical.canonical_source_hash);
    expect(Object.keys(BENCH_SHAPE_ROWS).sort()).toEqual(Object.keys(canonical.rows).sort());
  });

  it("treats soft bench-shape costs as nonbinding and never as positional caps", () => {
    const shape = resolveBenchShape("t14-2qb-std-te0.5-b4-ir1", 4);
    expect(shape.hardCaps).toBeNull();
    expect(shape.softMarginalCosts.QB.at(-1)).toBeTypeOf("number");
    expect(shape.degraded).toBe(true);
  });
});
