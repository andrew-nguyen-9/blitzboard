"use server";
import { getServerSupabase } from "@/lib/supabase/server";
import { parsePrefs } from "@/lib/auth/prefs";

// Persist the signed-in user's prefs. RLS restricts the write to the caller's own row;
// the .eq(user_id) is defense-in-depth. parsePrefs throws on invalid input → no write.
export async function updatePrefs(
  input: unknown,
): Promise<{ ok: boolean; error?: string }> {
  const supabase = await getServerSupabase();
  if (!supabase) return { ok: false, error: "offline" };
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return { ok: false, error: "unauthenticated" };
  const prefs = parsePrefs(input);
  const { error } = await supabase.from("accounts").update({ prefs }).eq("user_id", user.id);
  if (error) return { ok: false, error: error.message };
  return { ok: true };
}
