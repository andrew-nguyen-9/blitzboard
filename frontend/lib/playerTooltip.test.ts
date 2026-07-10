import { describe, expect, it } from "vitest";
import { columnTips, playerTooltipRows } from "@/lib/playerTooltip";
import type { SnapshotPlayer } from "@/lib/snapshot";

const base: SnapshotPlayer = {
  id: "p1",
  full_name: "Test Player",
  position: "RB",
  nfl_team: "SF",
  value: 42.34,
  vor: 12.5,
  rank: 7,
  predictability: 0.823,
  trend: 3,
  adp: 8.1,
  boom: 140,
  bust: 30,
  bye: 9,
};

describe("playerTooltipRows", () => {
  it("formats a fully-populated player", () => {
    const r = Object.fromEntries(playerTooltipRows(base, 2).map((x) => [x.label, x.value]));
    expect(r["Rank"]).toBe("#7");
    expect(r["Pos · Team"]).toBe("RB · SF");
    expect(r["Tier"]).toBe("T2");
    expect(r["Value"]).toBe("42.3");
    expect(r["VOR"]).toBe("12.5");
    expect(r["Predictability ρ"]).toBe("0.82");
    expect(r["Trend"]).toBe("▲ 3 adds");
  });

  it("renders em-dash for every missing field and normalizes DEF→DST", () => {
    const empty: SnapshotPlayer = {
      ...base, position: "DEF", nfl_team: null, value: null, vor: null,
      rank: null, predictability: null, trend: null,
    };
    const r = Object.fromEntries(playerTooltipRows(empty).map((x) => [x.label, x.value]));
    expect(r["Rank"]).toBe("—");
    expect(r["Pos · Team"]).toBe("DST · FA");
    expect(r["Tier"]).toBe("—");
    expect(r["Value"]).toBe("—");
    expect(r["Predictability ρ"]).toBe("—");
    expect(r["Trend"]).toBe("—");
  });

  it("shows downward and flat trends", () => {
    expect(playerTooltipRows({ ...base, trend: -4 }).find((x) => x.label === "Trend")?.value).toBe("▼ 4");
    expect(playerTooltipRows({ ...base, trend: 0 }).find((x) => x.label === "Trend")?.value).toBe("flat");
  });

  it("surfaces boom·bust and adp in the hover card", () => {
    const r = Object.fromEntries(playerTooltipRows(base, 2).map((x) => [x.label, x.value]));
    expect(r["Boom · Bust"]).toBe("140 · 30");
    expect(r["ADP"]).toBe("8.1");
  });
});

describe("columnTips", () => {
  it("defines a definition for every non-meta Explorer column key", () => {
    const keys = [
      "value", "vor", "boom", "bust", "rank", "adp", "tier",
      "pass_yds", "rush_yds", "rec", "rec_yds", "fantasy_pts",
      "scrim_ypg", "ypc", "ypr", "ypt", "catch_pct", "td_per_opp", "pass_ypg", "td_int",
    ];
    for (const k of keys) expect(columnTips[k]).toBeTruthy();
  });
});
