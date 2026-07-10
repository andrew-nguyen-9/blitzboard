import { describe, expect, it } from "vitest";
import {
  advancedMetrics,
  careerColumns,
  careerRows,
  careerSummary,
  collegeContext,
  isMultiPosition,
  isRookieOrNew,
  positionEligibility,
  type SeasonRow,
} from "@/lib/playerStats";
import type { Player } from "@/lib/types";

const history: SeasonRow[] = [
  {
    season: 2024,
    fantasy_pts: 200,
    stats: { games: 16, carries: 250, rushing_yards: 1100, rushing_tds: 8, receptions: 40, receiving_yards: 300, target_share: 0.18 },
  },
  {
    season: 2025,
    fantasy_pts: 260,
    stats: { games: 17, carries: 300, rushing_yards: 1400, rushing_tds: 12, receptions: 55, receiving_yards: 400, target_share: 0.21 },
  },
];

describe("careerColumns", () => {
  it("uses position-specific splits and shares WR columns with TE", () => {
    expect(careerColumns("RB").map((c) => c.key)).toContain("carries");
    expect(careerColumns("TE").map((c) => c.key)).toEqual(careerColumns("WR").map((c) => c.key));
    // unknown / K / DEF fall back to the shared trio only
    expect(careerColumns("K").map((c) => c.key)).toEqual(["season", "games", "fantasy_pts", "ppg"]);
    // season is a text row-header so a year never renders with a thousands separator
    expect(careerColumns("RB").find((c) => c.key === "season")?.numeric).toBe(false);
  });
});

describe("careerRows", () => {
  it("derives PPG, scales target share to %, and maps jsonb keys", () => {
    const rows = careerRows(history);
    expect(rows[1].ppg).toBeCloseTo(260 / 17, 4);
    expect(rows[0].tgt_share).toBeCloseTo(18, 4);
    expect(rows[1].rush_yds).toBe(1400);
  });
  it("is null-safe for a missing stats blob (no divide-by-zero PPG)", () => {
    const rows = careerRows([{ season: 2023, fantasy_pts: 50, stats: null }]);
    expect(rows[0].ppg).toBeNull();
    expect(rows[0].tgt_share).toBeNull();
  });
});

describe("careerSummary", () => {
  it("computes career high, blended PPG, and the YoY delta", () => {
    const s = careerSummary(history);
    expect(s.bestPts).toBe(260);
    expect(s.yoyDelta).toBe(60);
    expect(s.careerPpg).toBeCloseTo((200 + 260) / (16 + 17), 4);
  });
  it("returns nulls rather than NaN with too little data", () => {
    const s = careerSummary([]);
    expect(s).toEqual({ seasons: 0, bestPts: null, careerPpg: null, yoyDelta: null });
  });
});

describe("advancedMetrics", () => {
  it("derives efficiency rates and drops metrics with no denominator", () => {
    const m = advancedMetrics(history, "RB");
    const by = Object.fromEntries(m.map((x) => [x.key, x.value]));
    // 2500 rush + 700 rec yds over 33 games; 550 carries; 95 receptions
    expect(by.scrim_ypg).toBeCloseTo((2500 + 700) / 33, 1);
    expect(by.ypc).toBeCloseTo(2500 / 550, 2);
    expect(by.ypr).toBeCloseTo(700 / 95, 2);
    // the fixture has no `targets` key → target-denominated + passing metrics drop
    expect(by.ypt).toBeUndefined();
    expect(by.catch_pct).toBeUndefined();
    expect(by.pass_ypg).toBeUndefined();
    expect(by.td_int).toBeUndefined();
  });
  it("surfaces QB passing metrics and is empty for no history", () => {
    const qb: SeasonRow[] = [
      { season: 2024, fantasy_pts: 300, stats: { games: 16, passing_yards: 4200, passing_tds: 34, interceptions: 10, carries: 40, rushing_yards: 220 } },
    ];
    const by = Object.fromEntries(advancedMetrics(qb, "QB").map((x) => [x.key, x.value]));
    expect(by.pass_ypg).toBeCloseTo(4200 / 16, 1);
    expect(by.td_int).toBeCloseTo(34 / 10, 2);
    expect(advancedMetrics([], "WR")).toEqual([]);
  });
});

const mkPlayer = (over: Partial<Player>): Player => ({
  id: "p1",
  sleeper_id: "s1",
  espn_id: null,
  full_name: "Test Player",
  position: "RB",
  nfl_team: "SF",
  bye_week: null,
  age: 22,
  years_exp: 0,
  status: null,
  injury_status: null,
  metadata: null,
  ...over,
});

describe("collegeContext + isRookieOrNew", () => {
  it("reads the college_production summary the ingest merges into metadata", () => {
    const p = mkPlayer({
      years_exp: 0,
      metadata: { college_production: { prospect_score: 0.82, college: "Texas", season: 2024 } },
    });
    expect(isRookieOrNew(p)).toBe(true);
    expect(collegeContext(p)).toEqual({ college: "Texas", prospectScore: 0.82, season: 2024 });
  });
  it("clamps score and degrades to null with no context", () => {
    expect(collegeContext(mkPlayer({ metadata: null }))).toBeNull();
    const clamped = collegeContext(
      mkPlayer({ metadata: { college_production: { prospect_score: 5 } } }),
    );
    expect(clamped?.prospectScore).toBe(1);
    expect(isRookieOrNew(mkPlayer({ years_exp: 6 }))).toBe(false);
    expect(isRookieOrNew(mkPlayer({ years_exp: null }))).toBe(false);
  });
});

describe("positionEligibility + isMultiPosition", () => {
  it("extracts skill slots from metadata.fantasy_positions", () => {
    const p = mkPlayer({ metadata: { fantasy_positions: ["RB", "WR", "K"] } });
    expect(positionEligibility(p)).toEqual(["RB", "WR"]); // K filtered out
    expect(isMultiPosition(p)).toBe(true);
  });
  it("falls back to the primary position and detects single-position", () => {
    const p = mkPlayer({ position: "TE", metadata: null });
    expect(positionEligibility(p)).toEqual(["TE"]);
    expect(isMultiPosition(p)).toBe(false);
  });
});
