// Client-side ESPN live-draft adapter. Talks to our /api/espn proxy (cookies stay
// server-side). ESPN picks carry only player id + overall pick number, so we map by
// espn_id and derive the team from snake math (teamOnClock).
import type { PlayerWithValue } from "./types";
import { teamOnClock } from "./draft";
import type { MappedPick } from "./sleeperDraft";

export interface EspnNormPick {
  pickNo: number;
  espnId: string;
}
export interface EspnDraftResp {
  picks: EspnNormPick[];
  meta: { teams: number | null; status: string };
}

export async function fetchEspnDraft(leagueId?: string, season?: string): Promise<EspnDraftResp> {
  const qs = new URLSearchParams();
  if (leagueId) qs.set("leagueId", leagueId);
  if (season) qs.set("season", season);
  const r = await fetch(`/api/espn/draft?${qs.toString()}`, { cache: "no-store" });
  if (!r.ok) {
    let msg = `espn ${r.status}`;
    try {
      msg = (await r.json()).error ?? msg;
    } catch {}
    throw new Error(msg);
  }
  return r.json();
}

export function mapEspnPicks(
  picks: EspnNormPick[],
  byEspnId: Map<string, PlayerWithValue>,
  numTeams: number,
): MappedPick[] {
  return picks.map((pk) => {
    const player = byEspnId.get(pk.espnId) ?? fallback(pk);
    return { pickNo: pk.pickNo, team: teamOnClock(pk.pickNo, numTeams), player };
  });
}

function fallback(pk: EspnNormPick): PlayerWithValue {
  return {
    id: `espn-${pk.espnId}`,
    sleeper_id: `espn-${pk.espnId}`,
    espn_id: pk.espnId,
    full_name: `ESPN #${pk.espnId}`,
    position: null,
    nfl_team: null,
    bye_week: null,
    age: null,
    years_exp: null,
    status: null,
    injury_status: null,
    value: null,
  };
}
