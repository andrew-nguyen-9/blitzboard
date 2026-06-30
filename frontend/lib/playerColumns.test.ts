import { describe, it, expect } from "vitest";
import { PLAYER_COLUMNS, type ColDef } from "./playerColumns";
import type { SnapshotPlayer } from "./snapshot";

const find = (key: string): ColDef => PLAYER_COLUMNS.find((c) => c.key === key)!;

const p: SnapshotPlayer = {
  id: "1", full_name: "X", position: "RB", nfl_team: "KC",
  value: 100.4, vor: 50, rank: 3, predictability: 0.7, trend: 1,
  adp: 4.2, boom: 140, bust: 30, bye: 10,
};

describe("playerColumns accessors (one per group + null-safe path)", () => {
  it("proj reads snapshot fields, null when absent", () => {
    expect(find("boom").get(p, {})).toBe(140);
    expect(find("boom").get({ ...p, boom: null }, {})).toBeNull();
  });
  it("rank reads adp from snapshot + tier from ctx", () => {
    expect(find("adp").get(p, {})).toBe(4.2);
    expect(find("tier").get(p, { tier: 2 })).toBe(2);
    expect(find("tier").get(p, {})).toBeNull();
  });
  it("box reads ctx.box, null when not loaded", () => {
    expect(find("rec_yds").get(p, { box: { rec_yds: 800 } })).toBe(800);
    expect(find("rec_yds").get(p, { box: null })).toBeNull();
    expect(find("rec_yds").get(p, {})).toBeNull();
  });
  it("meta reads pos/team/bye from snapshot, null when absent", () => {
    expect(find("bye").get(p, {})).toBe(10);
    expect(find("pos").get(p, {})).toBe("RB");
    expect(find("pos").get({ ...p, position: null }, {})).toBeNull();
  });
});
