// Node bridge: run one 12-team superflex snake draft through the SHARED policy
// (pickForTeam) for the backtest harness. Reads pool+config+seed on stdin, emits
// rosters on stdout. Deterministic per seed (mulberry32 → AIContext.rng) so the
// Python harness gets identical drafts on re-runs. This keeps the draft policy a
// single source of truth — the backtest and the live board run the same code (D7).
// Run: node_modules/.bin/tsx scripts/draftSim.ts   (reads JSON config on stdin)
import { readFileSync } from "node:fs";
import { pickForTeam } from "../lib/draftAI";
import { teamOnClock, SUPERFLEX_ROSTER, BENCH_SIZE } from "../lib/draft";
import type { PlayerWithValue } from "../lib/types";
import type { MappedPick } from "../lib/sleeperDraft";

// Small, fast, seedable PRNG so a seed fully determines the draft.
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const cfg = JSON.parse(readFileSync(0, "utf8")) as {
  players: PlayerWithValue[];
  numTeams: number;
  seed: number;
  policy: string;
};
const { players, numTeams, seed } = cfg;
const rng = mulberry32(seed);
const ROSTER_SPOTS = SUPERFLEX_ROSTER.length + BENCH_SIZE;
const totalSpots = numTeams * ROSTER_SPOTS;

const picks: MappedPick[] = [];
const taken = new Set<string>();
const nextPickAfter = (team: number, from: number) => {
  let n = from + 1;
  while (n <= totalSpots) {
    if (teamOnClock(n, numTeams) === team) return n;
    n++;
  }
  return totalSpots + 1;
};

while (picks.length < totalSpots) {
  const pickNo = picks.length + 1;
  const team = teamOnClock(pickNo, numTeams);
  const pool = players.filter((p) => !taken.has(p.id));
  const teamPicks = picks.filter((p) => p.team === team).map((p) => p.player);
  const player =
    pickForTeam({
      pool,
      teamPicks,
      roster: SUPERFLEX_ROSTER,
      benchSize: BENCH_SIZE,
      allPicks: picks,
      numTeams,
      picksUntilNext: nextPickAfter(team, pickNo) - pickNo,
      round: Math.ceil(pickNo / numTeams),
      totalRounds: ROSTER_SPOTS,
      randomness: 0.05,
      rng,
    }) ?? pool[0];
  picks.push({ pickNo, team, player });
  taken.add(player.id);
}

const rosters: string[][] = Array.from({ length: numTeams }, () => []);
for (const pk of picks) rosters[pk.team - 1].push(pk.player.id);
process.stdout.write(JSON.stringify({ rosters }));
