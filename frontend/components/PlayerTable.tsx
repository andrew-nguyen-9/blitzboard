"use client";

import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { useWindowVirtualizer } from "@tanstack/react-virtual";
import { loadSnapshot, type SnapshotPlayer } from "@/lib/snapshot";
import { tierMap } from "@/lib/tiers";
import { playerTooltipRows } from "@/lib/playerTooltip";
import { compareCells } from "@/lib/playerSort";
import { PLAYER_COLUMNS, type BoxStats, type ColCtx, type ColDef, type ColGroup } from "@/lib/playerColumns";
import { usePrefetchOnIntent } from "@/lib/usePrefetchOnIntent";
import { useCursorTooltip } from "@/components/CursorTooltip";
import EmptyState from "@/components/EmptyState";
import type { Engine } from "@/lib/types";

const POSITIONS = ["ALL", "QB", "RB", "WR", "TE", "K", "DST"] as const;
type Pos = (typeof POSITIONS)[number];
const norm = (p: string | null | undefined) => (p === "DEF" ? "DST" : p ?? "—");

// Toggleable column groups; default-on reproduces the prior table (value/vor +
// pos/team) and adds the f1 fields (boom/bust/bye). Box is heavy + off by default.
const GROUPS: { key: ColGroup; label: string }[] = [
  { key: "proj", label: "Proj" },
  { key: "rank", label: "Ranks" },
  { key: "box", label: "Box" },
  { key: "meta", label: "Meta" },
];
const TEXT_COLS = new Set(["pos", "team"]); // left-aligned; everything else numeric/right
// sort keys whose natural order is ascending (text, or lower = better)
const ASC_FIRST = new Set(["name", "team", "pos", "rank", "adp", "tier", "bye"]);

// Sort value for a row under the active key: base name/ρ, else the matching ColDef.
function sortVal(p: SnapshotPlayer, key: string, ctx: ColCtx): number | string | null {
  if (key === "name") return p.full_name;
  if (key === "rho") return p.predictability;
  return PLAYER_COLUMNS.find((c) => c.key === key)?.get(p, ctx) ?? p.rank;
}

// A route link that warms on intent (hover/focus), never on touch-scroll.
function PlayerRowLink({ id, className, children }: { id: string; className?: string; children: ReactNode }) {
  const href = `/players/${id}`;
  const intent = usePrefetchOnIntent(href);
  return (
    <Link href={href} prefetch={false} data-cursor="view" className={className} {...intent}>
      {children}
    </Link>
  );
}

