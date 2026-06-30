"use server";

// Multi-league server actions (v2.5.4 → Epic 8). Persist a connected league + its rules,
// switch the active (default) league, and disconnect. All writes go through getServerSupabase()
// so RLS scopes every row to the signed-in user; the atomic default flip uses set_default_league().
import { getServerSupabase } from "@/lib/supabase/server";
import { MAX_LEAGUES } from "@/lib/leagueLimits";

export interface LeagueMeta {
  platform: "espn" | "sleeper" | "manual";
  external_league_id: string | null;
  season: string | null;
  name: string;
}

// Connect a (user-confirmed) league: store its full config as an owned rules profile, then the
// league row. The first league a user connects becomes their default automatically. Enforces the
// MAX_LEAGUES cap server-side (the UI also hides "connect" at the cap — defense in depth).
// `config` is the platform-normalized LeagueConfig (Sleeper) or a default shell (ESPN); it rides
// in jsonb so the authed draft can rebuild the board without re-fetching.
export async function connectLeague(
  config: Record<string, unknown>,
  meta: LeagueMeta,
): Promise<{ ok: boolean; error?: string }> {
  const sb = await getServerSupabase();
  if (!sb) return { ok: false, error: "offline" };
  const {
    data: { user },
  } = await sb.auth.getUser();
  if (!user) return { ok: false, error: "not signed in" };

  const { count } = await sb
    .from("user_leagues")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id);
  if ((count ?? 0) >= MAX_LEAGUES) {
    return { ok: false, error: `You can connect up to ${MAX_LEAGUES} leagues.` };
  }

  const { data: rule, error: ruleErr } = await sb
    .from("league_rules")
    .insert({ owner_user_id: user.id, name: meta.name, config })
    .select("id")
    .single();
  if (ruleErr || !rule) return { ok: false, error: ruleErr?.message ?? "rules insert failed" };

  const { error: leagueErr } = await sb.from("user_leagues").insert({
    user_id: user.id,
    platform: meta.platform,
    external_league_id: meta.external_league_id,
    season: meta.season,
    name: meta.name,
    scoring_profile_id: rule.id,
    is_default: (count ?? 0) === 0, // first league becomes the default
  });
  if (leagueErr) return { ok: false, error: leagueErr.message };
  return { ok: true };
}

// Switch the active league (atomic: exactly one default per user via the RPC).
export async function setDefaultLeague(leagueId: string): Promise<{ ok: boolean }> {
  const sb = await getServerSupabase();
  if (!sb) return { ok: false };
  const { error } = await sb.rpc("set_default_league", { p_league: leagueId });
  return { ok: !error };
}

// Disconnect a league (RLS scopes the delete to the owner). Its owned rules profile is removed
// too; user_leagues.scoring_profile_id is ON DELETE SET NULL so order doesn't matter.
export async function disconnectLeague(leagueId: string): Promise<{ ok: boolean }> {
  const sb = await getServerSupabase();
  if (!sb) return { ok: false };
  const {
    data: { user },
  } = await sb.auth.getUser();
  if (!user) return { ok: false };
  const { data: row } = await sb
    .from("user_leagues")
    .select("scoring_profile_id")
    .eq("id", leagueId)
    .maybeSingle();
  const { error } = await sb.from("user_leagues").delete().eq("id", leagueId);
  if (!error && row?.scoring_profile_id) {
    await sb.from("league_rules").delete().eq("id", row.scoring_profile_id);
  }
  return { ok: !error };
}
