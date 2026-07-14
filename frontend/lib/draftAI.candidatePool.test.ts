// Regression guard for the UI auto-draft path. The board sims (DraftWarRoom.runSim) score
// candidatePool(top-N) rather than runSnakeDraft's full pool — a path the fixtures never
// exercised. Top-N-by-projection alone starved skill backups (a replacement K outprojects
// hundreds of them), so every team ended with an empty TE and a bench full of kickers. These
// assert the same end-state invariants as the fixtures, but THROUGH candidatePool.
import { describe, it, expect } from "vitest";
import { pickForTeam, candidatePool, norm } from "./draftAI";
import { SUPERFLEX_ROSTER, BENCH_SIZE, fillRoster, teamOnClock } from "./draft";
import { mulberry32 } from "./snakeDraft";
import type { PlayerWithValue } from "./types";
import type { MappedPick } from "./sleeperDraft";

function mk(id: string, position: string, projPts: number, nfl_team: string | null, bye: number): PlayerWithValue {
  return {
    id, full_name: id, position, nfl_team, bye_week: bye, injury_status: null, metadata: {},
    value: { player_id: id, engine: "vorp", value: projPts, vor: projPts, replacement: 0, boom: projPts, bust: projPts, adp: null, rank: null },
  } as PlayerWithValue;
}

// Same scale as the fixtures' realisticPool: K/DST replacement floor (~118/108) sits far
// ABOVE a backup skill player (~30-50) — exactly the production projection scale.
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
      players.push(mk(`${pos}${k}`, pos, projPts, `T${n % 32}`, (n % 14) + 1));
      n++;
    }
  }
  return players;
}

// Exact copy of DraftRoom.runSim's inner loop (candidatePool path).
function runViaCandidatePool(players: PlayerWithValue[], numTeams: number, rng: () => number): MappedPick[] {
  const ROSTER_SPOTS = SUPERFLEX_ROSTER.length + BENCH_SIZE;
  const totalSpots = numTeams * ROSTER_SPOTS;
  const picks: MappedPick[] = [];
  const taken = new Set<string>();
  const nextPickAfter = (team: number, from: number) => {
    let x = from + 1;
    while (x <= totalSpots) { if (teamOnClock(x, numTeams) === team) return x; x++; }
    return totalSpots + 1;
  };
  while (picks.length < totalSpots) {
    const pickNo = picks.length + 1;
    const team = teamOnClock(pickNo, numTeams);
    const pool = candidatePool(players.filter((p) => !taken.has(p.id)));
    if (!pool.length) break;
    const teamPicks = picks.filter((p) => p.team === team).map((p) => p.player);
    const player = pickForTeam({
      pool, teamPicks, roster: SUPERFLEX_ROSTER, benchSize: BENCH_SIZE, allPicks: picks,
      numTeams, picksUntilNext: nextPickAfter(team, pickNo) - pickNo,
      round: Math.ceil(pickNo / numTeams), totalRounds: ROSTER_SPOTS, randomness: 0, rng,
    }) ?? pool[0];
    picks.push({ pickNo, team, player });
    taken.add(player.id);
  }
  return picks;
}

const OFFENSIVE = new Set(["QB", "RB", "WR", "TE", "FLEX", "OP"]);

describe("UI candidatePool auto-draft path: end-state invariants", () => {
  it.each([1, 7, 42])("seed %s: no empty offensive starter", (seed) => {
    const players = realisticPool();
    const byId = new Map(players.map((p) => [p.id, p]));
    const picks = runViaCandidatePool(players, 12, mulberry32(seed));
    for (let t = 1; t <= 12; t++) {
      const roster = picks.filter((pk) => pk.team === t).map((pk) => byId.get(pk.player.id)!);
      const empty = fillRoster(roster, SUPERFLEX_ROSTER).needs.filter((s) => OFFENSIVE.has(s));
      expect(empty).toEqual([]);
    }
  });
  it.each([1, 7, 42])("seed %s: no team holds 2+ K or 2+ DST before final 2 rounds", (seed) => {
    const players = realisticPool();
    const picks = runViaCandidatePool(players, 12, mulberry32(seed));
    const totalRounds = picks.length / 12;
    const early: Record<number, { K: number; DST: number }> = {};
    for (const p of picks) {
      if (Math.ceil(p.pickNo / 12) > totalRounds - 2) continue;
      const pos = norm(p.player.position);
      if (pos === "K" || pos === "DST") { early[p.team] ??= { K: 0, DST: 0 }; early[p.team][pos as "K" | "DST"]++; }
    }
    for (const c of Object.values(early)) { expect(c.K).toBeLessThanOrEqual(1); expect(c.DST).toBeLessThanOrEqual(1); }
  });
});
