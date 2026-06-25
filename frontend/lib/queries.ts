// All Supabase reads live here (no raw fetches in components — inherited
// convention). Every helper is null-safe: returns empty/falsy when the client
// is unconfigured so the UI renders empty states instead of throwing.
import { getSupabase } from "./supabase";
import type { Engine, Player, PlayerWithValue } from "./types";

const PLAYER_COLS =
  "id,sleeper_id,espn_id,full_name,position,nfl_team,bye_week,age,years_exp,status,injury_status,metadata";

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
      `value,vor,replacement,boom,bust,adp,rank,predictability,engine,player_id,
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
      predictability: r.predictability,
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

export interface WaiverTarget {
  player_id: string;
  full_name: string;
  position: string | null;
  nfl_team: string | null;
  injury_status: string | null;
  trend_score: number;
  sentiment_avg: number;
  sleeper_adds: number;
  sleeper_drops: number;
  vor: number | null;
}

// Waiver tool: top trending players blended with their VORP value (P4).
export async function getWaiverTargets(limit = 60): Promise<WaiverTarget[]> {
  const sb = getSupabase();
  if (!sb) return [];
  const { data: trend, error } = await sb
    .from("trending")
    .select("player_id,trend_score,sentiment_avg,sleeper_adds,sleeper_drops,players!inner(full_name,position,nfl_team,injury_status)")
    .order("trend_score", { ascending: false })
    .limit(limit);
  if (error) {
    console.error("[queries.getWaiverTargets]", error.message);
    return [];
  }
  const ids = (trend ?? []).map((t: any) => t.player_id);
  // attach VORP value for those players
  const { data: vals } = await sb
    .from("player_value")
    .select("player_id,vor")
    .eq("engine", "vorp")
    .in("player_id", ids.length ? ids : ["00000000-0000-0000-0000-000000000000"]);
  const vorById = new Map((vals ?? []).map((v: any) => [v.player_id, v.vor]));
  return (trend ?? []).map((t: any) => ({
    player_id: t.player_id,
    full_name: t.players.full_name,
    position: t.players.position,
    nfl_team: t.players.nfl_team,
    injury_status: t.players.injury_status,
    trend_score: t.trend_score,
    sentiment_avg: t.sentiment_avg,
    sleeper_adds: t.sleeper_adds,
    sleeper_drops: t.sleeper_drops,
    vor: vorById.get(t.player_id) ?? null,
  }));
}

export interface NewsItem {
  title: string;
  source: string | null;
  url: string | null;
  sentiment: number | null;
  injury_flag: boolean;
  opportunity_flag: boolean;
  published_at: string | null;
}

export async function getRecentNews(limit = 12): Promise<NewsItem[]> {
  const sb = getSupabase();
  if (!sb) return [];
  const { data } = await sb
    .from("news_articles")
    .select("title,source,url,sentiment,injury_flag,opportunity_flag,published_at")
    .order("ingested_at", { ascending: false })
    .limit(limit);
  return (data as NewsItem[]) ?? [];
}

export interface LeagueTeam {
  id: string;
  espn_team_id: number | null;
  team_name: string | null;
  owner: string | null;
  player_ids: string[];
}

// Teams + their rostered player ids (for the trade optimizer). Empty until league_sync runs.
export async function getLeagueTeams(): Promise<LeagueTeam[]> {
  const sb = getSupabase();
  if (!sb) return [];
  const { data: league } = await sb
    .from("leagues").select("id").eq("platform", "espn")
    .order("season", { ascending: false }).limit(1).maybeSingle();
  if (!league) return [];
  const { data } = await sb
    .from("rosters")
    .select("id,espn_team_id,team_name,owner,player_ids")
    .eq("league_id", league.id)
    .order("team_name");
  return (data as LeagueTeam[]) ?? [];
}

// Players (with VORP value) for a set of ids — used to hydrate two rosters for trades.
export async function getPlayersWithValueByIds(ids: string[]): Promise<PlayerWithValue[]> {
  const sb = getSupabase();
  if (!sb || !ids.length) return [];
  const [{ data: players }, { data: vals }] = await Promise.all([
    sb.from("players").select(PLAYER_COLS).in("id", ids),
    sb.from("player_value").select("player_id,value,vor,boom,bust,rank,predictability").eq("engine", "vorp").in("player_id", ids),
  ]);
  const vById = new Map((vals ?? []).map((v: any) => [v.player_id, v]));
  return (players ?? []).map((p: any) => {
    const v = vById.get(p.id);
    return {
      ...(p as Player),
      value: v
        ? { player_id: p.id, engine: "vorp", value: v.value, vor: v.vor, replacement: null, boom: v.boom, bust: v.bust, adp: null, rank: v.rank, predictability: v.predictability }
        : null,
    };
  });
}

// ALL players ranked by value, paginating past PostgREST's 1000-row cap (#1).
export async function getAllPlayersByValue(engine: Engine = "vorp"): Promise<PlayerWithValue[]> {
  const sb = getSupabase();
  if (!sb) return [];
  const out: PlayerWithValue[] = [];
  const PAGE = 1000;
  for (let start = 0; ; start += PAGE) {
    const { data, error } = await sb
      .from("player_value")
      .select(`value,vor,replacement,boom,bust,adp,rank,predictability,engine,player_id,players!inner(${PLAYER_COLS})`)
      .eq("engine", engine)
      .order("rank")
      .range(start, start + PAGE - 1);
    if (error) { console.error("[getAllPlayersByValue]", error.message); break; }
    const rows = data ?? [];
    for (const r of rows as any[]) {
      out.push({
        ...(r.players as Player),
        value: { player_id: r.player_id, engine: r.engine, value: r.value, vor: r.vor,
          replacement: r.replacement, boom: r.boom, bust: r.bust, adp: r.adp, rank: r.rank,
          predictability: r.predictability },
      });
    }
    if (rows.length < PAGE) break;
  }
  return out;
}

// Player ids rostered anywhere in the league (for the free-agent filter, #3).
export async function getRosteredIds(): Promise<Set<string>> {
  const sb = getSupabase();
  if (!sb) return new Set();
  const { data } = await sb.from("rosters").select("player_ids");
  const s = new Set<string>();
  for (const r of (data ?? []) as any[]) for (const id of r.player_ids ?? []) s.add(id);
  return s;
}

// player_id → trend_score (so growing-sentiment FAs survive the FA filter, #3).
export async function getTrendingMap(): Promise<Record<string, number>> {
  const sb = getSupabase();
  if (!sb) return {};
  const { data } = await sb.from("trending").select("player_id,trend_score");
  return Object.fromEntries((data ?? []).map((t: any) => [t.player_id, t.trend_score]));
}

export async function getPlayerCount(): Promise<number> {
  const sb = getSupabase();
  if (!sb) return 0;
  const { count } = await sb
    .from("players")
    .select("id", { count: "exact", head: true });
  return count ?? 0;
}
