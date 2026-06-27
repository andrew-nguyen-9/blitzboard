"use server";

// Multi-league server actions (v2.5.4). Persist an imported league + its confirmed rules, and
// switch the active (default) league. All writes go through getServerSupabase() so RLS scopes
// every row to the signed-in user; the atomic default flip uses the set_default_league() RPC.
import { getServerSupabase } from "@/lib/supabase/server";
import type { ImportedRules } from "@/lib/leagueRules";

export interface LeagueMeta {
  platform: "espn" | "sleeper" | "manual";
  external_league_id: string | null;
  season: string | null;
  name: string;
}

// Save a (user-confirmed) imported league: create an owned rules profile, then the league row.
// The first league a user connects becomes their default automatically.
export async function saveImportedLeague(
  rules: ImportedRules,
  meta: LeagueMeta,
): Promise<{ ok: boolean; error?: string }> {
  const sb = await getServerSupabase();
  if (!sb) return { ok: false, error: "offline" };
  const {
    data: { user },
  } = await sb.auth.getUser();
  if (!user) return { ok: false, error: "not signed in" };

  const { data: rule, error: ruleErr } = await sb
    .from("league_rules")
    .insert({ owner_user_id: user.id, name: meta.name, config: rules })
    .select("id")
    .single();
  if (ruleErr || !rule) return { ok: false, error: ruleErr?.message ?? "rules insert failed" };

  const { count } = await sb
    .from("user_leagues")
    .select("id", { count: "exact", head: true })
    .eq("user_id", user.id);

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
