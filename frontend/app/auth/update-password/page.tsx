import { requestPasswordReset, updatePassword } from "@/app/actions/auth";

// Two flows on one page: request a reset link (top), and set a new password after
// arriving via that link (bottom, once the recovery session is established).
export default async function UpdatePasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const sp = await searchParams;
  return (
    <main aria-labelledby="pw-h">
      <h1 id="pw-h">Reset password</h1>
      {sp.error && <p role="alert">{sp.error}</p>}

      <form action={requestPasswordReset}>
        <label htmlFor="reset-email">Email</label>
        <input id="reset-email" name="email" type="email" autoComplete="email" required />
        <button type="submit">Send reset link</button>
      </form>

      <form action={updatePassword}>
        <label htmlFor="new-password">New password (after clicking the email link)</label>
        <input
          id="new-password"
          name="password"
          type="password"
          autoComplete="new-password"
          minLength={8}
          required
        />
        <button type="submit">Set new password</button>
      </form>
    </main>
  );
}
