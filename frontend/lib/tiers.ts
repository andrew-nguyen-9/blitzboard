// Client-side positional tiers from gaps in shaped value (mirrors the engine's
// _assign_tiers). A big drop between consecutive players at a position = a tier
// break — the "cliff" a drafter feels. Returns player_id → tier number (1 = best).
import type { PlayerWithValue } from "./types";

const norm = (p: string | null | undefined) => (p === "DEF" ? "DST" : p ?? "?");

export function tierMap(players: PlayerWithValue[]): Record<string, number> {
  const byPos: Record<string, PlayerWithValue[]> = {};
  for (const p of players) (byPos[norm(p.position)] ??= []).push(p);
  const out: Record<string, number> = {};
  for (const pos in byPos) {
    const vs = byPos[pos].slice().sort((a, b) => (b.value?.value ?? -1e9) - (a.value?.value ?? -1e9));
    const vals = vs.map((p) => p.value?.value ?? 0);
    const gaps = vals.slice(1).map((v, i) => vals[i] - v);
    const avg = gaps.length ? gaps.reduce((a, b) => a + b, 0) / gaps.length : 0;
    let tier = 1;
    vs.forEach((p, i) => {
      if (i > 0 && vals[i - 1] - vals[i] > Math.max(6, avg * 1.6)) tier++;
      out[p.id] = tier;
    });
  }
  return out;
}
