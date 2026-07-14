import { describe, it, expect } from "vitest";
import { rosterHealth, equityImpact, resolveBye } from "./rosterHealth";
import { SUPERFLEX_ROSTER } from "@/lib/draft";
import type { PlayerWithValue } from "@/lib/types";

function player(
  id: string,
  position: string,
  { vor = 50, bye = null as number | null, team = "KC" as string | null } = {},
): PlayerWithValue {
  return {
    id,
    sleeper_id: id,
    espn_id: null,
    full_name: id,
    position: position as PlayerWithValue["position"],
    nfl_team: team,
    bye_week: bye,
    age: null,
    years_exp: null,
    status: null,
    injury_status: null,
    value: { player_id: id, engine: "vorp", value: vor, vor, replacement: 120, boom: vor, bust: vor, adp: null, rank: null },
  };
}

describe("resolveBye", () => {
  it("falls back to the baked schedule by nfl_team", () => {
    expect(resolveBye(player("x", "QB", { bye: 8 }))).toBe(8);
    // no explicit bye → resolves from BYE_WEEKS_2026 (KC has a known bye)
    expect(resolveBye(player("y", "QB", { bye: null, team: "KC" }))).not.toBeNull();
    expect(resolveBye(player("z", "QB", { bye: null, team: null }))).toBeNull();
  });
});

describe("rosterHealth", () => {
  it("flags an empty roster as critical with every starter slot open", () => {
    const h = rosterHealth([], SUPERFLEX_ROSTER);
    expect(h.startersFilled).toBe(0);
    expect(h.openSlots.length).toBe(SUPERFLEX_ROSTER.length);
    expect(h.invariants.find((i) => i.key === "starters")!.status).toBe("crit");
  });

  it("detects a stacked bye when two starters share a week", () => {
    // Two QBs on the same bye fill QB + OP → both out week 10.
    const picks = [
      player("qb1", "QB", { vor: 90, bye: 10, team: null }),
      player("qb2", "QB", { vor: 85, bye: 10, team: null }),
    ];
    const h = rosterHealth(picks, SUPERFLEX_ROSTER);
    const conflict = h.byeConflicts.find((c) => c.week === 10);
    expect(conflict).toBeDefined();
    expect(conflict!.players.length).toBe(2);
    expect(h.invariants.find((i) => i.key === "byes")!.status).toBe("warn");
  });

  it("warns when K/DST are over-drafted past the cap", () => {
    const picks = [player("k1", "K", { bye: null }), player("k2", "K", { bye: null })];
    const h = rosterHealth(picks, SUPERFLEX_ROSTER);
    expect(h.kCount).toBe(2);
    expect(h.invariants.find((i) => i.key === "kdst")!.status).toBe("warn");
  });
});

describe("equityImpact", () => {
  it("is the marginal starting-lineup points a pick adds, never negative", () => {
    const impact = equityImpact([], player("stud", "RB", { vor: 80 }), SUPERFLEX_ROSTER);
    expect(impact).toBeGreaterThan(0);
    // a body that can't crack the lineup over what's there adds no starting equity
    expect(equityImpact([], player("z", "RB", { vor: 0 }), SUPERFLEX_ROSTER)).toBeGreaterThanOrEqual(0);
  });
});
