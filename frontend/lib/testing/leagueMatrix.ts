// E7a league-config matrix loader — TEST-ONLY. Reads the checked-in fixture via node:fs; never
// import this from app code (leak-boundary.test.ts guards the client bundle).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { RosterSlot } from "../draft";
import { defaultTeams, type LeagueConfig } from "../leagueConfig";

export interface LeagueMatrixRow {
  id: string;
  teams: number;
  qb_mode: "1qb" | "superflex" | "2qb";
  scoring: "std" | "half" | "ppr";
  te_premium: number;
  bench_slots: number;
  ir_slots: number;
  starting_slots: Record<string, number>;
}

interface MatrixFile {
  version: number;
  factors: Record<string, unknown[]>;
  rows: LeagueMatrixRow[];
  smoke: string[];
}

const FIXTURE_PATH = join(__dirname, "..", "..", "..", "fixtures", "league_matrix.json");
let cached: MatrixFile | null = null;

function data(): MatrixFile {
  if (!cached) cached = JSON.parse(readFileSync(FIXTURE_PATH, "utf8"));
  return cached!;
}

export function all(): LeagueMatrixRow[] {
  return data().rows;
}

export function smoke(): LeagueMatrixRow[] {
  const ids = new Set(data().smoke);
  return all().filter((r) => ids.has(r.id));
}

export function byId(id: string): LeagueMatrixRow {
  const row = all().find((r) => r.id === id);
  if (!row) throw new Error(`unknown league_matrix row id: ${id}`);
  return row;
}

const ELIGIBLE: Record<string, string[]> = {
  QB: ["QB"],
  RB: ["RB"],
  WR: ["WR"],
  TE: ["TE"],
  FLEX: ["RB", "WR", "TE"],
  SUPERFLEX: ["QB", "RB", "WR", "TE"],
  K: ["K"],
  DST: ["DST", "DEF"],
};

// gotcha: `LeagueConfig` has no ir_slots field — the matrix's `ir_slots` factor has nowhere to
// land here (see the .done.md gotchas line); everything else maps cleanly.
export function toLeagueConfig(row: LeagueMatrixRow): LeagueConfig {
  const rosterSlots: RosterSlot[] = Object.entries(row.starting_slots).flatMap(([slot, n]) =>
    Array.from({ length: n }, () => ({ slot, eligible: ELIGIBLE[slot] ?? [slot] }))
  );
  const label = `${row.scoring.toUpperCase()} · ${row.qb_mode}${row.te_premium ? ` · TE+${row.te_premium}` : ""}`;
  return {
    source: "manual",
    leagueId: null,
    name: row.id,
    numTeams: row.teams,
    rosterSlots,
    benchSize: row.bench_slots,
    scoringLabel: label,
    teams: defaultTeams(row.teams),
  };
}
