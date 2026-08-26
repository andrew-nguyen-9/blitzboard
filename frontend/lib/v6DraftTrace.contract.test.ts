import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";

interface TraceSpec {
  fixture_status: string;
  schema_version: number;
  cases: {
    id: string;
    league: { qb_mode: string; bench_slots: number; ir_slots: number; te_premium: number };
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

describe.skip("C04 golden live traces — intentionally blocked on canonical C03 schema", () => {
  it.each(fixture.cases)("produces the canonical structured trace for $id", () => {});
  it("matches canonical and browser-safe shape source hashes byte-for-byte", () => {});
  it("treats soft bench-shape costs as nonbinding and never as positional caps", () => {});
});

