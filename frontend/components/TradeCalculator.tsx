"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { loadSnapshot, type SnapshotPlayer } from "@/lib/snapshot";
import { PlayerSearchIndex } from "@/lib/tradeSearch";
import { tierMap } from "@/lib/tiers";
import { playerTooltipRows } from "@/lib/playerTooltip";
import { useCursorTooltip } from "@/components/CursorTooltip";
import { PLAYER_COLUMNS, type ColDef, type ColGroup } from "@/lib/playerColumns";
import { getBoxStats, type NewsItem } from "@/lib/queries";
import type { BoxStats } from "@/lib/playerColumns";
import LeagueSelector, { type LeagueOpt } from "./LeagueSelector";

const POSITIONS = ["ALL", "QB", "RB", "WR", "TE", "K", "DST"] as const;
type Pos = (typeof POSITIONS)[number];
const norm = (p?: string | null) => (p === "DEF" ? "DST" : p ?? "—");

// Toggleable extra stat-column groups, shared with the Players table via
// lib/playerColumns.ts (single source — the two tables can't diverge).
const GROUPS: { key: ColGroup; label: string }[] = [
  { key: "proj", label: "Proj" },
  { key: "rank", label: "Rank" },
  { key: "box", label: "Box" },
  { key: "meta", label: "Meta" },
];
// Display a raw column value: null → "—", numbers honor the column's decimals.
const fmtCol = (c: ColDef, v: number | string | null): string =>
  v == null ? "—" : typeof v === "number" ? (c.decimals != null ? v.toFixed(c.decimals) : String(v)) : v;
// trade value = the player's VORP value (fall back to VOR), summed per side.
const pval = (p: SnapshotPlayer) => p.value ?? p.vor ?? 0;
const sumVal = (ps: SnapshotPlayer[]) => ps.reduce((s, p) => s + pval(p), 0);

