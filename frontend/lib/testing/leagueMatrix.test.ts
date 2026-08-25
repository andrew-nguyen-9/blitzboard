import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { all, smoke, byId, toLeagueConfig, type LeagueMatrixRow } from "./leagueMatrix";

const FACTORS = ["teams", "qb_mode", "scoring", "te_premium", "bench_slots", "ir_slots"] as const;

function expectedSlots(qbMode: string): Record<string, number> {
  const slots: Record<string, number> = { QB: 1, RB: 2, WR: 2, TE: 1, FLEX: 1 };
  if (qbMode === "superflex") slots.SUPERFLEX = 1;
  else if (qbMode === "2qb") slots.QB = 2;
  slots.K = 1;
  slots.DST = 1;
  return slots;
}

describe("league_matrix loader", () => {
  it("returns exactly 432 rows", () => {
    expect(all().length).toBe(432);
  });

  it("has unique ids", () => {
    const ids = all().map((r) => r.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("derives starting_slots per the rule", () => {
    for (const row of all()) {
      expect(row.starting_slots).toEqual(expectedSlots(row.qb_mode));
    }
  });

  it("smoke has 16 existing ids", () => {
    const rows = smoke();
    expect(rows.length).toBe(16);
    const allIds = new Set(all().map((r) => r.id));
    for (const r of rows) expect(allIds.has(r.id)).toBe(true);
  });

  it("smoke set is pairwise-covering", () => {
    const rows = smoke();
    const levels: Record<string, Set<unknown>> = {};
    for (const f of FACTORS) levels[f] = new Set(all().map((r) => (r as unknown as Record<string, unknown>)[f]));
    for (let i = 0; i < FACTORS.length; i++) {
      for (let j = i + 1; j < FACTORS.length; j++) {
        const [a, b] = [FACTORS[i], FACTORS[j]];
        const needed = new Set<string>();
        for (const la of levels[a]) for (const lb of levels[b]) needed.add(`${la}|${lb}`);
        const covered = new Set(rows.map((r) => `${(r as unknown as Record<string, unknown>)[a]}|${(r as unknown as Record<string, unknown>)[b]}`));
        expect(covered).toEqual(needed);
      }
    }
  });

  it("byId matches a raw JSON parse of the same fixture (tier-independent agreement)", () => {
    const raw = JSON.parse(
      readFileSync(join(process.cwd(), "..", "fixtures", "league_matrix.json"), "utf8")
    ) as { rows: LeagueMatrixRow[] };
    for (let i = 0; i < raw.rows.length; i += 37) {
      expect(byId(raw.rows[i].id)).toEqual(raw.rows[i]);
    }
  });

  it("byId throws on unknown id", () => {
    expect(() => byId("does-not-exist")).toThrow();
  });

  it("toLeagueConfig maps roster shape", () => {
    const row = byId("t12-superflex-ppr-te0.0-b6-ir1");
    const cfg = toLeagueConfig(row);
    expect(cfg.numTeams).toBe(12);
    expect(cfg.benchSize).toBe(6);
    expect(cfg.teams.length).toBe(12);
    expect(cfg.rosterSlots.some((s) => s.slot === "SUPERFLEX")).toBe(true);
  });
});
