import Link from "next/link";
import ThemeToggle from "./ThemeToggle";
import A11ySettings from "./A11ySettings";

// The seven sections. `ready: false` routes render a "coming soon" empty state
// (graceful degradation, inherited pattern) until their phase ships.
export const SECTIONS = [
  { href: "/", label: "Home", ready: true },
  { href: "/players", label: "Players", ready: true },
  { href: "/draft", label: "Draft", ready: true },
  { href: "/league", label: "League", ready: true },
  { href: "/waivers", label: "Waivers", ready: true },
  { href: "/trades", label: "Trades", ready: true },
] as const;

export default function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b border-hairline bg-bg/80 backdrop-blur">
      <nav className="mx-auto flex max-w-wide items-center justify-between px-5 py-3 md:px-8">
        <Link href="/" className="font-display text-heading font-bold tracking-tight">
          <span className="text-accent">▲</span> FFDT
        </Link>
        <ul className="hidden items-center gap-1 md:flex">
          {SECTIONS.slice(1).map((s) => (
            <li key={s.href}>
              <Link
                href={s.href}
                className="rounded-full px-3 py-1.5 text-label text-ink-muted transition hover:bg-surface-elevated hover:text-ink"
              >
                {s.label}
                {!s.ready && <span className="ml-1 text-[10px] text-accent/70">soon</span>}
              </Link>
            </li>
          ))}
        </ul>
        <div className="flex items-center gap-2">
          <A11ySettings />
          <ThemeToggle />
        </div>
      </nav>
    </header>
  );
}
