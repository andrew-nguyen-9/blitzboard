"use client";

import { Fragment, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { useVirtualizer } from "@tanstack/react-virtual";
import { loadSnapshot, type SnapshotPlayer } from "@/lib/snapshot";
import { tierMap } from "@/lib/tiers";
import { playerTooltipRows } from "@/lib/playerTooltip";
import { usePrefetchOnIntent } from "@/lib/usePrefetchOnIntent";
import EmptyState from "@/components/EmptyState";
import Tooltip from "@/components/Tooltip";
import type { Engine } from "@/lib/types";

const POSITIONS = ["ALL", "QB", "RB", "WR", "TE", "K", "DST"] as const;
type Pos = (typeof POSITIONS)[number];
type SortKey = "rank" | "name" | "team" | "value" | "vor" | "rho" | "trend";
const norm = (p: string | null | undefined) => (p === "DEF" ? "DST" : p ?? "—");

// Shared 7-track grid so the header and every virtual row align. Less-critical
// columns collapse on small screens (no horizontal scroll, no clipping).
const GRID =
  "grid grid-cols-[2.5rem_1fr_2.5rem_5rem_3.5rem] gap-x-2 sm:grid-cols-[3rem_1fr_2.5rem_3rem_5rem_4.5rem_5rem]";

// A route link that warms on intent (hover/focus), never on touch-scroll.
// usePrefetchOnIntent is a hook, so each row needs its own component.
function PlayerRowLink({ id, className, children }: { id: string; className?: string; children: ReactNode }) {
  const href = `/players/${id}`;
  const intent = usePrefetchOnIntent(href);
  return (
    <Link href={href} prefetch={false} data-cursor="view" className={className} {...intent}>
      {children}
    </Link>
  );
}

// numeric cell — mono + tabular so digits never reflow; reserves ch-width so the
// longest expected value never clips (the StatTable no-clip pattern).
function Num({ value, decimals = 1, hideBelow }: { value: number | null; decimals?: number; hideBelow?: "sm" }) {
  const text = value == null ? "—" : value.toFixed(decimals);
  return (
    <span role="cell" className={`block text-right font-mono tabular-nums text-ink ${hideBelow === "sm" ? "hidden sm:block" : ""}`}>
      <span style={{ minWidth: `${text.length + 0.5}ch`, display: "inline-block" }}>{text}</span>
    </span>
  );
}

export default function PlayerTable({ engine }: { engine: Engine }) {
  const [players, setPlayers] = useState<SnapshotPlayer[] | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "empty">("loading");
  const [q, setQ] = useState("");
  const [pos, setPos] = useState<Pos>("ALL");
  const [team, setTeam] = useState("ALL");
  const [tier, setTier] = useState(0); // 0 = all tiers
  const [minRho, setMinRho] = useState(0);
  const [sort, setSort] = useState<SortKey>("rank");
  const [asc, setAsc] = useState(true);

  useEffect(() => {
    let alive = true;
    setStatus("loading");
    loadSnapshot({ engine }).then((p) => {
      if (!alive) return;
      setPlayers(p ?? []);
      setStatus(p && p.length ? "ready" : "empty");
    });
    return () => {
      alive = false;
    };
  }, [engine]);

  const tiers = useMemo(() => (players ? tierMap(players) : {}), [players]);
  const teams = useMemo(
    () => (players ? (Array.from(new Set(players.map((p) => p.nfl_team).filter(Boolean))) as string[]).sort() : []),
    [players],
  );
  const maxTier = useMemo(() => Math.max(0, ...Object.values(tiers)), [tiers]);

  const filtered = useMemo(() => {
    let r = players ?? [];
    if (pos !== "ALL") r = r.filter((p) => norm(p.position) === pos);
    if (team !== "ALL") r = r.filter((p) => p.nfl_team === team);
    if (tier) r = r.filter((p) => (tiers[p.id] ?? 99) === tier);
    if (minRho > 0) r = r.filter((p) => (p.predictability ?? 0) >= minRho);
    if (q.trim()) {
      const n = q.toLowerCase();
      r = r.filter((p) => p.full_name.toLowerCase().includes(n) || (p.nfl_team ?? "").toLowerCase().includes(n));
    }
    const dir = asc ? 1 : -1;
    const num = (x: number | null) => x ?? (asc ? 1e9 : -1e9); // missing sorts last
    return [...r].sort((a, b) => {
      switch (sort) {
        case "name": return dir * a.full_name.localeCompare(b.full_name);
        case "team": return dir * (a.nfl_team ?? "").localeCompare(b.nfl_team ?? "");
        case "value": return dir * (num(a.value) - num(b.value));
        case "vor": return dir * (num(a.vor) - num(b.vor));
        case "rho": return dir * (num(a.predictability) - num(b.predictability));
        case "trend": return dir * (num(a.trend) - num(b.trend));
        default: return dir * (num(a.rank) - num(b.rank));
      }
    });
  }, [players, q, pos, team, tier, minRho, sort, asc, tiers]);

  const scrollRef = useRef<HTMLDivElement>(null);
  const rowVirt = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 48,
    overscan: 12,
  });

  function toggleSort(k: SortKey) {
    if (sort === k) setAsc(!asc);
    else {
      setSort(k);
      setAsc(k === "rank" || k === "name" || k === "team"); // text/rank asc, metrics desc
    }
  }

  // Sortable column header — aria-sort lives on the columnheader (not the button).
  const Th = ({ k, children, className }: { k: SortKey; children: ReactNode; className?: string }) => (
    <div
      role="columnheader"
      aria-sort={sort === k ? (asc ? "ascending" : "descending") : "none"}
      className={`items-center ${className ?? "flex"}`}
    >
      <button
        type="button"
        onClick={() => toggleSort(k)}
        data-cursor="sort"
        className="flex items-center gap-1 px-1 text-label uppercase text-ink-2 transition hover:text-ink"
      >
        {children}
        <span aria-hidden className="text-accent">{sort === k ? (asc ? "▲" : "▼") : ""}</span>
      </button>
    </div>
  );

  if (status === "loading") {
    return <div className="glass grid h-64 place-items-center text-label text-ink-muted">Loading the player universe…</div>;
  }
  if (status === "empty") {
    return (
      <EmptyState title="Player Explorer" phase="Phase 2">
        No snapshot published yet. Run the pipeline (value_engine_run.py → publish_snapshot.py),
        or set NEXT_PUBLIC_SUPABASE_URL to read the CDN snapshot.
      </EmptyState>
    );
  }

  const items = rowVirt.getVirtualItems();

  return (
    <div>
      {/* filters — instant, fully client-side over the in-memory snapshot */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search player or team…"
          aria-label="Search players"
          className="w-56 rounded-full border border-hairline bg-surface px-4 py-2 text-body text-ink outline-none focus:border-accent"
        />
        <div className="flex flex-wrap gap-1">
          {POSITIONS.map((p) => (
            <button
              key={p}
              onClick={() => setPos(p)}
              aria-pressed={pos === p}
              className={`rounded-full px-3 py-1.5 text-label transition ${pos === p ? "bg-accent text-bg" : "border border-hairline text-ink-muted hover:text-ink"}`}
            >
              {p}
            </button>
          ))}
        </div>
        <select
          value={team}
          onChange={(e) => setTeam(e.target.value)}
          aria-label="Filter by team"
          className="rounded-full border border-hairline bg-surface px-3 py-1.5 text-label text-ink outline-none focus:border-accent"
        >
          <option value="ALL">All teams</option>
          {teams.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <select
          value={tier}
          onChange={(e) => setTier(Number(e.target.value))}
          aria-label="Filter by tier"
          className="rounded-full border border-hairline bg-surface px-3 py-1.5 text-label text-ink outline-none focus:border-accent"
        >
          <option value={0}>All tiers</option>
          {Array.from({ length: maxTier }, (_, i) => i + 1).map((t) => <option key={t} value={t}>Tier {t}</option>)}
        </select>
        <label className="flex items-center gap-2 text-label text-ink-muted">
          ρ ≥ {minRho.toFixed(2)}
          <input
            type="range" min={0} max={1} step={0.05} value={minRho}
            onChange={(e) => setMinRho(Number(e.target.value))}
            aria-label="Minimum predictability"
            className="accent-[var(--accent)]"
          />
        </label>
        <span className="ml-auto text-label text-ink-muted">{filtered.length.toLocaleString()} players</span>
      </div>

      {/* virtualized table — only visible rows are in the DOM */}
      <div className="glass overflow-hidden" role="table" aria-rowcount={filtered.length} aria-label="Players ranked by value">
        <div className={`${GRID} border-b border-hairline px-3 py-2`} role="row" aria-rowindex={1}>
          <Th k="rank">#</Th>
          <Th k="name">Player</Th>
          <div role="columnheader" className="flex items-center px-1 text-label uppercase text-ink-2">Pos</div>
          <Th k="team" className="hidden sm:flex">Tm</Th>
          <Th k="value" className="flex justify-end">Value</Th>
          <Th k="vor" className="hidden justify-end sm:flex">VOR</Th>
          <Th k="rho" className="flex justify-end">ρ</Th>
        </div>

        <div ref={scrollRef} className="h-[68vh] overflow-auto">
          <div role="rowgroup" style={{ height: rowVirt.getTotalSize(), position: "relative" }}>
            {items.map((vi) => {
              const p = filtered[vi.index];
              const t = tiers[p.id];
              return (
                <div
                  key={p.id}
                  role="row"
                  aria-rowindex={vi.index + 2}
                  ref={rowVirt.measureElement}
                  data-index={vi.index}
                  className={`${GRID} group absolute left-0 top-0 w-full items-center border-b border-hairline/60 px-3 py-2.5 text-body transition hover:z-20 hover:bg-surface-elevated focus-within:z-20`}
                  style={{ transform: `translateY(${vi.start}px)` }}
                >
                  <span role="cell" className="font-mono text-ink-muted">{p.rank ?? vi.index + 1}</span>
                  <span role="cell" className="min-w-0 truncate font-medium">
                    <PlayerRowLink id={p.id} className="transition hover:text-accent">{p.full_name}</PlayerRowLink>
                    {t && <span className="ml-2 rounded bg-surface-elevated px-1.5 py-0.5 font-mono text-[10px] text-ink-muted">T{t}</span>}
                    {p.trend != null && p.trend > 0 && <span className="ml-1.5 align-middle text-[10px] text-accent" title={`${p.trend} adds`}>▲</span>}
                  </span>
                  <span role="cell" className="text-ink-muted">{norm(p.position)}</span>
                  <span role="cell" className="hidden text-ink-muted sm:block">{p.nfl_team ?? "FA"}</span>
                  <Num value={p.value} />
                  <Num value={p.vor} hideBelow="sm" />
                  <Num value={p.predictability} decimals={2} />
                  {/* decorative: the same value/VOR/ρ are already in the row cells for SR */}
                  <Tooltip
                    decorative
                    side="bottom"
                    content={
                      <>
                        <p className="mb-1.5 font-semibold text-ink">{p.full_name}</p>
                        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-0.5 font-mono tabular-nums">
                          {playerTooltipRows(p, t).map((r) => (
                            <Fragment key={r.label}>
                              <dt className="text-ink-muted">{r.label}</dt>
                              <dd className="text-right text-ink">{r.value}</dd>
                            </Fragment>
                          ))}
                        </dl>
                      </>
                    }
                  />
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
