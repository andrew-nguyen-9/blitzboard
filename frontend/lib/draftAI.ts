// Draft AI — a single scoring function used both to simulate rival teams and to
// reason about bench picks. The headline behaviour (#5) is that it *reads how the
// rest of the league is drafting*: it detects positional runs from recent picks,
// projects how many startable players at each position will survive until the
// team's next turn, and lets that pressure pull picks forward. Bench picks switch
// to an upside/thinness model and realistically defer K/DST to the final rounds.
import type { PlayerWithValue } from "./types";
import type { RosterSlot } from "./draft";
import { fillRoster, SUPERFLEX_ROSTER } from "./draft";
import type { MappedPick } from "./sleeperDraft";

const POS_GROUPS = ["QB", "RB", "WR", "TE", "K", "DST"] as const;
export function norm(pos: string | null | undefined): string {
  return pos === "DEF" ? "DST" : pos ?? "?";
}

export interface AIContext {
  pool: PlayerWithValue[]; // available players
  teamPicks: PlayerWithValue[]; // players this team already drafted
  roster: RosterSlot[];
  benchSize: number;
  allPicks: MappedPick[]; // every pick so far, all teams
  numTeams: number;
  picksUntilNext: number; // picks before this team is up again
  round: number;
  totalRounds: number;
  randomness?: number; // 0..1 jitter for human-like variance
  rng?: () => number;
}

export interface RunInfo {
  rate: Record<string, number>; // share of recent picks at each position (0..1)
  count: Record<string, number>; // raw recent picks at each position
  hot: string[]; // positions currently "running"
}

// Positional pace over the most recent ~1.5 rounds — the league's live tendency.
export function detectRuns(allPicks: MappedPick[], numTeams: number): RunInfo {
  const window = allPicks.slice(-Math.round(numTeams * 1.5));
  const count: Record<string, number> = {};
  for (const p of window) {
    const pos = norm(p.player.position);
    count[pos] = (count[pos] ?? 0) + 1;
  }
  const total = window.length || 1;
  const rate: Record<string, number> = {};
  for (const pos of POS_GROUPS) rate[pos] = (count[pos] ?? 0) / total;
  // a "run" = position taken at >1.6× its fair share of a window
  const fairShare = 1 / 4; // RB/WR/QB/TE compete for most early picks
  const hot = POS_GROUPS.filter((pos) => (rate[pos] ?? 0) > fairShare * 1.6 && (count[pos] ?? 0) >= 3);
  return { rate, count, hot };
}

// Count how many of a position the team already rosters.
function ownedByPos(teamPicks: PlayerWithValue[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const p of teamPicks) {
    const pos = norm(p.position);
    out[pos] = (out[pos] ?? 0) + 1;
  }
  return out;
}

// ── Additive draft policy (v2.4.2) ──────────────────────────────────────────
// Every term below resolves to projected fantasy points in the active league's
// scoring, so pick_score = max(marginalStarterValue, benchValue) − overfill is
// a meaningful sum. Coefficients live in DEFAULT_POLICY so v2.4.3 can tune/ablate.

export const STARTABLE_WEEKS = 17;

export interface PolicyParams {
  runDepletion: number;          // hot-position depletion multiplier in the replacement walk
  benchByeWeight: number;        // weight on bye-coverage starts
  benchInjuryWeight: number;     // weight on injury-cover starts
  benchCeilingWeight: number;    // weight on ceiling-week starts
  boomWeight: number;            // blend of boom vs mean in value-when-started (0..1)
  availabilityPrior: number;     // default health/role availability (~0.9)
  handcuffAmplify: number;       // injury-cover multiplier for a same-team handcuff
  injuryRate: Record<string, number>; // expected fraction of the season a starter at pos misses
  maxCeilingWeeks: number;       // cap on ceiling-week starts
  ceilingScale: number;          // scales boom-edge into ceiling weeks
  kdstCapRoundsFromEnd: number;  // K/DST become draftable only inside this many final rounds
  overfillDepth: Record<string, number>; // reasonable owned count per position before penalty
  overfillPenaltyPerExtra: number;        // points penalty per player past the depth cap
}

export const DEFAULT_POLICY: PolicyParams = {
  runDepletion: 1.6,
  benchByeWeight: 1,
  benchInjuryWeight: 1,
  benchCeilingWeight: 1,
  boomWeight: 0.5,
  availabilityPrior: 0.9,
  handcuffAmplify: 1.6,
  injuryRate: { QB: 0.08, RB: 0.18, WR: 0.12, TE: 0.12, K: 0.03, DST: 0.0 },
  maxCeilingWeeks: 4,
  ceilingScale: 6,
  kdstCapRoundsFromEnd: 2,
  overfillDepth: { QB: 3, RB: 5, WR: 5, TE: 2, K: 1, DST: 1 },
  overfillPenaltyPerExtra: 25,
};

