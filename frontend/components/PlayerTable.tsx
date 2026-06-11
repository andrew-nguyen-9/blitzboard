"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { PlayerWithValue } from "@/lib/types";

const POSITIONS = ["ALL", "QB", "RB", "WR", "TE", "K", "DST"] as const;
type SortKey = "rank" | "name" | "team" | "vor" | "boom";

export default function PlayerTable({ players }: { players: PlayerWithValue[] }) {
  const [q, setQ] = useState("");
  const [pos, setPos] = useState<(typeof POSITIONS)[number]>("ALL");
  const [sort, setSort] = useState<SortKey>("rank");
  const [asc, setAsc] = useState(true);

  const maxVor = useMemo(
    () => Math.max(1, ...players.map((p) => p.value?.vor ?? 0)),
    [players],
  );

  const rows = useMemo(() => {
    let r = players;
    if (pos !== "ALL") r = r.filter((p) => p.position === pos);
    if (q.trim()) {
      const needle = q.toLowerCase();
      r = r.filter(
        (p) =>
          p.full_name.toLowerCase().includes(needle) ||
          (p.nfl_team ?? "").toLowerCase().includes(needle),
      );
    }
    const dir = asc ? 1 : -1;
    return [...r].sort((a, b) => {
      switch (sort) {
        case "name":
          return dir * a.full_name.localeCompare(b.full_name);
        case "team":
          return dir * (a.nfl_team ?? "").localeCompare(b.nfl_team ?? "");
        case "vor":
          return dir * ((a.value?.vor ?? -999) - (b.value?.vor ?? -999));
        case "boom":
          return dir * ((a.value?.boom ?? -999) - (b.value?.boom ?? -999));
        default:
          return dir * ((a.value?.rank ?? 9999) - (b.value?.rank ?? 9999));
      }
    });
  }, [players, q, pos, sort, asc]);

  function toggleSort(key: SortKey) {
    if (sort === key) setAsc(!asc);
    else {
      setSort(key);
      setAsc(key === "rank" || key === "name" || key === "team");
    }
  }

  const Th = ({ k, children, right }: { k: SortKey; children: React.ReactNode; right?: boolean }) => (
    <th
      onClick={() => toggleSort(k)}
      className={`cursor-pointer select-none px-4 py-3 transition hover:text-ink ${right ? "text-right" : ""}`}
    >
      {children}
      <span className="ml-1 text-accent">{sort === k ? (asc ? "▲" : "▼") : ""}</span>
    </th>
  );

  return (
    <div>
      {/* controls */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search player or team…"
          className="w-64 rounded-full border border-hairline bg-surface px-4 py-2 text-body text-ink outline-none focus:border-accent"
        />
        <div className="flex flex-wrap gap-1">
          {POSITIONS.map((p) => (
            <button
              key={p}
              onClick={() => setPos(p)}
              className={`rounded-full px-3 py-1.5 text-label transition ${
                pos === p ? "bg-accent text-bg" : "border border-hairline text-ink-muted hover:text-ink"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
        <span className="ml-auto text-label text-ink-muted">{rows.length} shown</span>
      </div>

      {/* table */}
      <div className="glass overflow-hidden">
        <table className="w-full text-left text-body">
          <thead className="border-b border-hairline text-label text-ink-muted">
            <tr>
              <Th k="rank">#</Th>
              <Th k="name">Player</Th>
              <th className="px-4 py-3">Pos</th>
              <Th k="team">Team</Th>
              <th className="px-4 py-3">Bye</th>
              <Th k="vor" right>VOR</Th>
              <Th k="boom" right>Boom/Bust</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p, i) => {
              const v = p.value;
              const w = Math.max(2, ((v?.vor ?? 0) / maxVor) * 100);
              return (
                <tr key={p.id} className="border-b border-hairline/60 transition hover:bg-surface-elevated">
                  <td className="px-4 py-3 font-mono text-ink-muted">{v?.rank ?? i + 1}</td>
                  <td className="px-4 py-3 font-medium">
                    <Link href={`/players/${p.id}`} className="transition hover:text-accent">
                      {p.full_name}
                    </Link>
                    {p.injury_status && (
                      <span className="ml-2 text-label text-red-400">{p.injury_status}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-ink-muted">{p.position ?? "—"}</td>
                  <td className="px-4 py-3 text-ink-muted">{p.nfl_team ?? "FA"}</td>
                  <td className="px-4 py-3 text-ink-muted">{p.bye_week ?? "—"}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <div className="hidden h-1.5 w-24 overflow-hidden rounded-full bg-hairline sm:block">
                        <div className="h-full rounded-full bg-accent" style={{ width: `${w}%` }} />
                      </div>
                      <span className="w-12 text-right font-mono text-accent">
                        {v?.vor != null ? v.vor.toFixed(1) : "—"}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-ink-muted">
                    {v?.boom != null && v?.bust != null
                      ? `${v.boom.toFixed(0)} / ${v.bust.toFixed(0)}`
                      : "—"}
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
