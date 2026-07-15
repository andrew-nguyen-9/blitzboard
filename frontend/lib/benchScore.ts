// Bench scoring engine (v4). Scores a bench/reserve player 0-100 for "how worth a
// roster spot is this body." Two spec formulas (see docs/design/v4-bench-scoring.md):
// a general model and a superflex overlay (QB/RB/WR/TE get per-position weights + a
// positional multiplier) that activates when the league is superflex/2QB. K/DST always
// use the general model (no superflex per-position formula exists for them).
//
// Pure: no DB calls. The caller passes a `ctx` carrying the roster, league config, and
// the E1 `player_trends` / E3 schedule signals. Every formula term maps to a real signal
// or a neutral fill; neutral-filled terms are listed in the returned `coverage` array so
// callers can show which inputs were degraded.

import type { PlayerWithValue } from "./types";
import { rulesFromConfig, type LeagueConfig } from "./leagueConfig";
import { proj } from "./draftAI";
import { playoffSchedule } from "./schedule2026";

// ── ctx / result shapes ────────────────────────────────────────────────────

// E1 player_trends row (subset the scorer reads). All 0..1 with 0.5 neutral, except
// routes_run (a season count) and target_share (a raw fraction).
export interface BenchTrends {
  opportunity_trend?: number | null;
  target_share_trend?: number | null;
  target_share?: number | null;
  routes_run?: number | null;
  routes_trend?: number | null;
  starting_prob?: number | null;
  job_security?: number | null;
}

export interface BenchCtx {
  /** The full roster (starters + bench) — needed for handcuff, duplicate, bye-cover logic. */
  roster: PlayerWithValue[];
  /** Superflex/2QB overlay. If omitted, derived from `config` (OP/SF slot present). */
  superflex?: boolean;
  config?: LeagueConfig;
  /** player_id → E1 trends. */
  trends?: Record<string, BenchTrends>;
  /** Optional per-team defensive ratings (0..1, lower = tougher) for E3 scheduleStrength. */
  defRatings?: Record<string, number>;
  /** Optional player_id → positional tier (1 = best) from tiers.ts. */
  tiers?: Record<string, number>;
}

export interface BenchResult {
  /** 0-100 bench value. */
  score: number;
  /** Formula terms that fell back to a neutral value (missing signal). */
  coverage: string[];
  /** Whether the superflex overlay was used for this player. */
  superflex: boolean;
  position: string;
}

// ── weight tables (positives sum to 100 per docs/design/v4-bench-scoring.md) ──

export const GENERAL_WEIGHTS = {
  Upside: 25,
  OpportunityTrend: 20,
  HandcuffValue: 15,
  PositionalScarcity: 15,
  PlayoffSchedule: 10,
  WeeklyFlexValue: 5,
  ByeCoverage: 5,
  ReplacementDifficulty: 5,
} as const;
export const GENERAL_PENALTIES = { DuplicatePositionPenalty: 10, DeadRosterSpotPenalty: 5 } as const;

export const SF_QB_WEIGHTS = { Opportunity: 40, StartingProb: 25, WeeklyProj: 15, JobSecurity: 10, Schedule: 10 } as const;
export const SF_RB_WEIGHTS = { Upside: 35, Opportunity: 25, Injury: 15, StartingProbability: 15, TradeValue: 10 } as const;
export const SF_WR_WEIGHTS = { TargetShare: 35, RouteParticipation: 25, Upside: 20, Schedule: 10, TradeValue: 10 } as const;

/** Superflex positional multipliers (docs §3). TE reuses the WR formula at ×1.00. */
export const SF_MULTIPLIER: Record<string, number> = { QB: 2.25, RB: 1.2, WR: 1.1, TE: 1.0 };

// ── helpers ─────────────────────────────────────────────────────────────────

const NEUTRAL = 0.5;
const clamp01 = (x: number) => (x < 0 ? 0 : x > 1 ? 1 : x);
const clamp100 = (x: number) => (x < 0 ? 0 : x > 100 ? 100 : x);
/** Saturating map [0,∞)→[0,1): x/(x+k). x=k → 0.5. */
const sat = (x: number, k: number) => (x <= 0 ? 0 : x / (x + k));
const normPos = (p: string | null | undefined) => (p === "DEF" ? "DST" : (p ?? "?"));