// Season projection in league scoring — the common unit for every additive term.
export function proj(p: PlayerWithValue): number {
  return (p.value?.vor ?? 0) + (p.value?.replacement ?? 0);
}

// Points of the optimal starting lineup these players can field (reuses fillRoster).
export function optimalLineupPoints(
  players: PlayerWithValue[],
  roster: RosterSlot[] = SUPERFLEX_ROSTER,
): number {
  return fillRoster(players, roster).projectedPoints;
}

// A synthetic "replacement" body at a position with a given season projection.
function syntheticReplacement(pos: string, projPts: number): PlayerWithValue {
  return {
    id: "__rep__",
    full_name: "replacement",
    position: pos,
    nfl_team: null,
    bye_week: null,
    metadata: {},
    value: { player_id: "__rep__", engine: "vorp", value: projPts, vor: projPts, replacement: 0, boom: projPts, bust: projPts, adp: null, rank: null },
  } as PlayerWithValue;
}

// Projection of the player at `pos` you can realistically still get at your next turn:
// walk the pool down by the expected number gone, accelerated when the position is running.
export function expectedReplacementAtNextTurn(
  pos: string,
  pool: PlayerWithValue[],
  picksUntilNext: number,
  runs: RunInfo,
  params: PolicyParams,
): number {
  const atPos = pool
    .filter((p) => norm(p.position) === pos)
    .sort((a, b) => proj(b) - proj(a));
  if (atPos.length === 0) return 0;
  const share = runs.rate[pos] ?? 0;
  const accel = runs.hot.includes(pos) ? params.runDepletion : 1;
  const gone = Math.floor(share * accel * picksUntilNext);
  const idx = Math.min(atPos.length - 1, Math.max(0, gone));
  return proj(atPos[idx]);
}

// How much this pick raises my optimal lineup over the replacement I'd still get next turn.
export function marginalStarterValue(
  cand: PlayerWithValue,
  ctx: AIContext,
  params: PolicyParams = DEFAULT_POLICY,
): number {
  const base = optimalLineupPoints(ctx.teamPicks, ctx.roster);
  const candDelta = optimalLineupPoints([...ctx.teamPicks, cand], ctx.roster) - base;
  if (candDelta <= 0) return 0; // does not crack the starting lineup — Term B (bench) handles it
  const runs = detectRuns(ctx.allPicks, ctx.numTeams);
  // The replacement is the NEXT player you'd get, so exclude the candidate itself — otherwise a
  // position whose only body is the candidate would self-cancel to a 0 marginal (VONA).
  const others = ctx.pool.filter((p) => p.id !== cand.id);
  const repProj = expectedReplacementAtNextTurn(norm(cand.position), others, ctx.picksUntilNext, runs, params);
  const rep = syntheticReplacement(norm(cand.position), repProj);
  const repDelta = optimalLineupPoints([...ctx.teamPicks, rep], ctx.roster) - base;
  return Math.max(0, candDelta - repDelta);
}

// Distinct same-position starter byes this candidate could fill — one start each.
export function byeCover(cand: PlayerWithValue, starters: PlayerWithValue[]): number {
  const pos = norm(cand.position);
  const byes = new Set(
    starters.filter((s) => s && norm(s.position) === pos && s.bye_week != null).map((s) => s.bye_week),
  );
  return byes.size;
}

// Expected games filling in for an injured starter; amplified for a same-team handcuff,
// which starts precisely when its starter is out (negative availability correlation).
export function injuryCover(
  cand: PlayerWithValue,
  coveredStarter: PlayerWithValue | null,
  isHandcuff: boolean,
  params: PolicyParams,
): number {
  if (!coveredStarter) return 0;
  const pos = norm(cand.position);
  const games = (params.injuryRate[pos] ?? 0.1) * STARTABLE_WEEKS;
  return isHandcuff ? games * params.handcuffAmplify : games;
}

// Weeks the candidate's ceiling outscores a weak marginal starter — the upside term.
export function ceilingWeeks(
  cand: PlayerWithValue,
  marginalStarterProj: number,
  params: PolicyParams,
): number {
  const boom = cand.value?.boom ?? proj(cand);
  const edge = boom - marginalStarterProj;
  if (edge <= 0) return 0;
  return Math.min(params.maxCeilingWeeks, (edge / (Math.abs(marginalStarterProj) + 1)) * params.ceilingScale);
}

