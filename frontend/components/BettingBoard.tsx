"use client";

import { useMemo, useState } from "react";
import { biggestBets, topTotals, chalkParlay, type Game } from "@/app/betting/aggregate";

const TABS = ["Biggest bets", "Shootouts", "Parlay"] as const;
type Tab = (typeof TABS)[number];

const pct = (p: number) => `${Math.round(p * 100)}%`;
const ml = (m: number | null) => (m == null ? "—" : m > 0 ? `+${m}` : `${m}`);
const kickoff = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" }) : "TBD";

export default function BettingBoard({ games }: { games: Game[] }) {
  const [tab, setTab] = useState<Tab>("Biggest bets");

  const big = useMemo(() => biggestBets(games), [games]);
  const overs = useMemo(() => topTotals(games), [games]);
  const parlay = useMemo(() => chalkParlay(games, 3), [games]);

  return (
    <div className="min-w-0">
      <div className="mb-4 flex flex-wrap gap-1">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-full px-3 py-1.5 text-label transition ${
              tab === t ? "bg-accent text-bg" : "border border-hairline text-ink-muted hover:text-ink"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Biggest bets" && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {big.map((g, i) => (
            // F1 §Primitives → Elevation/edge: the single strongest play gets the
            // lit "neon-edge" rim; the rest stay on plain glass (ration the glow).
            <div key={g.id} className={`p-4 ${i === 0 ? "glass neon-edge" : "glass"}`}>
              <div className="flex items-center justify-between text-label text-ink-muted">
                <span>{kickoff(g.commenceTime)}</span>
                <span className="font-mono">{ml(g.favMoneyline)}</span>
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className={`font-display text-display-sm ${i === 0 ? "neon-text" : ""}`}>{g.favorite}</span>
                <span className="text-label text-ink-muted">−{g.spread}</span>
              </div>
              <div className="mt-1 text-label text-ink-muted">
                over {g.underdog} · win prob <span className="font-mono text-ink">{pct(g.favWinProb)}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "Shootouts" && (
        <div className="glass overflow-x-auto">
          <table className="w-full min-w-[32rem] text-left text-body">
            <thead className="border-b border-hairline text-label text-ink-muted">
              <tr>
                <th className="px-4 py-3">Game</th>
                <th className="px-4 py-3">Kickoff</th>
                <th className="px-4 py-3 text-right">Total (O/U)</th>
                <th className="px-4 py-3 text-right">Favorite</th>
              </tr>
            </thead>
            <tbody>
              {overs.map((g) => (
                <tr key={g.id} className="border-b border-hairline/60 transition hover:bg-surface-elevated">
                  <td className="px-4 py-3 font-medium">{g.away} @ {g.home}</td>
                  <td className="px-4 py-3 text-ink-muted">{kickoff(g.commenceTime)}</td>
                  <td className="px-4 py-3 text-right font-mono">{g.total ?? "—"}</td>
                  <td className="px-4 py-3 text-right text-ink-muted">{g.favorite} −{g.spread}</td>
                </tr>
              ))}
              {!overs.length && (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-label text-ink-muted">No totals posted.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {tab === "Parlay" && (
        <div className="glass mx-auto max-w-md p-6 text-center" style={{ boxShadow: "var(--glow)" }}>
          {parlay ? (
            <>
              <div className="text-label text-ink-muted">Suggested {parlay.label} parlay</div>
              <div className="mt-2 font-display text-display-md neon-text">{ml(parlay.american)}</div>
              <div className="mt-1 text-label text-ink-muted">
                combined implied prob <span className="font-mono text-ink">{pct(parlay.combinedProb)}</span>
              </div>
              <ul className="mt-4 space-y-2 text-left">
                {parlay.legs.map((l, i) => (
                  <li key={i} className="flex items-center justify-between border-b border-hairline/60 pb-2 last:border-0">
                    <span>{l.pick}</span>
                    <span className="font-mono text-ink-muted">{ml(l.moneyline)}</span>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <div className="text-body text-ink-muted">Not enough games on the board for a parlay.</div>
          )}
        </div>
      )}

      <p className="mt-4 text-label text-ink-muted">
        Consensus lines (median spread/total, mean moneyline) across US books. The free tier exposes no
        popularity data, so &ldquo;biggest / most-backed&rdquo; is proxied by market conviction (implied win
        probability). For entertainment only — bet responsibly.
      </p>
    </div>
  );
}
