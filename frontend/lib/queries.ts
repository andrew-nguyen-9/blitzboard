// All Supabase reads live here (no raw fetches in components — inherited
// convention). Every helper is null-safe: returns empty/falsy when the client
// is unconfigured so the UI renders empty states instead of throwing.
import { getSupabase } from "./supabase";
import type { Engine, Player, PlayerWithValue } from "./types";

const PLAYER_COLS =
  "id,sleeper_id,espn_id,full_name,position,nfl_team,bye_week,age,years_exp,status,injury_status";

export async function getPlayers(opts?: {
  position?: string;
  search?: string;
  limit?: number;
}): Promise<Player[]> {
  const sb = getSupabase();
  if (!sb) return [];
  let q = sb.from("players").select(PLAYER_COLS).order("full_name");
  if (opts?.position) q = q.eq("position", opts.position);
  if (opts?.search) q = q.ilike("search_name", `%${opts.search.toLowerCase()}%`);
  q = q.limit(opts?.limit ?? 200);
  const { data, error } = await q;
  if (error) {
    console.error("[queries.getPlayers]", error.message);
    return [];
  }
  return (data as Player[]) ?? [];
}

// Players ranked by value under a given engine (Player Explorer / draft board).
export async function getPlayersByValue(
  engine: Engine = "vorp",
  limit = 200,
): Promise<PlayerWithValue[]> {
  const sb = getSupabase();
  if (!sb) return [];
  const { data, error } = await sb
    .from("player_value")
    .select(
      `value,vor,replacement,boom,bust,adp,rank,engine,player_id,
       players!inner(${PLAYER_COLS})`,
    )
    .eq("engine", engine)
    .order("rank")
    .limit(limit);
  if (error) {
    console.error("[queries.getPlayersByValue]", error.message);
    return [];
  }
  // flatten the joined player row + attach value
  return (data ?? []).map((r: any) => ({
    ...(r.players as Player),
    value: {
      player_id: r.player_id,
      engine: r.engine,
      value: r.value,
      vor: r.vor,
      replacement: r.replacement,
      boom: r.boom,
      bust: r.bust,
      adp: r.adp,
      rank: r.rank,
    },
  }));
}

export interface PlayerDetail {
  player: Player;
  value: any | null;
  projection: any | null;
  history: Array<{ season: number; fantasy_pts: number | null; stats: any }>;
}

// Everything the player detail page needs, in one place (null-safe).
export async function getPlayerDetail(id: string): Promise<PlayerDetail | null> {
  const sb = getSupabase();
  if (!sb) return null;
  const { data: player } = await sb.from("players").select(PLAYER_COLS).eq("id", id).maybeSingle();
  if (!player) return null;

  const [{ data: value }, { data: projection }, { data: history }] = await Promise.all([
    sb.from("player_value").select("*").eq("player_id", id).eq("engine", "vorp").maybeSingle(),
    sb.from("projections").select("*").eq("player_id", id).eq("source", "ensemble").order("season", { ascending: false }).limit(1).maybeSingle(),
    sb.from("player_stats_history").select("season,fantasy_pts,stats").eq("player_id", id).is("week", null).order("season"),
  ]);

  return {
    player: player as Player,
    value: value ?? null,
    projection: projection ?? null,
    history: (history as any[]) ?? [],
  };
}

export interface RosterTeam {
  id: string;
  espn_team_id: number | null;
  team_name: string | null;
  owner: string | null;
  abbrev: string | null;
  division: string | null;
  player_ids: string[];
  wins: number;
  losses: number;
  ties: number;
  points_for: number;
  points_against: number;
  standing: number | null;
}

export interface LeagueOverview {
  league: { id: string; name: string | null; season: number; external_id: string } | null;
  teams: RosterTeam[];
}

// League Overview: the seeded/synced ESPN league + its teams ordered by standing.
export async function getLeagueOverview(): Promise<LeagueOverview> {
  const sb = getSupabase();
  if (!sb) return { league: null, teams: [] };
  const { data: league } = await sb
    .from("leagues")
    .select("id,name,season,external_id")
    .eq("platform", "espn")
    .order("season", { ascending: false })
    .limit(1)
    .maybeSingle();
  if (!league) return { league: null, teams: [] };
  const { data: teams } = await sb
    .from("rosters")
    .select("*")
    .eq("league_id", league.id)
    .order("standing", { nullsFirst: false });
  return { league: league as any, teams: (teams as RosterTeam[]) ?? [] };
}

export async function getPlayerCount(): Promise<number> {
  const sb = getSupabase();
  if (!sb) return 0;
  const { count } = await sb
    .from("players")
    .select("id", { count: "exact", head: true });
  return count ?? 0;
}
