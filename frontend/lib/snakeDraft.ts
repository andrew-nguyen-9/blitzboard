// Shared snake-draft driver: one definition of the 12-team superflex snake loop,
// used by BOTH the live offline sim (scripts/simulate.ts) and the backtest bridge
// (scripts/draftSim.ts). Keeping the loop here (not copy-pasted per script) means a
// change to pick mechanics lands in one place — the single-source-of-truth the
// backtest depends on (D7). The policy itself is pickForTeam (lib/draftAI.ts).
import { pickForTeam } from "./draftAI";
import type { AIContext } from "./draftAI";
import { teamOnClock, SUPERFLEX_ROSTER, BENCH_SIZE } from "./draft";
import type { PlayerWithValue } from "./types";
import type { MappedPick } from "./sleeperDraft";

// Small, fast, seedable PRNG so a seed fully determines a draft (deterministic backtests).
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface SnakeOpts {
  numTeams: number;
  rng?: () => number;
  randomness?: number;
  // Optional pick strategy (backtest baselines/ablations). Defaults to the shared v2 policy,
  // so the live board (simulate.ts) is unaffected.
  chooser?: (ctx: AIContext) => PlayerWithValue | null;
}

// Run a full snake draft with every team on the shared policy; return the pick log.
// Sync wrapper over the generator below — behavior and pick order are identical.
export function runSnakeDraft(players: PlayerWithValue[], opts: SnakeOpts): MappedPick[] {
  const g = snakeDraftPicks(players, opts);
  let r = g.next();
  while (!r.done) r = g.next();
  return r.value;
}

// Async driver for tests/tools: identical draft, but yields to the event loop after every
// pick. A full 192-pick draft is otherwise one multi-second synchronous block; inside a
// vitest worker under CPU load that block can starve the worker<->main RPC past its 60s
// ceiling and fail a fully green run ("Timeout calling onTaskUpdate"). Per-pick yields cap
// the longest synchronous stretch at a single pick, which no plausible load stretches to 60s.
export async function runSnakeDraftAsync(players: PlayerWithValue[], opts: SnakeOpts): Promise<MappedPick[]> {
  const g = snakeDraftPicks(players, opts);
  let r = g.next();
  while (!r.done) {
    await new Promise((res) => setImmediate(res));
    r = g.next();
  }
  return r.value;
}

// The single draft loop both drivers share: yields each pick, returns the full log.
function* snakeDraftPicks(players: PlayerWithValue[], opts: SnakeOpts): Generator<MappedPick, MappedPick[]> {
  const { numTeams, rng = Math.random, randomness = 0.05, chooser = pickForTeam } = opts;
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
      chooser({
        pool,
        teamPicks,
        roster: SUPERFLEX_ROSTER,
        benchSize: BENCH_SIZE,
        allPicks: picks,
        numTeams,
        picksUntilNext: nextPickAfter(team, pickNo) - pickNo,
        round: Math.ceil(pickNo / numTeams),
        totalRounds: ROSTER_SPOTS,
        randomness,
        rng,
      }) ?? pool[0];
    const pick: MappedPick = { pickNo, team, player };
    picks.push(pick);
    taken.add(player.id);
    yield pick;
  }
  return picks;
}
