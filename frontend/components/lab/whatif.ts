// What-if scenarios for the Lab: injure a player → downstream projection deltas.
// A toy "opportunity vacuum" model (pure + testable) that stands in until the
// engine exposes a live scenario endpoint: the injured player drops to zero, and a
// share of the vacated projection redistributes to same-team, same-position
// teammates in proportion to their current projection (the biggest beneficiary of
// vacated targets/carries gains the most). Honest and legible, not a real sim.

export interface ScenarioPlayer {
  id: string;
  name: string;
  team: string;
  position: string;
  proj: number; // current projected points
}

export interface PlayerDelta {
  id: string;
  name: string;
  team: string;
  position: string;
  before: number;
  after: number;
  delta: number; // after − before
}

// `transferShare` ∈ [0,1]: fraction of the injured player's projection that flows
// to teammates (the rest evaporates to worse game script / lower efficiency).
export function applyInjury(
  players: ScenarioPlayer[],
  injuredId: string,
  transferShare = 0.6,
): PlayerDelta[] {
  const injured = players.find((p) => p.id === injuredId);
  if (!injured) return [];

  const beneficiaries = players.filter(
    (p) => p.id !== injuredId && p.team === injured.team && p.position === injured.position,
  );
  const share = Math.max(0, Math.min(1, transferShare));
  const pool = Math.max(0, injured.proj) * share;
  const totalWeight = beneficiaries.reduce((s, p) => s + Math.max(0, p.proj), 0);

  const deltas: PlayerDelta[] = [
    {
      id: injured.id,
      name: injured.name,
      team: injured.team,
      position: injured.position,
      before: injured.proj,
      after: 0,
      delta: -injured.proj,
    },
  ];

  for (const b of beneficiaries) {
    const w = totalWeight > 0 ? Math.max(0, b.proj) / totalWeight : 1 / beneficiaries.length;
    const gain = pool * w;
    deltas.push({
      id: b.id,
      name: b.name,
      team: b.team,
      position: b.position,
      before: b.proj,
      after: b.proj + gain,
      delta: gain,
    });
  }

  // Largest absolute swing first (the injured player, then top beneficiaries).
  return deltas.sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
}
