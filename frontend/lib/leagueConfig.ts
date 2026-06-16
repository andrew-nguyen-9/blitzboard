// Normalized league configuration shared by the whole draft surface.
// A LeagueConfig is the single source of truth for roster shape, team count,
// team names, scoring, and (when imported) the live draft id. It can come from
// three places: the built-in SMORES default, a Sleeper username/league import,
// or an ESPN league id. Everything downstream (board, sim AI, scarcity,
// analysis) reads from this shape so adding a platform never touches the UI.

import type { RosterSlot } from "./draft";
import { SMORES_ROSTER, BENCH_SIZE } from "./draft";

export type LeagueSource = "manual" | "sleeper" | "espn";

export interface LeagueTeam {
  slot: number; // 1..numTeams draft slot
  name: string; // editable display name
  owner?: string; // platform owner/handle (read-only)
}

export interface LeagueConfig {
  source: LeagueSource;
  leagueId: string | null;
  name: string;
  numTeams: number;
  rosterSlots: RosterSlot[]; // starting lineup
  benchSize: number;
  scoringLabel: string; // human summary e.g. "PPR · Superflex"
  teams: LeagueTeam[];
  draftId?: string | null;
  draftType?: string; // snake | linear | auction
}

// The always-available default (Smores 2025 superflex).
export function defaultConfig(numTeams = 12): LeagueConfig {
  return {
    source: "manual",
    leagueId: null,
    name: "Manual Draft",
    numTeams,
    rosterSlots: SMORES_ROSTER,
    benchSize: BENCH_SIZE,
    scoringLabel: "Custom · Superflex",
    teams: defaultTeams(numTeams),
  };
}

export function defaultTeams(numTeams: number, existing: LeagueTeam[] = []): LeagueTeam[] {
  return Array.from({ length: numTeams }, (_, i) => {
    const slot = i + 1;
    const prior = existing.find((t) => t.slot === slot);
    return prior ?? { slot, name: `Team ${slot}` };
  });
}

// ── Sleeper roster_positions → our RosterSlot[] ────────────────────────────
// Sleeper encodes the starting lineup as a flat array with "BN" entries for the
// bench and "IR"/"TAXI" we ignore. Multi-position flex codes map to eligibility.
const SLEEPER_SLOT_MAP: Record<string, { slot: string; eligible: string[] }> = {
  QB: { slot: "QB", eligible: ["QB"] },
  RB: { slot: "RB", eligible: ["RB"] },
  WR: { slot: "WR", eligible: ["WR"] },
  TE: { slot: "TE", eligible: ["TE"] },
  K: { slot: "K", eligible: ["K"] },
  DEF: { slot: "DST", eligible: ["DST", "DEF"] },
  FLEX: { slot: "FLEX", eligible: ["RB", "WR", "TE"] },
  WRRB_FLEX: { slot: "W/R", eligible: ["RB", "WR"] },
  REC_FLEX: { slot: "W/T", eligible: ["WR", "TE"] },
  SUPER_FLEX: { slot: "SF", eligible: ["QB", "RB", "WR", "TE"] },
  IDP_FLEX: { slot: "IDP", eligible: ["DL", "LB", "DB"] },
  DL: { slot: "DL", eligible: ["DL"] },
  LB: { slot: "LB", eligible: ["LB"] },
  DB: { slot: "DB", eligible: ["DB"] },
};

export function rosterFromSleeper(positions: string[]): { slots: RosterSlot[]; bench: number } {
  const slots: RosterSlot[] = [];
  let bench = 0;
  for (const code of positions) {
    if (code === "BN") {
      bench++;
      continue;
    }
    if (code === "IR" || code === "TAXI") continue;
    const m = SLEEPER_SLOT_MAP[code];
    if (m) slots.push({ slot: m.slot, eligible: m.eligible });
  }
  return { slots: slots.length ? slots : SMORES_ROSTER, bench };
}

// Summarize Sleeper scoring into a short label (PPR detection + superflex flag).
export function scoringLabelFromSleeper(
  scoring: Record<string, number> | undefined,
  positions: string[],
): string {
  const rec = scoring?.rec ?? 0;
  const ppr = rec >= 1 ? "PPR" : rec >= 0.5 ? "Half-PPR" : "Standard";
  const sf = positions.includes("SUPER_FLEX") ? " · Superflex" : "";
  return `${ppr}${sf}`;
}

// All positions worth tracking for scarcity, derived from the roster's
// eligibility sets (so a non-superflex league won't show an SF row, etc.).
export function trackedPositions(config: LeagueConfig): string[] {
  const set = new Set<string>();
  for (const s of config.rosterSlots) for (const e of s.eligible) set.add(e === "DEF" ? "DST" : e);
  // stable, sensible order
  const order = ["QB", "RB", "WR", "TE", "FLEX", "K", "DST", "DL", "LB", "DB"];
  const tracked = [...set].filter((p) => p !== "DEF");
  return order.filter((p) => tracked.includes(p)).concat(tracked.filter((p) => !order.includes(p)));
}
