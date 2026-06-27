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
