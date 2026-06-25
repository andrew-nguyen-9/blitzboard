import { describe, it, expect } from "vitest";
import {
  proj,
  optimalLineupPoints,
  expectedReplacementAtNextTurn,
  marginalStarterValue,
  DEFAULT_POLICY,
  detectRuns,
  byeCover,
  injuryCover,
  ceilingWeeks,
  availability,
  benchValue,
  isCapped,
  overfillPenalty,
  scoreBoard,
  norm,
} from "./draftAI";
import { SUPERFLEX_ROSTER } from "./draft";
import { runSnakeDraft, mulberry32 } from "./snakeDraft";
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

describe("byeCover", () => {
  it("counts one start per distinct same-position starter bye", () => {
    const cand = mk("wr4", "WR", 120);
    const starters = [mk("wr1", "WR", 240, { bye_week: 7 }), mk("wr2", "WR", 230, { bye_week: 11 })];
    expect(byeCover(cand, starters)).toBe(2);
  });
  it("is 0 when no same-position starter has a bye", () => {
    expect(byeCover(mk("wr4", "WR", 120), [mk("rb1", "RB", 240, { bye_week: 7 })])).toBe(0);
  });
});

describe("injuryCover", () => {
  it("is 0 with no starter to cover", () => {
    expect(injuryCover(mk("rb3", "RB", 100), null, false, DEFAULT_POLICY)).toBe(0);
  });
  it("amplifies a same-team handcuff over a generic backup", () => {
    const cand = mk("rb-hc", "RB", 100, { nfl_team: "KC" });
    const starter = mk("rb1", "RB", 240, { nfl_team: "KC" });
    const hc = injuryCover(cand, starter, true, DEFAULT_POLICY);
    const generic = injuryCover(cand, starter, false, DEFAULT_POLICY);
    expect(hc).toBeGreaterThan(generic);
  });
});

describe("ceilingWeeks", () => {
  it("rewards a candidate whose boom beats a weak marginal starter", () => {
    const boomy = mk("wr4", "WR", 120, { boom: 240 });
    expect(ceilingWeeks(boomy, 130, DEFAULT_POLICY)).toBeGreaterThan(0);
  });
  it("is 0 when the ceiling cannot beat the marginal starter", () => {
    const flat = mk("wr5", "WR", 90, { boom: 95 });
    expect(ceilingWeeks(flat, 200, DEFAULT_POLICY)).toBe(0);
  });
});

describe("benchValue", () => {
  function ctx(teamPicks: PlayerWithValue[]): any {
    return { pool: [], teamPicks, roster: SUPERFLEX_ROSTER, benchSize: 6, allPicks: [], numTeams: 12, picksUntilNext: 1, round: 8, totalRounds: 16 };
  }
  it("ranks a high-ceiling WR4 above a second kicker", () => {
    const team = [
      mk("qb1", "QB", 300), mk("rb1", "RB", 250, { nfl_team: "KC" }), mk("rb2", "RB", 240),
      mk("wr1", "WR", 240, { bye_week: 7 }), mk("wr2", "WR", 230), mk("te1", "TE", 180),
      mk("k1", "K", 130),
    ];
    const wr4 = mk("wr4", "WR", 120, { boom: 230, bye_week: 11 });
    const k2 = mk("k2", "K", 125, { boom: 135 });
    expect(benchValue(wr4, ctx(team))).toBeGreaterThan(benchValue(k2, ctx(team)));
  });
});

describe("availability", () => {
  it("discounts a deeply buried role below the prior", () => {
    expect(availability(mk("x", "RB", 80, { depth: 4 }), DEFAULT_POLICY)).toBeLessThan(DEFAULT_POLICY.availabilityPrior);
    expect(availability(mk("y", "RB", 80, { depth: 1 }), DEFAULT_POLICY)).toBe(DEFAULT_POLICY.availabilityPrior);
  });
});