// Unauth trade calculator: search the all-NFL snapshot, stack players on either
// side, and see which side wins by value. The NEWS PULSE feed starts all-NFL and
// refocuses to the players in the trade on submit. Epic 8 (auth) layers a League
// Selector + roster multi-select + team-focused RSS on top of this.
export default function TradeCalculator({ news, leagues = [] }: { news: NewsItem[]; leagues?: LeagueOpt[] }) {
  const [players, setPlayers] = useState<SnapshotPlayer[] | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "empty">("loading");
  const [q, setQ] = useState("");
  const [pos, setPos] = useState<Pos>("ALL");
  const [team, setTeam] = useState("ALL");
  const [sideA, setSideA] = useState<SnapshotPlayer[]>([]);
  const [sideB, setSideB] = useState<SnapshotPlayer[]>([]);
  const [submitted, setSubmitted] = useState(false);
  const [leagueId, setLeagueId] = useState(leagues[0]?.id ?? "");
  const [groups, setGroups] = useState<Set<ColGroup>>(new Set());
  const [boxMap, setBoxMap] = useState<Record<string, BoxStats>>({});
  const tip = useCursorTooltip();
  const leagueName = leagues.find((l) => l.id === leagueId)?.name ?? leagues[0]?.name;

  useEffect(() => {
    let alive = true;
    setStatus("loading");
    loadSnapshot({ engine: "vorp" }).then((p) => {
      if (!alive) return;
      setPlayers(p ?? []);
      setStatus(p && p.length ? "ready" : "empty");
    });
    return () => {
      alive = false;
    };
  }, []);

  const index = useMemo(() => (players ? new PlayerSearchIndex(players) : null), [players]);
  const tiers = useMemo(() => (players ? tierMap(players) : {}), [players]);
  const activeCols = useMemo(() => PLAYER_COLUMNS.filter((c) => groups.has(c.group)), [groups]);
  const teams = useMemo(
    () => (players ? (Array.from(new Set(players.map((p) => p.nfl_team).filter(Boolean))) as string[]).sort() : []),
    [players],
  );

  const picked = useMemo(() => new Set([...sideA, ...sideB].map((p) => p.id)), [sideA, sideB]);

  const results = useMemo(() => {
    if (!index || !players) return [];
    let r = q.trim() ? index.search(q, 40) : players.slice(0, 40); // default: top by rank
    if (pos !== "ALL") r = r.filter((p) => norm(p.position) === pos);
    if (team !== "ALL") r = r.filter((p) => p.nfl_team === team);
    return r.filter((p) => !picked.has(p.id)).slice(0, 12);
  }, [index, players, q, pos, team, picked]);

  // ponytail: box-score fetched lazily, only for the ≤12 visible results and only
  // once the Box group is on. Every requested id is recorded (→ {} when no history)
  // so a player without a box never re-fetches. Same ceiling as e3's Players table.
  useEffect(() => {
    if (!groups.has("box")) return;
    const missing = results.map((p) => p.id).filter((id) => !(id in boxMap));
    if (!missing.length) return;
    let alive = true;
    getBoxStats(missing).then((m) => {
      if (!alive) return;
      setBoxMap((prev) => {
        const next = { ...prev };
        for (const id of missing) next[id] = m[id] ?? {};
        return next;
      });
    });
    return () => {
      alive = false;
    };
  }, [groups, results, boxMap]);

  const add = (p: SnapshotPlayer, side: "A" | "B") =>
    (side === "A" ? setSideA : setSideB)((s) => [...s, p]);
  const remove = (id: string, side: "A" | "B") =>
    (side === "A" ? setSideA : setSideB)((s) => s.filter((p) => p.id !== id));

  const totalA = sumVal(sideA);
  const totalB = sumVal(sideB);
  const delta = totalA - totalB;
  const fairness = Math.max(totalA, totalB) > 0 ? Math.min(totalA, totalB) / Math.max(totalA, totalB) : 1;

  // refocus the all-NFL feed to headlines about the traded players on submit.
  const tradePlayers = useMemo(() => [...sideA, ...sideB], [sideA, sideB]);
  const focusedNews = useMemo(() => {
    if (!submitted || !tradePlayers.length) return news;
    // ponytail: NewsItem carries no player_id, so match on name tokens ≥4 chars
    // (catches "Lamar …" and "… Jackson"). Ceiling: a generic first name could
    // false-match; upgrade path is a player_id join on news_articles if it bites.
    const names = tradePlayers.flatMap((p) =>
      p.full_name.toLowerCase().split(" ").filter((t) => t.length >= 4),
    );
    return news.filter((n) => names.some((nm) => n.title.toLowerCase().includes(nm)));
  }, [submitted, tradePlayers, news]);

  if (status === "loading") {
    return <div className="glass grid h-64 place-items-center text-label text-ink-muted">Loading the player universe…</div>;
  }
  if (status === "empty") {
    return (
      <div className="glass grid h-64 place-items-center px-6 text-center text-label text-ink-muted">
        No snapshot published yet. Run the pipeline (value_engine_run.py → publish_snapshot.py),
        or set NEXT_PUBLIC_SUPABASE_URL to read the CDN snapshot.
      </div>
    );
  }

  return (
    <div>
      {tip.element}
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-display-md">Trade Calculator</h1>
          <p className="mt-2 text-body text-ink-muted">
            Search any NFL player, stack both sides, see who wins by value — no league needed.
          </p>
        </div>
        {/* Authed: a League Selector sets the trade context; the RSS feed below stays focused on
            that league's players until submit, then flips to the players in the trade. Unauth: the
            static all-NFL scope chip (flips to "This trade" on submit). */}
        {leagues.length ? (
          <LeagueSelector leagues={leagues} value={leagueId} onChange={setLeagueId} />
        ) : (
          <span className="rounded-full border border-hairline px-3 py-1.5 text-label text-ink-muted">
            Scope: <span className="text-ink">{submitted && tradePlayers.length ? "This trade" : "All NFL"}</span>
          </span>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
        <div>
          {/* action controls first — the trade is the focus; search/filters sit below it */}
          <div className="grid gap-4 md:grid-cols-2">
            <Side label="Side A" total={totalA} players={sideA} onRemove={(id) => remove(id, "A")} tiers={tiers} tip={tip} />
            <Side label="Side B" total={totalB} players={sideB} onRemove={(id) => remove(id, "B")} tiers={tiers} tip={tip} />
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-hairline pt-4 text-label">
            {sideA.length || sideB.length ? (
              <>
                <span>
                  verdict{" "}
                  <span className="font-mono text-ink">
                    {Math.abs(delta) < 1 ? "even trade" : delta > 0 ? "Side A wins" : "Side B wins"}
                    {Math.abs(delta) >= 1 && <span className="text-accent"> by {Math.abs(delta).toFixed(0)}</span>}
                  </span>
                </span>
                <span>fairness <span className="font-mono text-ink">{Math.round(fairness * 100)}%</span></span>
              </>
            ) : (
              <span className="text-ink-muted">Add players to each side to compare.</span>
            )}
            <button
              type="button"
              onClick={() => setSubmitted(true)}
              disabled={!tradePlayers.length}
              className="ml-auto rounded-full bg-accent px-4 py-1.5 text-label text-bg transition hover:opacity-90 disabled:opacity-40"
            >
              Analyze trade
            </button>
          </div>

          {/* search + filters — instant, fully client-side over the in-memory snapshot */}
          <div className="mb-3 mt-8 flex flex-wrap items-center gap-3">
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search any player…"
              aria-label="Search players"
              className="w-56 rounded-full border border-hairline bg-surface px-4 py-2 text-body text-ink outline-none focus:border-accent"
            />
            <select
              value={pos}
              onChange={(e) => setPos(e.target.value as Pos)}
              aria-label="Filter by position"
              className="rounded-full border border-hairline bg-surface px-3 py-1.5 text-label text-ink outline-none focus:border-accent"
            >
              {POSITIONS.map((p) => <option key={p} value={p}>{p === "ALL" ? "All positions" : p}</option>)}
            </select>
            <select
              value={team}
              onChange={(e) => setTeam(e.target.value)}
              aria-label="Filter by team"
              className="rounded-full border border-hairline bg-surface px-3 py-1.5 text-label text-ink outline-none focus:border-accent"
            >
              <option value="ALL">All teams</option>
              {teams.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>

          {/* optional stat-column groups — shared contract with the Players table */}
          <div className="mb-3 flex flex-wrap items-center gap-2 text-label">
            <span className="text-ink-muted">Columns:</span>
            {GROUPS.map((g) => (
              <button
                key={g.key}
                type="button"
                aria-pressed={groups.has(g.key)}
                onClick={() =>
                  setGroups((s) => {
                    const n = new Set(s);
                    if (n.has(g.key)) n.delete(g.key);
                    else n.add(g.key);
                    return n;
                  })
                }
                className={`rounded-full px-3 py-1 transition ${groups.has(g.key) ? "bg-accent text-bg" : "border border-hairline text-ink-muted hover:text-ink"}`}
              >
                {g.label}
              </button>
            ))}
          </div>

          {/* results — tabular; add to either side */}
          <div role="table" aria-label="Search results" className="glass overflow-x-auto">
            <div role="row" className="flex items-center gap-3 border-b border-hairline px-4 py-2 text-label uppercase text-ink-2">
              <span role="columnheader" className="min-w-0 flex-1">Player</span>
              <span role="columnheader" className="w-10 text-right">Val</span>
              {activeCols.map((c) => (
                <span key={c.key} role="columnheader" className="w-16 truncate text-right" title={c.label}>{c.label}</span>
              ))}
              <span className="w-[5.5rem]" aria-hidden />
            </div>
            {results.map((p) => {
              const ctx = { tier: tiers[p.id], box: boxMap[p.id] ?? null };
              return (
                <div
                  key={p.id}
                  role="row"
                  onPointerEnter={() => tip.show({ title: p.full_name, rows: playerTooltipRows(p, tiers[p.id]) })}
                  onPointerLeave={tip.hide}
                  className="flex items-center gap-3 border-b border-hairline/60 px-4 py-2.5 text-body last:border-0 transition hover:bg-surface-elevated"
                >
                  <span role="cell" className="min-w-0 flex-1 truncate">
                    <span className="font-medium">{p.full_name}</span>{" "}
                    <span className="text-ink-muted">{norm(p.position)} · {p.nfl_team ?? "FA"}</span>
                  </span>
                  <span role="cell" className="w-10 text-right font-mono text-label text-accent">{pval(p).toFixed(0)}</span>
                  {activeCols.map((c) => (
                    <span key={c.key} role="cell" className="w-16 truncate text-right font-mono tabular-nums text-ink-muted">{fmtCol(c, c.get(p, ctx))}</span>
                  ))}
                  <span className="flex w-[5.5rem] justify-end gap-1.5">
                    <button type="button" onClick={() => add(p, "A")}
                      className="rounded-full border border-hairline px-2.5 py-1 text-label transition hover:border-accent"
                      aria-label={`Add ${p.full_name} to side A`}>+ A</button>
                    <button type="button" onClick={() => add(p, "B")}
                      className="rounded-full border border-hairline px-2.5 py-1 text-label transition hover:border-accent"
                      aria-label={`Add ${p.full_name} to side B`}>+ B</button>
                  </span>
                </div>
              );
            })}
            {!results.length && (
              <div role="row" className="px-4 py-6 text-center text-label text-ink-muted">No players match.</div>
            )}
          </div>
        </div>

        {/* live RSS news feed — all-NFL until submit, then scoped to the trade */}
        <aside className="glass h-fit p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-label text-ink-muted">NEWS PULSE</h3>
            <span className="text-label text-ink-muted/70">{submitted && tradePlayers.length ? "This trade" : leagues.length ? leagueName : "All NFL"}</span>
          </div>
          <div className="space-y-3">
            {focusedNews.map((n, i) => (
              <a key={i} href={n.url ?? "#"} target="_blank" rel="noreferrer"
                className="block border-b border-hairline/60 pb-3 last:border-0 transition hover:opacity-80">
                <div className="flex items-start gap-2">
                  <span className="mt-1 h-2 w-2 shrink-0 rounded-full"
                    style={{ background: (n.sentiment ?? 0) >= 0 ? "var(--accent)" : "#E0573A" }} />
                  <div>
                    <div className="text-body leading-snug">{n.title}</div>
                    <div className="mt-1 flex items-center gap-2 text-label text-ink-muted">
                      <span>{n.source}</span>
                      {n.injury_flag && <span className="text-red-400">injury</span>}
                      {n.opportunity_flag && <span className="text-accent">opportunity</span>}
                    </div>
                  </div>
                </div>
              </a>
            ))}
            {!focusedNews.length && (
              <div className="text-label text-ink-muted">
                {submitted ? "No recent headlines for these players." : "No news scored yet."}
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

function Side({
  label, total, players, onRemove, tiers, tip,
}: {
  label: string;
  total: number;
  players: SnapshotPlayer[];
  onRemove: (id: string) => void;
  tiers: Record<string, number>;
  tip: ReturnType<typeof useCursorTooltip>;
}) {
  return (
    <div className="glass p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-label text-ink-muted">{label}</span>
        <span className="font-mono text-body text-ink">{total.toFixed(0)}</span>
      </div>
      {players.length ? (
        <div className="flex flex-wrap gap-1.5">
          {players.map((p) => (
            <span key={p.id}
              onPointerEnter={() => tip.show({ title: p.full_name, rows: playerTooltipRows(p, tiers[p.id]) })}
              onPointerLeave={tip.hide}
              className="inline-flex items-center gap-1.5 rounded-full border border-hairline bg-surface px-2.5 py-1 text-label">
              <Link href={`/players/${p.id}`} className="transition hover:text-accent">
                {p.full_name} <span className="text-ink-muted">{norm(p.position)}</span>
              </Link>
              <button type="button" onClick={() => onRemove(p.id)} aria-label={`Remove ${p.full_name}`}
                className="text-ink-muted transition hover:text-ink">×</button>
            </span>
          ))}
        </div>
      ) : (
        <p className="text-label text-ink-muted">Empty — add players from the search above.</p>
      )}
    </div>
  );
}
