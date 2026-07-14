// Pure pre-draft plan builder: per-round targets + contingencies + tier map +
// ADP value flags, derived from the board and MY snake pick numbers. Feeds the
// strategy tree; recomputed only when a consequential pick fires (see
// consequential.ts) so inconsequential opponent picks don't churn the path.
import type { PlayerWithValue } from "@/lib/types";
import type { RosterSlot } from "@/lib/draft";
import { fillRoster, myPickNumbers } from "@/lib/draft";
import { norm, proj } from "@/lib/draftAI";
import { tierMap } from "@/lib/tiers";

export type ValueFlag = "value" | "reach" | "fair";

export interface PlanPlayer {
  id: string;
  name: string;
  position: string;
  proj: number;
  tier: number;
  flag: ValueFlag;
}

export interface RoundTarget {
  round: number;
  pickNo: number;
  primary: PlanPlayer[]; // best available at a needed position for that pick window
  contingency: PlanPlayer[]; // fallbacks if the primaries are gone
}

export interface DraftPlan {
  rounds: RoundTarget[];
  builtAtPickCount: number; // picks on the board when this plan was built (re-plan bookkeeping)
}

// ADP value flag: a player falling well past ADP relative to draft rank is a
// value; one you'd have to reach ahead of rank is a reach. Neutral without data.
export function valueFlag(p: PlayerWithValue): ValueFlag {
  const adp = p.value?.adp;
  const rank = p.value?.rank;
  if (adp == null || rank == null) return "fair";
  const delta = adp - rank; // positive → falls later than its rank → value
  if (delta >= 12) return "value";
  if (delta <= -12) return "reach";
  return "fair";
}

function toPlanPlayer(p: PlayerWithValue, tiers: Record<string, number>): PlanPlayer {
  return {
    id: p.id,
    name: p.full_name,
    position: norm(p.position),
    proj: proj(p),
    tier: tiers[p.id] ?? 1,
    flag: valueFlag(p),
  };
}

// Positions filling an open STARTING slot (flex/superflex eligibility included).
export function neededPositions(
  teamPicks: PlayerWithValue[],
  roster: RosterSlot[],
): Set<string> {
  const fill = fillRoster(teamPicks, roster);
  const s = new Set<string>();
  fill.starters.forEach((slot, i) => {
    if (!slot.player) roster[i]?.eligible.forEach((e) => s.add(norm(e)));
  });
  return s;
}

// Build the plan: for each of my upcoming picks, the top primaries at a needed
// position with a same-position contingency one tier down.
export function buildPlan(
  available: PlayerWithValue[],
  teamPicks: PlayerWithValue[],
  roster: RosterSlot[],
  numTeams: number,
  mySlot: number,
  currentPickNo: number,
  builtAtPickCount: number,
  { lookahead = 4, perRound = 3 }: { lookahead?: number; perRound?: number } = {},
): DraftPlan {
  const rounds = roster.length + 6; // starters + bench depth
  const tiers = tierMap(
    available.map((p) => ({ id: p.id, position: p.position, value: p.value?.value ?? proj(p) })),
  );
  const need = neededPositions(teamPicks, roster);
  const byProj = [...available].sort((a, b) => proj(b) - proj(a));

  const myUpcoming = myPickNumbers(numTeams, mySlot, rounds)
    .filter((n) => n >= currentPickNo)
    .slice(0, lookahead);

  const targets: RoundTarget[] = myUpcoming.map((pickNo) => {
    const round = Math.ceil(pickNo / numTeams);
    // Prefer needs; if every starter is filled, plan best-available depth.
    const pool = need.size
      ? byProj.filter((p) => need.has(norm(p.position)))
      : byProj;
    const primary = pool.slice(0, perRound).map((p) => toPlanPlayer(p, tiers));
    const primaryIds = new Set(primary.map((p) => p.id));
    const contingency = pool
      .filter((p) => !primaryIds.has(p.id))
      .slice(0, perRound)
      .map((p) => toPlanPlayer(p, tiers));
    return { round, pickNo, primary, contingency };
  });

  return { rounds: targets, builtAtPickCount };
}
