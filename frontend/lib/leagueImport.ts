// Client-side adapters for the league-import flow. Talks only to our own
// /api/sleeper proxy routes (never Sleeper directly). The Sleeper path needs no
// auth — a username resolves to leagues, a league_id resolves to a full config.
// ESPN has no public OAuth: public leagues work with a league id alone, private
// leagues additionally need the user's espn_s2 + SWID cookies (sent to the
// server proxy, never persisted in the browser).
import type { LeagueConfig } from "./leagueConfig";

export interface SleeperLeagueLite {
  leagueId: string;
  name: string;
  numTeams: number;
  draftId: string | null;
  status: string;
}

export interface SleeperUserLookup {
  user: { id: string; username: string; displayName: string };
  season: string;
  leagues: SleeperLeagueLite[];
}

export async function lookupSleeperUser(username: string, season?: string): Promise<SleeperUserLookup> {
  const qs = season ? `?season=${season}` : "";
  const r = await fetch(`/api/sleeper/user/${encodeURIComponent(username.trim())}${qs}`, { cache: "no-store" });
  if (!r.ok) throw new Error((await safeErr(r)) ?? `lookup ${r.status}`);
  return r.json();
}

export async function importSleeperLeague(leagueId: string): Promise<LeagueConfig> {
  const r = await fetch(`/api/sleeper/league/${leagueId.trim()}`, { cache: "no-store" });
  if (!r.ok) throw new Error((await safeErr(r)) ?? `import ${r.status}`);
  return r.json();
}

async function safeErr(r: Response): Promise<string | null> {
  try {
    return (await r.json()).error ?? null;
  } catch {
    return null;
  }
}
