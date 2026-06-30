"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { loadSnapshot, type SnapshotPlayer } from "@/lib/snapshot";
import { PlayerSearchIndex } from "@/lib/tradeSearch";
import type { NewsItem } from "@/lib/queries";

const POSITIONS = ["ALL", "QB", "RB", "WR", "TE", "K", "DST"] as const;
type Pos = (typeof POSITIONS)[number];
const norm = (p?: string | null) => (p === "DEF" ? "DST" : p ?? "—");
// trade value = the player's VORP value (fall back to VOR), summed per side.
const pval = (p: SnapshotPlayer) => p.value ?? p.vor ?? 0;
const sumVal = (ps: SnapshotPlayer[]) => ps.reduce((s, p) => s + pval(p), 0);

// Unauth trade calculator: search the all-NFL snapshot, stack players on either
// side, and see which side wins by value. The NEWS PULSE feed starts all-NFL and
// refocuses to the players in the trade on submit. Epic 8 (auth) layers a League
// Selector + roster multi-select + team-focused RSS on top of this.
export default function TradeCalculator({ news }: { news: NewsItem[] }) {
  const [players, setPlayers] = useState<SnapshotPlayer[] | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "empty">("loading");
  const [q, setQ] = useState("");
  const [pos, setPos] = useState<Pos>("ALL");
  const [team, setTeam] = useState("ALL");
  const [sideA, setSideA] = useState<SnapshotPlayer[]>([]);
  const [sideB, setSideB] = useState<SnapshotPlayer[]>([]);
  const [submitted, setSubmitted] = useState(false);

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
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-display-md">Trade Calculator</h1>
          <p className="mt-2 text-body text-ink-muted">
            Search any NFL player, stack both sides, see who wins by value — no league needed.
          </p>
        </div>
        {/* ponytail: unauth scope is fixed to all-NFL; it flips to the traded
            players on submit. Epic 8 (auth) replaces this with a <LeagueSelector/>
            + an all-NFL ↔ league/team scope toggle. */}
        <span className="rounded-full border border-hairline px-3 py-1.5 text-label text-ink-muted">
          Scope: <span className="text-ink">{submitted && tradePlayers.length ? "This trade" : "All NFL"}</span>
        </span>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
        <div>
          {/* search + filters — instant, fully client-side over the in-memory snapshot */}
          <div className="mb-4 flex flex-wrap items-center gap-3">
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

          {/* results — add to either side */}
          <ul className="glass divide-y divide-hairline/60" aria-label="Search results">
            {results.map((p) => (
              <li key={p.id} className="flex items-center gap-3 px-4 py-2.5 text-body">
                <span className="min-w-0 flex-1 truncate">
                  <span className="font-medium">{p.full_name}</span>{" "}
                  <span className="text-ink-muted">{norm(p.position)} · {p.nfl_team ?? "FA"}</span>
                </span>
                <span className="font-mono text-label text-accent">{pval(p).toFixed(0)}</span>
                <button type="button" onClick={() => add(p, "A")}
                  className="rounded-full border border-hairline px-2.5 py-1 text-label transition hover:border-accent"
                  aria-label={`Add ${p.full_name} to side A`}>+ A</button>
                <button type="button" onClick={() => add(p, "B")}
                  className="rounded-full border border-hairline px-2.5 py-1 text-label transition hover:border-accent"
                  aria-label={`Add ${p.full_name} to side B`}>+ B</button>
              </li>
            ))}
            {!results.length && (
              <li className="px-4 py-6 text-center text-label text-ink-muted">No players match.</li>
            )}
          </ul>

          {/* the two sides + verdict */}
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <Side label="Side A" total={totalA} players={sideA} onRemove={(id) => remove(id, "A")} />
            <Side label="Side B" total={totalB} players={sideB} onRemove={(id) => remove(id, "B")} />
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
        </div>

        {/* live RSS news feed — all-NFL until submit, then scoped to the trade */}
        <aside className="glass h-fit p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-label text-ink-muted">NEWS PULSE</h3>
            <span className="text-label text-ink-muted/70">{submitted && tradePlayers.length ? "This trade" : "All NFL"}</span>
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
  label, total, players, onRemove,
}: {
  label: string;
  total: number;
  players: SnapshotPlayer[];
  onRemove: (id: string) => void;
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
            <span key={p.id} className="inline-flex items-center gap-1.5 rounded-full border border-hairline bg-surface px-2.5 py-1 text-label">
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
