// Trade optimizer — find Pareto-improving swaps between two rosters (P5).
//
// "Pareto-improving" = the trade raises BOTH teams' starting-lineup value. We use
// fillRoster() so value is need-aware: a 3rd RB on your bench is worth little, but
// a WR when you start a replacement-level one is worth a lot. That positional-need
// sensitivity is what makes suggestions realistic instead of pure point-chasing.
import type { PlayerWithValue } from "./types";
import { fillRoster, SUPERFLEX_ROSTER, type RosterSlot } from "./draft";

// Starting-lineup value of a roster = sum of starters' value (need-aware via slotting).
export function rosterValue(players: PlayerWithValue[], roster: RosterSlot[] = SUPERFLEX_ROSTER): number {
  return fillRoster(players, roster).projectedPoints;
}

export interface TradeProposal {
  give: PlayerWithValue[];
  get: PlayerWithValue[];
  myDelta: number;     // my starting-value gain
  theirDelta: number;  // their starting-value gain
  fairness: number;    // 0..1, 1 = perfectly balanced gains
}

function combinations<T>(arr: T[], k: number): T[][] {
  if (k === 0) return [[]];
  if (k > arr.length) return [];
  const out: T[][] = [];
  const rec = (start: number, combo: T[]) => {
    if (combo.length === k) { out.push([...combo]); return; }
    for (let i = start; i < arr.length; i++) {
      combo.push(arr[i]);
      rec(i + 1, combo);
      combo.pop();
    }
  };
  rec(0, []);
  return out;
}

const idsOf = (ps: PlayerWithValue[]) => new Set(ps.map((p) => p.id));

export function findTrades(
  mine: PlayerWithValue[],
  theirs: PlayerWithValue[],
  opts: { maxPerSide?: number; limit?: number; minDelta?: number; roster?: RosterSlot[] } = {},
): TradeProposal[] {
  const { maxPerSide = 2, limit = 25, minDelta = 0.5, roster = SUPERFLEX_ROSTER } = opts;
  const baseMine = rosterValue(mine, roster);
  const baseTheirs = rosterValue(theirs, roster);

  const giveSets: PlayerWithValue[][] = [];
  const getSets: PlayerWithValue[][] = [];
  for (let k = 1; k <= maxPerSide; k++) {
    giveSets.push(...combinations(mine, k));
    getSets.push(...combinations(theirs, k));
  }

  const out: TradeProposal[] = [];
  for (const give of giveSets) {
    const giveIds = idsOf(give);
    const myAfterBase = mine.filter((p) => !giveIds.has(p.id));
    for (const get of getSets) {
      // keep trades roughly balanced in player count (±1)
      if (Math.abs(give.length - get.length) > 1) continue;
      const getIds = idsOf(get);
      const newMine = [...myAfterBase, ...get];
      const newTheirs = [...theirs.filter((p) => !getIds.has(p.id)), ...give];

      const myDelta = rosterValue(newMine, roster) - baseMine;
      const theirDelta = rosterValue(newTheirs, roster) - baseTheirs;
      if (myDelta > minDelta && theirDelta > minDelta) {
        const fairness = 1 - Math.abs(myDelta - theirDelta) / (myDelta + theirDelta);
        out.push({ give, get, myDelta, theirDelta, fairness });
      }
    }
  }
  // rank by my gain, then by fairness (a fair win is more likely to be accepted)
  out.sort((a, b) => b.myDelta - a.myDelta || b.fairness - a.fairness);
  return out.slice(0, limit);
}