// Generic dynamic cell over a ColDef; null → "—", numbers mono/right with decimals.
function ColCell({ col, p, ctx }: { col: ColDef; p: SnapshotPlayer; ctx: ColCtx }) {
  const v = col.get(p, ctx);
  const text = v == null ? "—" : typeof v === "number" ? v.toFixed(col.decimals ?? 0) : String(v);
  const numeric = !TEXT_COLS.has(col.key);
  return (
    <span role="cell" className={`truncate ${numeric ? "text-right font-mono tabular-nums text-ink" : "text-ink-muted"}`}>
      {text}
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
  const [sort, setSort] = useState<string>("rank");
  const [asc, setAsc] = useState(true);
  const [groups, setGroups] = useState<Record<ColGroup, boolean>>({
    proj: true,
    rank: false,
    box: false,
    meta: true,
  });
  const [box, setBox] = useState<Record<string, BoxStats>>({}); // latest-season box, lazily filled
  const fetchedBox = useRef<Set<string>>(new Set());

  const tip = useCursorTooltip();

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
  const activeCols = useMemo(() => PLAYER_COLUMNS.filter((c) => groups[c.group]), [groups]);

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
    return r;
  }, [players, q, pos, team, tier, minRho, tiers]);

  const ctxOf = useMemo(
    () => (p: SnapshotPlayer): ColCtx => ({ tier: tiers[p.id], box: box[p.id] ?? null }),
    [tiers, box],
  );

  // Sort separately from filter so scroll-driven box loads only re-sort, not re-filter.
  const sorted = useMemo(
    () => [...filtered].sort((a, b) => compareCells(sortVal(a, sort, ctxOf(a)), sortVal(b, sort, ctxOf(b)), asc)),
    [filtered, sort, asc, ctxOf],
  );

  const scrollRef = useRef<HTMLDivElement>(null);
  const [listOffset, setListOffset] = useState(0);

  // Single scroll region = the window (no inner overflow div → no double scrollbar).
  const rowVirt = useWindowVirtualizer({
    count: sorted.length,
    estimateSize: () => 48,
    overscan: 12,
    scrollMargin: listOffset,
  });
  const items = rowVirt.getVirtualItems();

  // Lazily fetch latest-season box-score for the visible window's sleeper ids when
  // the box group is on; each id fetched once, the map only grows.
  // ponytail: visible-window fetch (cheap `in(...)`); upgrade = a server-side
  // snapshot join so box columns sort across the whole universe, not just loaded rows.
  const visibleKey = items.map((vi) => sorted[vi.index]?.id ?? "").join(",");
  useEffect(() => {
    if (!groups.box) return;
    const missing = visibleKey.split(",").filter((id) => id && !fetchedBox.current.has(id));
    if (missing.length === 0) return;
    missing.forEach((id) => fetchedBox.current.add(id));
    let alive = true;
    // dynamic import keeps supabase-js out of the default players bundle (box off by default)
    import("@/lib/queries").then(({ getBoxStats }) =>
      getBoxStats(missing).then((m) => alive && setBox((b) => ({ ...b, ...m }))),
    );
    return () => {
      alive = false;
    };
  }, [groups.box, visibleKey]);

  // The list's document offset drives the window virtualizer's scrollMargin.
  // Recompute when layout above the list can shift (status, column count, resize).
  useLayoutEffect(() => {
    const measure = () => setListOffset(scrollRef.current?.offsetTop ?? 0);
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [status, activeCols.length]);

  function toggleSort(k: string) {
    if (sort === k) setAsc(!asc);
    else {
      setSort(k);
      setAsc(ASC_FIRST.has(k));
    }
  }

  // Sortable column header — aria-sort lives on the columnheader (not the button).
  const Th = ({ k, children, justify }: { k: string; children: ReactNode; justify?: "end" }) => (
    <div
      role="columnheader"
      aria-sort={sort === k ? (asc ? "ascending" : "descending") : "none"}
      className={`flex items-center ${justify === "end" ? "justify-end" : ""}`}
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

  // # + Player + ρ are always shown; toggled groups append their columns.
  const grid = {
    display: "grid",
    gridTemplateColumns: `2.5rem minmax(7rem,1fr) 3.5rem ${activeCols.map(() => "minmax(3.5rem,max-content)").join(" ")}`,
  } as const;

  return (
    <div>
      {tip.element}

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
        <span className="ml-auto text-label text-ink-muted">{sorted.length.toLocaleString()} players</span>
      </div>

      {/* column-group toggles */}
      <div className="mb-3 flex flex-wrap items-center gap-1">
        <span className="mr-1 text-label uppercase text-ink-2">Columns</span>
        {GROUPS.map((g) => (
          <button
            key={g.key}
            onClick={() => setGroups((s) => ({ ...s, [g.key]: !s[g.key] }))}
            aria-pressed={groups[g.key]}
            className={`rounded-full px-3 py-1 text-label transition ${groups[g.key] ? "bg-accent text-bg" : "border border-hairline text-ink-muted hover:text-ink"}`}
          >
            {g.label}
          </button>
        ))}
      </div>

      {/* virtualized table — window-scrolled (one scroll region); only visible rows in the DOM */}
      <div className="glass overflow-x-auto" role="table" aria-rowcount={sorted.length} aria-label="Players ranked by value">
        <div style={grid} className="sticky top-14 z-10 gap-x-2 border-b border-hairline bg-bg/95 px-3 py-2 backdrop-blur" role="row" aria-rowindex={1}>
          <Th k="rank">#</Th>
          <Th k="name">Player</Th>
          <Th k="rho" justify="end">ρ</Th>
          {activeCols.map((c) =>
            c.sortable ? (
              <Th key={c.key} k={c.key} justify={TEXT_COLS.has(c.key) ? undefined : "end"}>{c.label}</Th>
            ) : (
              <div key={c.key} role="columnheader" className="flex items-center px-1 text-label uppercase text-ink-2">{c.label}</div>
            ),
          )}
        </div>

        <div ref={scrollRef} role="rowgroup" style={{ height: rowVirt.getTotalSize(), position: "relative" }}>
          {items.map((vi) => {
            const p = sorted[vi.index];
            if (!p) return null;
            const t = tiers[p.id];
            const ctx = ctxOf(p);
            return (
              <div
                key={p.id}
                role="row"
                aria-rowindex={vi.index + 2}
                ref={rowVirt.measureElement}
                data-index={vi.index}
                style={{ ...grid, transform: `translateY(${vi.start - listOffset}px)` }}
                className="group absolute left-0 top-0 w-full items-center gap-x-2 border-b border-hairline/60 px-3 py-2.5 text-body transition hover:z-20 hover:bg-surface-elevated focus-within:z-20"
                onMouseEnter={() => tip.show({ title: p.full_name, rows: playerTooltipRows(p, t) })}
                onMouseLeave={tip.hide}
              >
                <span role="cell" className="font-mono text-ink-muted">{p.rank ?? vi.index + 1}</span>
                <span role="cell" className="min-w-0 truncate font-medium">
                  <PlayerRowLink id={p.id} className="transition hover:text-accent">{p.full_name}</PlayerRowLink>
                  {t && <span className="ml-2 rounded bg-surface-elevated px-1.5 py-0.5 font-mono text-[10px] text-ink-muted">T{t}</span>}
                  {p.trend != null && p.trend > 0 && <span className="ml-1.5 align-middle text-[10px] text-accent" title={`${p.trend} adds`}>▲</span>}
                </span>
                <span role="cell" className="block text-right font-mono tabular-nums text-ink">
                  {p.predictability == null ? "—" : p.predictability.toFixed(2)}
                </span>
                {activeCols.map((c) => <ColCell key={c.key} col={c} p={p} ctx={ctx} />)}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
