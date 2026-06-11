// Pure draft logic — snake pick math, superflex-aware roster fill, scarcity.
// Kept framework-free so it's trivially testable and reused by the board + sim.
import type { PlayerWithValue } from "./types";

export interface RosterSlot {
  slot: string;
  eligible: string[];
}

// Smores 2025 starting lineup (OP = superflex). DST eligible covers Sleeper's "DEF".
export const SMORES_ROSTER: RosterSlot[] = [
  { slot: "QB", eligible: ["QB"] },
  { slot: "RB", eligible: ["RB"] },
  { slot: "RB", eligible: ["RB"] },
  { slot: "WR", eligible: ["WR"] },
  { slot: "WR", eligible: ["WR"] },
  { slot: "TE", eligible: ["TE"] },
  { slot: "FLEX", eligible: ["RB", "WR", "TE"] },
  { slot: "OP", eligible: ["QB", "RB", "WR", "TE"] }, // superflex
  { slot: "DST", eligible: ["DST", "DEF"] },
  { slot: "K", eligible: ["K"] },
];
export const BENCH_SIZE = 6;

// Which overall pick numbers (1-indexed) belong to `slot` in a snake draft.
export function myPickNumbers(numTeams: number, slot: number, rounds: number): number[] {
  const picks: number[] = [];
  for (let r = 1; r <= rounds; r++) {
    const inRound = r % 2 === 1 ? slot : numTeams - slot + 1;
    picks.push((r - 1) * numTeams + inRound);
  }
  return picks;
}

// Team (1-indexed) on the clock at a given overall pick in a snake draft.
export function teamOnClock(pickNo: number, numTeams: number): number {
  const round = Math.ceil(pickNo / numTeams);
  const idx = ((pickNo - 1) % numTeams) + 1;
  return round % 2 === 1 ? idx : numTeams - idx + 1;
}

export interface RosterFill {
  starters: { slot: string; player: PlayerWithValue | null }[];
  bench: PlayerWithValue[];
  needs: string[];
  projectedPoints: number;
}

// Greedily fit a set of players (best value first) into the starting lineup,
// preferring dedicated slots before FLEX/OP, remainder → bench.
export function fillRoster(players: PlayerWithValue[]): RosterFill {
  const ordered = [...players].sort(
    (a, b) => (b.value?.vor ?? -999) - (a.value?.vor ?? -999),
  );
  const starters = SMORES_ROSTER.map((s) => ({ slot: s.slot, player: null as PlayerWithValue | null }));
  const bench: PlayerWithValue[] = [];

  for (const p of ordered) {
    const pos = p.position ?? "";
    // dedicated slot first (FLEX/OP last so studs don't burn flex early)
    const order = [...starters.keys()].sort((i, j) => rank(starters[i].slot) - rank(starters[j].slot));
    let placed = false;
    for (const i of order) {
      if (!starters[i].player && SMORES_ROSTER[i].eligible.includes(pos)) {
        starters[i].player = p;
        placed = true;
        break;
      }
    }
    if (!placed) bench.push(p);
  }

  const needs = starters.filter((s) => !s.player).map((s) => s.slot);
  const projectedPoints = starters.reduce(
    (sum, s) => sum + (s.player?.value?.value ?? 0),
    0,
  );
  return { starters, bench, needs, projectedPoints };
}

// dedicated positions before flexible ones
function rank(slot: string): number {
  if (slot === "OP") return 3;
  if (slot === "FLEX") return 2;
  return 1;
}

// Starter-caliber players remaining at each position (vor > 0) → scarcity signal.
export function scarcity(available: PlayerWithValue[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const p of available) {
    if ((p.value?.vor ?? 0) > 0) {
      const pos = p.position ?? "?";
      out[pos] = (out[pos] ?? 0) + 1;
    }
  }
  return out;
}
