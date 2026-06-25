"use server";
import { redirect } from "next/navigation";
import { getServerSupabase } from "@/lib/supabase/server";
import { safeNext } from "@/lib/auth/redirect";

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
