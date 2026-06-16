"use client";

import { useMemo } from "react";
import Link from "next/link";
import type { MappedPick } from "@/lib/sleeperDraft";
import type { LeagueConfig } from "@/lib/leagueConfig";
import { analyzeDraft, type TeamAnalysis } from "@/lib/analysis";

const GRADE_COLOR: Record<string, string> = {
  "A+": "#33D17A", A: "#33D17A", "B+": "#8cff5a", B: "#8cff5a",
  "C+": "#E0A33A", C: "#E0A33A", D: "#E0573A", F: "#E0573A",
};

// Shared analysis surface (#4): team grades, projected points, who matters, and
// the value board (steals/reaches). Used both as the in-room "Analysis" tab and
// the standalone /draft/analysis page.
export default function DraftAnalysis({
  picks,
  config,
  mySlot,
}: {
  picks: MappedPick[];
  config: LeagueConfig;
  mySlot: number;
}) {
  const a = useMemo(() => analyzeDraft(picks, config), [picks, config]);

  if (!picks.length) {
    return (
      <div className="glass p-10 text-center text-body text-ink-muted">
        No picks yet — draft some players, then come back for grades, projections, and strategy reads.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <div className="glass px-4 py-2 text-label">
          <span className="text-ink-muted">League avg starters </span>
          <span className="font-mono text-ink">{a.leagueAvgPoints.toFixed(0)}</span>
        </div>
        <div className="glass px-4 py-2 text-label">
          <span className="text-ink-muted">Picks </span>
          <span className="font-mono text-ink">{picks.length}/{a.totalSpots}</span>
        </div>
        <div className="glass px-4 py-2 text-label">
          {a.complete ? <span className="text-accent">Draft complete ✓</span> : <span className="text-ink-muted">In progress</span>}
        </div>
      </div>

      {/* power rankings */}
      <div>
        <h3 className="mb-3 font-display text-heading">Power Rankings</h3>
        <div className="space-y-3">
          {a.teams.map((t) => (
            <TeamRow key={t.slot} t={t} mine={t.slot === mySlot} max={a.teams[0]?.projectedPoints || 1} />
          ))}
        </div>
      </div>

      {/* value board */}
      <div className="grid gap-4 md:grid-cols-2">
        <ValueList title="Biggest Steals" subtitle="fell past ADP" events={a.steals} positive />
        <ValueList title="Biggest Reaches" subtitle="drafted ahead of ADP" events={a.reaches} positive={false} />
      </div>
    </div>
  );
}

function TeamRow({ t, mine, max }: { t: TeamAnalysis; mine: boolean; max: number }) {
  const w = Math.max(4, (t.projectedPoints / max) * 100);
  return (
    <div className={`glass p-4 ${mine ? "ring-1 ring-accent" : ""}`}>
      <div className="flex flex-wrap items-center gap-3">
        <span className="w-6 text-center font-mono text-ink-muted">{t.rank}</span>
        <span
          className="grid h-9 w-9 shrink-0 place-items-center rounded-lg font-display text-heading"
          style={{ background: (GRADE_COLOR[t.grade] ?? "#8A93A6") + "22", color: GRADE_COLOR[t.grade] ?? "#8A93A6" }}
        >
          {t.grade}
        </span>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="truncate font-display text-heading">{t.name}</span>
            {mine && <span className="rounded-full bg-accent px-2 py-0.5 text-label text-bg">you</span>}
          </div>
          <div className="text-label text-ink-muted">{t.strategy}</div>
        </div>
        <div className="ml-auto text-right">
          <div className="font-mono text-heading text-accent">{t.projectedPoints.toFixed(0)}</div>
          <div className="text-label text-ink-muted">proj starters</div>
        </div>
      </div>

      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-hairline">
        <div className="h-full rounded-full bg-accent" style={{ width: `${w}%` }} />
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_1fr]">
        <div>
          <div className="mb-1 text-label text-ink-muted">PLAYERS THAT MATTER</div>
          <div className="flex flex-wrap gap-1">
            {t.keyPlayers.map((p) => (
              <Link
                key={p.id}
                href={`/players/${p.id}`}
                className="rounded-full border border-hairline px-2 py-0.5 text-label transition hover:text-accent"
              >
                {p.full_name} <span className="text-ink-muted/70">{p.position}</span>
              </Link>
            ))}
            {!t.keyPlayers.length && <span className="text-label text-ink-muted/60">—</span>}
          </div>
        </div>
        <div>
          <div className="mb-1 text-label text-ink-muted">STRATEGY READ</div>
          <ul className="space-y-0.5 text-label text-ink-muted">
            {t.notes.length ? t.notes.map((n, i) => <li key={i}>· {n}</li>) : <li>· Standard balanced build.</li>}
          </ul>
        </div>
      </div>
    </div>
  );
}

function ValueList({
  title,
  subtitle,
  events,
  positive,
}: {
  title: string;
  subtitle: string;
  events: ReturnType<typeof analyzeDraft>["steals"];
  positive: boolean;
}) {
  return (
    <div className="glass p-4">
      <h3 className="font-display text-heading">{title}</h3>
      <p className="mb-3 text-label text-ink-muted">{subtitle}</p>
      <div className="space-y-1.5">
        {events.map((e) => (
          <div key={`${e.player.id}-${e.pickNo}`} className="flex items-center gap-2 text-label">
            <Link href={`/players/${e.player.id}`} className="min-w-0 flex-1 truncate transition hover:text-accent">
              {e.player.full_name} <span className="text-ink-muted/70">{e.player.position}</span>
            </Link>
            <span className="truncate text-ink-muted">{e.teamName}</span>
            <span className="font-mono text-ink-muted">@{e.pickNo}</span>
            <span className={`w-12 text-right font-mono ${positive ? "text-accent" : "text-red-400"}`}>
              {e.delta > 0 ? "+" : ""}
              {e.delta.toFixed(0)}
            </span>
          </div>
        ))}
        {!events.length && <div className="text-label text-ink-muted/60">No ADP data yet.</div>}
      </div>
    </div>
  );
}
