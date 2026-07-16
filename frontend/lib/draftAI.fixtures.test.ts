// E1 golden draft fixtures (spec categories 1–7 + the auto-draft end-state invariant).
// Each fixture = (roster state + available board) → the asserted correct pick, with a
// reason. The pipeline half (value/tuning + team-vs-team, cat 8) lives in
// pipeline/tests/test_draft_fixtures.py. Together they exceed the 50-fixture floor.
//
// Player factory mirrors draftAI.test.ts: value-fields live in `value`, player-fields
// (bye_week, nfl_team, injury_status, depth) on the row. proj(p)=vor+replacement.
import { describe, it, expect } from "vitest";
import {
  pickForTeam,
  scoreBoard,
  norm,
  injuryAvailability,
  byeStackPenalty,
  fillsEmptyOffensiveStarter,
  DEFAULT_POLICY,
  type PolicyParams,
} from "./draftAI";
import type { AIContext } from "./draftAI";
import { SUPERFLEX_ROSTER, fillRoster } from "./draft";
import { runSnakeDraft, mulberry32 } from "./snakeDraft";
import type { PlayerWithValue } from "./types";

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
    injury_status?: string | null;
  } = {},
): PlayerWithValue {
  const {
    boom, vor = projPts, replacement = 0, bye_week = null, nfl_team = null, depth,
    injury_status = null,
  } = opts;
  return {
    id,
    full_name: id,
    position,
    nfl_team,
    bye_week,
    injury_status,
    metadata: depth != null ? { depth_chart_order: depth } : {},
    value: {
      player_id: id, engine: "vorp", value: projPts, vor, replacement,
      boom: boom ?? projPts, bust: projPts, adp: null, rank: null,
    },
  } as PlayerWithValue;
}

function ctx(
  pool: PlayerWithValue[],
  teamPicks: PlayerWithValue[],
  round = 5,
  extra: Partial<AIContext> = {},
): AIContext {
  return {
    pool, teamPicks, roster: SUPERFLEX_ROSTER, benchSize: 6, allPicks: [],
    numTeams: 12, picksUntilNext: 1, round, totalRounds: 16, ...extra,
  };
}

// A full offensive starting core (QB,RB,RB,WR,WR,TE,FLEX,OP) + DST, no K — the common
// "everything but a kicker" late-draft roster.
function coreOffenseNoK(): PlayerWithValue[] {
  return [
    mk("qb1", "QB", 300, { nfl_team: "KC", bye_week: 10 }),
    mk("qb2", "QB", 280, { nfl_team: "BUF", bye_week: 7 }),
    mk("rb1", "RB", 250, { nfl_team: "SF", bye_week: 8 }),
    mk("rb2", "RB", 240, { nfl_team: "DET", bye_week: 6 }),
    mk("wr1", "WR", 240, { nfl_team: "MIA", bye_week: 6 }),
    mk("wr2", "WR", 230, { nfl_team: "PHI", bye_week: 10 }),
    mk("te1", "TE", 190, { nfl_team: "BAL", bye_week: 13 }),
    mk("rb3", "RB", 200, { nfl_team: "CIN", bye_week: 6 }),
    mk("dst1", "DST", 130, { nfl_team: "CLE", bye_week: 11 }),
  ];
}

// ── Category 1 — No second kicker (≥8) ───────────────────────────────────────
describe("cat1: never a second kicker before the final rounds", () => {
  const offense: [string, string, number][] = [
    ["rb", "RB", 120], ["wr", "WR", 118], ["qb", "QB", 260], ["te", "TE", 150],
    ["rb", "RB", 90], ["wr", "WR", 80], ["qb", "QB", 240], ["te", "TE", 110],
  ];
  it.each(offense)("has 1 K; picks the %s over a 2nd K (round 5)", (idp, pos, pts) => {
    const team = [...coreOffenseNoK(), mk("k1", "K", 135, { nfl_team: "DAL", bye_week: 7 })];
    const pool = [mk("k2", "K", 300, { nfl_team: "GB", bye_week: 5 }), mk(`${idp}X`, pos, pts, { nfl_team: "NYJ", bye_week: 13 })];
    const pick = pickForTeam(ctx(pool, team, 5))!;
    expect(norm(pick.position)).not.toBe("K");
    expect(pick.id).toBe(`${idp}X`);
  });
});

