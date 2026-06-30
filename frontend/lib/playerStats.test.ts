import { describe, expect, it } from "vitest";
import { careerColumns, careerRows, careerSummary, type SeasonRow } from "@/lib/playerStats";

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
