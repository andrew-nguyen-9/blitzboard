import { signUpWithEmail } from "@/app/actions/auth";
import { isSupabaseConfigured } from "@/lib/supabase";

// Next 15: searchParams is async.
export default async function SignupPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const sp = await searchParams;

  if (!isSupabaseConfigured()) {
    return (
      <main>
        <h1>Create account</h1>
        <p>Sign-up is unavailable offline.</p>
      </main>
    );
  }

  return (
    <main aria-labelledby="signup-h">
      <h1 id="signup-h">Create account</h1>
      {sp.error && <p role="alert">{sp.error}</p>}
      <form action={signUpWithEmail}>
        <label htmlFor="email">Email</label>
        <input id="email" name="email" type="email" autoComplete="email" required />
        <label htmlFor="password">Password</label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="new-password"
          minLength={8}
          required
        />
        <button type="submit">Sign up</button>
      </form>
      <p>
        <a href="/login">Already have an account?</a>
      </p>
    </main>
  );
}
