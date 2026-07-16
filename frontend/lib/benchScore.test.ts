import { describe, it, expect } from "vitest";
import {
  benchScore,
  benchHealth,
  dropPriority,
  GENERAL_WEIGHTS,
  SF_QB_WEIGHTS,
  SF_RB_WEIGHTS,
  SF_WR_WEIGHTS,
  type BenchCtx,
  type BenchTrends,
} from "./benchScore";
import type { PlayerWithValue, PlayerValue, Position } from "./types";

// ── fixtures ─────────────────────────────────────────────────────────────────

let seq = 0;
function player(over: Partial<PlayerWithValue> & { position: Position }): PlayerWithValue {
  const value: PlayerValue = {
    player_id: `p${seq}`,
    engine: "vorp",
    value: 20,
    vor: 20,
    replacement: 100,
    boom: 150,
    bust: 60,
    adp: null,
    rank: null,
    ...(over.value ?? {}),
  };
  const base: PlayerWithValue = {
    id: over.id ?? `p${++seq}`,
    sleeper_id: "s",
    espn_id: null,
    full_name: over.full_name ?? "Player",
    position: over.position,
    nfl_team: over.nfl_team ?? "KC",
    bye_week: over.bye_week ?? 10,
    age: 25,
    years_exp: 3,
    status: null,
    injury_status: over.injury_status ?? null,
    metadata: over.metadata ?? {},
    value,
  };
  return { ...base, ...over, value };
}

const sum = (o: Record<string, number>) => Object.values(o).reduce((a, b) => a + b, 0);

// ── weight integrity ─────────────────────────────────────────────────────────

describe("weight tables", () => {
  it("positive weights sum to 100 per formula", () => {
    expect(sum(GENERAL_WEIGHTS)).toBe(100);
    expect(sum(SF_QB_WEIGHTS)).toBe(100);
    expect(sum(SF_RB_WEIGHTS)).toBe(100);
    expect(sum(SF_WR_WEIGHTS)).toBe(100);
  });
});

// ── general model ────────────────────────────────────────────────────────────

describe("general benchScore", () => {
  it("returns 0-100", () => {
    const p = player({ position: "RB" });
    const ctx: BenchCtx = { roster: [p], superflex: false };
    const r = benchScore(p, ctx);
    expect(r.score).toBeGreaterThanOrEqual(0);
    expect(r.score).toBeLessThanOrEqual(100);
    expect(r.superflex).toBe(false);
  });

  it("rising-trend player scores higher than a flat one", () => {
    const rising = player({ id: "rise", position: "WR" });
    const flat = player({ id: "flat", position: "WR", nfl_team: "BUF" });
    const trends: Record<string, BenchTrends> = {
      rise: { opportunity_trend: 0.85 },
      flat: { opportunity_trend: 0.5 },
    };
    const ctx: BenchCtx = { roster: [rising, flat], superflex: false, trends };
    expect(benchScore(rising, ctx).score).toBeGreaterThan(benchScore(flat, ctx).score);
  });

  it("duplicate-position penalty lowers a stacked backup", () => {
    const starter = player({ id: "rb1", position: "RB", value: { vor: 60 } as PlayerValue });
    const backup = player({ id: "rb2", position: "RB", value: { vor: 40 } as PlayerValue });
    const dupe = player({ id: "rb3", position: "RB", value: { vor: 20 } as PlayerValue });
    const lone: BenchCtx = { roster: [starter, backup], superflex: false };
    const stacked: BenchCtx = { roster: [starter, backup, dupe], superflex: false };
    // rb3 sits deeper (more duplicated) → lower than the same body would score with fewer dupes.
    expect(benchScore(dupe, stacked).score).toBeLessThan(benchScore(backup, lone).score);
  });

  it("dead-roster-spot penalty fires on a backup K and backup DST", () => {
    const k1 = player({ id: "k1", position: "K", value: { vor: 5 } as PlayerValue });
    const k2 = player({ id: "k2", position: "K", value: { vor: 2 } as PlayerValue });
    const d1 = player({ id: "d1", position: "DEF", value: { vor: 5 } as PlayerValue });
    const d2 = player({ id: "d2", position: "DEF", value: { vor: 2 } as PlayerValue });
    const ctx: BenchCtx = { roster: [k1, k2, d1, d2], superflex: false };
    // backup (k2/d2) scores below the starter (k1/d1) — the penalty only hits the backup.
    expect(benchScore(k2, ctx).score).toBeLessThan(benchScore(k1, ctx).score);
    expect(benchScore(d2, ctx).score).toBeLessThan(benchScore(d1, ctx).score);
  });

  it("lists degraded terms in coverage when signals are missing", () => {
    const p = player({ id: "bare", position: "WR", nfl_team: null, bye_week: null });
    const ctx: BenchCtx = { roster: [p], superflex: false }; // no trends, no tiers, no schedule
    const r = benchScore(p, ctx);
    expect(r.coverage).toContain("OpportunityTrend");
    expect(r.coverage).toContain("PositionalScarcity");
    expect(r.coverage).toContain("PlayoffSchedule");
    expect(r.coverage).toContain("ByeCoverage");
  });
});

