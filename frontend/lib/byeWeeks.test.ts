import { describe, it, expect } from "vitest";
import { BYE_WEEKS_2026, parseScheduleByes, attachByes } from "./byeWeeks";

describe("BYE_WEEKS_2026", () => {
  it("covers all 32 teams with the Sleeper Rams code (LAR, not LA)", () => {
    expect(Object.keys(BYE_WEEKS_2026)).toHaveLength(32);
    expect(BYE_WEEKS_2026.LAR).toBeGreaterThan(0);
    expect(BYE_WEEKS_2026).not.toHaveProperty("LA");
    expect(BYE_WEEKS_2026.KC).toBe(5);
    expect(BYE_WEEKS_2026.DAL).toBe(14);
  });
});

describe("parseScheduleByes", () => {
  it("finds the REG week a team has no game and aliases nflverse LA → LAR", () => {
    const csv =
      "season,game_type,week,away_team,home_team\n" +
      "2026,REG,1,KC,LA\n" + // KC & LA play wk1
      "2026,REG,2,LA,DEN\n" + // LA & DEN play wk2
      "2026,REG,1,DEN,SF\n" + // DEN & SF play wk1
      "2025,REG,1,KC,SF"; // wrong season — ignored
    const byes = parseScheduleByes(csv, 2026);
    expect(byes.KC).toBe(2); // KC missing wk2
    expect(byes.SF).toBe(2); // SF missing wk2
    expect(byes.LAR).toBe(undefined); // LA→LAR plays both weeks in this fixture
    expect(byes).not.toHaveProperty("LA");
  });
});

describe("attachByes", () => {
  it("fills bye_week from nfl_team, preserves existing, leaves FAs null", () => {
    const out = attachByes([
      { nfl_team: "KC", bye_week: null },
      { nfl_team: "DAL", bye_week: 9 },
      { nfl_team: null, bye_week: null },
      { nfl_team: "ZZZ", bye_week: null }, // unknown team
    ]);
    expect(out[0].bye_week).toBe(5);
    expect(out[1].bye_week).toBe(9);
    expect(out[2].bye_week).toBe(null);
    expect(out[3].bye_week).toBe(null);
  });
});
