// FAAB bid recommendations (v2.6.2.2). A bid is a fraction of the manager's REMAINING budget,
// scaled by how much the league wants the player (trend), how much this roster needs the
// position (need), and how scarce startable options are. Pure + framework-free so the bid math
// is unit-tested; the authed Waivers tab feeds it the active league's budget + trending.
export interface BidInput {
  remainingBudget: number; // dollars left in the season's FAAB
  trend: number; // 0..1 league-wide add demand (news ⊕ add/drop)
  need: number; // 0..1 how badly this roster needs the position
  scarcity?: number; // 0..1 positional scarcity (few startable left)
}

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}

// Recommended FAAB bid in whole dollars. Aggression blends trend/need/scarcity, then maps to
// 5%–55% of the remaining budget. Always ≥ $1 when there's budget (you can't win at $0), and
// never exceeds the remaining budget.
export function faabBid(input: BidInput): number {
  if (input.remainingBudget <= 0) return 0;
  const aggression = clamp01(0.5 * clamp01(input.trend) + 0.35 * clamp01(input.need) + 0.15 * clamp01(input.scarcity ?? 0.5));
  const pct = 0.05 + aggression * 0.5; // 5%..55% of remaining budget
  const bid = Math.round(input.remainingBudget * pct);
  return Math.max(1, Math.min(input.remainingBudget, bid));
}

// A conservative/aggressive range around the recommendation, for the UI to show a band.
export function faabBidRange(input: BidInput): { low: number; rec: number; high: number } {
  const rec = faabBid(input);
  const low = Math.max(1, Math.round(rec * 0.6));
  const high = Math.min(input.remainingBudget, Math.round(rec * 1.4));
  return { low, rec, high };
}
