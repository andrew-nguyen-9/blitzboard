// ─────────────────────────────────────────────────────────────
// Supabase client (public / anon, read-only).
//
// Resilient by design (inherited from festival-analyzer): if env vars are
// absent, getSupabase() returns null and every query helper degrades to empty
// results instead of throwing. The app builds and renders empty states with no
// backend, and goes live the instant NEXT_PUBLIC_SUPABASE_* are set.
// ─────────────────────────────────────────────────────────────
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

let client: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient | null {
  if (client) return client;
  if (!url || !anonKey) {
    if (process.env.NODE_ENV !== "production") {
      console.warn(
        "[supabase] NEXT_PUBLIC_SUPABASE_URL / _ANON_KEY not set — " +
          "running in offline mode (empty data, empty states).",
      );
    }
    return null;
  }
  client = createClient(url, anonKey, { auth: { persistSession: false } });
  return client;
}

export function isSupabaseConfigured(): boolean {
  return Boolean(url && anonKey);
}
