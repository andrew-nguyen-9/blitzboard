// Authenticated, per-user Supabase reads — the RLS-isolated counterpart to queries.ts.
// Every helper goes through getServerSupabase() (anon key + the user's session cookie), so
// auth.uid() is populated and Row-Level Security restricts results to the caller's own rows
// at the database. The explicit .eq("user_id", user.id) is defense-in-depth, not the only
// guard. Null-safe: returns empty/falsy when offline so callers render empty states.
//
// This module must only be imported from server code (Server Components, Route Handlers,
// Server Actions). It reads httpOnly cookies and must never reach the client bundle — the
// bundle audit (scripts/audit-bundle.mjs) guards against secret leakage generally.
import { getServerSupabase } from "./supabase/server";

export interface Account {
  user_id: string;
  display_name: string | null;
  email: string | null;
  prefs: Record<string, unknown>;
}

// The signed-in user's account row, or null when offline / signed-out.
export async function getMyAccount(): Promise<Account | null> {
  const sb = await getServerSupabase();
  if (!sb) return null;
  const {
    data: { user },
  } = await sb.auth.getUser();
  if (!user) return null;
  const { data, error } = await sb
    .from("accounts")
    .select("user_id,display_name,email,prefs")
    .eq("user_id", user.id)
    .single();
  if (error) {
    console.error("[queries.auth.getMyAccount]", error.message);
    return null;
  }
  return data as Account;
}

// The signed-in user's saved preferences (a11y/theme), or {} when unavailable.
export async function getMyPrefs(): Promise<Record<string, unknown>> {
  const account = await getMyAccount();
  return account?.prefs ?? {};
}

export interface UserLeague {
  id: string;
  platform: "espn" | "sleeper" | "manual";
  external_league_id: string | null;
  season: string | null;
  name: string | null;
  scoring_profile_id: string | null;
  is_default: boolean;
}

// All of the signed-in user's connected leagues (RLS-isolated), oldest first.
export async function getMyLeagues(): Promise<UserLeague[]> {
  const sb = await getServerSupabase();
  if (!sb) return [];
  const { data, error } = await sb
    .from("user_leagues")
    .select("id,platform,external_league_id,season,name,scoring_profile_id,is_default")
    .order("created_at");
  if (error) {
    console.error("[queries.auth.getMyLeagues]", error.message);
    return [];
  }
  return (data ?? []) as UserLeague[];
}

// The user's active league — their default, or the first connected, or null. This is the
// league the gated tabs (v2.6) tailor value/standings/waivers to.
export async function getActiveLeague(): Promise<UserLeague | null> {
  const leagues = await getMyLeagues();
  return leagues.find((l) => l.is_default) ?? leagues[0] ?? null;
}

export interface UserLeagueWithConfig extends UserLeague {
  config: Record<string, unknown> | null;
}

// All connected leagues joined to their stored rules config — the authed draft/waiver/trade
// surfaces use `config` (a LeagueConfig for Sleeper, a default shell for ESPN) for league context.
export async function getMyLeaguesWithConfig(): Promise<UserLeagueWithConfig[]> {
  const sb = await getServerSupabase();
  if (!sb) return [];
  const { data, error } = await sb
    .from("user_leagues")
    .select(
      "id,platform,external_league_id,season,name,scoring_profile_id,is_default,league_rules(config)",
    )
    .order("created_at");
  if (error) {
    console.error("[queries.auth.getMyLeaguesWithConfig]", error.message);
    return [];
  }
  return (data ?? []).map((r: any) => ({
    id: r.id,
    platform: r.platform,
    external_league_id: r.external_league_id,
    season: r.season,
    name: r.name,
    scoring_profile_id: r.scoring_profile_id,
    is_default: r.is_default,
    config: r.league_rules?.config ?? null,
  }));
}

// The active league's scoring rules config, or null. Joins user_leagues → league_rules.
export async function getActiveLeagueRules(): Promise<Record<string, unknown> | null> {
  const sb = await getServerSupabase();
  if (!sb) return null;
  const active = await getActiveLeague();
  if (!active?.scoring_profile_id) return null;
  const { data, error } = await sb
    .from("league_rules")
    .select("config")
    .eq("id", active.scoring_profile_id)
    .single();
  if (error) {
    console.error("[queries.auth.getActiveLeagueRules]", error.message);
    return null;
  }
  return (data?.config ?? null) as Record<string, unknown> | null;
}
