// Server-side resolver for the authenticated-plane gate (v2.6.1). Reads the live session,
// active league, and credential status, then defers the decision to the pure gateFor() (which
// the access-matrix test covers). Server-only — imports getServerSupabase (httpOnly cookies).
import { getServerSupabase } from "@/lib/supabase/server";
import { getActiveLeague } from "@/lib/queries.auth";
import { getCredentialStatus } from "@/app/actions/credentials";
import { gateFor, type GateState } from "./gate";

export async function resolveGateState(): Promise<GateState> {
  const sb = await getServerSupabase();
  // Offline / unconfigured → present the login prompt (a friendly next step, never a crash).
  if (!sb) return "login";
  const {
    data: { user },
  } = await sb.auth.getUser();
  if (!user) return gateFor({ signedIn: false, hasLeague: false });

  const league = await getActiveLeague();
  // Only an ESPN/Sleeper league can have rotating credentials; a manual league never needs reconnect.
  let credentialExpired = false;
  if (league && league.platform !== "manual") {
    const creds = await getCredentialStatus();
    credentialExpired = creds.some((c) => c.platform === league.platform && c.status === "expired");
  }
  return gateFor({ signedIn: true, hasLeague: !!league, credentialExpired });
}
