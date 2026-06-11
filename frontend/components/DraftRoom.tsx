"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import type { PlayerWithValue } from "@/lib/types";
import {
  SMORES_ROSTER, BENCH_SIZE, fillRoster, scarcity, teamOnClock, myPickNumbers,
} from "@/lib/draft";
import { mapPicks, type MappedPick } from "@/lib/sleeperDraft";
import { mapEspnPicks } from "@/lib/espnDraft";
import { useSleeperSync } from "@/lib/useSleeperSync";
import { useEspnSync } from "@/lib/useEspnSync";

type Mode = "manual" | "sleeper" | "espn";
const POSITIONS = ["ALL", "QB", "RB", "WR", "TE", "K", "DEF"] as const;
const ROSTER_SPOTS = SMORES_ROSTER.length + BENCH_SIZE;

export default function DraftRoom({ players }: { players: PlayerWithValue[] }) {
  const [numTeams, setNumTeams] = useState(12);
  const [mySlot, setMySlot] = useState(6);
  const [manualPicks, setManualPicks] = useState<MappedPick[]>([]);
  const [q, setQ] = useState("");
  const [pos, setPos] = useState<(typeof POSITIONS)[number]>("ALL");

  // ── live sync (Sleeper reliable path, ESPN best-effort) ──────────────────
  const [mode, setMode] = useState<Mode>("manual");
  const [idInput, setIdInput] = useState("");
  const [connectedId, setConnectedId] = useState("");
  const sleeperSync = useSleeperSync(mode === "sleeper" ? connectedId : "", mode === "sleeper");
  const espnSync = useEspnSync(mode === "espn", mode === "espn" ? connectedId || undefined : undefined);

  const sleeperMap = useMemo(
    () => new Map(players.filter((p) => p.sleeper_id).map((p) => [p.sleeper_id, p])),
    [players],
  );
  const espnMap = useMemo(
    () => new Map(players.filter((p) => p.espn_id).map((p) => [p.espn_id as string, p])),
    [players],
  );

  // active live source (for status badge + fallback)
  const live = mode === "sleeper" ? sleeperSync : mode === "espn" ? espnSync : null;
  const liveDraftStatus =
    mode === "sleeper" ? sleeperSync.draft?.status : mode === "espn" ? espnSync.meta?.status : undefined;

  const syncedPicks = useMemo<MappedPick[]>(() => {
    if (mode === "sleeper") return mapPicks(sleeperSync.picks, sleeperMap);
    if (mode === "espn") return mapEspnPicks(espnSync.picks, espnMap, numTeams);
    return [];
  }, [mode, sleeperSync.picks, espnSync.picks, sleeperMap, espnMap, numTeams]);

  // adopt league size from the feed
  useEffect(() => {
    const t = mode === "sleeper" ? sleeperSync.draft?.settings?.teams : mode === "espn" ? espnSync.meta?.teams : undefined;
    if (t) setNumTeams(t);
  }, [sleeperSync.draft, espnSync.meta, mode]);

  const picks = mode === "manual" ? manualPicks : syncedPicks;

  const draftedIds = useMemo(() => new Set(picks.map((p) => p.player.id)), [picks]);
  const currentPickNo = picks.length + 1;
  const onClock = teamOnClock(currentPickNo, numTeams);
  const round = Math.ceil(currentPickNo / numTeams);
  const myUpcoming = myPickNumbers(numTeams, mySlot, ROSTER_SPOTS).find((p) => p >= currentPickNo);
  const picksUntilMe = myUpcoming ? myUpcoming - currentPickNo : null;
  const isMyPick = onClock === mySlot;

  const available = useMemo(() => players.filter((p) => !draftedIds.has(p.id)), [players, draftedIds]);
  const myRoster = useMemo(
    () => fillRoster(picks.filter((p) => p.team === mySlot).map((p) => p.player)),
    [picks, mySlot],
  );
  const scarce = useMemo(() => scarcity(available), [available]);

  const shown = useMemo(() => {
    let r = available;
    if (pos !== "ALL") r = r.filter((p) => (p.position ?? "") === pos);
    if (q.trim()) {
      const n = q.toLowerCase();
      r = r.filter((p) => p.full_name.toLowerCase().includes(n) || (p.nfl_team ?? "").toLowerCase().includes(n));
    }
    return r.slice(0, 60);
  }, [available, q, pos]);

  // ── manual actions ─────────────────────────────────────────────────────
  function draft(player: PlayerWithValue, team = onClock) {
    setManualPicks((cur) => [...cur, { pickNo: cur.length + 1, team, player }]);
  }
  const undo = () => setManualPicks((cur) => cur.slice(0, -1));
  const reset = () => setManualPicks([]);
  function simToMyPick() {
    setManualPicks((cur) => {
      const next = [...cur];
      const taken = new Set(next.map((p) => p.player.id));
      let guard = 0;
      while (guard++ < numTeams * ROSTER_SPOTS) {
        const pickNo = next.length + 1;
        const team = teamOnClock(pickNo, numTeams);
        if (team === mySlot) break;
        const pool = players.filter((p) => !taken.has(p.id));
        if (!pool.length) break;
        const needs = new Set(fillRoster(next.filter((p) => p.team === team).map((p) => p.player)).needs);
        const pick =
          pool.find((p) => needs.has(p.position ?? "") ||
            (needs.has("FLEX") && ["RB", "WR", "TE"].includes(p.position ?? "")) ||
            (needs.has("OP") && ["QB", "RB", "WR", "TE"].includes(p.position ?? ""))) ?? pool[0];
        next.push({ pickNo, team, player: pick });
        taken.add(pick.id);
      }
      return next;
    });
  }

  // ── sync controls ────────────────────────────────────────────────────────
  function connect(source: Exclude<Mode, "manual">) {
    if (source === "sleeper" && !idInput.trim()) return; // sleeper needs a draft_id
    setConnectedId(idInput.trim());
    setMode(source);
  }
  function fallbackToManual() {
    setManualPicks(syncedPicks); // keep what synced so far (D7)
    setMode("manual");
    setConnectedId("");
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div>
        {/* sync bar */}
        <div className="glass mb-4 flex flex-wrap items-center gap-3 p-3">
          <div className="inline-flex rounded-full border border-hairline p-1 text-label">
            <button onClick={() => setMode("manual")}
              className={`rounded-full px-3 py-1 transition ${mode === "manual" ? "bg-accent text-bg" : "text-ink-muted hover:text-ink"}`}>Manual</button>
            <button onClick={() => connect("sleeper")}
              className={`rounded-full px-3 py-1 transition ${mode === "sleeper" ? "bg-accent text-bg" : "text-ink-muted hover:text-ink"}`}>Sleeper Live</button>
            <button onClick={() => connect("espn")}
              className={`rounded-full px-3 py-1 transition ${mode === "espn" ? "bg-accent text-bg" : "text-ink-muted hover:text-ink"}`}>ESPN Live</button>
          </div>
          <input value={idInput} onChange={(e) => setIdInput(e.target.value)}
            placeholder={mode === "espn" ? "ESPN league_id (or env)" : "Sleeper draft_id…"}
            className="w-48 rounded-full border border-hairline bg-surface px-3 py-1.5 text-label outline-none focus:border-accent" />
          {live && <SyncBadge source={mode} status={live.status} lastSync={live.lastSync} draftStatus={liveDraftStatus} />}
          {mode !== "manual" && (
            <button onClick={fallbackToManual}
              className="ml-auto rounded-full border border-hairline px-3 py-1.5 text-label transition hover:bg-surface-elevated">
              ↩ Switch to manual (keep picks)
            </button>
          )}
        </div>

        {/* error → prompt fallback (D7) */}
        {live && live.status === "error" && (
          <div className="mb-4 rounded-xl border border-red-400/40 bg-red-400/5 p-3 text-label text-red-300">
            {mode.toUpperCase()} feed stalled ({live.error}). Still retrying — or switch to manual to keep drafting on this board.
          </div>
        )}

        {/* status */}
        <div className="glass mb-4 flex flex-wrap items-center gap-4 p-4">
          <div>
            <div className="text-label text-ink-muted">ROUND {round} · PICK {currentPickNo}</div>
            <div className={`font-display text-heading ${isMyPick ? "text-accent" : ""}`}>
              {isMyPick ? "YOUR PICK" : `Team ${onClock} on the clock`}
            </div>
          </div>
          {picksUntilMe != null && !isMyPick && <div className="text-label text-ink-muted">your pick in {picksUntilMe}</div>}
          {mode === "manual" && (
            <div className="ml-auto flex items-center gap-2">
              <button onClick={simToMyPick} className="rounded-full border border-hairline px-3 py-1.5 text-label transition hover:bg-surface-elevated">Sim to my pick</button>
              <button onClick={undo} disabled={!manualPicks.length} className="rounded-full border border-hairline px-3 py-1.5 text-label transition hover:bg-surface-elevated disabled:opacity-40">Undo</button>
              <button onClick={reset} disabled={!manualPicks.length} className="rounded-full border border-hairline px-3 py-1.5 text-label transition hover:bg-surface-elevated disabled:opacity-40">Reset</button>
            </div>
          )}
        </div>

        {/* controls */}
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search…"
            className="w-48 rounded-full border border-hairline bg-surface px-4 py-2 text-body outline-none focus:border-accent" />
          {POSITIONS.map((p) => (
            <button key={p} onClick={() => setPos(p)}
              className={`rounded-full px-3 py-1.5 text-label transition ${pos === p ? "bg-accent text-bg" : "border border-hairline text-ink-muted hover:text-ink"}`}>{p}</button>
          ))}
          <span className="ml-auto text-label text-ink-muted">{available.length} available</span>
        </div>

        {/* best available */}
        <div className="glass divide-y divide-hairline/60">
          {shown.map((p, i) => (
            <div key={p.id} className="flex items-center gap-3 px-4 py-2.5 transition hover:bg-surface-elevated">
              <span className="w-8 font-mono text-ink-muted">{p.value?.rank ?? i + 1}</span>
              <Link href={`/players/${p.id}`} className="min-w-0 flex-1 truncate font-medium transition hover:text-accent">{p.full_name}</Link>
              <span className="w-10 text-label text-ink-muted">{p.position}</span>
              <span className="w-10 text-label text-ink-muted">{p.nfl_team ?? "FA"}</span>
              <span className="w-14 text-right font-mono text-accent">{p.value?.vor != null ? p.value.vor.toFixed(1) : "—"}</span>
              {mode === "manual" ? (
                <button onClick={() => draft(p)}
                  className={`rounded-full px-3 py-1 text-label transition ${isMyPick ? "bg-accent text-bg" : "border border-hairline text-ink hover:bg-surface"}`}>
                  {isMyPick ? "Draft (you)" : `→ Team ${onClock}`}
                </button>
              ) : (
                <span className="w-20 text-right text-label text-ink-muted/60">feed-driven</span>
              )}
            </div>
          ))}
          {!shown.length && <div className="px-4 py-8 text-center text-label text-ink-muted">No players match.</div>}
        </div>
      </div>

      {/* SIDEBAR */}
      <aside className="space-y-6">
        <div className="glass p-4">
          <h3 className="mb-3 text-label text-ink-muted">DRAFT SETTINGS</h3>
          <label className="flex items-center justify-between py-1 text-body">
            Teams
            <input type="number" min={4} max={16} value={numTeams} disabled={mode !== "manual"}
              onChange={(e) => setNumTeams(+e.target.value)}
              className="w-16 rounded border border-hairline bg-surface px-2 py-1 text-right font-mono disabled:opacity-50" />
          </label>
          <label className="flex items-center justify-between py-1 text-body">
            My slot
            <input type="number" min={1} max={numTeams} value={mySlot} onChange={(e) => setMySlot(+e.target.value)}
              className="w-16 rounded border border-hairline bg-surface px-2 py-1 text-right font-mono" />
          </label>
        </div>

        <div className="glass p-4">
          <h3 className="mb-3 text-label text-ink-muted">MY ROSTER &amp; NEEDS</h3>
          <div className="space-y-1.5 text-body">
            {myRoster.starters.map((s, i) => (
              <div key={i} className="flex items-center justify-between">
                <span className="text-ink-muted">{s.slot}</span>
                {s.player ? <span className="truncate">{s.player.full_name}</span> : <span className="text-accent">— need —</span>}
              </div>
            ))}
          </div>
          <div className="mt-3 border-t border-hairline pt-3 text-label text-ink-muted">
            Bench {myRoster.bench.length}/{BENCH_SIZE} · Proj starters <span className="font-mono text-ink">{myRoster.projectedPoints.toFixed(0)}</span>
          </div>
        </div>

        <div className="glass p-4">
          <h3 className="mb-3 text-label text-ink-muted">POSITIONAL SCARCITY</h3>
          <div className="space-y-2">
            {["QB", "RB", "WR", "TE"].map((position) => {
              const n = scarce[position] ?? 0;
              const pct = Math.min(100, (n / 30) * 100);
              const color = n < 6 ? "#E0573A" : n < 14 ? "#E0A33A" : "var(--accent)";
              return (
                <div key={position} className="flex items-center gap-2 text-label">
                  <span className="w-8 text-ink-muted">{position}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-hairline">
                    <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
                  </div>
                  <span className="w-8 text-right font-mono text-ink-muted">{n}</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="glass p-4">
          <h3 className="mb-3 text-label text-ink-muted">RECENT PICKS</h3>
          <div className="space-y-1 text-label">
            {picks.slice(-8).reverse().map((p) => (
              <div key={p.pickNo} className="flex items-center gap-2">
                <span className="font-mono text-ink-muted">{Math.ceil(p.pickNo / numTeams)}.{((p.pickNo - 1) % numTeams) + 1}</span>
                <span className="flex-1 truncate">{p.player.full_name}</span>
                <span className={p.team === mySlot ? "text-accent" : "text-ink-muted"}>T{p.team}</span>
              </div>
            ))}
            {!picks.length && <div className="text-ink-muted">No picks yet.</div>}
          </div>
        </div>
      </aside>
    </div>
  );
}

function SyncBadge({ source, status, lastSync, draftStatus }: {
  source: string; status: string; lastSync: number | null; draftStatus?: string;
}) {
  const map: Record<string, { dot: string; text: string }> = {
    connecting: { dot: "#E0A33A", text: "connecting…" },
    live: { dot: "#33D17A", text: draftStatus === "complete" ? "complete" : "live" },
    error: { dot: "#E0573A", text: "stalled" },
    idle: { dot: "#8A93A6", text: "idle" },
  };
  const s = map[status] ?? map.idle;
  const label = source === "espn" ? "ESPN" : "Sleeper";
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-hairline px-3 py-1.5 text-label">
      <span className="h-2 w-2 rounded-full" style={{ background: s.dot }} />
      {label} {s.text}
      {lastSync && status === "live" && <span className="text-ink-muted/60">· {new Date(lastSync).toLocaleTimeString()}</span>}
    </span>
  );
}
