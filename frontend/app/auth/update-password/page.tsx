import { requestPasswordReset, updatePassword } from "@/app/actions/auth";

// Auth-UI styling composes the base design-system tokens already used by the sign-in page
// (cite F1 NORTH_STAR §Contrast / a11y — no globals/tailwind edits here; E10 owns those).
// Two flows on one page: request a reset link (top), and set a new password after arriving via
// that link (bottom, once the recovery session is established). Single-column card is fluid from
// 375px up (px-6, max-w-sm) — the prior unstyled markup rendered edge-to-edge and broke formatting.
const inputCls =
  "mt-1.5 w-full rounded-full border border-hairline bg-surface px-4 py-2.5 text-body text-ink outline-none transition focus:border-accent";
const primaryBtn =
  "w-full rounded-full bg-accent px-6 py-3 font-semibold text-bg transition hover:opacity-90";

export default async function UpdatePasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const sp = await searchParams;
  return (
    <main className="flex min-h-[80vh] flex-col justify-center px-6 py-16" aria-labelledby="pw-h">
      <div className="mx-auto w-full max-w-sm">
        <h1 id="pw-h" className="font-display text-heading">Reset password</h1>
        <p className="mb-6 mt-2 text-body text-ink-muted">
          Send yourself a reset link, then set a new password from the emailed link.
        </p>

        {sp.error && (
          <p role="alert" className="mb-4 rounded-2xl border border-hairline bg-surface px-4 py-3 text-label text-[#E0573A]">
            {sp.error}
          </p>
        )}

        <form action={requestPasswordReset} className="space-y-4">
          <div>
            <label htmlFor="reset-email" className="text-label text-ink-muted">Email</label>
            <input id="reset-email" name="email" type="email" autoComplete="email" required className={inputCls} />
          </div>
          <button type="submit" className={primaryBtn}>Send reset link</button>
        </form>

        <div className="my-5 flex items-center gap-3 text-label text-ink-muted">
          <span className="h-px flex-1 bg-hairline" />
          then
          <span className="h-px flex-1 bg-hairline" />
        </div>

        <form action={updatePassword} className="space-y-4">
          <div>
            <label htmlFor="new-password" className="text-label text-ink-muted">New password</label>
            <input
              id="new-password"
              name="password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              required
              className={inputCls}
            />
            <p className="mt-1.5 text-label text-ink-muted">
              Available after you open the emailed reset link.
            </p>
          </div>
          <button type="submit" className={primaryBtn}>Set new password</button>
        </form>

        <div className="mt-6 text-label text-ink-muted">
          <a href="/login" className="underline transition hover:text-accent">Back to sign in</a>
        </div>
      </div>
    </main>
  );
}
