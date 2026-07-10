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

// Parity band for the randomized fair-trade generator: two sides count as "fair"
// when the smaller total is within FAIR_TRADE_BAND of the larger — i.e. their
// gap is ≤15% of the bigger side. Expressed as a fairness floor of 1-band=0.85.
// Matches the calculator's fairness = min/max convention (see TradeCalculator).
export const FAIR_TRADE_BAND = 0.15;

// 0..1 balance between two side totals (1 = identical value). Guards div-by-zero:
// two empty/zero sides are trivially "fair".
export function tradeFairness(a: number, b: number): number {
  const hi = Math.max(a, b);
  return hi > 0 ? Math.min(a, b) / hi : 1;
}

// Small deterministic PRNG (mulberry32) so the fair-trade button is reproducible
// under test; production passes Math.random. ponytail: 4 lines beats a dep.
export function seededRng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface FairTrade<T> {
  give: T[];
  get: T[];
  giveValue: number;
  getValue: number;
  fairness: number; // ≥ 1 - band by construction
}

// Randomized balanced trade over an arbitrary player pool. Picks a random anchor
// for the GIVE side, then tries a 1-for-1 within the parity band; if none lands it
// packages a 2-for-1 to balance a lopsided anchor. Value is read via `value` so the
// same generator serves the unauth snapshot (pval) and the authed roster (VORP).
// Returns null only when the pool holds no fair pairing (e.g. one dominant player).
export function randomFairTrade<T extends { id: string }>(
  pool: T[],
  opts: { value: (p: T) => number; band?: number; rng?: () => number; maxGetPerSide?: number },
): FairTrade<T> | null {
  const { value, band = FAIR_TRADE_BAND, rng = Math.random, maxGetPerSide = 2 } = opts;
  const floor = 1 - band;
  const usable = pool.filter((p) => value(p) > 0);
  if (usable.length < 2) return null;

  // Fisher–Yates shuffle so the anchor scan order (and thus the trade) is random.
  const order = [...usable];
  for (let i = order.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [order[i], order[j]] = [order[j], order[i]];
  }

  for (const anchor of order) {
    const target = value(anchor);
    const rest = usable.filter((p) => p.id !== anchor.id);
    // 1-for-1: nearest-value counterpart within the band.
    let best: T | null = null;
    let bestFair = floor;
    for (const c of rest) {
      const f = tradeFairness(target, value(c));
      if (f >= bestFair) { bestFair = f; best = c; }
    }
    if (best) {
      const gv = value(best);
      return { give: [anchor], get: [best], giveValue: target, getValue: gv, fairness: tradeFairness(target, gv) };
    }
    // 2-for-1: a lopsided anchor packaged against two players summing into band.
    if (maxGetPerSide >= 2) {
      const sorted = [...rest].sort((a, b) => value(b) - value(a));
      for (let i = 0; i < sorted.length; i++) {
        for (let j = i + 1; j < sorted.length; j++) {
          const sum = value(sorted[i]) + value(sorted[j]);
          if (sum > target) break; // sorted desc: once the pair overshoots, inner only grows
          const f = tradeFairness(target, sum);
          if (f >= floor) {
            return { give: [anchor], get: [sorted[i], sorted[j]], giveValue: target, getValue: sum, fairness: f };
          }
        }
      }
    }
  }
  return null;
}

export interface BestTrade extends TradeProposal {
  partnerId: string;
  partnerName: string;
}

// The user's BEST trades across their whole league: run the Pareto finder against
// every opponent roster, tag each proposal with its partner, then rank by MY gain
// (fairness breaks ties — a fair win is likelier to be accepted). Reads ONLY the
// opponent rosters passed in, so the caller controls (and RLS-scopes) the universe:
// nothing outside `opponents` can ever surface. See trades/page.tsx for the authz gate.
export function bestTradesForRoster(
  mine: PlayerWithValue[],
  opponents: { id: string; name: string; players: PlayerWithValue[] }[],
  opts: { maxPerSide?: number; perPartner?: number; limit?: number; minDelta?: number; roster?: RosterSlot[] } = {},
): BestTrade[] {
  const { perPartner = 5, limit = 20, ...findOpts } = opts;
  const all: BestTrade[] = [];
  for (const opp of opponents) {
    if (!opp.players.length) continue;
    for (const t of findTrades(mine, opp.players, { ...findOpts, limit: perPartner })) {
      all.push({ ...t, partnerId: opp.id, partnerName: opp.name });
    }
  }
  all.sort((a, b) => b.myDelta - a.myDelta || b.fairness - a.fairness);
  return all.slice(0, limit);
}

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
