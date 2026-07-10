"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { PlayerWithValue } from "@/lib/types";
import type { LeagueTeam } from "@/lib/queries";
import { findTrades, bestTradesForRoster, rosterValue, type TradeProposal, type BestTrade } from "@/lib/trade";

type Mode = "league" | "partner";

export default function TradeFinder({
  teams,
  players,
}: {
  teams: LeagueTeam[];
  players: Record<string, PlayerWithValue>;
}) {
  const [myId, setMyId] = useState(teams[0]?.id ?? "");
  const [targetId, setTargetId] = useState(teams[1]?.id ?? "");
  const [mode, setMode] = useState<Mode>("league");

  const roster = (t?: LeagueTeam) =>
    (t?.player_ids ?? []).map((id) => players[id]).filter(Boolean) as PlayerWithValue[];

  const myTeam = teams.find((t) => t.id === myId);
  const targetTeam = teams.find((t) => t.id === targetId);
  const mine = roster(myTeam);
  const theirs = roster(targetTeam);

  // Pairwise: Pareto swaps against one chosen partner. League: the user's BEST trades
  // scanned across every OTHER team, ranked by their own lineup gain. Only rosters in
  // `teams` (server-scoped to the authed user's league) are ever searched.
  const proposals = useMemo(
    () => (myId && targetId && myId !== targetId ? findTrades(mine, theirs, { limit: 20 }) : []),
    [myId, targetId, mine, theirs],
  );
  const best = useMemo<BestTrade[]>(() => {
    if (!myId) return [];
    const opponents = teams
      .filter((t) => t.id !== myId)
      .map((t) => ({ id: t.id, name: t.team_name ?? "Team", players: roster(t) }));
    return bestTradesForRoster(mine, opponents, { limit: 20 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [myId, mine, teams, players]);

  const showLeague = mode === "league";
  const cards = showLeague ? best : proposals;

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2 text-label">
        {(["league", "partner"] as Mode[]).map((m) => (
          <button
            key={m}
            type="button"
            aria-pressed={mode === m}
            onClick={() => setMode(m)}
            className={`rounded-full px-3 py-1 transition ${mode === m ? "bg-accent text-bg" : "border border-hairline text-ink-muted hover:text-ink"}`}
          >
            {m === "league" ? "Best across league" : "Vs. one team"}
          </button>
        ))}
      </div>

      <div className="mb-6 flex flex-wrap items-end gap-4">
        <label className="text-label text-ink-muted">
          My team
          <select value={myId} onChange={(e) => setMyId(e.target.value)}
            className="mt-1 block w-56 rounded-lg border border-hairline bg-surface px-3 py-2 text-body text-ink">
            {teams.map((t) => <option key={t.id} value={t.id}>{t.team_name}</option>)}
          </select>
        </label>
        {!showLeague && (
          <>
            <span className="pb-2 text-ink-muted">↔</span>
            <label className="text-label text-ink-muted">
              Trade with
              <select value={targetId} onChange={(e) => setTargetId(e.target.value)}
                className="mt-1 block w-56 rounded-lg border border-hairline bg-surface px-3 py-2 text-body text-ink">
                {teams.filter((t) => t.id !== myId).map((t) => <option key={t.id} value={t.id}>{t.team_name}</option>)}
              </select>
            </label>
          </>
        )}
        <div className="ml-auto text-label text-ink-muted">
          your lineup value <span className="font-mono text-ink">{rosterValue(mine).toFixed(0)}</span>
          {!showLeague && (
            <> · them <span className="font-mono text-ink">{rosterValue(theirs).toFixed(0)}</span></>
          )}
        </div>
      </div>

      {!cards.length ? (
        <div className="glass p-10 text-center text-body text-ink-muted">
          {showLeague
            ? "No mutually-beneficial trades found across your league right now. Pareto-improving deals need a partner with complementary positional needs."
            : "No mutually-beneficial trades found between these two rosters. Try a different partner — Pareto-improving deals need complementary positional needs."}
        </div>
      ) : (
        <div className="space-y-3">
          {cards.map((p, i) => (
            <ProposalCard key={i} p={p} partner={showLeague ? (p as BestTrade).partnerName : undefined} />
          ))}
        </div>
      )}
    </div>
  );
}

function ProposalCard({ p, partner }: { p: TradeProposal; partner?: string }) {
  const fairnessPct = Math.round(p.fairness * 100);
  const fairColor = fairnessPct >= 75 ? "var(--accent)" : fairnessPct >= 50 ? "#E0A33A" : "#E0573A";
  return (
    <div className="glass p-5">
      {partner && (
        <div className="mb-3 text-label text-ink-muted">
          with <span className="text-ink">{partner}</span>
        </div>
      )}
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
