import { describe, it, expect } from "vitest";
import { benchBand, buildBenchEntries, humanizeSignal } from "./BenchPanel";
import type { DropRank } from "@/lib/benchScore";
import type { PlayerWithValue } from "@/lib/types";

function player(id: string, position: string, full_name = id): PlayerWithValue {
  return {
    id,
    sleeper_id: id,
    espn_id: null,
    full_name,
    position: position as PlayerWithValue["position"],
    nfl_team: "KC",
    bye_week: null,
    age: null,
    years_exp: null,
    status: null,
    injury_status: null,
  };
}

function rank(id: string, score: number, position = "RB"): DropRank {
  return { id, score, player: player(id, position) };
}

describe("benchBand", () => {
  it("maps bench value to ok / warn / crit bands", () => {
    expect(benchBand(80)).toBe("ok");
    expect(benchBand(55)).toBe("ok"); // boundary
    expect(benchBand(40)).toBe("warn");
    expect(benchBand(30)).toBe("warn"); // boundary
    expect(benchBand(10)).toBe("crit");
    expect(benchBand(0)).toBe("crit");
  });
});

describe("buildBenchEntries", () => {
  it("keeps the worst-first drop order and flags only the first cut", () => {
    // dropPriority returns worst→best; index 0 is the first body to drop.
    const drops = [rank("a", 12), rank("b", 44), rank("c", 71)];
    const entries = buildBenchEntries(drops);
    expect(entries.map((e) => e.id)).toEqual(["a", "b", "c"]);
    expect(entries[0].dropFirst).toBe(true);
    expect(entries.slice(1).every((e) => !e.dropFirst)).toBe(true);
  });

  it("does not flag a lone benchwarmer as a cut", () => {
    expect(buildBenchEntries([rank("a", 12)])[0].dropFirst).toBe(false);
    expect(buildBenchEntries([])).toEqual([]);
  });

  it("normalizes DEF → DST for display", () => {
    expect(buildBenchEntries([rank("d", 20, "DEF")])[0].position).toBe("DST");
  });
});

describe("humanizeSignal", () => {
  it("labels known benchScore terms and splits unknown camelCase", () => {
    expect(humanizeSignal("OpportunityTrend")).toBe("Opportunity trend");
    expect(humanizeSignal("RouteParticipation")).toBe("Route participation");
    expect(humanizeSignal("SomeNewTerm")).toBe("Some New Term");
  });
});