// ── superflex overlay ────────────────────────────────────────────────────────

describe("superflex overlay", () => {
  it("holds a healthy backup QB over a WR5", () => {
    const qb = player({
      id: "qb2",
      position: "QB",
      full_name: "Backup QB",
      metadata: { depth_chart_order: 2 },
    });
    const wr5 = player({
      id: "wr5",
      position: "WR",
      full_name: "WR5",
      nfl_team: "BUF",
      value: { vor: 2, boom: 60 } as PlayerValue,
    });
    const trends: Record<string, BenchTrends> = {
      qb2: { starting_prob: 0.3, job_security: 0.35, opportunity_trend: 0.5 },
      wr5: { target_share_trend: 0.25, routes_trend: 0.2, opportunity_trend: 0.3 },
    };
    const ctx: BenchCtx = { roster: [qb, wr5], superflex: true, trends };
    const qbR = benchScore(qb, ctx);
    const wrR = benchScore(wr5, ctx);
    expect(qbR.superflex).toBe(true);
    expect(qbR.score).toBeGreaterThan(wrR.score);
  });

  it("derives superflex from a league config with an OP slot", () => {
    const qb = player({ id: "q", position: "QB", metadata: { depth_chart_order: 2 } });
    const config = {
      source: "manual" as const,
      leagueId: null,
      name: "L",
      numTeams: 12,
      rosterSlots: [{ slot: "OP", eligible: ["QB", "RB", "WR", "TE"] }],
      benchSize: 6,
      scoringLabel: "PPR · Superflex",
      teams: [],
    };
    expect(benchScore(qb, { roster: [qb], config }).superflex).toBe(true);
  });
});

// ── aggregate + drop ranking ─────────────────────────────────────────────────

describe("benchHealth / dropPriority", () => {
  it("benchHealth is the mean of member scores", () => {
    const a = player({ id: "a", position: "RB" });
    const b = player({ id: "b", position: "WR", nfl_team: "BUF" });
    const ctx: BenchCtx = { roster: [a, b], superflex: false };
    const h = benchHealth([a, b], ctx);
    const mean = (benchScore(a, ctx).score + benchScore(b, ctx).score) / 2;
    expect(h.score).toBeCloseTo(mean, 6);
    expect(h.players).toHaveLength(2);
  });

  it("ranks a backup K first to drop", () => {
    const rb = player({ id: "rb", position: "RB", value: { vor: 45, boom: 200 } as PlayerValue });
    const wr = player({ id: "wr", position: "WR", nfl_team: "BUF", value: { vor: 35, boom: 170 } as PlayerValue });
    const kStarter = player({ id: "ks", position: "K", value: { vor: 6 } as PlayerValue });
    const kBackup = player({ id: "kb", position: "K", value: { vor: 1, boom: 90 } as PlayerValue });
    const roster = [rb, wr, kStarter, kBackup];
    const trends: Record<string, BenchTrends> = {
      rb: { opportunity_trend: 0.7 },
      wr: { opportunity_trend: 0.6, target_share_trend: 0.6 },
    };
    const ctx: BenchCtx = { roster, superflex: false, trends };
    const ranked = dropPriority([rb, wr, kBackup], ctx);
    expect(ranked[0].id).toBe("kb");
  });
});