// ── Category 2 — No second DEF (≥8) ──────────────────────────────────────────
describe("cat2: never a second DST before the final rounds", () => {
  const offense: [string, string, number][] = [
    ["rb", "RB", 130], ["wr", "WR", 125], ["qb", "QB", 250], ["te", "TE", 160],
    ["rb", "RB", 95], ["wr", "WR", 85], ["qb", "QB", 235], ["te", "TE", 105],
  ];
  it.each(offense)("has 1 DST; picks the %s over a 2nd DST (round 6)", (idp, pos, pts) => {
    const team = [...coreOffenseNoK(), mk("k1", "K", 135, { nfl_team: "DAL", bye_week: 7 })];
    const pool = [mk("dst2", "DST", 300, { nfl_team: "PIT", bye_week: 9 }), mk(`${idp}Y`, pos, pts, { nfl_team: "SEA", bye_week: 11 })];
    const pick = pickForTeam(ctx(pool, team, 6))!;
    expect(norm(pick.position)).not.toBe("DST");
    expect(pick.id).toBe(`${idp}Y`);
  });
});

// ── Category 3 — Startable-slots-first (≥10) ─────────────────────────────────
describe("cat3: fill an empty startable offensive slot before bench/K/DST", () => {
  // Each case: a partial roster leaving one offensive slot open, a viable filler vs a
  // bench-only body or a K/DST → the starter must win.
  const cases: [string, PlayerWithValue[], PlayerWithValue[], string][] = [
    ["empty QB", [mk("rb1", "RB", 250), mk("wr1", "WR", 240)],
      [mk("qbS", "QB", 200, { nfl_team: "KC" }), mk("k1", "K", 300, { nfl_team: "GB" })], "qbS"],
    ["empty TE", [mk("qb1", "QB", 300), mk("rb1", "RB", 250), mk("wr1", "WR", 240), mk("wr2", "WR", 230)],
      [mk("teS", "TE", 150, { nfl_team: "BAL" }), mk("dst1", "DST", 300, { nfl_team: "SF" })], "teS"],
    ["empty RB", [mk("qb1", "QB", 300), mk("wr1", "WR", 240)],
      [mk("rbS", "RB", 190, { nfl_team: "SF" }), mk("k1", "K", 300, { nfl_team: "GB" })], "rbS"],
    ["empty WR", [mk("qb1", "QB", 300), mk("rb1", "RB", 250)],
      [mk("wrS", "WR", 195, { nfl_team: "MIA" }), mk("dst1", "DST", 300, { nfl_team: "SF" })], "wrS"],
    ["empty FLEX", [mk("qb1", "QB", 300), mk("rb1", "RB", 250), mk("rb2", "RB", 240), mk("wr1", "WR", 235), mk("wr2", "WR", 230), mk("te1", "TE", 180), mk("qb2", "QB", 220)],
      [mk("flexS", "RB", 170, { nfl_team: "CIN" }), mk("k1", "K", 300, { nfl_team: "GB" })], "flexS"],
    ["empty OP (superflex)", [mk("qb1", "QB", 300), mk("rb1", "RB", 250), mk("rb2", "RB", 240), mk("wr1", "WR", 235), mk("wr2", "WR", 230), mk("te1", "TE", 180), mk("rb3", "RB", 175)],
      [mk("opS", "QB", 210, { nfl_team: "BUF" }), mk("dst1", "DST", 300, { nfl_team: "SF" })], "opS"],
    ["empty QB vs bench RB", [mk("rb1", "RB", 250), mk("rb2", "RB", 240), mk("wr1", "WR", 235), mk("wr2", "WR", 230), mk("te1", "TE", 180), mk("rb3", "RB", 175), mk("rb4", "RB", 170)],
      [mk("qbS", "QB", 205, { nfl_team: "KC" }), mk("rbBench", "RB", 150, { nfl_team: "NYG" })], "qbS"],
    ["empty TE vs K", [mk("qb1", "QB", 300), mk("qb2", "QB", 280), mk("rb1", "RB", 250), mk("rb2", "RB", 240), mk("wr1", "WR", 235), mk("wr2", "WR", 230), mk("rb3", "RB", 175)],
      [mk("teS", "TE", 160, { nfl_team: "BAL" }), mk("k1", "K", 300, { nfl_team: "GB" })], "teS"],
    ["empty WR vs bench TE", [mk("qb1", "QB", 300), mk("rb1", "RB", 250), mk("rb2", "RB", 240), mk("wr1", "WR", 235), mk("te1", "TE", 180)],
      [mk("wrS", "WR", 185, { nfl_team: "MIA" }), mk("teBench", "TE", 120, { nfl_team: "KC" })], "wrS"],
    ["empty RB vs DST", [mk("qb1", "QB", 300), mk("wr1", "WR", 240), mk("wr2", "WR", 230), mk("te1", "TE", 180)],
      [mk("rbS", "RB", 200, { nfl_team: "SF" }), mk("dst1", "DST", 300, { nfl_team: "PIT" })], "rbS"],
  ];
  it.each(cases)("%s → fills the starter", (_label, team, pool, want) => {
    expect(pickForTeam(ctx(pool, team, 4))!.id).toBe(want);
  });
});

