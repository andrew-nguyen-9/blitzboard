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

describe("advanced rate metrics (E2 keys, latest-season box)", () => {
  const b = { games: 10, carries: 100, rush_yds: 500, rush_td: 4, rec: 40, rec_yds: 400, rec_td: 2, tgt: 60 };
  it("computes per-opportunity rates from the loaded box", () => {
    expect(find("ypc").get(p, { box: b })).toBeCloseTo(5); // 500 / 100
    expect(find("ypr").get(p, { box: b })).toBeCloseTo(10); // 400 / 40
    expect(find("ypt").get(p, { box: b })).toBeCloseTo(400 / 60);
    expect(find("catch_pct").get(p, { box: b })).toBeCloseTo((40 / 60) * 100);
    expect(find("scrim_ypg").get(p, { box: b })).toBeCloseTo(90); // (500 + 400) / 10
    expect(find("td_per_opp").get(p, { box: b })).toBeCloseTo((6 / 160) * 100);
  });
  it("is null when the box is not loaded", () => {
    expect(find("ypc").get(p, { box: null })).toBeNull();
    expect(find("ypc").get(p, {})).toBeNull();
  });
  it("drops the metric on a zero/absent denominator (no divide-by-zero)", () => {
    expect(find("ypc").get(p, { box: { carries: 0, rush_yds: 0 } })).toBeNull();
    expect(find("pass_ypg").get(p, { box: { games: 10, pass_yds: 0 } })).toBeNull();
  });
  it("gates QB passing metrics on pass_yds and TD:INT on a positive denominator", () => {
    const qb = { games: 16, pass_yds: 4000, pass_td: 30, int: 10 };
    expect(find("pass_ypg").get(p, { box: qb })).toBeCloseTo(250);
    expect(find("td_int").get(p, { box: qb })).toBeCloseTo(3);
    expect(find("td_int").get(p, { box: { pass_yds: 4000, pass_td: 30, int: 0 } })).toBeNull();
  });
  it("carries a % suffix on percentage metrics", () => {
    expect(find("catch_pct").suffix).toBe("%");
    expect(find("td_per_opp").suffix).toBe("%");
  });
});
