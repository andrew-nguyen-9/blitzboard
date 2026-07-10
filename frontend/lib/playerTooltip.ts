import type { SnapshotPlayer } from "@/lib/snapshot";

// Pure, null-safe scouting summary for a player row's hover card. Kept out of the
// component so the formatting (missing → "—", decimals, derived pos·team, trend
// sign) stays unit-testable in the node test env.
export interface TipRow {
  label: string;
  value: string;
}

const normPos = (p: string | null | undefined) => (p === "DEF" ? "DST" : p ?? "—");
const fmt = (v: number | null | undefined, d = 1) => (v == null ? "—" : v.toFixed(d));

export function playerTooltipRows(p: SnapshotPlayer, tier?: number): TipRow[] {
  const trend =
    p.trend == null ? "—" : p.trend > 0 ? `▲ ${p.trend} adds` : p.trend < 0 ? `▼ ${Math.abs(p.trend)}` : "flat";
  return [
    { label: "Rank", value: p.rank == null ? "—" : `#${p.rank}` },
    { label: "Pos · Team", value: `${normPos(p.position)} · ${p.nfl_team ?? "FA"}` },
    { label: "Tier", value: tier ? `T${tier}` : "—" },
    { label: "Value", value: fmt(p.value) },
    { label: "VOR", value: fmt(p.vor) },
    { label: "Boom · Bust", value: `${fmt(p.boom, 0)} · ${fmt(p.bust, 0)}` },
    { label: "ADP", value: fmt(p.adp) },
    { label: "Predictability ρ", value: fmt(p.predictability, 2) },
    { label: "Trend", value: trend },
  ];
}

// One-line definitions for the Player Explorer column headers (E8). Keyed by
// ColDef.key (lib/playerColumns.ts); the header composes the shared Tooltip.tsx
// primitive (E10-owned — usage only, no restyle). Advanced-metric text mirrors
// E2's canonical tips in lib/playerStats.ts advancedMetrics / ANALYTICS_SURVEY.md.
export const columnTips: Record<string, string> = {
  value: "Projected value — points above replacement translated to the ranking scale. The core draft signal.",
  vor: "Value Over Replacement: projected points above a freely-available replacement starter at this position.",
  boom: "P90 outcome — the simulated ceiling (top-decile season) from the value engine's distribution.",
  bust: "P10 outcome — the simulated floor (bottom-decile season) from the value engine's distribution.",
  rank: "Overall rank across the player universe by value under the active engine.",
  adp: "Average draft position across public drafts — compare to rank to spot market mispricings.",
  tier: "Value tier — a natural gap in the ranking; players inside a tier are roughly interchangeable.",
  pass_yds: "Passing yards, most recent loaded season.",
  rush_yds: "Rushing yards, most recent loaded season.",
  rec: "Receptions, most recent loaded season.",
  rec_yds: "Receiving yards, most recent loaded season.",
  fantasy_pts: "Fantasy points scored in the most recent loaded season.",
  scrim_ypg: "Scrimmage yards (rush + receiving) per game — total offensive volume, the base usage signal.",
  ypc: "Yards per carry — rushing efficiency independent of volume.",
  ypr: "Yards per reception — depth/efficiency of completed catches.",
  ypt: "Yards per target — receiving efficiency per opportunity; a free-data proxy for aDOT × catch quality.",
  catch_pct: "Reception rate — receptions ÷ targets; hands + role reliability.",
  td_per_opp: "Scrimmage touchdowns per opportunity (carry + target) — scoring efficiency / red-zone role.",
  pass_ypg: "Passing yards per game — quarterback passing volume.",
  td_int: "Touchdown-to-interception ratio — quarterback decision quality.",
};
