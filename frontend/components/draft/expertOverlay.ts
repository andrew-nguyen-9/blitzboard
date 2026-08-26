import boardData from "@/lib/data/expert-board-2026.json";
import type { PlayerWithValue } from "@/lib/types";

export const DISAGREEMENT_RANKS = 24;

export interface ExpertBoardEntry {
  modelRank: number;
  name: string;
  position: string;
  marketAdp: number | "";
  risk: string;
  upside: string;
  tier: number | "";
  note: string;
}

export interface ExpertOverlay {
  byPlayerId: Map<string, ExpertBoardEntry>;
  unmatched: string[];
  ambiguous: string[];
  asOf: string;
}

export function normalizeExpertName(name: string): string {
  return name
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\b(jr|sr|ii|iii|iv)\b/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

export const normalizeExpertPosition = (position: string | null) =>
  position === "DEF" ? "DST" : (position ?? "").toUpperCase();

const key = (name: string, position: string | null) =>
  `${normalizeExpertName(name)}|${normalizeExpertPosition(position)}`;

export function disagreement(
  vorpRank: number | null | undefined,
  expertRank: number,
): "opportunity" | "landmine" | null {
  if (vorpRank == null) return null;
  if (vorpRank - expertRank >= DISAGREEMENT_RANKS) return "opportunity";
  if (expertRank - vorpRank >= DISAGREEMENT_RANKS) return "landmine";
  return null;
}

export function matchExpertBoard(
  players: PlayerWithValue[],
  numTeams: number,
  data: typeof boardData = boardData,
): ExpertOverlay | null {
  const selected = data?.boards?.[String(numTeams) as "11" | "12"];
  const entries = (selected === "shared" ? data.sharedBoard : selected) as ExpertBoardEntry[] | undefined;
  if (!Array.isArray(entries) || !entries.length) return null;

  const playersByKey = new Map<string, PlayerWithValue[]>();
  for (const player of players) {
    const k = key(player.full_name, player.position);
    playersByKey.set(k, [...(playersByKey.get(k) ?? []), player]);
  }
  const entriesByKey = new Map<string, ExpertBoardEntry[]>();
  for (const entry of entries) {
    if (!entry || typeof entry.name !== "string" || typeof entry.position !== "string" || typeof entry.modelRank !== "number") continue;
    const k = key(entry.name, entry.position);
    entriesByKey.set(k, [...(entriesByKey.get(k) ?? []), entry]);
  }

  const byPlayerId = new Map<string, ExpertBoardEntry>();
  const unmatched: string[] = [];
  const ambiguous: string[] = [];
  for (const [k, matches] of entriesByKey) {
    const candidates = playersByKey.get(k) ?? [];
    if (!candidates.length) unmatched.push(matches[0].name);
    else if (candidates.length !== 1 || matches.length !== 1) ambiguous.push(matches[0].name);
    else byPlayerId.set(candidates[0].id, matches[0]);
  }
  return { byPlayerId, unmatched, ambiguous, asOf: typeof data.asOf === "string" ? data.asOf : "unknown date" };
}
