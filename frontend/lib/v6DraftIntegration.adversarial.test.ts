import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fillRoster, type RosterSlot } from "./draft";
import { benchScore } from "./benchScore";
import { isCapped, scoreBoard, type AIContext } from "./draftAI";
import { contingentValuation, weeklyByeCoverage } from "./contingency";
import type { PlayerWithValue } from "./types";

function player(
  id: string,
  position: string,
  options: {
    projection?: number;
    boom?: number | null;
    bye?: number | null;
    team?: string | null;
    depth?: number | null;
    roleTransfer?: { source: string } | null;
  } = {},
): PlayerWithValue {
  const projection = options.projection ?? 170;
  return {
    id,
    full_name: id,
    position,
    nfl_team: options.team === undefined ? "TST" : options.team,
    bye_week: options.bye === undefined ? 8 : options.bye,
    injury_status: null,
    metadata: {
      depth_chart_order: options.depth === undefined ? 1 : options.depth,
      ...(options.roleTransfer ? { role_transfer: options.roleTransfer } : {}),
    },
    value: {
      player_id: id,
      engine: "vorp",
      value: projection,
      vor: projection - 100,
      replacement: 100,
      boom: options.boom === undefined ? projection : options.boom,
      bust: projection - 130,
      adp: null,
      rank: null,
    },
  } as PlayerWithValue;
}

const ONE_QB: RosterSlot[] = [
  { slot: "QB", eligible: ["QB"] },
  { slot: "RB", eligible: ["RB"] },
  { slot: "WR", eligible: ["WR"] },
  { slot: "TE", eligible: ["TE"] },
  { slot: "FLEX", eligible: ["RB", "WR", "TE"] },
  { slot: "K", eligible: ["K"] },
  { slot: "DST", eligible: ["DST", "DEF"] },
];
const SUPERFLEX = [...ONE_QB, { slot: "OP", eligible: ["QB", "RB", "WR", "TE"] }];
const TWO_QB: RosterSlot[] = [
  { slot: "QB", eligible: ["QB"] },
  { slot: "QB", eligible: ["QB"] },
  { slot: "RB", eligible: ["RB"] },
  { slot: "WR", eligible: ["WR"] },
];
const CUSTOM_WR_TE: RosterSlot[] = [
  { slot: "QB", eligible: ["QB"] },
  { slot: "W/T", eligible: ["WR", "TE"] },
];

describe("C04 executable live-draft invariants", () => {
  it.each([
    ["1QB", ONE_QB],
    ["superflex", SUPERFLEX],
    ["pure 2QB", TWO_QB],
    ["custom WR/TE flex", CUSTOM_WR_TE],
  ] as const)("places only eligible starters in %s", (_name, slots) => {
    const roster = [player("qb", "QB"), player("rb", "RB"), player("wr", "WR"), player("te", "TE")];
    const filled = fillRoster(roster, [...slots]);
    filled.starters.forEach((assignment, index) => {
      if (assignment.player) expect(slots[index].eligible).toContain(assignment.player.position);
    });
  });

  it("does not treat a backup QB as a legal 1QB starter, but does in SF and pure 2QB", () => {
    const qbs = [player("qb1", "QB", { projection: 300 }), player("qb2", "QB", { projection: 260 })];
    expect(fillRoster(qbs, ONE_QB).bench.map((p) => p.id)).toContain("qb2");
    expect(fillRoster(qbs, SUPERFLEX).bench).toHaveLength(0);
    expect(fillRoster(qbs, TWO_QB).bench).toHaveLength(0);
  });

  it("hard-demotes an early duplicate K or DST", () => {
    expect(isCapped(player("k2", "K"), { K: 1 }, false)).toBe(true);
    expect(isCapped(player("dst2", "DST"), { DST: 1 }, false)).toBe(true);
    expect(isCapped(player("k2", "K"), { K: 1 }, true)).toBe(false);
  });

  it("gives the same QB2 substantially more bench value in SF than 1QB", () => {
    const qb1 = player("qb1", "QB", { projection: 310 });
    const qb2 = player("qb2", "QB", { projection: 250 });
    const roster = [qb1, qb2];
    const trends = { qb2: { opportunity_trend: 0.8, starting_prob: 0.9, job_security: 0.9 } };
    const one = benchScore(qb2, { roster, rosterSlots: ONE_QB, trends, tiers: { qb2: 1 } });
    const sf = benchScore(qb2, { roster, rosterSlots: SUPERFLEX, trends, tiers: { qb2: 1 } });
    expect(sf.superflex).toBe(true);
    expect(one.superflex).toBe(false);
    expect(sf.score).toBeGreaterThan(one.score + 20);
  });

  it("rejects teammate WR/TE handcuffs without explicit same-position transfer evidence", () => {
    const starter = player("wr1", "WR", { team: "AAA", depth: 1 });
    const teammateTe = player("te2", "TE", { team: "AAA", depth: 2 });
    const teammateWr = player("wr2", "WR", { team: "AAA", depth: 2 });
    expect(contingentValuation(teammateTe, starter).eligible).toBe(false);
    expect(contingentValuation(teammateWr, starter).eligible).toBe(false);
  });

  it("degrades ambiguous QB/RB depth instead of making a succession claim", () => {
    for (const pos of ["QB", "RB"]) {
      const result = contingentValuation(
        player(`${pos}2`, pos, { team: "AAA", depth: 2 }),
        player(`${pos}x`, pos, { team: "AAA", depth: null }),
      );
      expect(result.eligible).toBe(false);
      expect(result.inheritanceProb).toBe(0);
      expect(result.degradedReason).toBeTruthy();
    }
  });

  it("awards neither same-bye coverage nor coverage of an ineligible slot", () => {
    const sameBye = weeklyByeCoverage(
      player("wr2", "WR", { bye: 7 }),
      [{ slot: "WR", player: player("wr1", "WR", { bye: 7 }) }],
      [{ slot: "WR", eligible: ["WR"] }],
    );
    const ineligible = weeklyByeCoverage(
      player("wr3", "WR", { bye: 9 }),
      [{ slot: "RB", player: player("rb1", "RB", { bye: 7 }) }],
      [{ slot: "RB", eligible: ["RB"] }],
    );
    expect(sameBye.expectedStarts).toBe(0);
    expect(ineligible.expectedStarts).toBe(0);
  });

  it("keeps the browser scoring import graph free of simulation/Monte Carlo modules", () => {
    const source = readFileSync(new URL("./draftAI.ts", import.meta.url), "utf8");
    expect(source).not.toMatch(/from\s+["'][^"']*(simulation|season_eval|monte.?carlo)/i);
    expect(source).not.toMatch(/\bMonteCarlo\b|\bsimulate(?:Season|Draft)\s*\(/);
  });

  it("uses a deterministic single-board operation budget, not repeated stochastic trials", () => {
    const pool = Array.from({ length: 24 }, (_, i) => player(`wr${i}`, "WR", { projection: 240 - i }));
    let rngCalls = 0;
    const ctx: AIContext = {
      pool,
      teamPicks: [],
      roster: ONE_QB,
      benchSize: 4,
      allPicks: [],
      numTeams: 12,
      picksUntilNext: 11,
      round: 5,
      totalRounds: 13,
      randomness: 0.1,
      rng: () => { rngCalls += 1; return 0.5; },
    };
    expect(scoreBoard(ctx)).toHaveLength(pool.length);
    expect(rngCalls).toBe(pool.length);
  });
});
