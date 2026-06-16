"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { PlayerWithValue } from "@/lib/types";
import type { LeagueTeam } from "@/lib/queries";
import { findTrades, rosterValue, type TradeProposal } from "@/lib/trade";

export default function TradeFinder({
  teams,
  players,
}: {
  teams: LeagueTeam[];
  players: Record<string, PlayerWithValue>;
}) {
  const [myId, setMyId] = useState(teams[0]?.id ?? "");
  const [targetId, setTargetId] = useState(teams[1]?.id ?? "");

  const roster = (t?: LeagueTeam) =>
    (t?.player_ids ?? []).map((id) => players[id]).filter(Boolean) as PlayerWithValue[];

  const myTeam = teams.find((t) => t.id === myId);
  const targetTeam = teams.find((t) => t.id === targetId);
  const mine = roster(myTeam);
  const theirs = roster(targetTeam);

  const proposals = useMemo(
    () => (myId && targetId && myId !== targetId ? findTrades(mine, theirs, { limit: 20 }) : []),
    [myId, targetId, mine, theirs],
  );

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end gap-4">
        <label className="text-label text-ink-muted">
          My team
          <select value={myId} onChange={(e) => setMyId(e.target.value)}
            className="mt-1 block w-56 rounded-lg border border-hairline bg-surface px-3 py-2 text-body text-ink">
            {teams.map((t) => <option key={t.id} value={t.id}>{t.team_name}</option>)}
          </select>
        </label>
        <span className="pb-2 text-ink-muted">↔</span>
        <label className="text-label text-ink-muted">
          Trade with
          <select value={targetId} onChange={(e) => setTargetId(e.target.value)}
            className="mt-1 block w-56 rounded-lg border border-hairline bg-surface px-3 py-2 text-body text-ink">
            {teams.filter((t) => t.id !== myId).map((t) => <option key={t.id} value={t.id}>{t.team_name}</option>)}
          </select>
        </label>
        <div className="ml-auto text-label text-ink-muted">
          lineup value — you <span className="font-mono text-ink">{rosterValue(mine).toFixed(0)}</span> ·
          them <span className="font-mono text-ink">{rosterValue(theirs).toFixed(0)}</span>
        </div>
      </div>

      {!proposals.length ? (
        <div className="glass p-10 text-center text-body text-ink-muted">
          No mutually-beneficial trades found between these two rosters. Try a different partner —
          Pareto-improving deals need complementary positional needs.
        </div>
      ) : (
        <div className="space-y-3">
          {proposals.map((p, i) => <ProposalCard key={i} p={p} />)}
        </div>
      )}
    </div>
  );
}

function ProposalCard({ p }: { p: TradeProposal }) {
  const fairnessPct = Math.round(p.fairness * 100);
  const fairColor = fairnessPct >= 75 ? "var(--accent)" : fairnessPct >= 50 ? "#E0A33A" : "#E0573A";
  return (
    <div className="glass p-5">
      <div className="grid items-center gap-4 md:grid-cols-[1fr_auto_1fr]">
        <div>
          <div className="mb-1 text-label text-ink-muted">YOU GIVE</div>
          <Pills ps={p.give} />
        </div>
        <div className="text-center text-2xl text-ink-muted">⇄</div>
        <div>
          <div className="mb-1 text-label text-ink-muted">YOU GET</div>
          <Pills ps={p.get} />
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-1 border-t border-hairline pt-3 text-label">
        <span>your lineup <span className="font-mono text-accent">+{p.myDelta.toFixed(1)}</span></span>
        <span>their lineup <span className="font-mono text-ink-muted">+{p.theirDelta.toFixed(1)}</span></span>
        <span className="ml-auto">fairness <span className="font-mono" style={{ color: fairColor }}>{fairnessPct}%</span></span>
      </div>
    </div>
  );
}

function Pills({ ps }: { ps: PlayerWithValue[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {ps.map((p) => (
        <Link key={p.id} href={`/players/${p.id}`}
          className="rounded-full border border-hairline bg-surface px-2.5 py-1 text-label transition hover:border-accent">
          {p.full_name} <span className="text-ink-muted">{p.position}</span>
          {p.value?.vor != null && <span className="ml-1 font-mono text-accent">{p.value.vor.toFixed(0)}</span>}
        </Link>
      ))}
    </div>
  );
}
