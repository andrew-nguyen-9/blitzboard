import { describe, it, expect } from "vitest";
import { isConsequential, anyConsequential, type ConsequentialCtx } from "./consequential";
import type { PlayerWithValue } from "@/lib/types";
import type { MappedPick } from "@/lib/sleeperDraft";

function player(id: string, position: string, vor = 10): PlayerWithValue {
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
    value: { player_id: id, engine: "vorp", value: vor, vor, replacement: 100, boom: vor, bust: vor, adp: null, rank: null },
  };
}
const pick = (team: number, p: PlayerWithValue): MappedPick => ({ pickNo: 1, team, player: p });

const ctx: ConsequentialCtx = {
  mySlot: 6,
  needed: new Set(["RB"]),
  targetIds: new Set(["target-rb"]),
  starterCaliberIds: new Set(["good-rb"]),
};

describe("isConsequential", () => {
  it("my own pick is always consequential", () => {
    expect(isConsequential(pick(6, player("x", "WR")), ctx).consequential).toBe(true);
  });

  it("an opponent taking a planned target is consequential", () => {
    expect(isConsequential(pick(2, player("target-rb", "RB")), ctx).consequential).toBe(true);
  });

  it("an opponent taking a starter-caliber player at a need is consequential", () => {
    expect(isConsequential(pick(2, player("good-rb", "RB")), ctx).consequential).toBe(true);
  });

  it("an opponent taking a deep body I never wanted is NOT consequential", () => {
    // WR is not a need, id is neither a target nor starter-caliber → no re-plan churn.
    expect(isConsequential(pick(2, player("scrub-wr", "WR")), ctx).consequential).toBe(false);
  });

  it("anyConsequential is true iff some pick in the window matters", () => {
    const noise = [pick(1, player("a", "WR")), pick(3, player("b", "TE"))];
    expect(anyConsequential(noise, ctx)).toBe(false);
    expect(anyConsequential([...noise, pick(4, player("good-rb", "RB"))], ctx)).toBe(true);
  });
});
