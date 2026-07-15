import { describe, expect, it } from "vitest";
import { BYE_WEEKS_2026 } from "./byeWeeks";
import {
  SCHEDULE_2026,
  REGULAR_SEASON_WEEKS,
  PLAYOFF_WEEKS,
  opponentFor,
  remainingSchedule,
  playoffOpponents,
  scheduleStrength,
  playoffSchedule,
  byeWeekFor,
} from "./schedule2026";

const TEAMS = Object.keys(BYE_WEEKS_2026);

describe("SCHEDULE_2026 shape", () => {
  it("has all 32 teams, 18 weeks each", () => {
    expect(Object.keys(SCHEDULE_2026).sort()).toEqual([...TEAMS].sort());
    for (const t of TEAMS) {
      expect(SCHEDULE_2026[t]).toHaveLength(REGULAR_SEASON_WEEKS);
    }
  });

  it("every non-bye opponent is a valid team code and never self", () => {
    const valid = new Set(TEAMS);
    for (const t of TEAMS) {
      for (const g of SCHEDULE_2026[t]) {
        if (g.opponent === "BYE") continue;
        expect(valid.has(g.opponent)).toBe(true);
        expect(g.opponent).not.toBe(t);
        // boolean home, or null for a neutral-site (international) game
        expect(g.home === null || typeof g.home === "boolean").toBe(true);
      }
    }
  });

  it("has exactly one bye per team", () => {
    for (const t of TEAMS) {
      const byes = SCHEDULE_2026[t].filter((g) => g.opponent === "BYE");
      expect(byes).toHaveLength(1);
    }
  });
});

describe("byes match BYE_WEEKS_2026 for all 32 teams", () => {
  it.each(TEAMS)("%s", (team) => {
    expect(byeWeekFor(team)).toBe(BYE_WEEKS_2026[team]);
  });
});

describe("schedule symmetry", () => {
  it("if A plays B in week W, B plays A that week (opposite home/away, or both neutral)", () => {
    for (const t of TEAMS) {
      SCHEDULE_2026[t].forEach((g, i) => {
        if (g.opponent === "BYE") return;
        const back = SCHEDULE_2026[g.opponent][i];
        expect(back.opponent).toBe(t);
        if (g.home === null) expect(back.home).toBeNull(); // neutral site
        else expect(back.home).toBe(!g.home);
      });
    }
  });
});

describe("helpers", () => {
  it("opponentFor spot-checks (ARI wk1 @LAC away, wk2 SEA home, bye wk14)", () => {
    expect(opponentFor("ARI", 1)).toBe("LAC");
    expect(SCHEDULE_2026.ARI[0].home).toBe(false);
    expect(opponentFor("ARI", 2)).toBe("SEA");
    expect(SCHEDULE_2026.ARI[1].home).toBe(true);
    expect(opponentFor("ARI", 14)).toBe("BYE");
    expect(opponentFor("ARI", 0)).toBeNull();
    expect(opponentFor("ARI", 19)).toBeNull();
    expect(opponentFor("ZZZ", 1)).toBeNull();
  });

  it("remainingSchedule returns fromWeek..18 with weeks tagged", () => {
    const rem = remainingSchedule("BUF", 16);
    expect(rem.map((r) => r.week)).toEqual([16, 17, 18]);
    expect(remainingSchedule("BUF", 1)).toHaveLength(18);
    expect(remainingSchedule("ZZZ", 1)).toEqual([]);
  });

  it("playoffOpponents returns weeks 15-17", () => {
    const po = playoffOpponents("ARI");
    expect(po).toHaveLength(3);
    expect(po).toEqual([
      opponentFor("ARI", 15),
      opponentFor("ARI", 16),
      opponentFor("ARI", 17),
    ]);
    expect(PLAYOFF_WEEKS).toEqual([15, 16, 17]);
  });
});

describe("scheduleStrength", () => {
  it("defaults to neutral 0.5 with covered 0 when no defRatings", () => {
    const s = scheduleStrength("ARI", [1, 2, 3]);
    expect(s.strength).toBe(0.5);
    expect(s.covered).toBe(0);
  });

  it("uses defRatings (lower rating = tougher = lower easiness)", () => {
    const opp1 = opponentFor("ARI", 1)!;
    const opp2 = opponentFor("ARI", 2)!;
    const tough = scheduleStrength("ARI", [1], { [opp1]: 0.9 });
    expect(tough.strength).toBeCloseTo(0.1);
    expect(tough.covered).toBe(1);
    const mixed = scheduleStrength("ARI", [1, 2], { [opp1]: 0.8 });
    // opp1 easiness 0.2 (covered), opp2 defaults 0.5 → mean 0.35, covered 0.5
    expect(mixed.strength).toBeCloseTo(0.35);
    expect(mixed.covered).toBe(0.5);
  });

  it("skips bye weeks; empty/unknown → neutral", () => {
    expect(scheduleStrength("ARI", [14]).covered).toBe(0);
    expect(scheduleStrength("ZZZ", [1]).strength).toBe(0.5);
  });
});

describe("playoffSchedule (E4 consumer)", () => {
  it("returns 3 playoff games + strength for a real team", () => {
    const ps = playoffSchedule({ nfl_team: "ARI" });
    expect(ps.team).toBe("ARI");
    expect(ps.games.map((g) => g.week)).toEqual([15, 16, 17]);
    expect(ps.strength).toBe(0.5);
    expect(ps.covered).toBe(0);
  });

  it("degrades for unknown/absent team", () => {
    expect(playoffSchedule({ nfl_team: null }).games).toEqual([]);
    expect(playoffSchedule({}).strength).toBe(0.5);
    expect(playoffSchedule({ nfl_team: "ZZZ" }).games).toEqual([]);
  });
});
