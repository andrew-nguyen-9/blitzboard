"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { WaiverTarget } from "@/lib/queries";

const POSITIONS = ["ALL", "QB", "RB", "WR", "TE", "K", "DEF"] as const;

// FAAB bid recommendation from the blended trend score (D9: this league is FAAB,
// so we recommend a BID, not a priority). Injured players → hold.
function faab(trend: number, injury: string | null, budget: number) {
  if (injury && /out|ir|doubtful/i.test(injury)) return { pct: 0, label: "hold", dollars: 0 };
  if (trend <= 0) return { pct: 0, label: "stream", dollars: 0 };
  const pct = Math.max(1, Math.min(40, Math.round(trend * 38)));
  const tier = pct >= 25 ? "priority" : pct >= 15 ? "strong" : pct >= 5 ? "moderate" : "speculative";
  return { pct, label: tier, dollars: Math.max(1, Math.round((budget * pct) / 100)) };
}

const TIER_COLOR: Record<string, string> = {
  priority: "var(--accent)", strong: "#5AB8FF", moderate: "#E0A33A",
  speculative: "#8A93A6", stream: "#8A93A6", hold: "#E0573A",
};

export default function WaiverBoard({ targets }: { targets: WaiverTarget[] }) {
  const [pos, setPos] = useState<(typeof POSITIONS)[number]>("ALL");
  const [budget, setBudget] = useState(100);

  const rows = useMemo(() => {
    let r = targets;
    if (pos !== "ALL") r = r.filter((t) => (t.position ?? "") === pos);
    return r;
  }, [targets, pos]);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap gap-1">
          {POSITIONS.map((p) => (
            <button key={p} onClick={() => setPos(p)}
              className={`rounded-full px-3 py-1.5 text-label transition ${pos === p ? "bg-accent text-bg" : "border border-hairline text-ink-muted hover:text-ink"}`}>
              {p}
            </button>
          ))}
        </div>
        <label className="ml-auto flex items-center gap-2 text-label text-ink-muted">
          FAAB remaining
          <span className="text-ink">$</span>
          <input type="number" min={1} max={1000} value={budget} onChange={(e) => setBudget(+e.target.value)}
            className="w-20 rounded border border-hairline bg-surface px-2 py-1 text-right font-mono text-ink" />
        </label>
      </div>

      <div className="glass overflow-hidden">
        <table className="w-full text-left text-body">
          <thead className="border-b border-hairline text-label text-ink-muted">
            <tr>
              <th className="px-4 py-3">Player</th>
              <th className="px-4 py-3">Pos</th>
              <th className="px-4 py-3 text-right">Trend</th>
              <th className="px-4 py-3 text-right">Adds/Drops</th>
              <th className="px-4 py-3 text-right">VOR</th>
              <th className="px-4 py-3 text-right">Suggested bid</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => {
              const bid = faab(t.trend_score, t.injury_status, budget);
              return (
                <tr key={t.player_id} className="border-b border-hairline/60 transition hover:bg-surface-elevated">
                  <td className="px-4 py-3 font-medium">
                    <Link href={`/players/${t.player_id}`} className="transition hover:text-accent">{t.full_name}</Link>
                    {t.injury_status && <span className="ml-2 text-label text-red-400">{t.injury_status}</span>}
                  </td>
                  <td className="px-4 py-3 text-ink-muted">{t.position ?? "—"} · {t.nfl_team ?? "FA"}</td>
                  <td className="px-4 py-3 text-right font-mono" style={{ color: t.trend_score >= 0 ? "var(--accent)" : "#E0573A" }}>
                    {t.trend_score >= 0 ? "+" : ""}{t.trend_score.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-ink-muted">{t.sleeper_adds}/{t.sleeper_drops}</td>
                  <td className="px-4 py-3 text-right font-mono text-ink-muted">{t.vor != null ? t.vor.toFixed(1) : "—"}</td>
                  <td className="px-4 py-3 text-right">
                    <span className="font-mono" style={{ color: TIER_COLOR[bid.label] }}>
                      {bid.dollars > 0 ? `$${bid.dollars}` : "—"}
                    </span>
                    <span className="ml-2 text-label text-ink-muted">{bid.label}</span>
                  </td>
                </tr>
              );
            })}
            {!rows.length && <tr><td colSpan={6} className="px-4 py-8 text-center text-label text-ink-muted">No trending players.</td></tr>}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-label text-ink-muted">
        Bids = % of remaining FAAB scaled by blended trend (news sentiment ⊕ Sleeper add velocity). Injured/out players flagged as hold.
      </p>
    </div>
  );
}
