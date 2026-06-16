"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { PlayerWithValue } from "@/lib/types";
import { tierMap } from "@/lib/tiers";
import { projPoints, draftScores, scoreColor } from "@/lib/score";

const POSITIONS = ["ALL", "QB", "RB", "WR", "TE", "K", "DST"] as const;
type SortKey = "rank" | "name" | "team" | "score" | "pts" | "adp";
const CAP = 500;
const FA_SENTIMENT = 0.15; // growing-sentiment FAs survive the free-agent filter (#3)
const norm = (p: string | null | undefined) => (p === "DEF" ? "DST" : p ?? "—");

export default function PlayerTable({
  players,
  rosteredIds,
  trending,
}: {
  players: PlayerWithValue[];
  rosteredIds?: Set<string>;
  trending?: Record<string, number>;
}) {
  const [q, setQ] = useState("");
  const [pos, setPos] = useState<(typeof POSITIONS)[number]>("ALL");
  const [sort, setSort] = useState<SortKey>("rank");
  const [asc, setAsc] = useState(true);
  const [faOnly, setFaOnly] = useState(false);

  const tiers = useMemo(() => tierMap(players), [players]);
  const scores = useMemo(() => draftScores(players), [players]);
  const maxPts = useMemo(() => Math.max(1, ...players.map((p) => projPoints(p))), [players]);

  const filtered = useMemo(() => {
    let r = players;
    if (faOnly && rosteredIds) {
      r = r.filter((p) => !rosteredIds.has(p.id) || (trending?.[p.id] ?? 0) > FA_SENTIMENT);
    }
    if (pos !== "ALL") r = r.filter((p) => norm(p.position) === pos);
    if (q.trim()) {
      const n = q.toLowerCase();
      r = r.filter((p) => p.full_name.toLowerCase().includes(n) || (p.nfl_team ?? "").toLowerCase().includes(n));
    }
    const dir = asc ? 1 : -1;
    return [...r].sort((a, b) => {
      switch (sort) {
        case "name": return dir * a.full_name.localeCompare(b.full_name);
        case "team": return dir * (a.nfl_team ?? "").localeCompare(b.nfl_team ?? "");
        case "score": return dir * ((scores[a.id] ?? 0) - (scores[b.id] ?? 0));
        case "pts": return dir * (projPoints(a) - projPoints(b));
        case "adp": return dir * ((a.value?.adp ?? 1e9) - (b.value?.adp ?? 1e9));
        default: return dir * ((a.value?.rank ?? 1e9) - (b.value?.rank ?? 1e9));
      }
    });
  }, [players, q, pos, sort, asc, faOnly, rosteredIds, trending, scores]);

  const rows = filtered.slice(0, CAP);

  function toggleSort(key: SortKey) {
    if (sort === key) setAsc(!asc);
    else { setSort(key); setAsc(key === "rank" || key === "name" || key === "team" || key === "adp"); }
  }
  const Th = ({ k, children, right }: { k: SortKey; children: React.ReactNode; right?: boolean }) => (
    <th onClick={() => toggleSort(k)} data-cursor="sort"
      className={`cursor-pointer select-none px-3 py-3 transition hover:text-ink ${right ? "text-right" : ""}`}>
      {children}<span className="ml-1 text-accent">{sort === k ? (asc ? "▲" : "▼") : ""}</span>
    </th>
  );

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search player or team…"
          className="w-60 rounded-full border border-hairline bg-surface px-4 py-2 text-body text-ink outline-none focus:border-accent" />
        <div className="flex flex-wrap gap-1">
          {POSITIONS.map((p) => (
            <button key={p} onClick={() => setPos(p)}
              className={`rounded-full px-3 py-1.5 text-label transition ${pos === p ? "bg-accent text-bg" : "border border-hairline text-ink-muted hover:text-ink"}`}>
              {p}
            </button>
          ))}
        </div>
        {rosteredIds && (
          <button onClick={() => setFaOnly((v) => !v)} data-cursor="filter"
            title="Free agents only — but players with growing positive sentiment stay visible"
            className={`rounded-full px-3 py-1.5 text-label transition ${faOnly ? "bg-accent text-bg" : "border border-hairline text-ink-muted hover:text-ink"}`}>
            Free agents{faOnly ? " ✓" : ""}
          </button>
        )}
        <span className="ml-auto text-label text-ink-muted">
          {filtered.length.toLocaleString()} shown{filtered.length > CAP ? ` · top ${CAP}` : ""}
        </span>
      </div>

      <div className="glass overflow-hidden">
        <table className="w-full text-left text-body">
          <thead className="border-b border-hairline text-label text-ink-muted">
            <tr>
              <Th k="rank">#</Th>
              <Th k="name">Player</Th>
              <th className="px-3 py-3">Pos</th>
              <Th k="team">Tm</Th>
              <th className="px-3 py-3 text-right">Bye</th>
              <Th k="adp" right>ADP</Th>
              <Th k="pts" right>Proj Pts</Th>
              <Th k="score" right>Score</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p, i) => {
              const v = p.value;
              const pts = projPoints(p);
              const score = scores[p.id] ?? 0;
              const w = Math.max(2, Math.min(100, (pts / maxPts) * 100));
              const tier = tiers[p.id];
              const isFa = rosteredIds && !rosteredIds.has(p.id);
              return (
                <tr key={p.id} className="border-b border-hairline/60 transition hover:bg-surface-elevated">
                  <td className="px-3 py-2.5 font-mono text-ink-muted">{v?.rank ?? i + 1}</td>
                  <td className="px-3 py-2.5 font-medium">
                    <Link href={`/players/${p.id}`} data-cursor="view" className="transition hover:text-accent">{p.full_name}</Link>
                    {tier && <span className="ml-2 rounded bg-surface-elevated px-1.5 py-0.5 font-mono text-[10px] text-ink-muted">T{tier}</span>}
                    {isFa && <span className="ml-1.5 text-[10px] uppercase tracking-wider text-accent/70">FA</span>}
                    {p.injury_status && <span className="ml-2 text-label text-red-400">{p.injury_status}</span>}
                  </td>
                  <td className="px-3 py-2.5 text-ink-muted">{norm(p.position)}</td>
                  <td className="px-3 py-2.5 text-ink-muted">{p.nfl_team ?? "FA"}</td>
                  <td className="px-3 py-2.5 text-right text-ink-muted">{p.bye_week ?? "—"}</td>
                  <td className="px-3 py-2.5 text-right font-mono text-ink-muted">{v?.adp != null ? v.adp.toFixed(1) : "—"}</td>
                  <td className="px-3 py-2.5">
                    <div className="flex items-center justify-end gap-2">
                      <div className="hidden h-1.5 w-20 overflow-hidden rounded-full bg-hairline sm:block">
                        <div className="h-full rounded-full bg-accent" style={{ width: `${w}%` }} />
                      </div>
                      <span className="w-12 text-right font-mono text-ink">{pts > 0 ? pts.toFixed(0) : "—"}</span>
                    </div>
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    <span className="inline-block w-9 rounded-md py-0.5 text-center font-mono text-bg" style={{ background: scoreColor(score) }}>
                      {score}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