/** Probability the starter is lost, from injury_status (null/active = low baseline). */
function injuryRisk(status: string | null | undefined): number {
  const s = (status ?? "").toLowerCase();
  if (!s || s === "active" || s === "healthy") return 0.1;
  if (s.includes("question")) return 0.35;
  if (s.includes("doubt")) return 0.65;
  if (s.includes("out")) return 0.85;
  if (s.includes("ir") || s.includes("pup") || s.includes("reserve") || s.includes("suspend")) return 0.95;
  return 0.4;
}

/** Season-projection-based upside from the ceiling estimate. */
function upsideSignal(p: PlayerWithValue): { v: number; degraded: boolean } {
  const boom = p.value?.boom;
  if (boom == null) return { v: NEUTRAL, degraded: true };
  return { v: sat(boom, 150), degraded: false };
}

const FLEX_POS = new Set(["RB", "WR", "TE"]);
const DEFAULT_STARTERS: Record<string, number> = { QB: 1, RB: 2, WR: 2, TE: 1, K: 1, DST: 1 };

/** Same-position roster mates sorted best→worst by projection, and this player's depth index. */
function positionDepth(player: PlayerWithValue, roster: PlayerWithValue[]) {
  const pos = normPos(player.position);
  const same = roster.filter((r) => normPos(r.position) === pos).sort((a, b) => proj(b) - proj(a));
  const idx = same.findIndex((r) => r.id === player.id);
  return { pos, same, idx: idx < 0 ? same.length : idx };
}

// ── term collector ────────────────────────────────────────────────────────

class Terms {
  score = 0;
  coverage: string[] = [];
  /** Add a positive weighted term; `degraded` flags a neutral fill for `coverage`. */
  add(name: string, weight: number, v: number, degraded: boolean) {
    this.score += weight * clamp01(v);
    if (degraded) this.coverage.push(name);
  }
  /** Subtract a penalty term (never adds to coverage). */
  sub(weight: number, v: number) {
    this.score -= weight * clamp01(v);
  }
}

// ── general model ───────────────────────────────────────────────────────────

function generalScore(player: PlayerWithValue, ctx: BenchCtx, t: Terms): number {
  const pos = normPos(player.position);
  const trends = ctx.trends?.[player.id];
  const up = upsideSignal(player);

  t.add("Upside", GENERAL_WEIGHTS.Upside, up.v, up.degraded);

  const opp = trends?.opportunity_trend;
  t.add("OpportunityTrend", GENERAL_WEIGHTS.OpportunityTrend, opp ?? NEUTRAL, opp == null);

  const hc = handcuffValue(player, ctx, up.v);
  t.add("HandcuffValue", GENERAL_WEIGHTS.HandcuffValue, hc.v, hc.degraded);

  const scar = scarcity(player, ctx);
  t.add("PositionalScarcity", GENERAL_WEIGHTS.PositionalScarcity, scar.v, scar.degraded);

  const ps = playoffSchedule(player, ctx.defRatings);
  t.add("PlayoffSchedule", GENERAL_WEIGHTS.PlayoffSchedule, ps.strength, ps.covered === 0);

  // Weekly flex value: only RB/WR/TE can fill a FLEX — structurally 0 for QB/K/DST.
  const weekly = FLEX_POS.has(pos) ? sat(proj(player) / 17, 12) : 0;
  t.add("WeeklyFlexValue", GENERAL_WEIGHTS.WeeklyFlexValue, weekly, false);

  const bye = byeCoverage(player, ctx);
  t.add("ByeCoverage", GENERAL_WEIGHTS.ByeCoverage, bye.v, bye.degraded);

  const vor = player.value?.vor;
  t.add("ReplacementDifficulty", GENERAL_WEIGHTS.ReplacementDifficulty, vor == null ? NEUTRAL : sat(vor, 40), vor == null);

  t.sub(GENERAL_PENALTIES.DuplicatePositionPenalty, duplicatePenalty(player, ctx));
  t.sub(GENERAL_PENALTIES.DeadRosterSpotPenalty, deadRosterSpot(player, ctx));
  return clamp100(t.score);
}

