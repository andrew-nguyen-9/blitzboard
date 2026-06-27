import { signInWithEmail, signInWithGoogle } from "@/app/actions/auth";
import { isSupabaseConfigured } from "@/lib/supabase";

// Next 15: searchParams is async.
export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; check?: string; reset?: string; next?: string }>;
}) {
  const sp = await searchParams;

  if (!isSupabaseConfigured()) {
    return (
      <main>
        <h1>Sign in</h1>
        <p>Sign-in is unavailable offline.</p>
      </main>
    );
  }

  const next = sp.next ?? "/";
  return (
    <main aria-labelledby="login-h">
      <h1 id="login-h">Sign in</h1>
      {sp.error && <p role="alert">{sp.error}</p>}
      {sp.check === "email" && <p role="status">Check your email to confirm your account.</p>}
      {sp.reset === "sent" && <p role="status">If that email exists, a reset link is on its way.</p>}

      <form action={signInWithEmail}>
        <input type="hidden" name="next" value={next} />
        <label htmlFor="email">Email</label>
        <input id="email" name="email" type="email" autoComplete="email" required />
        <label htmlFor="password">Password</label>
        <input id="password" name="password" type="password" autoComplete="current-password" required />
        <button type="submit">Sign in</button>
      </form>

      <form action={signInWithGoogle}>
        <input type="hidden" name="next" value={next} />
        <button type="submit">Continue with Google</button>
      </form>

      <p>
        <a href="/auth/update-password">Forgot password?</a>
      </p>
      <p>
        <a href="/signup">Create an account</a>
      </p>
    </main>
  );
}
