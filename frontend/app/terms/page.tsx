import type { Metadata } from "next";

export const metadata: Metadata = { title: "Terms" };

export default function TermsPage() {
  return (
    <article className="mx-auto max-w-3xl px-5 py-20 md:px-8">
      <h1 className="font-display text-display-md text-ink">Terms</h1>
      <div className="mt-8 space-y-5 text-body-lg leading-relaxed text-ink-2">
        <p>
          BlitzBoard is provided as-is, for informational and entertainment
          purposes. Projections, player values, and rankings are model output
          built on third-party data and may be incomplete, estimated, or out of
          date — always confirm details before making roster decisions. Fantasy
          football is volatile; no projection is a guarantee.
        </p>
        <p>
          Player names, team names, and logos are the property of their
          respective owners. Player, roster, and news data is surfaced under the
          terms of its source providers (Sleeper, nflverse, and ESPN); BlitzBoard
          claims no ownership over them.
        </p>
        <p>
          By using the site you agree that the project and its creator are not
          liable for decisions made based on this data.
        </p>
      </div>
    </article>
  );
}
