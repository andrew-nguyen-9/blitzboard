import EmptyState from "@/components/EmptyState";
import WaiverBoard from "@/components/WaiverBoard";
import { getWaiverTargets, getRecentNews } from "@/lib/queries";
import { isSupabaseConfigured } from "@/lib/supabase";

export const metadata = { title: "Waiver Wire" };
export const dynamic = "force-dynamic"; // trending refreshes every 30 min — never serve stale

// P4: FAAB bid recommendations driven by the blended trending signal
// (news sentiment ⊕ Sleeper add/drop), with a live news-sentiment feed.
export default async function WaiversPage() {
  const live = isSupabaseConfigured();
  const [targets, news] = live
    ? await Promise.all([getWaiverTargets(60), getRecentNews(12)])
    : [[], []];

  if (!targets.length) {
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
      <h1 className="font-display text-display-md">Waiver Wire</h1>
      <p className="mt-2 text-body text-ink-muted">
        FAAB bids × trending · narrative (news sentiment) blended with behavior (Sleeper adds)
      </p>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_300px]">
        <WaiverBoard targets={targets} />

        {/* live news-sentiment feed (broadcast lower-third vibe) */}
        <aside className="glass h-fit p-4">
          <h3 className="mb-3 text-label text-ink-muted">NEWS PULSE</h3>
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
