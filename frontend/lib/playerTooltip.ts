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
    { label: "Predictability ρ", value: fmt(p.predictability, 2) },
    { label: "Trend", value: trend },
  ];
}
