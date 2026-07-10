// Shared, data-only column contract over the decoded snapshot row, consumed by
// BOTH the Players table (e3) and the TradeCalc table (e5) so the two can't
// diverge. Pure + null-safe + no JSX → testable in the node env. Display ("—"
// for null, decimals) is the consumer's job; accessors return raw values so they
// stay sortable.
import type { SnapshotPlayer } from "./snapshot";

// One player-season's box-score, as flattened by lib/playerStats.ts (careerRows
// turns player_stats_history jsonb into this flat number record). The consumer
// fetches it per visible row and passes it in ctx.box; null when not loaded.
export type BoxStats = Record<string, number | null>;

export type ColGroup = "proj" | "rank" | "box" | "meta";

export interface ColCtx {
  tier?: number;
  box?: BoxStats | null;
}

export interface ColDef {
  key: string;
  label: string;
  group: ColGroup;
  get: (p: SnapshotPlayer, ctx: ColCtx) => number | string | null;
  sortable?: boolean;
  decimals?: number;
  /** appended to numeric cells (e.g. "%"); rendered by the consuming cell. */
  suffix?: string;
}

// snapshot-field column: pull a field off the decoded row, null-safe.
const field = (
  key: string, label: string, group: ColGroup,
  pick: (p: SnapshotPlayer) => number | string | null, decimals?: number,
): ColDef => ({ key, label, group, sortable: true, decimals, get: (p) => pick(p) ?? null });

// box-score column: pull a key off ctx.box; null when the row's box isn't loaded.
const box = (key: string, label: string, decimals = 0): ColDef =>
  ({ key, label, group: "box", sortable: true, decimals, get: (_p, ctx) => ctx.box?.[key] ?? null });

// ── Advanced per-player rate metrics (E2) ───────────────────────────────────
// E2's advancedMetrics(history) in lib/playerStats.ts computes these over a full
// career; the Explorer lazily loads only the latest-season box (lib/queries.
// groupLatestBox), so here they are latest-season rates using the SAME formulas +
// definitions (playerStats.ts §Advanced metrics + docs/research/ANALYTICS_SURVEY.md).
// Null when the denominator is absent, so a QB and a WR each surface only what
// applies. Header tooltips/definitions live in lib/playerTooltip.ts `columnTips`.
const bn = (b: BoxStats, k: string): number => {
  const v = b[k];
  return typeof v === "number" && Number.isFinite(v) ? v : 0;
};
const rate = (numer: number, denom: number): number | null => (denom > 0 ? numer / denom : null);

// derived box metric: computed from the loaded box row; null when box unloaded.
const metric = (
  key: string, label: string, decimals: number,
  calc: (b: BoxStats) => number | null, suffix?: string,
): ColDef => ({
  key, label, group: "box", sortable: true, decimals, suffix,
  get: (_p, ctx) => (ctx.box ? calc(ctx.box) : null),
});

export const PLAYER_COLUMNS: ColDef[] = [
  field("value", "Value", "proj", (p) => p.value, 1),
  field("vor", "VOR", "proj", (p) => p.vor, 1),
  field("boom", "Boom", "proj", (p) => p.boom, 1),
  field("bust", "Bust", "proj", (p) => p.bust, 1),
  field("rank", "Rank", "rank", (p) => p.rank),
  field("adp", "ADP", "rank", (p) => p.adp, 1),
  { key: "tier", label: "Tier", group: "rank", sortable: true, get: (_p, ctx) => ctx.tier ?? null },
  // ponytail: position-agnostic box core; a consumer can subset by position.
  box("pass_yds", "Pass Yds"),
  box("rush_yds", "Rush Yds"),
  box("rec", "Rec"),
  box("rec_yds", "Rec Yds"),
  box("fantasy_pts", "Pts", 1),
  // E2 advanced rate metrics (latest-season) — position-aware via null denominators.
  metric("scrim_ypg", "Scrim Y/G", 1, (b) => rate(bn(b, "rush_yds") + bn(b, "rec_yds"), bn(b, "games"))),
  metric("ypc", "YPC", 1, (b) => rate(bn(b, "rush_yds"), bn(b, "carries"))),
  metric("ypr", "YPR", 1, (b) => rate(bn(b, "rec_yds"), bn(b, "rec"))),
  metric("ypt", "YPT", 1, (b) => rate(bn(b, "rec_yds"), bn(b, "tgt"))),
  metric("catch_pct", "Catch %", 0, (b) => rate(bn(b, "rec") * 100, bn(b, "tgt")), "%"),
  metric("td_per_opp", "TD/Opp", 1, (b) => rate((bn(b, "rush_td") + bn(b, "rec_td")) * 100, bn(b, "carries") + bn(b, "tgt")), "%"),
  metric("pass_ypg", "Pass Y/G", 1, (b) => (bn(b, "pass_yds") > 0 ? rate(bn(b, "pass_yds"), bn(b, "games")) : null)),
  metric("td_int", "TD:INT", 1, (b) => (bn(b, "pass_yds") > 0 ? rate(bn(b, "pass_td"), bn(b, "int")) : null)),
  field("pos", "Pos", "meta", (p) => p.position),
  field("team", "Team", "meta", (p) => p.nfl_team),
  field("bye", "Bye", "meta", (p) => p.bye),
];