// ── Category 4 — Bye-cover (≥6) ──────────────────────────────────────────────
describe("cat4: covering a fresh bye beats stacking a shared one", () => {
  // Two WR starters share bye 7. A candidate that stacks bye 7 must lose to a slightly
  // lower-projection candidate covering a different week.
  function sharedByeTeam(): PlayerWithValue[] {
    return [
      mk("qb1", "QB", 300, { nfl_team: "KC", bye_week: 10 }),
      mk("qb2", "QB", 280, { nfl_team: "BUF", bye_week: 7 }),
      mk("rb1", "RB", 250, { nfl_team: "SF", bye_week: 9 }),
      mk("rb2", "RB", 240, { nfl_team: "DET", bye_week: 5 }),
      mk("wr1", "WR", 235, { nfl_team: "JAX", bye_week: 7 }),
      mk("wr2", "WR", 230, { nfl_team: "LAC", bye_week: 7 }),
      mk("te1", "TE", 180, { nfl_team: "BAL", bye_week: 13 }),
    ];
  }
  const cases: [string, number, number, number, number, string][] = [
    // [label, stackProj, stackBye, coverProj, coverBye, expectedId]
    ["small edge", 152, 7, 150, 11, "cover"],
    ["tiny edge", 151, 7, 150, 14, "cover"],
    ["equal", 150, 7, 150, 8, "cover"],
    ["cover bye 5-adjacent", 154, 7, 150, 6, "cover"],
    ["cover different", 153, 7, 150, 12, "cover"],
    ["cover clean week", 152, 7, 149, 9, "cover"],
  ];
  it.each(cases)("%s: covers instead of stacking bye 7", (_l, sp, sb, cp, cb, want) => {
    const pool = [
      mk("stack", "WR", sp, { nfl_team: "MIN", bye_week: sb }),
      mk("cover", "WR", cp, { nfl_team: "NYG", bye_week: cb }),
    ];
    expect(pickForTeam(ctx(pool, sharedByeTeam(), 6))!.id).toBe(want);
  });
  it("byeStackPenalty scales with the number of starters already on that bye", () => {
    const c = ctx([], sharedByeTeam());
    const stacks = mk("s", "WR", 150, { bye_week: 7 });
    const fresh = mk("f", "WR", 150, { bye_week: 12 });
    expect(byeStackPenalty(stacks, c)).toBeGreaterThan(byeStackPenalty(fresh, c));
    expect(byeStackPenalty(fresh, c)).toBe(0);
  });
});

// ── Category 5 — Injury discount (≥6) ────────────────────────────────────────
describe("cat5: an injured body's value drops below a healthy comparable", () => {
  // Both candidates fill the same empty WR slot; the injured one carries a higher raw
  // projection but its availability discount drops it below the healthy pick.
  const cases: [string, string, number, number, string][] = [
    // [label, status, injuredProj, healthyProj, expectedId]
    ["questionable", "Questionable", 210, 200, "healthy"],
    ["doubtful", "Doubtful", 240, 200, "healthy"],
    ["out", "Out", 300, 200, "healthy"],
    ["ir", "IR", 400, 200, "healthy"],
    ["pup", "PUP", 380, 200, "healthy"],
    ["suspended", "Sus", 320, 200, "healthy"],
  ];
  it.each(cases)("%s injured loses to healthy comparable", (_l, status, ip, hp, want) => {
    const team = [mk("qb1", "QB", 300), mk("rb1", "RB", 250)]; // WR slots open
    const pool = [
      mk("injured", "WR", ip, { nfl_team: "MIA", injury_status: status }),
      mk("healthy", "WR", hp, { nfl_team: "PHI" }),
    ];
    expect(pickForTeam(ctx(pool, team, 5))!.id).toBe(want);
  });
  it("injuryAvailability is identity when no status is present (degrade-safe)", () => {
    expect(injuryAvailability(mk("x", "WR", 200), DEFAULT_POLICY)).toBe(1);
    expect(injuryAvailability(mk("x", "WR", 200, { injury_status: "Questionable" }), DEFAULT_POLICY)).toBeLessThan(1);
  });
});

