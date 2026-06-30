"use client";

import { useState } from "react";
import Link from "next/link";
import { changeEmail, changePassword, changePhone, deleteAccount } from "@/app/actions/account";

const FIELD =
  "w-full max-w-sm rounded-full border border-hairline bg-surface px-4 py-2 text-body text-ink outline-none focus:border-accent";
const BTN = "rounded-full bg-accent px-4 py-2 text-label font-medium text-bg transition hover:opacity-90 disabled:opacity-40";

// Epic 8 Settings: change email/password/phone, manage 2FA, delete account. Each form posts to a
// server action (RLS-scoped); 2FA lives at /auth/2fa (Epic 6) so we link rather than duplicate it.
export default function AccountSettings({
  email,
  twoFactorOn,
  hasPhone,
}: {
  email: string | null;
  twoFactorOn: boolean;
  hasPhone: boolean;
}) {
  const [confirmDelete, setConfirmDelete] = useState(false);

  return (
    <div className="space-y-10">
      <Section title="Email" hint="Changing your email sends a confirmation link to the new address.">
        <form action={changeEmail} className="flex flex-wrap items-center gap-3">
          <input name="email" type="email" required defaultValue={email ?? ""} aria-label="New email" className={FIELD} />
          <button type="submit" className={BTN}>Update email</button>
        </form>
      </Section>

      <Section title="Password">
        <form action={changePassword} className="flex flex-wrap items-center gap-3">
          <input name="password" type="password" required minLength={8} autoComplete="new-password"
            placeholder="New password (min 8 chars)" aria-label="New password" className={FIELD} />
          <button type="submit" className={BTN}>Update password</button>
        </form>
      </Section>

      <Section title="Phone" hint={hasPhone ? "A phone number is on file (stored encrypted). Submit a new one to replace it, or leave blank to remove." : "Stored encrypted; used for account recovery."}>
        <form action={changePhone} className="flex flex-wrap items-center gap-3">
          <input name="phone" type="tel" autoComplete="tel" placeholder="+1 555 555 5555" aria-label="Phone number" className={FIELD} />
          <button type="submit" className={BTN}>Save phone</button>
        </form>
      </Section>

      <Section title="Two-factor authentication" hint={twoFactorOn ? "Authenticator-app 2FA is on." : "Add a second factor with an authenticator app."}>
        <Link href="/auth/2fa" className="inline-block rounded-full border border-hairline px-4 py-2 text-label transition hover:border-accent">
          {twoFactorOn ? "Manage 2FA" : "Turn on 2FA"}
        </Link>
      </Section>

      <Section title="Delete account" hint="Permanently deletes your account and all connected leagues. This cannot be undone.">
        <form action={deleteAccount} className="space-y-3">
          <label className="flex items-center gap-2 text-label text-ink-muted">
            <input type="checkbox" checked={confirmDelete} onChange={(e) => setConfirmDelete(e.target.checked)} />
            I understand this permanently deletes my account.
          </label>
          <button type="submit" disabled={!confirmDelete}
            className="rounded-full border border-red-400/50 px-4 py-2 text-label text-red-400 transition hover:bg-red-400/10 disabled:opacity-40">
            Delete my account
          </button>
        </form>
      </Section>
    </div>
  );
}

function Section({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-hairline/60 pt-6 first:border-0 first:pt-0">
      <h2 className="font-display text-heading">{title}</h2>
      {hint && <p className="mb-3 mt-1 text-label text-ink-muted">{hint}</p>}
      {!hint && <div className="mb-3" />}
      {children}
    </section>
  );
}
