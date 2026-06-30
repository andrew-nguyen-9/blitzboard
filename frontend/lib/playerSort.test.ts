import { describe, expect, it } from "vitest";
import { compareCells, latestBoxBySleeper } from "@/lib/playerSort";

describe("compareCells", () => {
  it("orders numbers by direction", () => {
    expect(compareCells(1, 2, true)).toBeLessThan(0);
    expect(compareCells(1, 2, false)).toBeGreaterThan(0);
  });
  it("orders strings by locale, direction-aware", () => {
    expect(compareCells("a", "b", true)).toBeLessThan(0);
    expect(compareCells("a", "b", false)).toBeGreaterThan(0);
  });
  it("sorts null last regardless of direction", () => {
    expect(compareCells(null, 5, true)).toBe(1);
    expect(compareCells(null, 5, false)).toBe(1);
    expect(compareCells(5, null, true)).toBe(-1);
    expect(compareCells(null, null, true)).toBe(0);
  });
});

describe("latestBoxBySleeper", () => {
  const players = [
    { id: "u1", sleeper_id: "s1" },
    { id: "u2", sleeper_id: null }, // no sleeper id → dropped
  ];
  const history = [
    { player_id: "u1", season: 2023, fantasy_pts: 100, stats: { receptions: 50 } },
    { player_id: "u1", season: 2024, fantasy_pts: 120, stats: { receptions: 60 } },
    { player_id: "u2", season: 2024, fantasy_pts: 80, stats: { receptions: 40 } },
  ];

  it("keeps the latest season per player, keyed by sleeper id", () => {
    const box = latestBoxBySleeper(players, history);
    expect(Object.keys(box)).toEqual(["s1"]);
    expect(box.s1.rec).toBe(60); // 2024, not 2023
    expect(box.s1.fantasy_pts).toBe(120);
  });

  it("returns empty when nothing matches", () => {
    expect(latestBoxBySleeper([], history)).toEqual({});
  });
});
