import Link from "next/link";
import { SECTIONS } from "./Nav";

const CREATOR = "https://an9.dev";

// Global footer, rendered once in app/layout.tsx. Theme-aware via the token
// layer. Groups: site-pages nav (reuses Nav's SECTIONS — single source of
// truth), legal/info (About, Privacy, Terms), and the an9.dev creator link.
// No animation here, so nothing to gate for prefers-reduced-motion.
export default function Footer() {
  return (
    <footer className="mt-24 border-t border-line bg-surface-elevated">
      <div className="mx-auto grid max-w-wide gap-10 px-5 py-12 md:grid-cols-[1.6fr_1fr_1fr] md:px-8">
        <div>
          <p className="font-display text-heading text-ink">BlitzBoard</p>
          <p className="mt-3 max-w-xs text-body text-ink-2">
            Your draft war room — player intelligence, draft assistance, trade
            &amp; waiver optimization, and live news-sentiment trending.
          </p>
          <p className="mt-4 text-label text-ink-2">
            Data from Sleeper, nflverse &amp; ESPN · Built with Next.js + Supabase
          </p>
        </div>

        <FooterGroup title="Sections">
          {SECTIONS.map((s) => (
            <FooterLink key={s.href} href={s.href}>
              {s.label}
            </FooterLink>
          ))}
        </FooterGroup>

        <FooterGroup title="Info">
          <FooterLink href="/about">About &amp; methodology</FooterLink>
          <FooterLink href="/privacy">Privacy</FooterLink>
          <FooterLink href="/terms">Terms</FooterLink>
          <FooterLink href={CREATOR} external>
            an9.dev
          </FooterLink>
        </FooterGroup>
      </div>

      <div className="border-t border-line">
        <p className="mx-auto max-w-wide px-5 py-5 text-label text-ink-2 md:px-8">
          © {new Date().getFullYear()} BlitzBoard · Made by{" "}
          <a href={CREATOR} target="_blank" rel="noreferrer" className="text-accent underline underline-offset-2">
            an9.dev
          </a>
        </p>
      </div>
    </footer>
  );
}

function FooterGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-3 text-label uppercase tracking-[0.12em] text-ink-2">{title}</p>
      <ul className="space-y-2.5">{children}</ul>
    </div>
  );
}

function FooterLink({
  href,
  external,
  children,
}: {
  href: string;
  external?: boolean;
  children: React.ReactNode;
}) {
  const cls = "text-body text-ink-2 transition-colors hover:text-ink";
  return (
    <li>
      {external ? (
        <a href={href} target="_blank" rel="noreferrer" className={cls}>
          {children} ↗
        </a>
      ) : (
        <Link href={href} className={cls}>
          {children}
        </Link>
      )}
    </li>
  );
}
