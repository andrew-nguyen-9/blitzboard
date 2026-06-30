// Pure, null-safe helpers behind the Players table's dynamic columns (e3): a
// generic cell comparator (any ColDef value is sortable) and the latest-season
// box-score reducer that backs the lazy box-column fetch. Kept out of the
// component so they stay testable in the node env (playerSort.test.ts).
import type { BoxStats } from "./playerColumns";
import { careerRows, type SeasonRow } from "./playerStats";

// Compare two raw column cells. Missing (null) ALWAYS sorts last regardless of
// direction (mirrors the table's prior "missing sorts last"); numbers compare
// numerically, everything else by locale string.
export function compareCells(
  a: number | string | null,
  b: number | string | null,
  asc: boolean,
): number {
  if (a == null) return b == null ? 0 : 1;
  if (b == null) return -1;
  const dir = asc ? 1 : -1;
  if (typeof a === "number" && typeof b === "number") return dir * (a - b);
  return dir * String(a).localeCompare(String(b));
}

// Reduce a (sleeper_id ↔ uuid) lookup + season history into the latest-season
// flat BoxStats per sleeper id. The Players table keys rows by sleeper id but
// player_stats_history keys by uuid, so we bridge here. Pure → the DB fetch in
// queries.getBoxStatsBySleeper stays a thin shell.
export function latestBoxBySleeper(
  players: Array<{ id: string; sleeper_id: string | null }>,
  history: Array<{ player_id: string; season: number } & Omit<SeasonRow, "season">>,
): Record<string, BoxStats> {
  const sleeperByUuid = new Map<string, string>();
  for (const p of players) if (p.sleeper_id) sleeperByUuid.set(p.id, p.sleeper_id);

  const latest = new Map<string, SeasonRow>();
  for (const h of history) {
    const prev = latest.get(h.player_id);
    if (!prev || h.season > prev.season) {
      latest.set(h.player_id, { season: h.season, fantasy_pts: h.fantasy_pts, stats: h.stats });
    }
  }

  const out: Record<string, BoxStats> = {};
  for (const [uuid, row] of latest) {
    const sid = sleeperByUuid.get(uuid);
    if (sid) out[sid] = careerRows([row])[0];
  }
  return out;
}
