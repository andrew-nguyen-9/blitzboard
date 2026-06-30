"use client";

import { useMemo, useState } from "react";
import WaiverBoard from "./WaiverBoard";
import LeagueSelector, { type LeagueOpt } from "./LeagueSelector";
import { freeAgentsOnWaivers, newsForTargets } from "@/lib/waiverScope";
import type { WaiverTarget, NewsItem } from "@/lib/queries";

// Epic 8 authed waiver surface: a League Selector + an all-NFL ↔ free-agents-on-waivers scope
// toggle wrapping the existing WaiverBoard + NEWS PULSE. Default scope is "free agents", per spec.
export default function WaiverScope({
  leagues,
  targets,
  news,
  rosteredIds,
}: {
  leagues: LeagueOpt[];
  targets: WaiverTarget[];
  news: NewsItem[];
  rosteredIds: string[];
}) {
  const [leagueId, setLeagueId] = useState(leagues[0]?.id ?? "");
  const [scope, setScope] = useState<"league" | "all">("league");

  const shown = useMemo(
    () => (scope === "league" ? freeAgentsOnWaivers(targets, rosteredIds) : targets),
    [scope, targets, rosteredIds],
  );
  const feed = useMemo(
    () => (scope === "league" ? newsForTargets(news, shown) : news),
    [scope, news, shown],
  );
  const scopeLabel = scope === "league" ? "Free agents" : "All NFL";

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-display-md">Waiver Wire</h1>
          <p className="mt-2 text-body text-ink-muted">
            FAAB bids × trending · narrative (news sentiment) blended with behavior (Sleeper adds)
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <LeagueSelector leagues={leagues} value={leagueId} onChange={setLeagueId} />
          <div className="inline-flex rounded-full border border-hairline p-1 text-label" role="group" aria-label="Waiver scope">
            <button type="button" onClick={() => setScope("league")} aria-pressed={scope === "league"}
              className={`rounded-full px-3 py-1 transition ${scope === "league" ? "bg-accent text-bg" : "text-ink-muted hover:text-ink"}`}>
              Free agents
            </button>
            <button type="button" onClick={() => setScope("all")} aria-pressed={scope === "all"}
              className={`rounded-full px-3 py-1 transition ${scope === "all" ? "bg-accent text-bg" : "text-ink-muted hover:text-ink"}`}>
              All NFL
            </button>
          </div>
        </div>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_300px]">
        <WaiverBoard targets={shown} />

        <aside className="glass h-fit p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-label text-ink-muted">NEWS PULSE</h3>
            <span className="text-label text-ink-muted/70">{scopeLabel}</span>
          </div>
          <div className="space-y-3">
            {feed.map((n, i) => (
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
            {!feed.length && (
              <div className="text-label text-ink-muted">
                {scope === "league" ? "No headlines for your free agents right now." : "No news scored yet."}
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
