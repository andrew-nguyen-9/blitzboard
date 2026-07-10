import { getPlayerCount } from "@/lib/queries";
import { isSupabaseConfigured } from "@/lib/supabase";
import { Reveal, Magnetic, CountUp } from "@/components/motion";
import { StatCell } from "@/components/StatTable";
import PrefetchLink from "@/components/PrefetchLink";
import HeroHeadline from "@/components/HeroHeadline";
import ScrollCue from "@/components/ScrollCue";
import TiltCard from "@/components/TiltCard";
import Marquee from "@/components/Marquee";
import Tooltip from "@/components/Tooltip";
import BlitzField from "@/components/BlitzField";

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
        {/* Masked neon-grid overlay (war-room-hero template) — layered over the
            hero-media wash, faded to the top-right so it reads as texture behind
            the headline, never behind the body copy. Static/paint-only. */}
        <div className="neon-grid hero-grid" aria-hidden />
        {/* Decorative play-field: a RIGHT-column accent on desktop. Below md the hero
            stacks to one column and the body copy spans full width, so the field's
            X/O marks would sit BEHIND the paragraph — line-art under text reads as
            noise and blends the copy into the background (the reported phone
            readability bug). Hidden on phones; the hero-media wash still carries the
            band. Contrast contract: body text never overlaps a decorative layer
            (NORTH_STAR §Contrast / a11y).
            The wrapper owns visibility+position because BlitzField's own `.bp` rule
            sets `display:block` and — being authored after the utilities layer —
            would beat a `hidden` on the svg itself; on a plain div `hidden` wins. */}
        <div aria-hidden className="hidden md:block absolute inset-y-0 right-0 z-[-1] w-[58%] text-accent/35">
          <BlitzField className="h-full w-full" />
        </div>
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
              <PrefetchLink href="/players" data-cursor="explore"
                className="inline-block rounded-full bg-accent px-6 py-3 font-semibold text-accent-ink transition-shadow hover:shadow-[0_12px_30px_-10px_var(--accent)]">
                Explore players
              </PrefetchLink>
            </Magnetic>
            <Magnetic>
              <PrefetchLink href="/draft" data-cursor="draft"
                className="inline-block rounded-full border border-line px-6 py-3 font-semibold text-ink transition hover:bg-surface-elevated">
                Open the draft board →
              </PrefetchLink>
            </Magnetic>
          </Reveal>

          <ScrollCue target="#trending" />
        </div>
      </section>

      {/* ── BROADCAST TICKER ─────────────────────────────────────────── */}
      <div id="trending" className="mt-16 scroll-mt-24">
        <Marquee items={ticker} duration={38} />
      </div>

      {/* ── SCOREBOARD STAT BAND ─────────────────────────────────────────────
          StatCell gives mono/tabular cells that reserve ch-width for the final
          value, so the CountUp tally never clips or reflows (CLS≈0). */}
      <section className="mt-16 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-line bg-line md:grid-cols-4">
        {[
          { n: count, label: "Players ranked" },
          { n: 12, label: "Teams synced" },
          { n: 0.5, label: "PPR scoring", dec: 1 },
          { n: 2, label: "Value engines" },
        ].map((s, i) => (
          <div key={i} className="bg-bg p-6">
            <StatCell count size="lg" value={s.n} decimals={s.dec ?? 0} label={s.label} />
          </div>
        ))}
      </section>

      {/* ── SECTION GRID ─────────────────────────────────────────────── */}
      <section className="mt-16">
        <Reveal className="mb-6 flex items-baseline justify-between">
          <h2 className="font-display text-display-md">The deck</h2>
          <span className="group relative inline-flex items-center gap-1.5 text-label uppercase text-ink-2">
            six tools, one spine
            <button
              type="button"
              aria-label="What the spine means"
              aria-describedby="deck-spine-tip"
              className="grid h-4 w-4 place-items-center rounded-full border border-line text-[9px] leading-none text-ink-2 transition hover:text-ink focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent"
            >
              i
            </button>
            <Tooltip
              id="deck-spine-tip"
              side="bottom"
              content={
                <span>
                  Every tool runs on one spine —{" "}
                  <b className="text-ink">LeagueRules</b>, <b className="text-ink">Projector</b>,{" "}
                  <b className="text-ink">ValueEngine</b>, and <b className="text-ink">SentimentScorer</b> —
                  so a ranking, a draft pick, and a trade all reflect your league&apos;s exact rules.
                </span>
              }
            />
          </span>
        </Reveal>
        {/* Static responsive grid — 1 col on mobile, 2 on small, 3 on desktop. No
            horizontal scroll: every tool is visible at once. Cards are links, so
            keyboard users tab straight through them in source order. */}
        <div role="group" aria-label="Tools" className="grid grid-cols-1 gap-[var(--space-m)] sm:grid-cols-2 lg:grid-cols-3">
          {tiles.map((t, i) => (
            <TiltCard key={i} href={t.href} label={t.label} desc={t.desc} index={i} />
          ))}
        </div>
      </section>
    </div>
  );
}