/** Contingent value of a backup who inherits a role: starterRisk × standalone upside. */
function handcuffValue(player: PlayerWithValue, ctx: BenchCtx, upside: number): { v: number; degraded: boolean } {
  const { same, idx } = positionDepth(player, ctx.roster);
  if (idx <= 0) return { v: 0.2 * upside, degraded: false }; // this IS the starter — not a handcuff
  const starter = same[0];
  const risk = injuryRisk(starter.injury_status);
  return { v: clamp01(0.4 * upside + risk * upside * 1.5), degraded: false };
}

/** Positional scarcity from the player's tier (1 = scarcest/best). */
function scarcity(player: PlayerWithValue, ctx: BenchCtx): { v: number; degraded: boolean } {
  const tier = ctx.tiers?.[player.id];
  if (tier == null) return { v: NEUTRAL, degraded: true };
  return { v: clamp01(1 - (tier - 1) * 0.2), degraded: false };
}

/** 1 if the bench player's bye differs from the position starter's (covers it), 0.25 if stacked. */
function byeCoverage(player: PlayerWithValue, ctx: BenchCtx): { v: number; degraded: boolean } {
  const { same, idx } = positionDepth(player, ctx.roster);
  const mine = player.bye_week;
  if (mine == null) return { v: NEUTRAL, degraded: true };
  if (idx <= 0) return { v: 0.5, degraded: false }; // starter — no one to cover for
  const starterBye = same[0].bye_week;
  if (starterBye == null) return { v: NEUTRAL, degraded: true };
  return { v: mine === starterBye ? 0.25 : 1, degraded: false };
}

function startersAt(pos: string, ctx: BenchCtx): number {
  let n = DEFAULT_STARTERS[pos] ?? 1;
  if (pos === "QB" && (ctx.superflex ?? deriveSuperflex(ctx))) n += 1; // OP slot lets a 2nd QB start
  return n;
}

/** Grows as the player sits deeper past the starting slots at its position. */
function duplicatePenalty(player: PlayerWithValue, ctx: BenchCtx): number {
  const { pos, idx } = positionDepth(player, ctx.roster);
  return clamp01((idx + 1 - startersAt(pos, ctx)) / 3);
}

/** Backup K, backup DST, or a backup QB in a 1QB league = a wasted roster spot. */
function deadRosterSpot(player: PlayerWithValue, ctx: BenchCtx): number {
  const { pos, idx } = positionDepth(player, ctx.roster);
  if (idx <= 0) return 0; // the starter is never a dead spot
  if (pos === "K" || pos === "DST") return 1;
  if (pos === "QB" && !(ctx.superflex ?? deriveSuperflex(ctx))) return 1;
  return 0;
}

// ── superflex overlay ─────────────────────────────────────────────────────

function superflexScore(player: PlayerWithValue, ctx: BenchCtx, t: Terms): number {
  const pos = normPos(player.position);
  const trends = ctx.trends?.[player.id];
  const up = upsideSignal(player);
  const oppV = trends?.opportunity_trend;
  const ps = playoffSchedule(player, ctx.defRatings);
  const trade = player.value?.value;
  const tradeV = trade == null ? NEUTRAL : sat(trade, 50);

  if (pos === "QB") {
    t.add("Opportunity", SF_QB_WEIGHTS.Opportunity, oppV ?? NEUTRAL, oppV == null);
    const sp = trends?.starting_prob;
    t.add("StartingProb", SF_QB_WEIGHTS.StartingProb, sp ?? NEUTRAL, sp == null);
    t.add("WeeklyProj", SF_QB_WEIGHTS.WeeklyProj, sat(proj(player) / 17, 14), false);
    const js = trends?.job_security;
    t.add("JobSecurity", SF_QB_WEIGHTS.JobSecurity, js ?? NEUTRAL, js == null);
    t.add("Schedule", SF_QB_WEIGHTS.Schedule, ps.strength, ps.covered === 0);
  } else if (pos === "RB") {
    t.add("Upside", SF_RB_WEIGHTS.Upside, up.v, up.degraded);
    t.add("Opportunity", SF_RB_WEIGHTS.Opportunity, oppV ?? NEUTRAL, oppV == null);
    t.add("Injury", SF_RB_WEIGHTS.Injury, 1 - injuryRisk(player.injury_status), false);
    const sp = rbStartingProb(player);
    t.add("StartingProbability", SF_RB_WEIGHTS.StartingProbability, sp.v, sp.degraded);
    t.add("TradeValue", SF_RB_WEIGHTS.TradeValue, tradeV, trade == null);
  } else {
    // WR and TE share the pass-catcher formula (TE at ×1.00).
    const ts = targetShare(player, trends);
    t.add("TargetShare", SF_WR_WEIGHTS.TargetShare, ts.v, ts.degraded);
    const rp = routeParticipation(trends);
    t.add("RouteParticipation", SF_WR_WEIGHTS.RouteParticipation, rp.v, rp.degraded);
    t.add("Upside", SF_WR_WEIGHTS.Upside, up.v, up.degraded);
    t.add("Schedule", SF_WR_WEIGHTS.Schedule, ps.strength, ps.covered === 0);
    t.add("TradeValue", SF_WR_WEIGHTS.TradeValue, tradeV, trade == null);
  }
  return clamp100(t.score * (SF_MULTIPLIER[pos] ?? 1));
}

