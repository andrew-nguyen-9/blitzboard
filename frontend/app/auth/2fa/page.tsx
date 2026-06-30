import { redirect } from "next/navigation";
import { getServerSupabase } from "@/lib/supabase/server";
import { verifiedTotpFactor } from "@/lib/auth/mfa";
import { enrollTotpVerify, disableTotp } from "@/app/actions/auth";

// Opt-in management for authenticator-app (TOTP) 2FA. Signed-in users land here from the
// header profile icon. Supabase Auth stores the factor itself — no app table, no migration.
export default async function TwoFactorPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; enrolled?: string; disabled?: string }>;
}) {
  const sp = await searchParams;
  const sb = await getServerSupabase();
  if (!sb) {
    return (
      <main aria-labelledby="tfa-h">
        <h1 id="tfa-h">Two-factor authentication</h1>
        <p>Unavailable offline.</p>
      </main>
    );
  }
  const {
    data: { user },
  } = await sb.auth.getUser();
  if (!user) redirect("/login?next=/auth/2fa");

  const { data: factors } = await sb.auth.mfa.listFactors();
  const active = verifiedTotpFactor(factors?.all);

  if (active) {
    return (
      <main aria-labelledby="tfa-h">
        <h1 id="tfa-h">Two-factor authentication</h1>
        {sp.enrolled && <p role="status">Two-factor authentication is now on.</p>}
        <p>
          Authenticator-app 2FA is <strong>enabled</strong> for your account.
        </p>
        <form action={disableTotp}>
          <input type="hidden" name="factorId" value={active.id} />
          <button type="submit">Turn off 2FA</button>
        </form>
      </main>
    );
  }

  // No verified factor → clear any stale unverified TOTP factors, then enroll a fresh one to show.
  // ponytail: re-enrolls on every render of the unverified state (cleaned above); fine for a
  // setup page. Move enrollment behind a "Start setup" action if churn ever matters.
  for (const f of factors?.all ?? []) {
    if (f.factor_type === "totp" && f.status === "unverified") {
      await sb.auth.mfa.unenroll({ factorId: f.id });
    }
  }
  const { data: enrolled, error } = await sb.auth.mfa.enroll({ factorType: "totp" });
  if (error || !enrolled) {
    return (
      <main aria-labelledby="tfa-h">
        <h1 id="tfa-h">Set up two-factor authentication</h1>
        <p role="alert">Couldn&apos;t start setup right now. Please try again.</p>
      </main>
    );
  }
  const qrSrc = `data:image/svg+xml;utf-8,${encodeURIComponent(enrolled.totp.qr_code)}`;
  return (
    <main aria-labelledby="tfa-h">
      <h1 id="tfa-h">Set up two-factor authentication</h1>
      {sp.error && <p role="alert">{sp.error}</p>}
      {sp.disabled && <p role="status">Two-factor authentication is now off.</p>}
      <p>
        Scan this QR code with an authenticator app (or enter the key manually), then enter the
        6-digit code to confirm.
      </p>
      {/* eslint-disable-next-line @next/next/no-img-element -- inline SVG data URI from Supabase, not an optimizable asset */}
      <img src={qrSrc} alt="QR code to add BlitzBoard to your authenticator app" width={200} height={200} />
      <p>
        Manual key: <code>{enrolled.totp.secret}</code>
      </p>
      <form action={enrollTotpVerify}>
        <input type="hidden" name="factorId" value={enrolled.id} />
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
        <button type="submit">Confirm and enable</button>
      </form>
    </main>
  );
}
