// Client-side Sleeper live-draft adapter. Talks to our own /api/sleeper proxy
// (not Sleeper directly). Maps Sleeper picks → our player pool by sleeper_id,
// with a graceful fallback player built from the pick's own metadata when a
// player isn't in our value table (e.g. value not computed yet).
import type { PlayerWithValue } from "./types";

export interface SleeperPick {
  player_id: string;
  pick_no: number;
  round: number;
  draft_slot: number; // 1..teams — the team that made the pick
  picked_by: string;
  metadata?: { first_name?: string; last_name?: string; position?: string; team?: string };
}

export interface SleeperDraftMeta {
  draft_id: string;
  status: string; // pre_draft | drafting | complete | paused
  type: string; // snake | linear | auction
  settings?: { teams?: number; rounds?: number };
  draft_order?: Record<string, number> | null; // user_id -> slot
}

export async function fetchSleeperPicks(draftId: string): Promise<SleeperPick[]> {
  const r = await fetch(`/api/sleeper/draft/${draftId}/picks`, { cache: "no-store" });
  if (!r.ok) throw new Error(`picks ${r.status}`);
  return r.json();
}

export async function fetchSleeperDraft(draftId: string): Promise<SleeperDraftMeta> {
  const r = await fetch(`/api/sleeper/draft/${draftId}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`draft ${r.status}`);
  return r.json();
}

// Build a usable PlayerWithValue from a Sleeper pick when we can't match by id.
function fallbackPlayer(pk: SleeperPick): PlayerWithValue {
  const m = pk.metadata ?? {};
  return {
    id: `sleeper-${pk.player_id}`,
    sleeper_id: pk.player_id,
    espn_id: null,
    full_name: `${m.first_name ?? ""} ${m.last_name ?? ""}`.trim() || pk.player_id,
    position: (m.position as any) ?? null,
    nfl_team: m.team ?? null,
    bye_week: null,
    age: null,
    years_exp: null,
    status: null,
    injury_status: null,
    value: null,
  };
}

export interface MappedPick {
  pickNo: number;
  team: number;
  player: PlayerWithValue;
}

export function mapPicks(
  picks: SleeperPick[],
  bySleeperId: Map<string, PlayerWithValue>,
): MappedPick[] {
  return [...picks]
    .sort((a, b) => a.pick_no - b.pick_no)
    .map((pk) => ({
      pickNo: pk.pick_no,
      team: pk.draft_slot,
      player: bySleeperId.get(pk.player_id) ?? fallbackPlayer(pk),
    }));
}
