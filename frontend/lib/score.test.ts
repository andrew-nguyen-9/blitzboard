import { describe, it, expect } from "vitest";
import { projPoints } from "./score";
import type { PlayerWithValue } from "./types";

const mk = (nfl_team: string | null, vor: number, replacement: number): PlayerWithValue =>
  ({ id: "x", full_name: "x", position: "RB", nfl_team, bye_week: null,
     value: { player_id: "x", engine: "vorp", value: vor, vor, replacement, boom: 0, bust: 0, adp: null, rank: null } } as PlayerWithValue);

describe("projPoints — free agents can't score", () => {
  it("is 0 for a player with no NFL team even if the value row is stale", () => {
    expect(projPoints(mk(null, 200, 50))).toBe(0);
  });
  it("is vor+replacement for a rostered player", () => {
    expect(projPoints(mk("KC", 200, 50))).toBe(250);
  });
});
