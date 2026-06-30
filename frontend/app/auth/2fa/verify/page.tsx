import { redirect } from "next/navigation";
import { getServerSupabase } from "@/lib/supabase/server";
import { safeNext } from "@/lib/auth/redirect";
import { verifyTotp } from "@/app/actions/auth";

// Sign-in step-up: after a correct password, a user with 2FA enabled lands here to enter
// their current authenticator code before the session is fully trusted (aal1 → aal2).
export default async function TwoFactorVerifyPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; next?: string }>;
}) {
  const sp = await searchParams;
  const next = safeNext(sp.next);
  const sb = await getServerSupabase();
  if (!sb) redirect("/login");
  const {
    data: { user },
  } = await sb.auth.getUser();
  if (!user) redirect(`/login?next=${encodeURIComponent(next)}`);

  return (
    <main aria-labelledby="tfa-v-h">
      <h1 id="tfa-v-h">Enter your authentication code</h1>
      {sp.error && <p role="alert">{sp.error}</p>}
      <p>Open your authenticator app and enter the current 6-digit code.</p>
      <form action={verifyTotp}>
        <input type="hidden" name="next" value={next} />
        <label htmlFor="code">6-digit code</label>
        <input
          id="code"
          name="code"
          inputMode="numeric"
          autoComplete="one-time-code"
          pattern="[0-9]*"
          maxLength={6}
          required
        />
        <button type="submit">Verify</button>
      </form>
    </main>
  );
}