// ── Category 6 — Tier cliffs (≥6) ────────────────────────────────────────────
describe("cat6: take the value before the cliff (last of a tier > first of the next)", () => {
  // Two positions both fill a starter slot; the pre-cliff (higher-value) body wins.
  const cases: [string, string, number, string, number, string][] = [
    // [label, posA, projA(pre-cliff), posB, projB(post-cliff), expectedId]
    ["RB cliff over WR", "RB", 210, "WR", 150, "A"],
    ["WR cliff over TE", "WR", 205, "TE", 140, "A"],
    ["QB cliff over RB", "QB", 260, "RB", 160, "A"],
    ["RB cliff over QB", "RB", 240, "QB", 175, "A"],
    ["TE cliff over WR", "TE", 200, "WR", 120, "A"],
    ["WR cliff over RB", "WR", 220, "RB", 130, "A"],
  ];
  it.each(cases)("%s", (_l, posA, pa, posB, pb, want) => {
    const team = [mk("qb1", "QB", 300), mk("rb1", "RB", 250), mk("wr1", "WR", 240)];
    const pool = [
      mk("A", posA, pa, { nfl_team: "KC" }),
      mk("B", posB, pb, { nfl_team: "SF" }),
    ];
    expect(pickForTeam(ctx(pool, team, 5))!.id).toBe(want);
  });
});

// ── Category 7 — Late-round K/DEF timing (≥4) ────────────────────────────────
describe("cat7: in the final rounds the single K/DST is correctly taken", () => {
  it("takes the K to fill the empty K slot late (round 15)", () => {
    const team = coreOffenseNoK(); // full offense + DST, no K
    const pool = [mk("k1", "K", 130, { nfl_team: "DAL", bye_week: 7 }), mk("wr9", "WR", 90, { nfl_team: "NYJ", boom: 130, bye_week: 13 })];
    expect(norm(pickForTeam(ctx(pool, team, 15))!.position)).toBe("K");
  });
  it("takes the DST to fill the empty DST slot late (round 16)", () => {
    const team = [
      ...coreOffenseNoK().filter((p) => p.id !== "dst1"),
      mk("k1", "K", 130, { nfl_team: "DAL", bye_week: 7 }),
    ]; // full offense + K, no DST
    const pool = [mk("dst1", "DST", 125, { nfl_team: "PIT", bye_week: 9 }), mk("te5", "TE", 80, { nfl_team: "KC", boom: 120, bye_week: 10 })];
    expect(norm(pickForTeam(ctx(pool, team, 16))!.position)).toBe("DST");
  });
  it("a 2nd K is allowed only inside the final-rounds window", () => {
    const team = [...coreOffenseNoK(), mk("k1", "K", 135, { nfl_team: "DAL" })];
    const pool = [mk("k2", "K", 128, { nfl_team: "GB" })];
    // final rounds → the cap lifts, so the K is a legal (indeed the only) pick
    expect(scoreBoard(ctx(pool, team, 16))[0].reason).not.toContain("capped");
  });
  it("still defers K when a startable offensive slot remains open late", () => {
    const team = [mk("qb1", "QB", 300), mk("rb1", "RB", 250), mk("wr1", "WR", 240)]; // many slots open
    const pool = [mk("k1", "K", 130, { nfl_team: "DAL" }), mk("wrS", "WR", 150, { nfl_team: "MIA" })];
    expect(norm(pickForTeam(ctx(pool, team, 15))!.position)).not.toBe("K");
  });
});

