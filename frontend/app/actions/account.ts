"use server";

// Account-settings server actions (Epic 8). Change email/password/phone, and delete the account.
// All run through getServerSupabase() (session cookie → RLS). The phone is envelope-encrypted
// server-side before it touches the DB (same vault as signup); the plaintext never persists and
// is never returned. Deletion goes through the delete_my_account() SECURITY DEFINER RPC.
import { redirect } from "next/navigation";
import { getServerSupabase } from "@/lib/supabase/server";
import { loadMasterKey, encryptSecret } from "@/lib/crypto/vault";

const back = (q: string) => redirect(`/account?${q}`);

export async function changeEmail(formData: FormData) {
  const sb = await getServerSupabase();
  if (!sb) back("error=offline");
  const email = String(formData.get("email") ?? "").trim();
  if (!email) back("error=" + encodeURIComponent("Email required"));
  const { error } = await sb!.auth.updateUser({ email });
  if (error) back("error=" + encodeURIComponent(error.message));
  // Supabase emails a confirmation link before the change takes effect.
  back("sent=email");
}

export async function changePassword(formData: FormData) {
  const sb = await getServerSupabase();
  if (!sb) back("error=offline");
  const password = String(formData.get("password") ?? "");
  if (password.length < 8) back("error=" + encodeURIComponent("Password must be at least 8 characters"));
  const { error } = await sb!.auth.updateUser({ password });
  if (error) back("error=" + encodeURIComponent(error.message));
  back("updated=password");
}

export async function changePhone(formData: FormData) {
  const sb = await getServerSupabase();
  if (!sb) back("error=offline");
  const {
    data: { user },
  } = await sb!.auth.getUser();
  if (!user) redirect("/login?next=/account");
  const phone = String(formData.get("phone") ?? "").trim();
  const key = loadMasterKey();
  if (!key) back("error=" + encodeURIComponent("Phone vault not configured"));
  // Empty input clears the stored phone; otherwise store ciphertext only.
  const phone_encrypted = phone ? encryptSecret(phone, key!) : null;
  const { error } = await sb!.from("accounts").update({ phone_encrypted }).eq("user_id", user.id);
  if (error) back("error=" + encodeURIComponent(error.message));
  back("updated=phone");
}

export async function deleteAccount() {
  const sb = await getServerSupabase();
  if (!sb) back("error=offline");
  const { error } = await sb!.rpc("delete_my_account");
  if (error) back("error=" + encodeURIComponent(error.message));
  await sb!.auth.signOut();
  redirect("/login?deleted=1");
}
