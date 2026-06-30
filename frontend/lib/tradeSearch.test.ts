import { describe, it, expect } from "vitest";
import { PlayerSearchIndex } from "./tradeSearch";
import type { SnapshotPlayer } from "./snapshot";

const mk = (id: string, full_name: string, rank: number): SnapshotPlayer => ({
  id, full_name, position: "WR", nfl_team: "KC",
  value: null, vor: null, rank, predictability: null, trend: null,
  adp: null, boom: null, bust: null, bye: null,
});

const players = [
  mk("1", "Patrick Mahomes", 1),
  mk("2", "Justin Jefferson", 2),
  mk("3", "Josh Allen", 3),
  mk("4", "Jalen Hurts", 4),
  mk("5", "Ja'Marr Chase", 5),
];
const idx = new PlayerSearchIndex(players);
const names = (q: string) => idx.search(q).map((p) => p.full_name);

describe("PlayerSearchIndex", () => {
  it("prefix-matches a last name", () => {
    expect(names("mah")[0]).toBe("Patrick Mahomes");
  });

  it("prefix-matches a first name token", () => {
    expect(names("justin")).toContain("Justin Jefferson");
  });

  it("ranks prefix hits by player rank", () => {
    // Justin/Josh/Jalen/Ja'Marr all have a 'j' token — lowest rank (2) wins
    expect(names("j")[0]).toBe("Justin Jefferson");
  });

  it("intersects multi-token queries", () => {
    expect(names("patrick m")).toEqual(["Patrick Mahomes"]);
  });

  it("falls back to fuzzy subsequence on a typo", () => {
    // 'jeferson' (dropped one f) is a subsequence of 'justinjefferson'
    expect(names("jeferson")).toContain("Justin Jefferson");
  });

  it("ignores punctuation (Ja'Marr)", () => {
    expect(names("jamarr")).toContain("Ja'Marr Chase");
  });

  it("returns nothing for empty/whitespace", () => {
    expect(idx.search("   ")).toEqual([]);
  });
});
