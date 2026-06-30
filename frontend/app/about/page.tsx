import type { Metadata } from "next";

export const metadata: Metadata = { title: "About" };

export default function AboutPage() {
  return (
    <article className="mx-auto max-w-3xl px-5 py-20 md:px-8">
      <h1 className="font-display text-display-md text-ink">About BlitzBoard</h1>
      <div className="mt-8 space-y-5 text-body-lg leading-relaxed text-ink-2">
        <p>
          BlitzBoard is an independent NFL fantasy war room. It pulls player,
          roster, and news data from public sources (Sleeper, nflverse, and
          ESPN) and turns it into draft, trade, and waiver decisions. The numbers
          you see come from two models that we run ahead of time, not from a
          black box. Here is how each one works.
        </p>

        <h2 className="pt-4 font-display text-heading text-ink">VORP — value over replacement</h2>
        <p>
          A player&apos;s raw projection only matters relative to what you could
          get for free. VORP measures each player against the{" "}
          <em>replacement level</em> at their position — the projection of the
          best player who would still be sitting on the waiver wire in a league
          of your size and starting requirements. A quarterback projected for 280
          points is only worth the gap between 280 and the replacement-level QB,
          because that replacement is the realistic alternative if you pass.
          Computing VORP this way makes positions comparable on one scale:
          scarcity, not just point totals, drives a player&apos;s draft value.
        </p>

        <h2 className="pt-4 font-display text-heading text-ink">
          Monte Carlo — simulated seasons
        </h2>
        <p>
          A single projection hides the range of outcomes a player can actually
          produce. The Monte Carlo model simulates a full season many times over,
          re-rolling each player&apos;s week-to-week usage, injury exposure, and
          scoring variance on every run. The spread of those simulated seasons
          becomes a season-long distribution per player rather than one number.
        </p>
        <p>
          From that distribution we read off the values on the player pages: a{" "}
          <strong>floor</strong> (the 10th-percentile season — a realistic bad
          year), a <strong>ceiling</strong> (the 90th-percentile season — a
          realistic great one), and <strong>boom / bust probabilities</strong>,
          the share of simulated seasons that land far above or far below the
          player&apos;s expected total. Two players with the same projection can
          have very different floors and ceilings; that difference is what the
          simulation surfaces.
        </p>

        <h2 className="pt-4 font-display text-heading text-ink">How we check it</h2>
        <p>
          Both models are validated out-of-sample: we run them against historical
          seasons and compare their output to what actually happened, rather than
          fitting to the same data we report on. Fantasy football is genuinely
          volatile season to season, so treat every projection as a distribution,
          not a promise. BlitzBoard is a decision aid — the final call on your
          roster is always yours.
        </p>

        <p className="pt-4 text-body text-ink-2">
          Built by{" "}
          <a href="https://an9.dev" target="_blank" rel="noreferrer" className="text-accent hover:underline">
            an9.dev
          </a>
          .
        </p>
      </div>
    </article>
  );
}