describe("isCapped (hard K/DST gate)", () => {
  it("blocks a 2nd K before the final rounds and allows it inside them", () => {
    expect(isCapped(mk("k2", "K", 120), { K: 1 }, false)).toBe(true);
    expect(isCapped(mk("k2", "K", 120), { K: 1 }, true)).toBe(false);
    expect(isCapped(mk("k1", "K", 120), { K: 0 }, false)).toBe(false);
  });
});

describe("overfillPenalty", () => {
  function ctx(teamPicks: PlayerWithValue[]): any {
    return { pool: [], teamPicks, roster: SUPERFLEX_ROSTER, benchSize: 6, allPicks: [], numTeams: 12, picksUntilNext: 1, round: 9, totalRounds: 16 };
  }
  it("penalizes a position past its reasonable depth", () => {
    const team = Array.from({ length: 5 }, (_, i) => mk(`rb${i}`, "RB", 150 - i));
    expect(overfillPenalty(mk("rb5", "RB", 90), ctx(team), DEFAULT_POLICY)).toBeGreaterThan(0);
  });
  it("is 0 within depth", () => {
    expect(overfillPenalty(mk("rb1", "RB", 150), ctx([]), DEFAULT_POLICY)).toBe(0);
  });
});

describe("scoreBoard assembly", () => {
  function ctx(pool: PlayerWithValue[], teamPicks: PlayerWithValue[], round = 1): any {
    return { pool, teamPicks, roster: SUPERFLEX_ROSTER, benchSize: 6, allPicks: [], numTeams: 12, picksUntilNext: 1, round, totalRounds: 16 };
  }
  it("does not surface a 2nd K/DST before the final rounds", () => {
    const pool = [mk("k2", "K", 300), mk("wr3", "WR", 120)];
    const team = [mk("k1", "K", 130)];
    const ranked = scoreBoard(ctx(pool, team, 5));
    expect(norm(ranked[0].player.position)).not.toBe("K");
  });
});

describe("full-draft regression", () => {
  it("no team holds 2+ K or 2+ DST before the final 2 rounds (the anti-hoarding cap)", () => {
    // Realistic pool: offense is plentiful and high-value; K/DST are few and low-value
    // (~110-140 pts, as in real leagues). The policy defers K/DST on value, and the hard
    // cap prevents a 2nd before the final rounds. [pos, count, topProj, bottomProj]
    const spec: [string, number, number, number][] = [
      ["QB", 60, 300, 120],
      ["RB", 110, 290, 40],
      ["WR", 130, 285, 30],
      ["TE", 45, 230, 50],
      ["K", 24, 140, 118],
      ["DST", 24, 135, 108],
    ];
    const players: PlayerWithValue[] = [];
    let n = 0;
    for (const [pos, count, top, bot] of spec) {
      for (let k = 0; k < count; k++) {
        const projPts = Math.round(top - ((top - bot) * k) / Math.max(1, count - 1));
        players.push(mk(`${pos}${k}`, pos, projPts, { bye_week: (n % 14) + 1, nfl_team: `T${n % 32}` }));
        n++;
      }
    }
    const picks = runSnakeDraft(players, { numTeams: 12, rng: mulberry32(42), randomness: 0 });
    const totalRounds = picks.length / 12;
    const earlyByTeam: Record<number, { K: number; DST: number }> = {};
    for (const p of picks) {
      if (Math.ceil(p.pickNo / 12) > totalRounds - 2) continue; // final 2 rounds are exempt
      const pos = norm(p.player.position);
      if (pos === "K" || pos === "DST") {
        earlyByTeam[p.team] ??= { K: 0, DST: 0 };
        earlyByTeam[p.team][pos as "K" | "DST"] += 1;
      }
    }
    for (const counts of Object.values(earlyByTeam)) {
      expect(counts.K).toBeLessThanOrEqual(1);
      expect(counts.DST).toBeLessThanOrEqual(1);
    }
  });
});
