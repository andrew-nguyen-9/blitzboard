"use server";
import { redirect } from "next/navigation";
import { getServerSupabase } from "@/lib/supabase/server";
import { safeNext } from "@/lib/auth/redirect";
import { needsMfaStepUp, verifiedTotpFactor } from "@/lib/auth/mfa";

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export async function signInWithEmail(formData: FormData) {
  const supabase = await getServerSupabase();
  if (!supabase) redirect("/login?error=offline");
  const next = safeNext(String(formData.get("next") ?? "/"));
  const { error } = await supabase.auth.signInWithPassword({
    email: String(formData.get("email") ?? ""),
    password: String(formData.get("password") ?? ""),
  });
  if (error) redirect(`/login?error=${encodeURIComponent(error.message)}`);
  // TOTP step-up: a verified second factor leaves the session at aal1 → challenge before landing.
  const { data: aal } = await supabase.auth.mfa.getAuthenticatorAssuranceLevel();
  if (aal && needsMfaStepUp(aal.currentLevel, aal.nextLevel)) {
    redirect(`/auth/2fa/verify?next=${encodeURIComponent(next)}`);
  }
  redirect(next);
}

export async function signUpWithEmail(formData: FormData) {
  const supabase = await getServerSupabase();
  if (!supabase) redirect("/signup?error=offline");
  const { error } = await supabase.auth.signUp({
    email: String(formData.get("email") ?? ""),
    password: String(formData.get("password") ?? ""),
    options: { emailRedirectTo: `${SITE}/auth/confirm` },
  });
  if (error) redirect(`/signup?error=${encodeURIComponent(error.message)}`);
  redirect("/login?check=email");
}

export async function signInWithGoogle(formData: FormData) {
  const supabase = await getServerSupabase();
  if (!supabase) redirect("/login?error=offline");
  const next = safeNext(String(formData.get("next") ?? "/"));
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: `${SITE}/auth/callback?next=${encodeURIComponent(next)}` },
  });
  if (error || !data?.url) redirect("/login?error=oauth");
  redirect(data.url);
}

export async function signOut() {
  const supabase = await getServerSupabase();
  if (supabase) await supabase.auth.signOut();
  redirect("/login");
}

export async function requestPasswordReset(formData: FormData) {
  const supabase = await getServerSupabase();
  if (!supabase) redirect("/auth/update-password?error=offline");
  await supabase.auth.resetPasswordForEmail(String(formData.get("email") ?? ""), {
    redirectTo: `${SITE}/auth/confirm?next=/auth/update-password`,
  });
  // Always report success — never reveal whether an email exists.
  redirect("/login?reset=sent");
}

export async function updatePassword(formData: FormData) {
  const supabase = await getServerSupabase();
  if (!supabase) redirect("/auth/update-password?error=offline");
  const { error } = await supabase.auth.updateUser({
    password: String(formData.get("password") ?? ""),
  });
  if (error) redirect(`/auth/update-password?error=${encodeURIComponent(error.message)}`);
  redirect("/?passwordUpdated=1");
}

// ── TOTP 2FA (opt-in). Supabase Auth owns the factor + challenge records (auth schema),
// so there is no new app table to add RLS to. SMS is a separate, unconfigured factor (lib/auth/sms.ts).

// Confirm a freshly-enrolled TOTP factor with the first 6-digit code → it becomes verified.
export async function enrollTotpVerify(formData: FormData) {
  const supabase = await getServerSupabase();
  if (!supabase) redirect("/auth/2fa?error=offline");
  const factorId = String(formData.get("factorId") ?? "");
  const code = String(formData.get("code") ?? "").trim();
  const { error } = await supabase.auth.mfa.challengeAndVerify({ factorId, code });
  if (error) redirect(`/auth/2fa?error=${encodeURIComponent(error.message)}`);
  redirect("/auth/2fa?enrolled=1");
}

// Sign-in step-up: verify the current TOTP code against the user's verified factor.
export async function verifyTotp(formData: FormData) {
  const supabase = await getServerSupabase();
  if (!supabase) redirect("/login?error=offline");
  const next = safeNext(String(formData.get("next") ?? "/"));
  const code = String(formData.get("code") ?? "").trim();
  const { data: factors } = await supabase.auth.mfa.listFactors();
  const factor = verifiedTotpFactor(factors?.all);
  if (!factor) redirect(next); // no factor to satisfy → nothing to challenge
  const { error } = await supabase.auth.mfa.challengeAndVerify({ factorId: factor.id, code });
  if (error) {
    redirect(`/auth/2fa/verify?error=${encodeURIComponent(error.message)}&next=${encodeURIComponent(next)}`);
  }
  redirect(next);
}

// Turn off 2FA by unenrolling the TOTP factor.
export async function disableTotp(formData: FormData) {
  const supabase = await getServerSupabase();
  if (!supabase) redirect("/auth/2fa?error=offline");
  const factorId = String(formData.get("factorId") ?? "");
  await supabase.auth.mfa.unenroll({ factorId });
  redirect("/auth/2fa?disabled=1");
}
