// Bridges a decoded snapshot row to the shared uncertainty kit so the player table
// can show a floor–median–ceiling range per row. The snapshot ships the value
// row's bust(P10)/value(P50)/boom(P90) band (no projection mean/stdev yet), so we
// hand those to the existing `playerUncertainty` deriver — it yields quantiles when
// the band exists and null when it doesn't (→ the row renders its empty state).
import { playerUncertainty, type PlayerUncertainty } from "@/components/uncertainty";
import type { SnapshotPlayer } from "./snapshot";

export function rowUncertainty(p: SnapshotPlayer): PlayerUncertainty | null {
  return playerUncertainty({ value: p.value, boom: p.boom, bust: p.bust, adp: p.adp, rank: p.rank }, null);
}
