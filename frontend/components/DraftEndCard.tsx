"use client";

import Link from "next/link";
import { useMemo } from "react";
import type { MappedPick } from "@/lib/sleeperDraft";
import type { LeagueConfig } from "@/lib/leagueConfig";
import { analyzeDraft } from "@/lib/analysis";

// Shown the moment a draft fills up (#4). Celebrates the finish, surfaces the
// user's grade + finish, their best pick, and a one-tap route to full analysis.
export default function DraftEndCard({
  picks,
  config,
  mySlot,
  onViewAnalysis,
  onDismiss,
}: {
  picks: MappedPick[];
  config: LeagueConfig;
  mySlot: number;
  onViewAnalysis: () => void;
  onDismiss: () => void;
}) {
  const { mine, topPlayer, total } = useMemo(() => {
    const a = analyzeDraft(picks, config);
    const me = a.teams.find((t) => t.slot === mySlot);
    return { mine: me, topPlayer: me?.keyPlayers[0] ?? null, total: a.teams.length };
  }, [picks, config, mySlot]);

  return (
    <div className="glass mb-6 overflow-hidden" style={{ boxShadow: "var(--glow)" }}>
      <div className="border-b border-hairline bg-accent-soft px-6 py-5">
        <div className="text-label text-ink-muted">DRAFT COMPLETE</div>
        <h2 className="font-display text-display-md">That&apos;s a wrap 🏈</h2>
        <p className="mt-1 text-body text-ink-muted">
          {config.name} · {config.numTeams} teams · {config.scoringLabel}
        </p>
      </div>
      <div className="grid gap-4 p-6 sm:grid-cols-3">
        <Stat label="Your grade" value={mine?.grade ?? "—"} accent />
        <Stat label="Projected finish" value={mine ? `#${mine.rank} of ${total}` : "—"} />
        <Stat label="Proj. starters" value={mine ? mine.projectedPoints.toFixed(0) : "—"} />
      </div>
      {topPlayer && (
        <div className="px-6 pb-4 text-body text-ink-muted">
          Cornerstone pick:{" "}
          <Link href={`/players/${topPlayer.id}`} className="text-ink transition hover:text-accent">
            {topPlayer.full_name}
          </Link>{" "}
          ({topPlayer.position}). {mine?.notes[0]}
        </div>
      )}
      <div className="flex flex-wrap gap-2 px-6 pb-6">
        <button
          onClick={onViewAnalysis}
          className="rounded-full bg-accent px-5 py-2 text-label font-medium text-bg transition hover:opacity-90"
        >
          See full analysis →
        </button>
        <Link
          href="/draft/analysis"
          className="rounded-full border border-hairline px-5 py-2 text-label transition hover:bg-surface-elevated"
        >
          Open analysis page
        </Link>
        <button
          onClick={onDismiss}
          className="ml-auto rounded-full border border-hairline px-4 py-2 text-label text-ink-muted transition hover:bg-surface-elevated"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="glass p-4 text-center">
      <div className={`font-display text-display-md ${accent ? "text-accent" : ""}`}>{value}</div>
      <div className="mt-1 text-label text-ink-muted">{label}</div>
    </div>
  );
}
