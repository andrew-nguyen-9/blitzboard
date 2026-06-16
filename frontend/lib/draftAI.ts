// Draft AI — a single scoring function used both to simulate rival teams and to
// reason about bench picks. The headline behaviour (#5) is that it *reads how the
// rest of the league is drafting*: it detects positional runs from recent picks,
// projects how many startable players at each position will survive until the
// team's next turn, and lets that pressure pull picks forward. Bench picks switch
// to an upside/thinness model and realistically defer K/DST to the final rounds.
import type { PlayerWithValue } from "./types";
import type { RosterSlot } from "./draft";
import { fillRoster } from "./draft";
import type { MappedPick } from "./sleeperDraft";

const POS_GROUPS = ["QB", "RB", "WR", "TE", "K", "DST"] as const;
function norm(pos: string | null | undefined): string {
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

// How "needed" each position is given the team's open starting slots. A dedicated
// open slot weighs a full point; a flex slot splits its weight across eligibles.
function positionDemand(teamPicks: PlayerWithValue[], roster: RosterSlot[]): Record<string, number> {
  const fill = fillRoster(teamPicks, roster);
  const demand: Record<string, number> = {};
  fill.starters.forEach((s, i) => {
    if (s.player) return; // slot already filled
    const elig = roster[i].eligible.map(norm);
    const w = 1 / elig.length;
    for (const pos of elig) demand[pos] = (demand[pos] ?? 0) + w;
  });
  return demand;
}

// Startable players (vor > 0) left at each position in the pool.
function startableLeft(pool: PlayerWithValue[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const p of pool) if ((p.value?.vor ?? 0) > 0) {
    const pos = norm(p.position);
    out[pos] = (out[pos] ?? 0) + 1;
  }
  return out;
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

export interface ScoredPick {
  player: PlayerWithValue;
  score: number;
  reason: string;
}

// Score every available player for a team and return them ranked.
export function scoreBoard(ctx: AIContext): ScoredPick[] {
  const { pool, teamPicks, roster, allPicks, numTeams, picksUntilNext, round, totalRounds } = ctx;
  const rng = ctx.rng ?? Math.random;
  const jitter = ctx.randomness ?? 0;

  const demand = positionDemand(teamPicks, roster);
  const runs = detectRuns(allPicks, numTeams);
  const left = startableLeft(pool);
  const owned = ownedByPos(teamPicks);
  const currentPickNo = allPicks.length + 1;
  const hasOpenStarters = Object.keys(demand).length > 0;
  const lateDraft = round > totalRounds - 2;

  const scored = pool.map((p) => {
    const pos = norm(p.position);
    const base = p.value?.vor ?? p.value?.value ?? 0;
    let score = base;
    const why: string[] = [];

    const dem = demand[pos] ?? 0;
    if (dem > 0) {
      // fills an open starting slot — the core driver
      score *= 1 + dem * 0.7;
      why.push("fills need");

      // bye-week stacking: discourage piling starters onto an already-heavy bye
      if (p.bye_week) {
        const stack = teamPicks.filter((t) => t.bye_week === p.bye_week).length;
        if (stack >= 2) { score *= 1 - Math.min(0.14, (stack - 1) * 0.05); why.push("bye stack"); }
      }

      // run pressure: if this position is running, the tier won't survive until
      // our next pick → pull it forward. Scaled by how thin it already is.
      const expectedGone = (runs.rate[pos] ?? 0) * picksUntilNext;
      const survive = (left[pos] ?? 0) - expectedGone;
      if (runs.hot.includes(pos)) {
        score *= 1.18;
        why.push("positional run");
      }
      if (survive < 2) {
        score *= 1.22;
        why.push("won't survive");
      }
    } else {
      // BENCH / depth pick — no open starting slot for this position.
      // Defer kickers & defenses to the last two rounds like real drafters do.
      if ((pos === "K" || pos === "DST") && !lateDraft) {
        score *= 0.05;
        why.push("too early for K/DST");
      } else {
        // upside + thinness model: back up the spots we're thin at, chase boom.
        const depth = owned[pos] ?? 0;
        const thinness = depth <= 1 ? 1.15 : depth === 2 ? 1.0 : 0.85;
        const boom = p.value?.boom ?? base;
        const upside = base > 0 ? 1 + Math.max(0, (boom - base) / (Math.abs(base) + 1)) * 0.3 : 1;

        // a high-quality bench is built for contingency & future value:
        const ownedAtPos = teamPicks.filter((t) => norm(t.position) === pos && t.id !== p.id);
        const starter = ownedAtPos.sort((a, b) => (b.value?.vor ?? 0) - (a.value?.vor ?? 0))[0];
        const depthOrder = p.metadata?.depth_chart_order ?? null;
        const isBackup = depthOrder != null && depthOrder >= 2; // confirmed reserve
        const consensus = p.metadata?.search_rank ?? 999;       // lower = better

        // HANDCUFF: backs up a starter you own (same team+pos). A depth-chart-confirmed
        // direct backup is the cleanest insurance → stronger bonus.
        let handcuff = 1;
        if (starter && starter.nfl_team === p.nfl_team) {
          handcuff = isBackup ? 1.55 : 1.35;
          why.push("handcuff");
        }
        // BURIED UPSIDE: talented (good consensus) but stuck behind someone — one
        // injury from a role anywhere in the league. The "injury-contingent" stash.
        const buriedUpside = isBackup && consensus < 200 ? 1.18 : 1;
        if (buriedUpside > 1) why.push("upside stash");
        // CONTINGENT: high ceiling relative to floor — boom equity.
        const contingent = (p.value?.boom ?? 0) > base * 1.6 ? 1.12 : 1;
        // BYE COVERAGE: a bench piece that covers your starter's bye is worth more.
        let byeFactor = 1;
        if (p.bye_week && starter?.bye_week) byeFactor = p.bye_week !== starter.bye_week ? 1.08 : 0.94;

        score *= 0.6 * thinness * upside * handcuff * buriedUpside * contingent * byeFactor;
        why.push("bench depth");
      }
    }

    // ADP realism: rarely reach more than a round ahead of a player's ADP.
    const adp = p.value?.adp;
    if (adp != null && adp > 0) {
      const reach = adp - currentPickNo; // positive = drafting earlier than ADP
      if (reach > numTeams) {
        score *= 1 - Math.min(0.45, (reach - numTeams) / (numTeams * 4));
      } else if (reach < -numTeams * 1.5) {
        score *= 1.08; // falling past ADP — slight value bump
        why.push("falling value");
      }
    }

    if (jitter > 0) score *= 1 + (rng() - 0.5) * jitter;

    return { player: p, score, reason: why.join(" · ") || "best available" };
  });

  scored.sort((a, b) => b.score - a.score);
  // Safety: if every startable slot is full and pool is bench-only, still return
  // the best-scored option rather than nothing.
  void hasOpenStarters;
  return scored;
}

// The single best pick for a team in the given context.
export function pickForTeam(ctx: AIContext): PlayerWithValue | null {
  const ranked = scoreBoard(ctx);
  return ranked[0]?.player ?? null;
}