// ── Auto-draft end-state invariant ───────────────────────────────────────────
describe("auto-draft end-state invariant (full 12-team sim)", () => {
  function realisticPool(): PlayerWithValue[] {
    const spec: [string, number, number, number][] = [
      ["QB", 60, 300, 120], ["RB", 110, 290, 40], ["WR", 130, 285, 30],
      ["TE", 45, 230, 50], ["K", 24, 140, 118], ["DST", 24, 135, 108],
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
    return players;
  }
  const OFFENSIVE = new Set(["QB", "RB", "WR", "TE", "FLEX", "OP"]);

  it.each([1, 7, 42, 100])("seed %s: no team ends with an empty startable offensive slot", (seed) => {
    const players = realisticPool();
    const byId = new Map(players.map((p) => [p.id, p]));
    const picks = runSnakeDraft(players, { numTeams: 12, rng: mulberry32(seed), randomness: 0 });
    for (let t = 1; t <= 12; t++) {
      const roster = picks.filter((pk) => pk.team === t).map((pk) => byId.get(pk.player.id)!);
      const needs = fillRoster(roster, SUPERFLEX_ROSTER).needs;
      const offenseEmpty = needs.filter((slot) => OFFENSIVE.has(slot));
      expect(offenseEmpty).toEqual([]);
    }
  });

  it.each([1, 7, 42])("seed %s: no team holds 2+ K or 2+ DST before the final 2 rounds", (seed) => {
    const players = realisticPool();
    const picks = runSnakeDraft(players, { numTeams: 12, rng: mulberry32(seed), randomness: 0 });
    const totalRounds = picks.length / 12;
    const early: Record<number, { K: number; DST: number }> = {};
    for (const p of picks) {
      if (Math.ceil(p.pickNo / 12) > totalRounds - DEFAULT_POLICY.kdstCapRoundsFromEnd) continue;
      const pos = norm(p.player.position);
      if (pos === "K" || pos === "DST") {
        early[p.team] ??= { K: 0, DST: 0 };
        early[p.team][pos as "K" | "DST"] += 1;
      }
    }
    for (const c of Object.values(early)) {
      expect(c.K).toBeLessThanOrEqual(1);
      expect(c.DST).toBeLessThanOrEqual(1);
    }
  });

  // Backtest: v4 (tuned, with the new draft-awareness terms) ≥ v3 (terms neutralized) on
  // total starting-lineup points-for across the league — the "v4 ≥ v3" regression gate.
  it.each([1, 7, 42])("seed %s: v4 lineup points-for ≥ v3", (seed) => {
    const players = realisticPool();
    const byId = new Map(players.map((p) => [p.id, p]));
    const V3: PolicyParams = {
      ...DEFAULT_POLICY,
      emptyOffensiveStarterBonus: 0,
      byeStackPenalty: 0,
      injuryDiscount: {},
    };
    const total = (params: PolicyParams) => {
      const picks = runSnakeDraft(players, {
        numTeams: 12, rng: mulberry32(seed), randomness: 0,
        chooser: (c) => pickForTeam(c, params),
      });
      let sum = 0;
      for (let t = 1; t <= 12; t++) {
        const roster = picks.filter((pk) => pk.team === t).map((pk) => byId.get(pk.player.id)!);
        sum += fillRoster(roster, SUPERFLEX_ROSTER).projectedPoints;
      }
      return sum;
    };
    expect(total(DEFAULT_POLICY)).toBeGreaterThanOrEqual(total(V3));
  });

  // E5: folding E4's bench scoring into the bench arm builds the ideal superflex bench —
  // ≥2 QB rostered (OP slot + a real backup), ≥1 RB lottery + ≥1 WR breakout benched, and
  // no dead K/DST pileup. (The dedicated end-to-end sim is E7; this proves the integration.)
  it.each([1, 7, 42, 100])("seed %s: ideal superflex bench (≥2 QB, RB+WR bench, no dead K/DST pileup)", (seed) => {
    const players = realisticPool();
    const byId = new Map(players.map((p) => [p.id, p]));
    const picks = runSnakeDraft(players, { numTeams: 12, rng: mulberry32(seed), randomness: 0 });
    for (let t = 1; t <= 12; t++) {
      const roster = picks.filter((pk) => pk.team === t).map((pk) => byId.get(pk.player.id)!);
      const qbCount = roster.filter((p) => norm(p.position) === "QB").length;
      expect(qbCount).toBeGreaterThanOrEqual(2); // superflex: 2 startable QB slots + backup depth

      const bench = fillRoster(roster, SUPERFLEX_ROSTER).bench;
      const benchPos = (pos: string) => bench.filter((p) => norm(p.position) === pos).length;
      expect(benchPos("RB")).toBeGreaterThanOrEqual(1); // RB lottery ticket
      expect(benchPos("WR")).toBeGreaterThanOrEqual(1); // WR breakout
      expect(benchPos("K")).toBeLessThanOrEqual(1);     // no dead kicker pileup
      expect(benchPos("DST")).toBeLessThanOrEqual(1);   // no dead defense pileup
    }
  });
});

// ── Helper-unit coverage for the new terms ───────────────────────────────────
describe("new-term unit coverage", () => {
  it("fillsEmptyOffensiveStarter is true for an open slot, false when offense is full", () => {
    const openTeam = [mk("qb1", "QB", 300)];
    expect(fillsEmptyOffensiveStarter(mk("rb1", "RB", 200), ctx([], openTeam))).toBe(true);
    const full = coreOffenseNoK();
    expect(fillsEmptyOffensiveStarter(mk("wrX", "WR", 90), ctx([], full))).toBe(false);
    expect(fillsEmptyOffensiveStarter(mk("k1", "K", 130), ctx([], openTeam))).toBe(false);
  });
});
