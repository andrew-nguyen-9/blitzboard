// Pure, null-safe career-production helpers for the player detail page. The
// pipeline already stores a rich per-season `stats` jsonb in player_stats_history
// (passing/rushing/receiving yards, TDs, attempts, receptions, target share,
// games…) that the page previously dropped on the floor in favour of just
// fantasy_pts. This turns that blob into a position-aware StatTable + a small
// career summary. No DOM, no React — testable in the node env (playerStats.test.ts).
import type { StatColumn } from "@/components/StatTable";
import type { StatFormat } from "@/lib/viz";
import type { Player } from "@/lib/types";

// One season's aggregate row as read from player_stats_history (week IS NULL).
export interface SeasonRow {
  season: number;
  fantasy_pts: number | null;
  stats: Record<string, number | null> | null;
}

const num = (s: SeasonRow["stats"], k: string): number | null => {
  const v = s?.[k];
  return typeof v === "number" && Number.isFinite(v) ? v : null;
};

// Position-aware box-score columns. K/DEF have no meaningful split, so they fall
// through to the shared games/pts/ppg trio (POS_COLS lookup misses → []).
const POS_COLS: Record<string, StatColumn[]> = {
  QB: [
    { key: "pass_yds", label: "Pass Yds", numeric: true },
    { key: "pass_td", label: "Pass TD", numeric: true },
    { key: "int", label: "INT", numeric: true },
    { key: "rush_yds", label: "Rush Yds", numeric: true },
    { key: "rush_td", label: "Rush TD", numeric: true },
  ],
  RB: [
    { key: "carries", label: "Car", numeric: true },
    { key: "rush_yds", label: "Rush Yds", numeric: true },
    { key: "rush_td", label: "Rush TD", numeric: true },
    { key: "rec", label: "Rec", numeric: true },
    { key: "rec_yds", label: "Rec Yds", numeric: true },
  ],
  WR: [
    { key: "tgt", label: "Tgt", numeric: true },
    { key: "rec", label: "Rec", numeric: true },
    { key: "rec_yds", label: "Rec Yds", numeric: true },
    { key: "rec_td", label: "Rec TD", numeric: true },
    { key: "tgt_share", label: "Tgt%", numeric: true, decimals: 0, suffix: "%" },
  ],
};
POS_COLS.TE = POS_COLS.WR;

// Full column set: Season (text row-header, so a year never renders as "2,026")
// → Games → position split → Pts → PPG.
export function careerColumns(position: string | null | undefined): StatColumn[] {
  const pos = POS_COLS[position ?? ""] ?? [];
  return [
    { key: "season", label: "Season", numeric: false },
    { key: "games", label: "G", numeric: true },
    ...pos,
    { key: "fantasy_pts", label: "Pts", numeric: true, decimals: 1 },
    { key: "ppg", label: "PPG", numeric: true, decimals: 1 },
  ];
}

export interface CareerRow {
  season: number;
  games: number | null;
  fantasy_pts: number | null;
  ppg: number | null;
  [stat: string]: number | null;
}

// Flatten each season's jsonb into the flat record StatTable renders. PPG is
// derived (pts/games) and target_share is scaled to a percentage for display.
export function careerRows(history: SeasonRow[]): CareerRow[] {
  return history.map((h) => {
    const s = h.stats;
    const games = num(s, "games");
    const share = num(s, "target_share");
    return {
      season: h.season,
      games,
      fantasy_pts: h.fantasy_pts,
      ppg: games && games > 0 && h.fantasy_pts != null ? h.fantasy_pts / games : null,
      pass_yds: num(s, "passing_yards"),
      pass_td: num(s, "passing_tds"),
      int: num(s, "interceptions"),
      rush_yds: num(s, "rushing_yards"),
      rush_td: num(s, "rushing_tds"),
      carries: num(s, "carries"),
      rec: num(s, "receptions"),
      rec_yds: num(s, "receiving_yards"),
      rec_td: num(s, "receiving_tds"),
      tgt: num(s, "targets"),
      tgt_share: share == null ? null : share * 100,
    };
  });
}

