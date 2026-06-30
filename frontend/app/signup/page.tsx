import SignupForm from "@/components/SignupForm";
import { isSupabaseConfigured } from "@/lib/supabase";

export default function SignupPage() {
  if (!isSupabaseConfigured()) {
    return (
      <main className="mx-auto max-w-md px-4 py-16" aria-labelledby="signup-h">
        <h1 id="signup-h" className="font-display text-heading">Create account</h1>
        <p className="mt-3 text-body text-ink-muted">Sign-up is unavailable offline.</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-md px-4 py-16" aria-labelledby="signup-h">
      <h1 id="signup-h" className="font-display text-heading">Create account</h1>
      <p className="mb-6 mt-2 text-body text-ink-muted">Join the war room.</p>
      <SignupForm />
      <p className="mt-6 text-label text-ink-muted">
        <a href="/login" className="underline transition hover:text-accent">
          Already have an account?
        </a>
      </p>
    </main>
  );
}