// Health/role availability prior, discounted for a deeply buried depth-chart role.
export function availability(cand: PlayerWithValue, params: PolicyParams): number {
  const order = cand.metadata?.depth_chart_order ?? 1;
  return order >= 3 ? params.availabilityPrior * 0.9 : params.availabilityPrior;
}

// Bench worth = expected starts × per-game value when started × availability (season points).
export function benchValue(
  cand: PlayerWithValue,
  ctx: AIContext,
  params: PolicyParams = DEFAULT_POLICY,
): number {
  const fill = fillRoster(ctx.teamPicks, ctx.roster);
  const starters = fill.starters.map((s) => s.player).filter((p): p is PlayerWithValue => !!p);
  const pos = norm(cand.position);

  const samePos = ctx.teamPicks.filter((p) => norm(p.position) === pos).sort((a, b) => proj(b) - proj(a));
  const coveredStarter = samePos[0] ?? null;
  const isHandcuff = !!cand.nfl_team && coveredStarter?.nfl_team === cand.nfl_team;
  // weakest same-eligible starter is the bar the candidate's ceiling must clear
  const marginalStarter = starters
    .filter((s) => norm(s.position) === pos)
    .sort((a, b) => proj(a) - proj(b))[0];
  const marginalStarterProj = marginalStarter ? proj(marginalStarter) : 0;

  const eStarts =
    params.benchByeWeight * byeCover(cand, starters) +
    params.benchInjuryWeight * injuryCover(cand, coveredStarter, isHandcuff, params) +
    params.benchCeilingWeight * ceilingWeeks(cand, marginalStarterProj, params);

  const mean = proj(cand);
  const boom = cand.value?.boom ?? mean;
  const valuePerGame = ((1 - params.boomWeight) * mean + params.boomWeight * boom) / STARTABLE_WEEKS;

  return eStarts * valuePerGame * availability(cand, params);
}

export interface ScoredPick {
  player: PlayerWithValue;
  score: number;
  reason: string;
}

// Hard K/DST cap: a 2nd kicker/defense is ineligible until the final rounds.
export function isCapped(
  cand: PlayerWithValue,
  owned: Record<string, number>,
  lateDraft: boolean,
): boolean {
  const pos = norm(cand.position);
  if (pos !== "K" && pos !== "DST") return false;
  return (owned[pos] ?? 0) >= 1 && !lateDraft;
}

// Diminishing returns once a position is past its reasonable depth.
export function overfillPenalty(
  cand: PlayerWithValue,
  ctx: AIContext,
  params: PolicyParams,
): number {
  const pos = norm(cand.position);
  const owned = ctx.teamPicks.filter((p) => norm(p.position) === pos).length;
  const cap = params.overfillDepth[pos] ?? 4;
  const over = Math.max(0, owned + 1 - cap);
  return over * params.overfillPenaltyPerExtra;
}

// Additive policy: pick_score = max(starter-marginal, bench) − overfill, hard K/DST gate.
export function scoreBoard(ctx: AIContext, params: PolicyParams = DEFAULT_POLICY): ScoredPick[] {
  const rng = ctx.rng ?? Math.random;
  const jitter = ctx.randomness ?? 0;
  const lateDraft = ctx.round > ctx.totalRounds - params.kdstCapRoundsFromEnd;
  const owned = ownedByPos(ctx.teamPicks);

  const scored = ctx.pool.map((p) => {
    const capped = isCapped(p, owned, lateDraft);
    const marg = marginalStarterValue(p, ctx, params);
    const bench = benchValue(p, ctx, params);
    const why: string[] = [];
    let score: number;
    if (marg >= bench) {
      score = marg;
      if (marg > 0) why.push("raises starters");
    } else {
      score = bench;
      why.push("bench upside");
    }
    score -= overfillPenalty(p, ctx, params);
    if (capped) {
      score -= 1e6; // demote below every legal pick without dropping it from the board
      why.push("K/DST capped");
    }
    if (jitter > 0) score *= 1 + (rng() - 0.5) * jitter;
    return { player: p, score, reason: why.join(" · ") || "best available" };
  });

  scored.sort((a, b) => b.score - a.score);
  return scored;
}

// The single best pick for a team in the given context.
export function pickForTeam(ctx: AIContext): PlayerWithValue | null {
  const ranked = scoreBoard(ctx);
  return ranked[0]?.player ?? null;
}
