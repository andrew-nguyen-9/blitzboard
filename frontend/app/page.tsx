import Link from "next/link";
import { getPlayerCount } from "@/lib/queries";
import { isSupabaseConfigured } from "@/lib/supabase";
import { Reveal, Magnetic, CountUp } from "@/components/motion";
import HeroHeadline from "@/components/HeroHeadline";
import TiltCard from "@/components/TiltCard";
import Marquee from "@/components/Marquee";

export const dynamic = "force-dynamic";

export default async function Home() {
  const count = await getPlayerCount();
  const live = isSupabaseConfigured();

  const tiles = [
    { href: "/players", label: "Player Explorer", desc: "Search the universe, ranked by superflex value" },
    { href: "/draft", label: "Draft Board", desc: "Live ESPN + Sleeper sync, offline manual, draft AI" },
    { href: "/league", label: "League Overview", desc: "Example Superflex League — rosters, standings, settings" },
    { href: "/waivers", label: "Waiver Wire", desc: "FAAB bids × news-sentiment trending" },
    { href: "/trades", label: "Trade Optimizer", desc: "Pareto-improving, need-aware swaps" },
    { href: "/players", label: "Value Engines", desc: "VORP now · Monte Carlo distributions next" },
  ];

  const ticker = [
    `${count.toLocaleString()} players`, "Superflex-aware VORP", "Monte Carlo (soon)",
    "Live Sleeper + ESPN sync", "FAAB bid optimizer", "News-sentiment trending",
    "Half-PPR · 12-team", "Distance-based K · tiered D/ST",
  ];

  return (
    <div className="pb-24">
      {/* ── HERO ─────────────────────────────────────────────────────────────
          Full-bleed band: .full-bleed breaks out of the padded <main>; the media
          layer's wash meets the viewport edge (no container seam). The headline
          is static, server-rendered text — it is the LCP element and never waits
          on JS. The mask-wipe (.hero-media) and kinetic word reveal are CSS-only,
          so they run deterministically without blocking first paint. */}
      <section className="full-bleed relative isolate overflow-hidden">
        <div className="hero-media" aria-hidden />
        <div className="relative mx-auto max-w-wide px-5 pb-20 pt-20 md:px-8 md:pb-28 md:pt-28">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-line bg-surface/60 px-3 py-1.5 text-label uppercase text-ink-2 backdrop-blur">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
            </span>
            {live ? <><CountUp to={count} /> players in the universe</> : "Offline mode"}
          </div>

          <HeroHeadline
            className="font-display text-display-xl leading-[0.9]"
            lines={[{ text: "Your fantasy" }, { text: "war room.", accent: true }]}
          />

          <Reveal delay={0.2} className="mt-7 max-w-2xl">
            <p className="text-body-lg text-ink-1">
              Player intelligence, live draft assistance, and trade &amp; waiver optimization —
              tuned to your league&apos;s exact rules. Superflex VORP, Monte&nbsp;Carlo distributions,
              news-sentiment trending. One broadcast deck.
            </p>
          </Reveal>

          <Reveal delay={0.3} className="mt-9 flex flex-wrap gap-3">
            <Magnetic>
              <Link href="/players" data-cursor="explore"
                className="inline-block rounded-full bg-accent px-6 py-3 font-semibold text-accent-ink transition hover:brightness-110">
                Explore players
              </Link>
            </Magnetic>
            <Magnetic>
              <Link href="/draft" data-cursor="draft"
                className="inline-block rounded-full border border-line px-6 py-3 font-semibold text-ink transition hover:bg-surface-elevated">
                Open the draft board →
              </Link>
            </Magnetic>
          </Reveal>
        </div>
      </section>

      {/* ── BROADCAST TICKER ─────────────────────────────────────────── */}
      <div className="mt-16">
        <Marquee items={ticker} duration={38} />
      </div>

      {/* ── SCOREBOARD STAT BAND ─────────────────────────────────────── */}
      <section className="mt-16 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-line bg-line md:grid-cols-4">
        {[
          { n: count, label: "Players ranked", suffix: "" },
          { n: 12, label: "Teams synced", suffix: "" },
          { n: 0.5, label: "PPR scoring", suffix: "", dec: 1 },
          { n: 2, label: "Value engines", suffix: "" },
        ].map((s, i) => (
          <div key={i} className="bg-bg p-6">
            <div className="font-scoreboard text-score-xl text-[clamp(2.5rem,6vw,4.5rem)] leading-none text-ink">
              <CountUp to={s.n} decimals={s.dec ?? 0} suffix={s.suffix} />
            </div>
            <div className="mt-1 text-label uppercase text-ink-2">{s.label}</div>
          </div>
        ))}
      </section>

      {/* ── SECTION GRID ─────────────────────────────────────────────── */}
      <section className="mt-16">
        <Reveal className="mb-6 flex items-baseline justify-between">
          <h2 className="font-display text-display-md">The deck</h2>
          <span className="text-label uppercase text-ink-2">seven tools, one spine</span>
        </Reveal>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {tiles.map((t, i) => (
            <TiltCard key={i} href={t.href} label={t.label} desc={t.desc} index={i} />
          ))}
        </div>
      </section>
    </div>
  );
}
