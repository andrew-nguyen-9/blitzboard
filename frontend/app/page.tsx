import Link from "next/link";
import { getPlayerCount } from "@/lib/queries";
import { isSupabaseConfigured } from "@/lib/supabase";

export default async function Home() {
  const count = await getPlayerCount();
  const live = isSupabaseConfigured();

  const tiles = [
    { href: "/players", label: "Player Explorer", desc: "Search the universe, ranked by value", ready: true },
    { href: "/draft", label: "Draft Board", desc: "Live ESPN-sync + offline manual board", ready: false },
    { href: "/league", label: "League Overview", desc: "Smores 2025 — rosters, standings", ready: false },
    { href: "/waivers", label: "Waiver Wire", desc: "FAAB bids × trending sentiment", ready: false },
    { href: "/trades", label: "Trade Optimizer", desc: "Pareto-improving swaps", ready: false },
  ];

  return (
    <div className="py-16 md:py-24">
      {/* Hero — P6 gets the cinematic creative-dev treatment; this is the shell. */}
      <section className="animate-fade-up">
        <div className="mb-4 inline-block rounded-full border border-hairline px-3 py-1 text-label text-accent">
          {live ? `${count.toLocaleString()} players in the universe` : "Offline mode — empty states"}
        </div>
        <h1 className="font-display text-display-xl">
          Your fantasy<br />
          <span className="text-accent">war room.</span>
        </h1>
        <p className="mt-6 max-w-2xl text-body-lg text-ink-muted">
          Player intelligence, draft assistance, and trade &amp; waiver optimization —
          tuned to your league&apos;s exact rules. Superflex-aware, VORP and Monte&nbsp;Carlo,
          on one board.
        </p>
        <div className="mt-8 flex gap-3">
          <Link href="/players" className="rounded-full bg-accent px-5 py-2.5 font-semibold text-bg transition hover:opacity-90">
            Explore players
          </Link>
          <Link href="/draft" className="rounded-full border border-hairline px-5 py-2.5 font-semibold text-ink transition hover:bg-surface-elevated">
            Draft board →
          </Link>
        </div>
      </section>

      {/* Section grid */}
      <section className="mt-20 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {tiles.map((t) => (
          <Link
            key={t.href}
            href={t.href}
            className="glass group p-6 transition hover:-translate-y-0.5"
            style={{ boxShadow: "var(--glow)" }}
          >
            <div className="flex items-center justify-between">
              <h3 className="font-display text-heading">{t.label}</h3>
              {!t.ready && <span className="text-label text-accent/70">soon</span>}
            </div>
            <p className="mt-2 text-body text-ink-muted">{t.desc}</p>
            <span className="mt-4 inline-block text-label text-accent opacity-0 transition group-hover:opacity-100">
              Open →
            </span>
          </Link>
        ))}
      </section>
    </div>
  );
}
