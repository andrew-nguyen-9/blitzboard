import { describe, it, expect } from "vitest";
import { groupLatestBox } from "./queries";

describe("groupLatestBox", () => {
  const idToSleeper = new Map([
    ["uuid-a", "100"],
    ["uuid-b", "200"],
  ]);

  it("keys by sleeper_id and keeps the latest season as a flat box-score", () => {
    const rows = [
      { player_id: "uuid-a", season: 2023, fantasy_pts: 200, stats: { receiving_yards: 900, receptions: 70 } },
      { player_id: "uuid-a", season: 2024, fantasy_pts: 250, stats: { receiving_yards: 1100, receptions: 85 } },
    ];
    const out = groupLatestBox(rows, idToSleeper);
    expect(out["100"].rec_yds).toBe(1100); // latest season wins
    expect(out["100"].rec).toBe(85);
    expect(out["100"].fantasy_pts).toBe(250);
  });

  it("drops rows whose player_id has no sleeper mapping", () => {
    const rows = [{ player_id: "uuid-x", season: 2024, fantasy_pts: 10, stats: {} }];
    expect(groupLatestBox(rows, idToSleeper)).toEqual({});
  });
});
