"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { MappedPick } from "@/lib/sleeperDraft";
import type { LeagueConfig } from "@/lib/leagueConfig";
import { fillRoster } from "@/lib/draft";

// Every team's current lineup at a glance (#1). Starters slot into the league's
// roster shape, extras fall to the bench, and each team name is inline-editable
// so a manual drafter can label rivals ("Trade target", "QB-needy", …).
export default function AllTeamsBoard({
  config,
  picks,
  mySlot,
  onRename,
}: {
  config: LeagueConfig;
  picks: MappedPick[];
  mySlot: number;
  onRename: (slot: number, name: string) => void;
}) {
  const byTeam = useMemo(() => {
    const m = new Map<number, MappedPick["player"][]>();
    for (let s = 1; s <= config.numTeams; s++) m.set(s, []);
    for (const pk of picks) m.get(pk.team)?.push(pk.player);
    return m;
  }, [picks, config.numTeams]);

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: config.numTeams }, (_, i) => i + 1).map((slot) => {
        const tp = byTeam.get(slot) ?? [];
        const fill = fillRoster(tp, config.rosterSlots);
        const team = config.teams.find((t) => t.slot === slot);
        return (
          <TeamCard
            key={slot}
            slot={slot}
            name={team?.name ?? `Team ${slot}`}
            owner={team?.owner}
            isMine={slot === mySlot}
            fill={fill}
            benchSize={config.benchSize}
            onRename={(n) => onRename(slot, n)}
          />
        );
      })}
    </div>
  );
}

function TeamCard({
  slot,
  name,
  owner,
  isMine,
  fill,
  benchSize,
  onRename,
}: {
  slot: number;
  name: string;
  owner?: string;
  isMine: boolean;
  fill: ReturnType<typeof fillRoster>;
  benchSize: number;
  onRename: (n: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(name);

  function commit() {
    const v = draft.trim();
    if (v && v !== name) onRename(v);
    else setDraft(name);
    setEditing(false);
  }

  return (
    <div className={`glass p-4 ${isMine ? "ring-1 ring-accent" : ""}`}>
      <div className="mb-3 flex items-center gap-2">
        <span className="font-mono text-label text-ink-muted">#{slot}</span>
        {editing ? (
          <input
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
              if (e.key === "Enter") commit();
              if (e.key === "Escape") {
                setDraft(name);
                setEditing(false);
              }
            }}
            className="min-w-0 flex-1 rounded border border-hairline bg-surface px-2 py-1 text-body outline-none focus:border-accent"
          />
        ) : (
          <button
            onClick={() => {
              setDraft(name);
              setEditing(true);
            }}
            className="group flex min-w-0 flex-1 items-center gap-1.5 text-left"
            title="Rename team"
          >
            <span className="truncate font-display text-heading">{name}</span>
            <span className="text-label text-ink-muted opacity-0 transition group-hover:opacity-100">✎</span>
          </button>
        )}
        {isMine && <span className="rounded-full bg-accent px-2 py-0.5 text-label text-bg">you</span>}
      </div>
      {owner && <div className="mb-2 -mt-2 text-label text-ink-muted/70">@{owner}</div>}

      <div className="space-y-1 text-label">
        {fill.starters.map((s, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="w-10 shrink-0 text-ink-muted">{s.slot}</span>
            {s.player ? (
              <>
                <Link href={`/players/${s.player.id}`} className="min-w-0 flex-1 truncate transition hover:text-accent">
                  {s.player.full_name}
                </Link>
                <span className="shrink-0 text-ink-muted/70">{s.player.nfl_team ?? "FA"}</span>
              </>
            ) : (
              <span className="flex-1 text-accent/80">— empty —</span>
            )}
          </div>
        ))}
      </div>

      <div className="mt-3 border-t border-hairline pt-2">
        <div className="mb-1 text-label text-ink-muted">
          BENCH {fill.bench.length}/{benchSize}
        </div>
        <div className="flex flex-wrap gap-1">
          {fill.bench.map((p) => (
            <Link
              key={p.id}
              href={`/players/${p.id}`}
              className="rounded-full border border-hairline px-2 py-0.5 text-label text-ink-muted transition hover:text-accent"
            >
              {p.full_name.split(" ").slice(-1)[0]} <span className="text-ink-muted/60">{p.position}</span>
            </Link>
          ))}
          {!fill.bench.length && <span className="text-label text-ink-muted/60">—</span>}
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between border-t border-hairline pt-2 text-label">
        <span className="text-ink-muted">Proj starters</span>
        <span className="font-mono text-ink">{fill.projectedPoints.toFixed(0)}</span>
      </div>
    </div>
  );
}
