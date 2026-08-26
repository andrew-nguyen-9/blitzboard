import type { LeagueConfig } from "@/lib/leagueConfig";
import type { MappedPick } from "@/lib/sleeperDraft";
import type { PlayerWithValue } from "@/lib/types";

export interface ManualDraftState {
  leagueId: string;
  config: LeagueConfig;
  mySlot: number;
  picks: MappedPick[];
  keepers: PlayerWithValue[];
}

const STORAGE_PREFIX = "blitzboard:manual-draft";

export function localDate(date = new Date()): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function manualDraftKey(leagueId: string, date = new Date()): string {
  return `${STORAGE_PREFIX}:${encodeURIComponent(leagueId || "manual")}:${localDate(date)}`;
}

export function serializeManualDraft(state: ManualDraftState): string {
  return JSON.stringify(state);
}

export function deserializeManualDraft(value: string): ManualDraftState | null {
  try {
    const parsed = JSON.parse(value) as Partial<ManualDraftState>;
    if (!parsed.config || !Array.isArray(parsed.picks) || !Array.isArray(parsed.keepers)) return null;
    return {
      leagueId: typeof parsed.leagueId === "string" ? parsed.leagueId : "",
      config: parsed.config,
      mySlot: typeof parsed.mySlot === "number" ? parsed.mySlot : 1,
      picks: parsed.picks,
      keepers: parsed.keepers,
    };
  } catch {
    return null;
  }
}

export function replacePick(picks: MappedPick[], pickNo: number, player: PlayerWithValue): MappedPick[] {
  if (picks.some((pick) => pick.pickNo !== pickNo && pick.player.id === player.id)) return picks;
  return picks.map((pick) => (pick.pickNo === pickNo ? { ...pick, player } : pick));
}

export function availablePlayerIds(
  players: PlayerWithValue[],
  picks: MappedPick[],
  keepers: PlayerWithValue[],
): string[] {
  const unavailable = new Set([...picks.map((pick) => pick.player.id), ...keepers.map((player) => player.id)]);
  return players.filter((player) => !unavailable.has(player.id)).map((player) => player.id);
}