export interface CareerSummary {
  seasons: number;
  bestPts: number | null;
  careerPpg: number | null;
  // Last season's fantasy_pts minus the prior season's (the YoY arrow).
  yoyDelta: number | null;
}

// Career-high, career PPG (total pts / total games), and the most recent
// year-over-year delta. History is assumed season-ascending (queries.ts orders it).
export function careerSummary(history: SeasonRow[]): CareerSummary {
  const pts = history.map((h) => h.fantasy_pts).filter((p): p is number => p != null);
  const totalGames = history.reduce((a, h) => a + (num(h.stats, "games") ?? 0), 0);
  const totalPts = pts.reduce((a, p) => a + p, 0);
  const n = history.length;
  return {
    seasons: n,
    bestPts: pts.length ? Math.max(...pts) : null,
    careerPpg: totalGames > 0 ? totalPts / totalGames : null,
    yoyDelta:
      n >= 2 && history[n - 1].fantasy_pts != null && history[n - 2].fantasy_pts != null
        ? (history[n - 1].fantasy_pts as number) - (history[n - 2].fantasy_pts as number)
        : null,
  };
}

// ── Advanced per-player metrics (E2) ────────────────────────────────────────
// Career-aggregate efficiency/usage metrics derived from the same per-season
// `stats` jsonb the box score already loads — no new DB read. Each metric is a
// standard football-analytics rate (see docs/research/ANALYTICS_SURVEY.md for the
// definition and why it is/ isn't the full pro version given free data). Metrics
// with no denominator (e.g. YPT for a player with 0 targets) return null and are
// dropped by `advancedMetrics`, so a QB and a WR each surface only what applies.

export interface PlayerMetric {
  key: string;
  label: string;
  value: number | null;
  format: StatFormat; // decimals / suffix for the shared StatCell renderer
  tip: string; // one-line definition (assistive-tech + tooltip)
}

// Sum a jsonb key across every season (missing → 0), mapping our display keys to
// the raw player_stats_history column names once.
const RAW: Record<string, string> = {
  games: "games",
  carries: "carries",
  rush_yds: "rushing_yards",
  rush_td: "rushing_tds",
  rec: "receptions",
  rec_yds: "receiving_yards",
  rec_td: "receiving_tds",
  tgt: "targets",
  pass_yds: "passing_yards",
  pass_td: "passing_tds",
  int: "interceptions",
};
const total = (history: SeasonRow[], key: keyof typeof RAW): number =>
  history.reduce((a, h) => a + (num(h.stats, RAW[key]) ?? 0), 0);

const rate = (numer: number, denom: number): number | null =>
  denom > 0 ? numer / denom : null;

/**
 * Position-aware advanced metrics for the player detail page. Returns only the
 * metrics whose denominator exists, so the caller renders a clean, dense panel.
 * E8 renders these same keys as optional Player Explorer columns.
 */
