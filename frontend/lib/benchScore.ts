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
import type { LeagueConfig } from "./leagueConfig";
import { proj } from "./draftAI";
import { playoffSchedule } from "./schedule2026";
import { contingentValuation, injuryRisk, weeklyByeCoverage } from "./contingency";
import { SUPERFLEX_ROSTER, fillRoster, type RosterSlot } from "./draft";

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
  /** The league's actual starting-lineup slots. If omitted, read from `config.rosterSlots`;
   * the hard-coded superflex preset is only the last-resort default for flag-only callers. */
  rosterSlots?: RosterSlot[];
  /** Superflex/2QB overlay. If omitted, derived from the league slots (≥2 QB-capable slots). */
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
// e10 — `TradeValue` is PINNED at 10, deliberately NOT fitted. e5's season simulator trades
// nothing (trades are one of its documented omissions), so TradeValue has ZERO GRADIENT under
// `started_points` and no amount of search can adjudicate it. Measured both ways to prove it:
// ablating both TradeValue terms to 0 scored +5.3 pts "helps" (p=0.021) on the 2024 fit slice and
// −1.1 "neutral" (p=0.403) on the held-out 2021 slice — sign-flipping noise, exactly the
// signature of a zero-gradient knob. It therefore did NOT clear block-release and was NOT changed.
// Any future fit must PIN or ABLATE this term, never free-fit it. Receipts:
// engine/experiments/static/{results,holdout-2021}.json (exp e10-trade_value_zero).
export const SF_RB_WEIGHTS = { Upside: 35, Opportunity: 25, Injury: 15, StartingProbability: 15, TradeValue: 10 } as const;
export const SF_WR_WEIGHTS = { TargetShare: 35, RouteParticipation: 25, Upside: 20, Schedule: 10, TradeValue: 10 } as const;

/** Superflex positional multipliers (docs §3). TE reuses the WR formula at ×1.00. */
// e10 — UNCHANGED, and the reason is a negative result, not an oversight. e6 derived that
// superflex DRAINS RB bench depth (mean derived ceiling 3.75 → 2.50), so a 1.2 RB *boost* is
// backwards on paper; the corrected value 0.67 (= 2.50/3.75) was gated against e5's metric over
// the real policy and came back **neutral** (+1.2 pts, p=0.545) — the metric cannot tell the two
// apart, so under block-release the unproven correction does not ship. WR's 1.1 is left alone:
// e6 confirmed its sign (WR ceiling 1.50 → 2.25 in superflex). Receipt: exp e10-sf_multiplier_rb.
export const SF_MULTIPLIER: Record<string, number> = { QB: 2.25, RB: 1.2, WR: 1.1, TE: 1.0 };

// ── helpers ─────────────────────────────────────────────────────────────────

const NEUTRAL = 0.5;
const clamp01 = (x: number) => (x < 0 ? 0 : x > 1 ? 1 : x);
const clamp100 = (x: number) => (x < 0 ? 0 : x > 100 ? 100 : x);
/** Saturating map [0,∞)→[0,1): x/(x+k). x=k → 0.5. */
const sat = (x: number, k: number) => (x <= 0 ? 0 : x / (x + k));
const normPos = (p: string | null | undefined) => (p === "DEF" ? "DST" : (p ?? "?"));

/** Upside from CEILING VOR (value.boom = projection ceiling − replacement — the C01 unit
 * contract; it is NOT a raw season ceiling). Points-over-replacement is the right scale for
 * "worth a bench spot", and it is never compared against a raw projection here. */
function upsideSignal(p: PlayerWithValue): { v: number; degraded: boolean } {
  const ceilVor = p.value?.boom;
  if (ceilVor == null) return { v: NEUTRAL, degraded: true };
  return { v: sat(ceilVor, 150), degraded: false };
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

/** Contingent value of a backup who inherits a role, from the SHARED valuation
 * (contingency.ts): whether (eligibility) and probability come from it exclusively; this
 * model only rescales the shared expectedValue (= inheritanceProb × raw projection) onto
 * its saturating VOR upside scale — inheritanceProb × upside — with the v5 coefficients
 * (0.4, 1.5) unchanged. Missing/ambiguous evidence is a degraded term, never value. */
function handcuffValue(player: PlayerWithValue, ctx: BenchCtx, upside: number): { v: number; degraded: boolean } {
  const { same, idx } = positionDepth(player, ctx.roster);
  if (idx <= 0) return { v: 0.2 * upside, degraded: false }; // this IS the starter — not a handcuff
  const val = contingentValuation(player, same[0]);
  if (!val.eligible) return { v: 0, degraded: val.degradedReason != null };
  return { v: clamp01(0.4 * upside + val.inheritanceProb * upside * 1.5), degraded: false };
}

/** Positional scarcity from the player's tier (1 = scarcest/best). */
function scarcity(player: PlayerWithValue, ctx: BenchCtx): { v: number; degraded: boolean } {
  const tier = ctx.tiers?.[player.id];
  if (tier == null) return { v: NEUTRAL, degraded: true };
  return { v: clamp01(1 - (tier - 1) * 0.2), degraded: false };
}

/** The league's actual starting slots, when the caller provided them. */
function leagueSlots(ctx: BenchCtx): RosterSlot[] | null {
  return ctx.rosterSlots ?? ctx.config?.rosterSlots ?? null;
}

/** The starting template this league implies: the REAL slots when available (custom
 * shapes, 2QB, missing slots all honored — the same template both consumers pass to
 * weeklyByeCoverage); the superflex preset only for flag-only callers. */
export function starterTemplate(ctx: BenchCtx): RosterSlot[] {
  const slots = leagueSlots(ctx);
  if (slots && slots.length > 0) return slots;
  const sf = ctx.superflex ?? deriveSuperflex(ctx);
  return sf ? SUPERFLEX_ROSTER : SUPERFLEX_ROSTER.filter((s) => s.slot !== "OP");
}

/** Candidate-aware weekly bye coverage via the consolidated implementation (contingency.ts):
 * 1 when the candidate can legally fill ≥1 starter-bye hole it is not itself absent for,
 * 0 otherwise (a shared bye earns nothing), neutral+degraded when byes are unknown. */
function byeCoverage(player: PlayerWithValue, ctx: BenchCtx): { v: number; degraded: boolean } {
  if (player.bye_week == null) return { v: NEUTRAL, degraded: true }; // unknowable availability
  const { idx } = positionDepth(player, ctx.roster);
  if (idx <= 0) return { v: 0.5, degraded: false }; // starter — no one to cover for
  const template = starterTemplate(ctx);
  const fill = fillRoster(ctx.roster, template);
  const starterIds = new Set(fill.starters.flatMap((s) => (s.player ? [s.player.id] : [])));
  const ownedBench = ctx.roster.filter((p) => !starterIds.has(p.id));
  const cov = weeklyByeCoverage(player, fill.starters, template, ownedBench);
  if (cov.degraded && cov.expectedStarts === 0) return { v: NEUTRAL, degraded: true };
  return { v: cov.expectedStarts > 0 ? 1 : 0, degraded: cov.degraded };
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
  const slots = leagueSlots(ctx);
  if (!slots) return false;
  // An explicitly named OP/SF slot, or any shape with ≥2 QB-capable slots (pure 2QB included).
  return slots.some((s) => s.slot === "OP" || s.slot === "SF") ||
    slots.filter((s) => s.eligible.includes("QB")).length >= 2;
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
