// Client-side positional tiers from gaps in shaped value (mirrors the engine's
// _assign_tiers). A big drop between consecutive players at a position = a tier
// break — the "cliff" a drafter feels. Returns player id → tier number (1 = best).
// Generic over any row carrying an id, position, and a flat value — both the
// snapshot row and a flattened PlayerWithValue adapt to this.
export interface TierRow {
  id: string;
  position: string | null;
  value: number | null;
}

const norm = (p: string | null | undefined) => (p === "DEF" ? "DST" : p ?? "?");

export function tierMap(players: TierRow[]): Record<string, number> {
  const byPos: Record<string, TierRow[]> = {};
  for (const p of players) (byPos[norm(p.position)] ??= []).push(p);
  const out: Record<string, number> = {};
  for (const pos in byPos) {
    const vs = byPos[pos].slice().sort((a, b) => (b.value ?? -1e9) - (a.value ?? -1e9));
    const vals = vs.map((p) => p.value ?? 0);
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
