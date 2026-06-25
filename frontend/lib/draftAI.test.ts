import { describe, it, expect } from "vitest";
import {
  proj,
  optimalLineupPoints,
  expectedReplacementAtNextTurn,
  marginalStarterValue,
  DEFAULT_POLICY,
  detectRuns,
} from "./draftAI";
import { SUPERFLEX_ROSTER } from "./draft";
import type { PlayerWithValue } from "./types";

// Minimal player factory — only the fields the policy reads. Value-fields (boom, vor,
// replacement) go INSIDE value; player-fields (bye_week, nfl_team, depth) stay on the player.
// proj(p) = vor + replacement, so it defaults to projPts.
function mk(
  id: string,
  position: string,
  projPts: number,
  opts: {
    boom?: number;
    vor?: number;
    replacement?: number;
    bye_week?: number | null;
    nfl_team?: string | null;
    depth?: number;
  } = {},
): PlayerWithValue {
  const { boom, vor = projPts, replacement = 0, bye_week = null, nfl_team = null, depth } = opts;
  return {
    id,
    full_name: id,
    position,
    nfl_team,
    bye_week,
    metadata: depth != null ? { depth_chart_order: depth } : {},
    value: {
      player_id: id,
      engine: "vorp",
      value: projPts,
      vor,
      replacement,
      boom: boom ?? projPts,
      bust: projPts,
      adp: null,
      rank: null,
    },
  } as PlayerWithValue;
}

describe("proj", () => {
  it("sums vor and replacement (season projection)", () => {
    const p = mk("a", "RB", 0);
    p.value!.vor = 120;
    p.value!.replacement = 80;
    expect(proj(p)).toBe(200);
  });
});

describe("optimalLineupPoints", () => {
  it("is 0 for an empty roster and adds a placed starter's projection", () => {
    expect(optimalLineupPoints([], SUPERFLEX_ROSTER)).toBe(0);
    expect(optimalLineupPoints([mk("qb1", "QB", 300)], SUPERFLEX_ROSTER)).toBe(300);
  });
});

describe("expectedReplacementAtNextTurn", () => {
  const runs = detectRuns([], 12);
  it("returns the best-at-position when nothing is expected to go", () => {
    const pool = [mk("rb1", "RB", 200), mk("rb2", "RB", 190)];
    expect(expectedReplacementAtNextTurn("RB", pool, 0, runs, DEFAULT_POLICY)).toBe(200);
  });
  it("walks down the pool as more picks pass before the next turn", () => {
    const pool = [mk("rb1", "RB", 200), mk("rb2", "RB", 190), mk("rb3", "RB", 150)];
    // a thicker run share + more picks => a worse expected replacement survives
    const hot = { rate: { RB: 0.5 }, count: { RB: 6 }, hot: ["RB"] };
    const deep = expectedReplacementAtNextTurn("RB", pool, 10, hot, DEFAULT_POLICY);
    expect(deep).toBeLessThan(200);
  });
});

describe("marginalStarterValue", () => {
  function ctx(pool: PlayerWithValue[], teamPicks: PlayerWithValue[], picksUntilNext = 1): any {
    return { pool, teamPicks, roster: SUPERFLEX_ROSTER, benchSize: 6, allPicks: [], numTeams: 12, picksUntilNext, round: 1, totalRounds: 16 };
  }
  it("scores a needed superflex QB higher than a redundant 3rd RB", () => {
    const pool = [mk("qb2", "QB", 280), mk("rb3", "RB", 180)];
    const team = [mk("qb1", "QB", 300), mk("rb1", "RB", 220), mk("rb2", "RB", 210)];
    const qb = marginalStarterValue(pool[0], ctx([...pool], team));
    const rb = marginalStarterValue(pool[1], ctx([...pool], team));
    expect(qb).toBeGreaterThan(rb);
  });
  it("is 0 when a candidate cannot crack the optimal starting lineup", () => {
    // every slot a weak RB is eligible for (RB, FLEX, superflex OP) is filled by a stronger body.
    const team = [
      mk("qb1", "QB", 300), mk("rb1", "RB", 250), mk("rb2", "RB", 240),
      mk("wr1", "WR", 230), mk("wr2", "WR", 220), mk("te1", "TE", 210),
      mk("rb3", "RB", 200), mk("rb4s", "RB", 190), // these two fill FLEX + OP
    ];
    const weakRb = mk("rb5", "RB", 50);
    expect(marginalStarterValue(weakRb, ctx([weakRb], team))).toBe(0);
  });
});
