"use server";

// Credential-vault server actions (v2.5.3). The browser WRITES a secret once (over TLS into
// this server action, which encrypts before it touches the DB) and thereafter only ever sees a
// masked "connected ✓" status — never the secret back. Decryption for ESPN/Sleeper calls
// happens in the pipeline (service-role), never here and never client-side.
import { getServerSupabase } from "@/lib/supabase/server";
import { loadMasterKey, encryptSecret, maskHint } from "@/lib/crypto/vault";
import { credentialInput, validate } from "@/lib/validation";

export type Platform = "espn" | "sleeper";

export interface CredentialStatus {
  platform: Platform;
  masked_hint: string | null;
  status: "connected" | "expired";
  expires_at: string | null;
}

// Encrypt and store (or replace) the user's credential for a platform. Returns only ok/error —
// the plaintext never leaves this function and the ciphertext is never returned to the client.
export async function saveCredential(
  platform: Platform,
  secret: string,
): Promise<{ ok: boolean; error?: string }> {
  const valid = validate(credentialInput, { platform, secret });
  if (!valid.ok) return { ok: false, error: valid.error };
  const key = loadMasterKey();
  if (!key) return { ok: false, error: "vault not configured" };
  const sb = await getServerSupabase();
  if (!sb) return { ok: false, error: "offline" };
  const {
    data: { user },
  } = await sb.auth.getUser();
  if (!user) return { ok: false, error: "not signed in" };

  const { error } = await sb.from("credential_vault").upsert(
    {
      user_id: user.id,
      platform,
      ciphertext: encryptSecret(secret, key),
      masked_hint: maskHint(secret),
      status: "connected",
      expires_at: null,
    },
    { onConflict: "user_id,platform" },
  );
  if (error) return { ok: false, error: error.message };
  return { ok: true };
}

// Masked connection status for the signed-in user (via the SECURITY DEFINER RPC — no ciphertext).
export async function getCredentialStatus(): Promise<CredentialStatus[]> {
  const sb = await getServerSupabase();
  if (!sb) return [];
  const { data, error } = await sb.rpc("credential_status");
  if (error) {
    console.error("[credentials.getCredentialStatus]", error.message);
    return [];
  }
  return (data ?? []) as CredentialStatus[];
}

// Disconnect = hard-delete the credential row (RLS scopes it to the owner).
export async function disconnectCredential(platform: Platform): Promise<{ ok: boolean }> {
  const sb = await getServerSupabase();
  if (!sb) return { ok: false };
  const {
    data: { user },
  } = await sb.auth.getUser();
  if (!user) return { ok: false };
  const { error } = await sb
    .from("credential_vault")
    .delete()
    .eq("user_id", user.id)
    .eq("platform", platform);
  return { ok: !error };
}
