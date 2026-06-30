import type { Metadata } from "next";

export const metadata: Metadata = { title: "Privacy" };

export default function PrivacyPage() {
  return (
    <article className="mx-auto max-w-3xl px-5 py-20 md:px-8">
      <h1 className="font-display text-display-md text-ink">Privacy</h1>
      <div className="mt-8 space-y-5 text-body-lg leading-relaxed text-ink-2">
        <p>
          BlitzBoard is an independent project. You can use most of the site
          without an account. Your theme and accessibility preferences are stored
          only in your browser&apos;s localStorage — they never leave your device
          and are not sent to any server.
        </p>
        <p>
          If you create an account, we store the email address and authentication
          details needed to sign you in (handled by Supabase Auth), plus the
          league and roster data you connect or import. That data is isolated to
          your account and is never shared with other users or sold. You can
          request deletion of your account and its data at any time.
        </p>
        <p>
          Player, roster, and news data is aggregated from public sources
          (Sleeper, nflverse, and ESPN). Anonymous, aggregate performance metrics
          (Web Vitals) may be collected to keep the site fast; they are not tied
          to any individual.
        </p>
        <p>
          Questions? Reach out via{" "}
          <a href="https://an9.dev" target="_blank" rel="noreferrer" className="text-accent hover:underline">
            an9.dev
          </a>
          .
        </p>
      </div>
    </article>
  );
}
