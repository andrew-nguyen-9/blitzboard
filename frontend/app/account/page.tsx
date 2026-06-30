import { redirect } from "next/navigation";
import { getServerSupabase } from "@/lib/supabase/server";
import { verifiedTotpFactor } from "@/lib/auth/mfa";
import AccountSettings from "@/components/AccountSettings";

export const metadata = { title: "Account Settings" };
export const dynamic = "force-dynamic";

// Epic 8 Settings surface. Session-gated. Surfaces a status banner from the action redirect
// query (?updated=, ?sent=, ?error=) and renders the settings forms.
export default async function AccountPage({
  searchParams,
}: {
  searchParams: Promise<{ updated?: string; sent?: string; error?: string }>;
}) {
  const sp = await searchParams;
  const sb = await getServerSupabase();
  if (!sb) redirect("/login?next=/account");
  const {
    data: { user },
  } = await sb.auth.getUser();
  if (!user) redirect("/login?next=/account");

  const { data: factors } = await sb.auth.mfa.listFactors();
  const twoFactorOn = Boolean(verifiedTotpFactor(factors?.all));
  const { data: account } = await sb
    .from("accounts")
    .select("phone_encrypted")
    .eq("user_id", user.id)
    .maybeSingle();

  const banner =
    sp.error ? { tone: "error" as const, msg: sp.error }
    : sp.updated === "password" ? { tone: "ok" as const, msg: "Password updated." }
    : sp.updated === "phone" ? { tone: "ok" as const, msg: "Phone saved." }
    : sp.sent === "email" ? { tone: "ok" as const, msg: "Check your new email to confirm the change." }
    : null;

  return (
    <div className="py-12">
      <div className="mb-8">
        <h1 className="font-display text-display-md">Account Settings</h1>
        <p className="mt-2 text-body text-ink-muted">{user.email}</p>
      </div>
      {banner && (
        <p role="status" className={`mb-6 rounded-xl border px-4 py-3 text-label ${banner.tone === "error" ? "border-red-400/40 text-red-400" : "border-accent/40 text-accent"}`}>
          {banner.msg}
        </p>
      )}
      <AccountSettings email={user.email ?? null} twoFactorOn={twoFactorOn} hasPhone={Boolean((account as any)?.phone_encrypted)} />
    </div>
  );
}
