// C01 unit-contract regression tests: value.boom is CEILING VOR; raw projections are never
// compared with replacement-adjusted values in the draft policy.
import { describe, it, expect } from "vitest";
import { projectionMean, projectionCeiling, ceilingVor } from "./valueUnits";
import { ceilingWeeks, benchValue, DEFAULT_POLICY, proj } from "./draftAI";
import { SUPERFLEX_ROSTER } from "./draft";
import type { PlayerWithValue } from "./types";

function mkv(id: string, position: string, vor: number, replacement: number, boomVor: number | null): PlayerWithValue {
  return {
    id, full_name: id, position, nfl_team: null, bye_week: 4, injury_status: null, metadata: {},
    value: { player_id: id, engine: "vorp", value: vor, vor, replacement, boom: boomVor, bust: null, adp: null, rank: null },
  } as PlayerWithValue;
}

describe("value unit helpers", () => {
  it("projectionMean = vor + replacement; projectionCeiling = boom + replacement", () => {
    const p = mkv("a", "RB", 100, 100, 150);
    expect(projectionMean(p)).toBe(200);
    expect(ceilingVor(p)).toBe(150);
    expect(projectionCeiling(p)).toBe(250);
  });
  it("missing boom or replacement degrades to null — no silent substitution", () => {
    expect(projectionCeiling(mkv("a", "RB", 100, 100, null))).toBeNull();
    const noRepl = mkv("b", "RB", 100, 0, 150);
    (noRepl.value as { replacement: number | null }).replacement = null;
    expect(projectionCeiling(noRepl)).toBeNull();
  });
});

describe("ceilingWeeks compares raw ceiling with raw starter projection (the v5 unit bug)", () => {
  it("a candidate whose RAW ceiling clears the starter keeps ceiling-week credit even when stored boom (ceiling VOR) sits below the bar", () => {
    // raw ceiling = 150 + 100 = 250 > bar 180, but v5 compared 150 < 180 → zero credit.
    const cand = mkv("candidate", "RB", 100, 100, 150);
    expect(ceilingWeeks(cand, 180, DEFAULT_POLICY)).toBeGreaterThan(0);
  });
  it("no credit when the raw ceiling truly sits below the bar", () => {
    const cand = mkv("weak", "RB", 10, 100, 20); // raw ceiling 120 < 180
    expect(ceilingWeeks(cand, 180, DEFAULT_POLICY)).toBe(0);
  });
  it("high-replacement positions are not upside-suppressed relative to identical raw ceilings", () => {
    // Same raw projection and raw ceiling; only the replacement split differs.
    const qb = mkv("sfqb", "QB", 40, 210, 60);   // raw ceiling 270
    const rb = mkv("rb", "RB", 150, 100, 170);   // raw ceiling 270
    expect(proj(qb)).toBe(proj(rb));
    expect(ceilingWeeks(qb, 220, DEFAULT_POLICY)).toBeCloseTo(ceilingWeeks(rb, 220, DEFAULT_POLICY), 10);
  });
});

describe("benchValue blends raw mean with raw ceiling", () => {
  it("the expected-starts × value-per-game core is invariant to the replacement split of identical raw numbers", () => {
    // benchQualityWeight: 0 ablates the E4 benchScore fold, which legitimately works on the
    // VOR scale (no mixed comparison there); the remaining core must be raw-unit-clean.
    const params = { ...DEFAULT_POLICY, benchQualityWeight: 0 };
    const mkCtx = (cand: PlayerWithValue) => ({
      pool: [cand], teamPicks: [], roster: SUPERFLEX_ROSTER, benchSize: 6, allPicks: [],
      numTeams: 12, picksUntilNext: 12, round: 8, totalRounds: 16, randomness: 0, rng: () => 0.5,
    });
    const a = mkv("a", "WR", 120, 80, 140);  // raw mean 200, raw ceiling 220
    const b = mkv("b", "WR", 60, 140, 80);   // raw mean 200, raw ceiling 220
    expect(benchValue(a, mkCtx(a), params)).toBeCloseTo(benchValue(b, mkCtx(b), params), 10);
  });
});
