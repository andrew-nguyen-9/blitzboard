import { describe, it, expect } from "vitest";
import { parseSleeperRules, parseEspnRules } from "./leagueRules";

describe("parseSleeperRules", () => {
  it("detects superflex, FAAB, distance kicking and PPR from a Sleeper league", () => {
    const r = parseSleeperRules({
      total_rosters: 12,
      roster_positions: ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "SUPER_FLEX", "K", "DEF", "BN", "BN", "BN", "BN", "BN", "BN"],
      scoring_settings: { rec: 0.5, pass_td: 4, fgm_0_19: 3, fgm_50p: 5, pts_allow_0: 5 },
      settings: { waiver_type: 2, waiver_budget: 100, num_teams: 12 },
    });
    expect(r.superflex).toBe(true);
    expect(r.waiver_type).toBe("faab");
    expect(r.distance_kicking).toBe(true);
    expect(r.yardage_dst).toBe(false); // only points-allowed here
    expect(r.ppr).toBe(0.5);
    expect(r.league_size).toBe(12);
    expect(r.bench).toBe(6);
    expect(r.scoring_label).toBe("Half-PPR · Superflex");
  });

  it("detects yardage D/ST and a standard, non-superflex, rolling-waiver league", () => {
    const r = parseSleeperRules({
      total_rosters: 10,
      roster_positions: ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF", "BN", "BN"],
      scoring_settings: { rec: 0, yds_allow_0_100: 5, yds_allow_350_399: -1 },
      settings: { waiver_type: 0 },
    });
    expect(r.superflex).toBe(false);
    expect(r.waiver_type).toBe("rolling");
    expect(r.yardage_dst).toBe(true);
    expect(r.distance_kicking).toBe(false);
    expect(r.ppr).toBe(0);
    expect(r.league_size).toBe(10);
    expect(r.scoring_label).toBe("Standard");
  });
});

describe("parseEspnRules", () => {
  it("detects superflex (slot 7), FAAB, distance kicking and yardage D/ST from ESPN settings", () => {
    const r = parseEspnRules({
      settings: {
        size: 12,
        rosterSettings: { lineupSlotCounts: { "0": 1, "2": 2, "4": 2, "6": 1, "23": 1, "7": 1, "16": 1, "17": 1, "20": 6 } },
        scoringSettings: { scoringItems: [{ statId: 53 }, { statId: 201 }, { statId: 127 }] },
        acquisitionSettings: { isUsingAcquisitionBudget: true, acquisitionBudget: 100 },
      },
    });
    expect(r.superflex).toBe(true);
    expect(r.waiver_type).toBe("faab");
    expect(r.distance_kicking).toBe(true);
    expect(r.yardage_dst).toBe(true);
    expect(r.league_size).toBe(12);
    expect(r.bench).toBe(6);
    // roster has QB,RB,RB,WR,WR,TE,FLEX,OP,DST,K = 10 starters
    expect(r.roster_slots).toHaveLength(10);
    expect(r.roster_slots.some((s) => s.slot === "OP")).toBe(true);
  });

  it("detects a standard non-superflex non-FAAB ESPN league", () => {
    const r = parseEspnRules({
      settings: {
        size: 10,
        rosterSettings: { lineupSlotCounts: { "0": 1, "2": 2, "4": 2, "6": 1, "23": 1, "16": 1, "17": 1, "20": 5 } },
        scoringSettings: { scoringItems: [{ statId: 53 }] },
        acquisitionSettings: { isUsingAcquisitionBudget: false, acquisitionBudget: 0 },
      },
    });
    expect(r.superflex).toBe(false);
    expect(r.waiver_type).toBe("unknown");
    expect(r.distance_kicking).toBe(false);
    expect(r.yardage_dst).toBe(false);
    expect(r.bench).toBe(5);
  });
});
