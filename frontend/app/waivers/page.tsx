import EmptyState from "@/components/EmptyState";
import WaiverBoard from "@/components/WaiverBoard";
import { getWaiverTargets, getRecentNews } from "@/lib/queries";
import { isSupabaseConfigured } from "@/lib/supabase";

export const metadata = { title: "Waiver Wire" };
export const dynamic = "force-dynamic"; // trending refreshes every 30 min — never serve stale

// P4 / Epic 9 (unauth): FAAB bid recommendations driven by the blended trending
// signal (news sentiment ⊕ Sleeper add/drop), with a live RSS news-sentiment feed.
// Scope here is fixed to **all NFL players** (no league context). Epic 8 (auth)
// layers a League Selector + an all-NFL ↔ league/team scope toggle on top of this.
export default async function WaiversPage() {
  const live = isSupabaseConfigured();
  const [targets, news] = live
    ? await Promise.all([getWaiverTargets(60), getRecentNews(12)])
    : [[], []];

  // All-NFL feed: render whenever there's a board OR an RSS feed to show. Only the
  // truly-empty (offline / pipeline never ran) case falls back to the empty state —
  // a sparse trending table must never hide the all-NFL RSS feed.
  if (!targets.length && !news.length) {
    return (
      <EmptyState title="Waiver Wire Tool" phase="Phase 4">
        {live
          ? "No trending data yet. Run pipeline/news_sentiment.py to score news + Sleeper add/drop velocity."
          : "Connect Supabase and run the sentiment pipeline to surface waiver targets and FAAB bids."}
      </EmptyState>
    );
  }

  return (
    <div className="py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-display-md">Waiver Wire</h1>
          <p className="mt-2 text-body text-ink-muted">
            FAAB bids × trending · narrative (news sentiment) blended with behavior (Sleeper adds)
          </p>
        </div>
        {/* ponytail: unauth scope is fixed to all-NFL. Epic 8 (auth) replaces this
            chip with a <LeagueSelector/> + an all-NFL ↔ league/team scope toggle. */}
        <span className="rounded-full border border-hairline px-3 py-1.5 text-label text-ink-muted">
          Scope: <span className="text-ink">All NFL</span>
        </span>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_300px]">
        <WaiverBoard targets={targets} />

        {/* live RSS news-sentiment feed (broadcast lower-third vibe), all-NFL scope */}
        <aside className="glass h-fit p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-label text-ink-muted">NEWS PULSE</h3>
            <span className="text-label text-ink-muted/70">All NFL</span>
          </div>
          <div className="space-y-3">
            {news.map((n, i) => (
              <a key={i} href={n.url ?? "#"} target="_blank" rel="noreferrer"
                className="block border-b border-hairline/60 pb-3 last:border-0 transition hover:opacity-80">
                <div className="flex items-start gap-2">
                  <span className="mt-1 h-2 w-2 shrink-0 rounded-full"
                    style={{ background: (n.sentiment ?? 0) >= 0 ? "var(--accent)" : "#E0573A" }} />
                  <div>
                    <div className="text-body leading-snug">{n.title}</div>
                    <div className="mt-1 flex items-center gap-2 text-label text-ink-muted">
                      <span>{n.source}</span>
                      {n.injury_flag && <span className="text-red-400">injury</span>}
                      {n.opportunity_flag && <span className="text-accent">opportunity</span>}
                    </div>
                  </div>
                </div>
              </a>
            ))}
            {!news.length && <div className="text-label text-ink-muted">No news scored yet.</div>}
          </div>
        </aside>
      </div>
    </div>
  );
}
