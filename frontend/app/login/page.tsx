import { signInWithEmail, signInWithGoogle } from "@/app/actions/auth";
import { isSupabaseConfigured } from "@/lib/supabase";
import BlueprintField from "@/components/BlueprintField";

// Brand panel — reused on both the offline and live branches. Motion lives entirely
// inside BlueprintField (static-SVG, prefers-reduced-motion / data-motion safe).
function BrandPanel() {
  return (
    <aside className="relative isolate hidden overflow-hidden bg-surface md:flex md:flex-col md:justify-end md:p-10 lg:p-14">
      <BlueprintField className="absolute inset-0 z-[-1] h-full w-full text-accent/30" />
      <div className="relative max-w-sm">
        <p className="text-label uppercase tracking-wide text-ink-muted">BlitzBoard</p>
        <h2 className="mt-3 font-display text-display-xl leading-[0.9]">
          Your fantasy<br />
          <span className="text-accent">war room.</span>
        </h2>
        <p className="mt-6 text-body-lg text-ink-muted">
          Superflex VORP, live draft sync, and trade &amp; waiver optimization — tuned to
          your league&apos;s exact rules.
        </p>
      </div>
    </aside>
  );
}

const inputCls =
  "mt-1.5 w-full rounded-full border border-hairline bg-surface px-4 py-2.5 text-body text-ink outline-none transition focus:border-accent";
const primaryBtn =
  "w-full rounded-full bg-accent px-6 py-3 font-semibold text-bg transition hover:opacity-90";
const ghostBtn =
  "w-full rounded-full border border-hairline bg-surface px-6 py-3 font-semibold text-ink transition hover:border-accent";

// Auth redirects carry short error codes; render them as human copy (unknown codes — e.g. a raw
// provider/Supabase message — pass through unchanged so nothing is swallowed).
const ERROR_COPY: Record<string, string> = {
  oauth: "Google sign-in is unavailable right now. Try email, or contact support.",
  auth: "We couldn't complete sign-in. Please try again.",
  offline: "Sign-in is unavailable offline.",
};
function friendlyError(code: string): string {
  return ERROR_COPY[code] ?? code;
}

// Next 15: searchParams is async.
export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; check?: string; reset?: string; next?: string }>;
}) {
  const sp = await searchParams;

  if (!isSupabaseConfigured()) {
    return (
      <main className="grid min-h-[80vh] md:grid-cols-2" aria-labelledby="login-h">
        <BrandPanel />
        <section className="flex flex-col justify-center px-6 py-16 md:px-10 lg:px-16">
          <div className="mx-auto w-full max-w-sm">
            <h1 id="login-h" className="font-display text-heading">Sign in</h1>
            <p className="mt-3 text-body text-ink-muted">Sign-in is unavailable offline.</p>
          </div>
        </section>
      </main>
    );
  }

  const next = sp.next ?? "/";
  return (
    <main className="grid min-h-[80vh] md:grid-cols-2" aria-labelledby="login-h">
      <BrandPanel />
      <section className="flex flex-col justify-center px-6 py-16 md:px-10 lg:px-16">
        <div className="mx-auto w-full max-w-sm">
          <h1 id="login-h" className="font-display text-heading">Sign in</h1>
          <p className="mb-6 mt-2 text-body text-ink-muted">Welcome back to the war room.</p>

          {sp.error && (
            <p role="alert" className="mb-4 rounded-2xl border border-hairline bg-surface px-4 py-3 text-label text-[#E0573A]">
              {friendlyError(sp.error)}
            </p>
          )}
          {sp.check === "email" && (
            <p role="status" className="mb-4 rounded-2xl border border-hairline bg-surface px-4 py-3 text-label text-ink-muted">
              Check your email to confirm your account.
            </p>
          )}
          {sp.reset === "sent" && (
            <p role="status" className="mb-4 rounded-2xl border border-hairline bg-surface px-4 py-3 text-label text-ink-muted">
              If that email exists, a reset link is on its way.
            </p>
          )}

          <form action={signInWithEmail} className="space-y-4">
            <input type="hidden" name="next" value={next} />
            <div>
              <label htmlFor="email" className="text-label text-ink-muted">Email</label>
              <input id="email" name="email" type="email" autoComplete="email" required className={inputCls} />
            </div>
            <div>
              <label htmlFor="password" className="text-label text-ink-muted">Password</label>
              <input id="password" name="password" type="password" autoComplete="current-password" required className={inputCls} />
            </div>
            <button type="submit" className={primaryBtn}>Sign in</button>
          </form>

          <div className="my-5 flex items-center gap-3 text-label text-ink-muted">
            <span className="h-px flex-1 bg-hairline" />
            or
            <span className="h-px flex-1 bg-hairline" />
          </div>

          <form action={signInWithGoogle}>
            <input type="hidden" name="next" value={next} />
            <button type="submit" className={ghostBtn}>Continue with Google</button>
          </form>

          <div className="mt-6 flex items-center justify-between text-label text-ink-muted">
            <a href="/auth/update-password" className="underline transition hover:text-accent">Forgot password?</a>
            <a href="/signup" className="underline transition hover:text-accent">Create an account</a>
          </div>
        </div>
      </section>
    </main>
  );
}
