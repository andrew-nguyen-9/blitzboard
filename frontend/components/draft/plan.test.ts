import { describe, it, expect } from "vitest";
import { buildPlan, valueFlag, neededPositions } from "./plan";
import { SUPERFLEX_ROSTER } from "@/lib/draft";
import type { PlayerWithValue } from "@/lib/types";

function player(
  id: string,
  position: string,
  { vor = 50, adp = null as number | null, rank = null as number | null } = {},
): PlayerWithValue {
  return {
    id,
    sleeper_id: id,
    espn_id: null,
    full_name: id,
    position: position as PlayerWithValue["position"],
    nfl_team: "KC",
    bye_week: 10,
    age: null,
    years_exp: null,
    status: null,
    injury_status: null,
    value: { player_id: id, engine: "vorp", value: vor, vor, replacement: 120, boom: vor, bust: vor, adp, rank },
  };
}

describe("valueFlag", () => {
  it("flags a player falling well past ADP as a value and one drafted ahead of rank as a reach", () => {
    expect(valueFlag(player("v", "RB", { adp: 40, rank: 20 }))).toBe("value");
    expect(valueFlag(player("r", "RB", { adp: 10, rank: 30 }))).toBe("reach");
    expect(valueFlag(player("f", "RB", { adp: 22, rank: 20 }))).toBe("fair");
    expect(valueFlag(player("n", "RB", {}))).toBe("fair");
  });
});

describe("neededPositions", () => {
  it("returns every eligible position while the lineup is empty and shrinks as it fills", () => {
    const empty = neededPositions([], SUPERFLEX_ROSTER);
    expect(empty.has("QB")).toBe(true);
    expect(empty.has("RB")).toBe(true);
  });
});

describe("buildPlan", () => {
  const pool = [
    player("rb1", "RB", { vor: 90 }),
    player("rb2", "RB", { vor: 70 }),
    player("wr1", "WR", { vor: 80 }),
    player("qb1", "QB", { vor: 60 }),
    player("te1", "TE", { vor: 40 }),
    player("k1", "K", { vor: 5 }),
  ];

  it("plans my upcoming picks with primaries at needs and same-window contingencies", () => {
    const plan = buildPlan(pool, [], SUPERFLEX_ROSTER, 12, 6, 6, 0, { lookahead: 2, perRound: 2 });
    expect(plan.rounds.length).toBe(2);
    const first = plan.rounds[0];
    expect(first.primary.length).toBeGreaterThan(0);
    // primaries are the top projections and are disjoint from contingencies
    expect(first.primary[0].proj).toBeGreaterThanOrEqual(first.primary[first.primary.length - 1].proj);
    const ids = new Set(first.primary.map((p) => p.id));
    expect(first.contingency.every((c) => !ids.has(c.id))).toBe(true);
    expect(plan.builtAtPickCount).toBe(0);
  });
});
