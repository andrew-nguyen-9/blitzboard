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
}

// snapshot-field column: pull a field off the decoded row, null-safe.
const field = (
  key: string, label: string, group: ColGroup,
  pick: (p: SnapshotPlayer) => number | string | null, decimals?: number,
): ColDef => ({ key, label, group, sortable: true, decimals, get: (p) => pick(p) ?? null });

// box-score column: pull a key off ctx.box; null when the row's box isn't loaded.
const box = (key: string, label: string, decimals = 0): ColDef =>
  ({ key, label, group: "box", sortable: true, decimals, get: (_p, ctx) => ctx.box?.[key] ?? null });

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
  field("pos", "Pos", "meta", (p) => p.position),
  field("team", "Team", "meta", (p) => p.nfl_team),
  field("bye", "Bye", "meta", (p) => p.bye),
];