export function advancedMetrics(
  history: SeasonRow[],
  _position?: string | null,
): PlayerMetric[] {
  if (!history.length) return [];
  const g = total(history, "games");
  const carries = total(history, "carries");
  const recs = total(history, "rec");
  const tgt = total(history, "tgt");
  const rushYds = total(history, "rush_yds");
  const recYds = total(history, "rec_yds");
  const passYds = total(history, "pass_yds");
  const passTd = total(history, "pass_td");
  const ints = total(history, "int");
  const scrimTd = total(history, "rush_td") + total(history, "rec_td");
  const opp = carries + tgt;

  const all: PlayerMetric[] = [
    {
      key: "scrim_ypg",
      label: "Scrim Y/G",
      value: rate(rushYds + recYds, g),
      format: { decimals: 1 },
      tip: "Scrimmage yards (rush + receiving) per game — total offensive volume, the base usage signal.",
    },
    {
      key: "ypc",
      label: "YPC",
      value: rate(rushYds, carries),
      format: { decimals: 1 },
      tip: "Yards per carry — rushing efficiency independent of volume.",
    },
    {
      key: "ypr",
      label: "YPR",
      value: rate(recYds, recs),
      format: { decimals: 1 },
      tip: "Yards per reception — depth/efficiency of completed catches.",
    },
    {
      key: "ypt",
      label: "YPT",
      value: rate(recYds, tgt),
      format: { decimals: 1 },
      tip: "Yards per target — receiving efficiency per opportunity; a free-data proxy for aDOT × catch quality.",
    },
    {
      key: "catch_pct",
      label: "Catch %",
      value: tgt > 0 ? (recs / tgt) * 100 : null,
      format: { decimals: 0, suffix: "%" },
      tip: "Reception rate — receptions ÷ targets; hands + role reliability.",
    },
    {
      key: "td_per_opp",
      label: "TD/Opp",
      value: opp > 0 ? (scrimTd / opp) * 100 : null,
      format: { decimals: 1, suffix: "%" },
      tip: "Scrimmage touchdowns per opportunity (carry + target) — scoring efficiency / red-zone role.",
    },
    {
      key: "pass_ypg",
      label: "Pass Y/G",
      value: passYds > 0 ? rate(passYds, g) : null,
      format: { decimals: 1 },
      tip: "Passing yards per game — quarterback passing volume.",
    },
    {
      key: "td_int",
      label: "TD:INT",
      value: passYds > 0 ? rate(passTd, ints) : null,
      format: { decimals: 1 },
      tip: "Touchdown-to-interception ratio — quarterback decision quality (INT of 0 → shown as raw TDs).",
    },
  ];
  return all.filter((m) => m.value != null && Number.isFinite(m.value));
}

// ── College context for rookies / new players (E2) ──────────────────────────
// Reads the `college_production` summary that pipeline/ingest/college_ingest.py
// merges into players.metadata (prospect_score ∈ [0,1], 0.5 neutral). Degrades to
// null when there is no college context, so the page simply omits the block.

export interface CollegeContext {
  college: string | null;
  prospectScore: number | null; // 0–1 (0.5 neutral)
  season: number | null;
}

// A rookie/new player is where the college signal is decision-relevant.
export function isRookieOrNew(player: Pick<Player, "years_exp">): boolean {
  return player.years_exp != null && player.years_exp <= 1;
}

export function collegeContext(player: Player): CollegeContext | null {
  const prod = (player.metadata as Record<string, unknown> | null | undefined)?.[
    "college_production"
  ] as { prospect_score?: number; college?: string; season?: number } | undefined;
  if (!prod || typeof prod !== "object") return null;
  const score =
    typeof prod.prospect_score === "number" && Number.isFinite(prod.prospect_score)
      ? Math.max(0, Math.min(1, prod.prospect_score))
      : null;
  const college = typeof prod.college === "string" ? prod.college : null;
  const season = typeof prod.season === "number" ? prod.season : null;
  if (score == null && !college) return null;
  return { college, prospectScore: score, season };
}

// ── Multi-position eligibility (E2) ─────────────────────────────────────────
// Mirrors pipeline/models/multipos.eligible_positions on the frontend: the skill
// slots a player is eligible at, from metadata.fantasy_positions.

const SKILL_SLOTS = ["QB", "RB", "WR", "TE"] as const;

export function positionEligibility(player: Player): string[] {
  const raw =
    ((player.metadata as Record<string, unknown> | null | undefined)?.[
      "fantasy_positions"
    ] as unknown[] | undefined) ??
    (player.position ? [player.position] : []);
  const out: string[] = [];
  for (const p of raw) {
    if (typeof p === "string" && (SKILL_SLOTS as readonly string[]).includes(p) && !out.includes(p)) {
      out.push(p);
    }
  }
  return out;
}

export function isMultiPosition(player: Player): boolean {
  return positionEligibility(player).length > 1;
}
