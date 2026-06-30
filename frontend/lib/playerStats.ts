// Pure, null-safe career-production helpers for the player detail page. The
// pipeline already stores a rich per-season `stats` jsonb in player_stats_history
// (passing/rushing/receiving yards, TDs, attempts, receptions, target share,
// games…) that the page previously dropped on the floor in favour of just
// fantasy_pts. This turns that blob into a position-aware StatTable + a small
// career summary. No DOM, no React — testable in the node env (playerStats.test.ts).
import type { StatColumn } from "@/components/StatTable";

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