function rbStartingProb(player: PlayerWithValue): { v: number; degraded: boolean } {
  const order = player.metadata?.depth_chart_order;
  if (order == null) return { v: NEUTRAL, degraded: true };
  const v = order <= 1 ? 0.9 : order === 2 ? 0.55 : order === 3 ? 0.3 : 0.15;
  return { v, degraded: false };
}

function targetShare(player: PlayerWithValue, trends?: BenchTrends): { v: number; degraded: boolean } {
  const trend = trends?.target_share_trend;
  const base = trends?.target_share;
  const parts: number[] = [];
  if (trend != null) parts.push(trend);
  if (base != null) parts.push(clamp01(base / 0.28));
  if (parts.length === 0) return { v: NEUTRAL, degraded: true };
  return { v: parts.reduce((a, b) => a + b, 0) / parts.length, degraded: false };
}

function routeParticipation(trends?: BenchTrends): { v: number; degraded: boolean } {
  if (trends?.routes_trend != null) return { v: trends.routes_trend, degraded: false };
  if (trends?.routes_run != null) return { v: clamp01(trends.routes_run / 700), degraded: false };
  return { v: NEUTRAL, degraded: true };
}

// ── public API ──────────────────────────────────────────────────────────────

function deriveSuperflex(ctx: BenchCtx): boolean {
  if (ctx.superflex != null) return ctx.superflex;
  return ctx.config ? rulesFromConfig(ctx.config).superflex : false;
}

const SF_POS = new Set(["QB", "RB", "WR", "TE"]);

/** Score a single bench player 0-100 with per-term coverage. */
export function benchScore(player: PlayerWithValue, ctx: BenchCtx): BenchResult {
  const pos = normPos(player.position);
  const superflex = deriveSuperflex(ctx);
  const t = new Terms();
  const useSF = superflex && SF_POS.has(pos);
  const local = { ...ctx, superflex };
  const score = useSF ? superflexScore(player, local, t) : generalScore(player, local, t);
  return { score, coverage: t.coverage, superflex: useSF, position: pos };
}

export interface BenchHealth {
  /** Mean bench value 0-100. */
  score: number;
  /** Union of degraded terms across the bench. */
  coverage: string[];
  players: { id: string; score: number; coverage: string[] }[];
}

/** Aggregate bench strength = mean per-player bench score. */
export function benchHealth(bench: PlayerWithValue[], ctx: BenchCtx): BenchHealth {
  const players = bench.map((p) => {
    const r = benchScore(p, ctx);
    return { id: p.id, score: r.score, coverage: r.coverage };
  });
  const score = players.length ? players.reduce((a, p) => a + p.score, 0) / players.length : 0;
  const coverage = [...new Set(players.flatMap((p) => p.coverage))];
  return { score, coverage, players };
}

export interface DropRank {
  id: string;
  score: number;
  player: PlayerWithValue;
}

/** Rank bench players worst→best (lowest bench value = first to drop). */
export function dropPriority(bench: PlayerWithValue[], ctx: BenchCtx): DropRank[] {
  return bench
    .map((p) => ({ id: p.id, score: benchScore(p, ctx).score, player: p }))
    .sort((a, b) => a.score - b.score);
}
