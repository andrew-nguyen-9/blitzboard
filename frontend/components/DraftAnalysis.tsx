"use client";

import { useMemo } from "react";
import Link from "next/link";
import type { MappedPick } from "@/lib/sleeperDraft";
import type { LeagueConfig } from "@/lib/leagueConfig";
import type { PlayerWithValue } from "@/lib/types";
import { analyzeDraft, type TeamAnalysis } from "@/lib/analysis";

const GRADE_COLOR: Record<string, string> = {
  "A+": "#33D17A", A: "#33D17A", "B+": "#8cff5a", B: "#8cff5a",
  "C+": "#E0A33A", C: "#E0A33A", D: "#E0573A", F: "#E0573A",
};

// Weeks where 3+ starters share a bye — a real lineup hole worth flagging (4.4 / byes from 4.5).
function byeStacks(starters: { player: PlayerWithValue | null }[]): { week: number; names: string[] }[] {
  const byWeek = new Map<number, string[]>();
  for (const s of starters) {
    const w = s.player?.bye_week;
    if (w != null) byWeek.set(w, [...(byWeek.get(w) ?? []), s.player!.full_name]);
  }
  return [...byWeek.entries()]
    .filter(([, names]) => names.length >= 3)
    .map(([week, names]) => ({ week, names }))
    .sort((x, y) => y.names.length - x.names.length);
}

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

      {/* your team — the full detail view (4.4) */}
      {(() => {
        const mine = a.teams.find((t) => t.slot === mySlot);
        return mine && mine.picks.length ? <MyTeam t={mine} /> : null;
      })()}

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

      {t.posStrength.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {t.posStrength.map((s) => (
            <div key={s.pos} className="flex items-center gap-1.5 text-label" title={`${s.pos}: ${(s.rankPct * 100).toFixed(0)}th pct in league`}>
              <span className="w-7 text-ink-muted">{s.pos}</span>
              <div className="h-1.5 w-16 overflow-hidden rounded-full bg-hairline">
                <div className="h-full rounded-full" style={{ width: `${Math.max(6, s.rankPct * 100)}%`, background: s.rankPct >= 0.66 ? "#33D17A" : s.rankPct >= 0.33 ? "#E0A33A" : "#E0573A" }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Your-team deep dive (4.4): the full starting lineup by slot, the bench, projected starter
// points, open needs, and any bye-week stacks the byes import (4.5) now surfaces.
function MyTeam({ t }: { t: TeamAnalysis }) {
  const stacks = byeStacks(t.roster.starters);
  return (
    <div className="glass p-5 ring-1 ring-accent">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h3 className="font-display text-heading">Your team — {t.name}</h3>
        <span className="rounded-full bg-accent px-2 py-0.5 text-label text-bg">grade {t.grade}</span>
        <span className="ml-auto text-right">
          <span className="font-mono text-heading text-accent">{t.projectedPoints.toFixed(0)}</span>
          <span className="ml-1 text-label text-ink-muted">proj starters</span>
        </span>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <div>
          <div className="mb-2 text-label text-ink-muted">STARTING LINEUP</div>
          <div className="space-y-1 text-body">
            {t.roster.starters.map((s, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="w-12 shrink-0 text-label text-ink-muted">{s.slot}</span>
                {s.player ? (
                  <>
                    <Link href={`/players/${s.player.id}`} className="min-w-0 flex-1 truncate transition hover:text-accent">{s.player.full_name}</Link>
                    <span className="shrink-0 text-label text-ink-muted/70">{s.player.position === "DEF" ? "DST" : s.player.position}</span>
                    <span className="w-8 shrink-0 text-right text-label text-ink-muted/70" title="bye week">{s.player.bye_week ?? "—"}</span>
                  </>
                ) : (
                  <span className="flex-1 text-accent">— need —</span>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <div className="mb-2 text-label text-ink-muted">BENCH ({t.roster.bench.length})</div>
            <div className="flex flex-wrap gap-1">
              {t.roster.bench.length ? t.roster.bench.map((p) => (
                <Link key={p.id} href={`/players/${p.id}`} className="rounded-full border border-hairline px-2 py-0.5 text-label transition hover:text-accent">
                  {p.full_name} <span className="text-ink-muted/70">{p.position === "DEF" ? "DST" : p.position}</span>
                </Link>
              )) : <span className="text-label text-ink-muted/60">No bench yet.</span>}
            </div>
          </div>

          {t.roster.needs.length > 0 && (
            <div>
              <div className="mb-1 text-label text-ink-muted">OPEN STARTERS</div>
              <div className="text-label text-[#E0573A]">{t.roster.needs.join(" · ")}</div>
            </div>
          )}

          <div>
            <div className="mb-1 text-label text-ink-muted">BYE-WEEK STACKS</div>
            {stacks.length ? (
              <ul className="space-y-0.5 text-label text-ink-muted">
                {stacks.map((s) => (
                  <li key={s.week}><span className="text-[#E0A33A]">Wk {s.week}</span>: {s.names.length} starters off ({s.names.join(", ")})</li>
                ))}
              </ul>
            ) : (
              <div className="text-label text-ink-muted/70">No bye weeks stack 3+ starters — clean schedule.</div>
            )}
          </div>
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
