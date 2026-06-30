"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import type { PlayerWithValue } from "@/lib/types";
import { fillRoster, scarcity, teamOnClock, myPickNumbers } from "@/lib/draft";
import { defaultConfig, defaultTeams, trackedPositions, applyRules, rulesFromConfig, type LeagueConfig } from "@/lib/leagueConfig";
import { pickForTeam, detectRuns, scoreBoard, candidatePool } from "@/lib/draftAI";
import { mapPicks, type MappedPick } from "@/lib/sleeperDraft";
import { mapEspnPicks } from "@/lib/espnDraft";
import { useSleeperSync } from "@/lib/useSleeperSync";
import { useEspnSync } from "@/lib/useEspnSync";
import { saveSnapshot } from "@/lib/draftStore";
import { projPoints } from "@/lib/score";
import LeagueImport, { type EspnCreds } from "./LeagueImport";
import AllTeamsBoard from "./AllTeamsBoard";
import DraftAnalysis from "./DraftAnalysis";
import DraftEndCard from "./DraftEndCard";

type Mode = "manual" | "sleeper" | "espn";
type View = "board" | "teams" | "analysis";
const POSITIONS = ["ALL", "QB", "RB", "WR", "TE", "K", "DST"] as const;

// Optional stat columns the user can toggle onto the best-available table (#2).
const STAT_COLS: { key: string; label: string; num?: boolean; get: (p: PlayerWithValue) => string }[] = [
  { key: "pos", label: "Pos", get: (p) => p.position ?? "—" },
  { key: "team", label: "Tm", get: (p) => p.nfl_team ?? "FA" },
  { key: "bye", label: "Bye", get: (p) => (p.bye_week != null ? String(p.bye_week) : "—") },
  { key: "pts", label: "Pts", num: true, get: (p) => { const v = projPoints(p); return v > 0 ? v.toFixed(0) : "—"; } },
  { key: "vor", label: "VOR", num: true, get: (p) => (p.value?.vor != null ? p.value.vor.toFixed(1) : "—") },
  { key: "adp", label: "ADP", num: true, get: (p) => (p.value?.adp != null ? p.value.adp.toFixed(0) : "—") },
  { key: "boom", label: "Boom", num: true, get: (p) => (p.value?.boom != null ? p.value.boom.toFixed(0) : "—") },
  { key: "bust", label: "Bust", num: true, get: (p) => (p.value?.bust != null ? p.value.bust.toFixed(0) : "—") },
  { key: "age", label: "Age", num: true, get: (p) => (p.age != null ? String(p.age) : "—") },
  { key: "exp", label: "Exp", num: true, get: (p) => (p.years_exp != null ? String(p.years_exp) : "—") },
  { key: "inj", label: "Inj", get: (p) => p.injury_status ?? "—" },
];

// `savedLeagues` (Epic 8 authed draft): when present, the platform selector + import are replaced
// by a 2-3 league toggle that swaps in each connected league's stored rules. Unauth passes none.
export interface SavedLeague {
  id: string;
  name: string;
  config: LeagueConfig;
}

export default function DraftRoom({
  players,
  savedLeagues,
}: {
  players: PlayerWithValue[];
  savedLeagues?: SavedLeague[];
}) {
  const authed = !!savedLeagues?.length;
  const [config, setConfig] = useState<LeagueConfig>(
    () => savedLeagues?.[0]?.config ?? defaultConfig(12),
  );
  const [leagueId, setLeagueId] = useState(savedLeagues?.[0]?.id ?? "");
  const numTeams = config.numTeams;
  const ROSTER_SPOTS = config.rosterSlots.length + config.benchSize;

  const [mySlot, setMySlot] = useState(6);
  const [manualPicks, setManualPicks] = useState<MappedPick[]>([]);
  const [q, setQ] = useState("");
  const [pos, setPos] = useState<(typeof POSITIONS)[number]>("ALL");
  const [view, setView] = useState<View>("board");
  const [cols, setCols] = useState<string[]>(["pos", "team", "pts"]);
  const [showCols, setShowCols] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [showRules, setShowRules] = useState(false);
  const [endDismissed, setEndDismissed] = useState(false);

  // ── live sync (Sleeper reliable, ESPN best-effort) ───────────────────────
  const [mode, setMode] = useState<Mode>("manual");
  // Which live source the user is configuring — reveals its id input inline (4.7), so the
  // Sleeper/ESPN id lives under its own option instead of always showing on the manual board.
  const [liveSetup, setLiveSetup] = useState<Exclude<Mode, "manual"> | null>(null);
  const [idInput, setIdInput] = useState("");
  const [connectedId, setConnectedId] = useState("");
  const [espnCreds, setEspnCreds] = useState<EspnCreds | null>(null);
  const sleeperSync = useSleeperSync(mode === "sleeper" ? connectedId : "", mode === "sleeper");
  const espnSync = useEspnSync(
    mode === "espn",
    mode === "espn" ? connectedId || undefined : undefined,
    espnCreds?.season,
    espnCreds ? { s2: espnCreds.s2, swid: espnCreds.swid } : undefined,
  );

  const sleeperMap = useMemo(
    () => new Map(players.filter((p) => p.sleeper_id).map((p) => [p.sleeper_id, p])),
    [players],
  );
  const espnMap = useMemo(
    () => new Map(players.filter((p) => p.espn_id).map((p) => [p.espn_id as string, p])),
    [players],
  );

  const live = mode === "sleeper" ? sleeperSync : mode === "espn" ? espnSync : null;
  const liveDraftStatus =
    mode === "sleeper" ? sleeperSync.draft?.status : mode === "espn" ? espnSync.meta?.status : undefined;

  const syncedPicks = useMemo<MappedPick[]>(() => {
    if (mode === "sleeper") return mapPicks(sleeperSync.picks, sleeperMap);
    if (mode === "espn") return mapEspnPicks(espnSync.picks, espnMap, numTeams);
    return [];
  }, [mode, sleeperSync.picks, espnSync.picks, sleeperMap, espnMap, numTeams]);

  // adopt league size from the feed (preserving any renamed teams)
  useEffect(() => {
    const t = mode === "sleeper" ? sleeperSync.draft?.settings?.teams : mode === "espn" ? espnSync.meta?.teams : undefined;
    if (t && t !== numTeams) setConfig((c) => ({ ...c, numTeams: t, teams: defaultTeams(t, c.teams) }));
  }, [sleeperSync.draft, espnSync.meta, mode, numTeams]);

  const picks = mode === "manual" ? manualPicks : syncedPicks;

  const draftedIds = useMemo(() => new Set(picks.map((p) => p.player.id)), [picks]);
  const currentPickNo = picks.length + 1;
  const onClock = teamOnClock(currentPickNo, numTeams);
  const round = Math.ceil(currentPickNo / numTeams);
  const myUpcoming = myPickNumbers(numTeams, mySlot, ROSTER_SPOTS).find((p) => p >= currentPickNo);
  const picksUntilMe = myUpcoming ? myUpcoming - currentPickNo : null;
  const isMyPick = onClock === mySlot;
  const totalSpots = numTeams * ROSTER_SPOTS;
  const complete = picks.length >= totalSpots;

  const available = useMemo(() => players.filter((p) => !draftedIds.has(p.id)), [players, draftedIds]);
  const myRoster = useMemo(
    () => fillRoster(picks.filter((p) => p.team === mySlot).map((p) => p.player), config.rosterSlots),
    [picks, mySlot, config.rosterSlots],
  );
  const scarce = useMemo(() => scarcity(available), [available]);
  const runs = useMemo(() => detectRuns(picks, numTeams), [picks, numTeams]);
  const positionsTracked = useMemo(() => trackedPositions(config), [config]);

  // Positions still needed to fill an open STARTING slot (incl. flex/superflex eligibility).
  const neededPositions = useMemo(() => {
    const s = new Set<string>();
    myRoster.starters.forEach((slot, i) => {
      if (!slot.player) config.rosterSlots[i]?.eligible.forEach((e) => s.add(e === "DEF" ? "DST" : e));
    });
    return s;
  }, [myRoster, config.rosterSlots]);

  // Top recommendations for MY next pick, straight from the shared v2 policy (D7 — the same
  // scoreBoard the auto-draft and backtest use). Capped to the top projections for snappiness;
  // memoized so it only recomputes when the board changes, not on every keystroke.
  const recs = useMemo(() => {
    if (complete) return [];
    const myNos = myPickNumbers(numTeams, mySlot, ROSTER_SPOTS);
    const myPickNo = myNos.find((n) => n >= currentPickNo) ?? currentPickNo;
    const after = myNos.find((n) => n > myPickNo) ?? myPickNo + numTeams;
    const candidates = candidatePool(available);
    return scoreBoard({
      pool: candidates,
      teamPicks: picks.filter((p) => p.team === mySlot).map((p) => p.player),
      roster: config.rosterSlots,
      benchSize: config.benchSize,
      allPicks: picks,
      numTeams,
      picksUntilNext: after - myPickNo,
      round: Math.ceil(myPickNo / numTeams),
      totalRounds: ROSTER_SPOTS,
      randomness: 0,
    }).slice(0, 3);
  }, [available, picks, mySlot, numTeams, config, ROSTER_SPOTS, currentPickNo, complete]);

  // Legible "why" for a recommended player: need / scarcity / upside, in user terms.
  function rationaleChips(p: PlayerWithValue): string[] {
    const pos = p.position === "DEF" ? "DST" : p.position ?? "";
    const chips: string[] = [];
    if (neededPositions.has(pos)) chips.push("fills need");
    if ((scarce[pos] ?? 99) <= numTeams) chips.push("scarce");
    const mean = (p.value?.vor ?? 0) + (p.value?.replacement ?? 0);
    if (mean > 0 && (p.value?.boom ?? 0) > mean * 1.15) chips.push("upside");
    if (runs.hot.includes(pos)) chips.push("run on");
    return chips.length ? chips : ["best value"];
  }

  const shown = useMemo(() => {
    let r = available;
    if (pos !== "ALL") r = r.filter((p) => (p.position === "DEF" ? "DST" : p.position ?? "") === pos);
    if (q.trim()) {
      const n = q.toLowerCase();
      r = r.filter((p) => p.full_name.toLowerCase().includes(n) || (p.nfl_team ?? "").toLowerCase().includes(n));
    }
    return r.slice(0, 60);
  }, [available, q, pos]);

  const visibleCols = STAT_COLS.filter((c) => cols.includes(c.key));

  // persist snapshot for the standalone analysis page
  useEffect(() => {
    saveSnapshot({ config, picks, mySlot });
  }, [config, picks, mySlot]);

  useEffect(() => {
    if (!complete) setEndDismissed(false);
  }, [complete]);

  // ── manual actions ───────────────────────────────────────────────────────
  function draft(player: PlayerWithValue, team = onClock) {
    setManualPicks((cur) => [...cur, { pickNo: cur.length + 1, team, player }]);
  }
  const undo = () => setManualPicks((cur) => cur.slice(0, -1));
  const reset = () => setManualPicks([]);

  function nextPickAfter(team: number, fromPick: number): number {
    let n = fromPick + 1;
    const cap = totalSpots;
    while (n <= cap) {
      if (teamOnClock(n, numTeams) === team) return n;
      n++;
    }
    return cap + 1;
  }

  // AI-driven auto-pick used by both sims. `stopAtMe` powers "sim to my pick".
  function runSim(stopAtMe: boolean) {
    setManualPicks((cur) => {
      const next = [...cur];
      const taken = new Set(next.map((p) => p.player.id));
      let guard = 0;
      while (guard++ < totalSpots + 5) {
        const pickNo = next.length + 1;
        if (pickNo > totalSpots) break;
        const team = teamOnClock(pickNo, numTeams);
        if (stopAtMe && team === mySlot) break;
        // Cap the board before scoring — scoring the full ~4k pool per pick froze the auto-draft
        // (Epic 4 fix). candidatePool keeps the top projections + a few K/DST for late rounds.
        const pool = candidatePool(players.filter((p) => !taken.has(p.id)));
        if (!pool.length) break;
        const teamPicks = next.filter((p) => p.team === team).map((p) => p.player);
        const player =
          pickForTeam({
            pool,
            teamPicks,
            roster: config.rosterSlots,
            benchSize: config.benchSize,
            allPicks: next,
            numTeams,
            picksUntilNext: nextPickAfter(team, pickNo) - pickNo,
            round: Math.ceil(pickNo / numTeams),
            totalRounds: ROSTER_SPOTS,
            randomness: 0.06,
          }) ?? pool[0];
        next.push({ pickNo, team, player });
        taken.add(player.id);
      }
      return next;
    });
  }

  // ── league import / sync controls ─────────────────────────────────────────
  function handleSleeperImport(imported: LeagueConfig, liveDraftId: string | null) {
    setConfig(imported);
    setManualPicks([]);
    setShowImport(false);
    if (liveDraftId) {
      setIdInput(liveDraftId);
      setConnectedId(liveDraftId);
      setMode("sleeper");
    } else {
      setMode("manual");
    }
  }
  function handleEspnConnect(creds: EspnCreds) {
    setEspnCreds(creds);
    setConnectedId(creds.leagueId);
    setMode("espn");
    setShowImport(false);
  }
  function connect(source: Exclude<Mode, "manual">) {
    if (!idInput.trim()) return;
    setConnectedId(idInput.trim());
    setMode(source);
    setLiveSetup(null);
  }
  function updateRules(patch: Partial<ReturnType<typeof rulesFromConfig>>) {
    setConfig((c) => applyRules(c, { ...rulesFromConfig(c), ...patch }));
    setManualPicks([]); // roster shape changed → start the board fresh
  }
  function fallbackToManual() {
    setManualPicks(syncedPicks);
    setMode("manual");
    setConnectedId("");
    setLiveSetup(null);
  }
  function renameTeam(slot: number, name: string) {
    setConfig((c) => ({ ...c, teams: c.teams.map((t) => (t.slot === slot ? { ...t, name } : t)) }));
  }
  function toggleCol(key: string) {
    setCols((c) => (c.includes(key) ? c.filter((k) => k !== key) : [...c, key]));
  }
  // Authed league toggle: swap in the selected connected league's rules and clear the board.
  function pickLeague(id: string) {
    const lg = savedLeagues?.find((l) => l.id === id);
    if (!lg) return;
    setLeagueId(id);
    setConfig(lg.config);
    setManualPicks([]);
  }

  return (
    <div>
      {/* league bar */}
      <div className="glass mb-4 flex flex-wrap items-center gap-3 p-3">
        <div className="text-body">
          <span className="font-display text-heading">{config.name}</span>
          <span className="ml-2 text-label text-ink-muted">
            {numTeams} teams · {config.scoringLabel}
            {config.source !== "manual" && <span className="ml-1 text-accent">· {config.source}</span>}
          </span>
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <button
            onClick={() => setShowRules((s) => !s)}
            className="rounded-full border border-hairline px-3 py-1.5 text-label transition hover:bg-surface-elevated"
          >
            {showRules ? "✕ Close rules" : "⚙ League rules"}
          </button>
          {!authed && (
            <button
              onClick={() => setShowImport((s) => !s)}
              className="rounded-full border border-hairline px-3 py-1.5 text-label transition hover:bg-surface-elevated"
            >
              {showImport ? "✕ Close import" : "⚡ Import league (Sleeper / ESPN)"}
            </button>
          )}
        </div>
      </div>

      {showRules && <RulesEditor config={config} onChange={updateRules} imported={config.source !== "manual"} />}

      {showImport && !authed && (
        <LeagueImport
          onSleeperImport={handleSleeperImport}
          onEspnConnect={handleEspnConnect}
          onClose={() => setShowImport(false)}
        />
      )}

      {/* Authed: a 2-3 league toggle replaces the Manual/Sleeper/ESPN selector. */}
      {authed && savedLeagues!.length > 1 && (
        <div className="glass mb-4 flex flex-wrap items-center gap-2 p-3">
          <span className="text-label text-ink-muted">League:</span>
          <div className="inline-flex rounded-full border border-hairline p-1 text-label" role="group" aria-label="Select league">
            {savedLeagues!.map((l) => (
              <button key={l.id} type="button" onClick={() => pickLeague(l.id)} aria-pressed={leagueId === l.id}
                className={`max-w-[12rem] truncate rounded-full px-3 py-1 transition ${leagueId === l.id ? "bg-accent text-bg" : "text-ink-muted hover:text-ink"}`}>
                {l.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* sync bar (unauth only — authed draft is manual over the connected league's rules) */}
      {!authed && (
      <div className="glass mb-4 flex flex-wrap items-center gap-3 p-3">
        <div className="inline-flex rounded-full border border-hairline p-1 text-label">
          <button onClick={() => { setMode("manual"); setLiveSetup(null); }} className={`rounded-full px-3 py-1 transition ${mode === "manual" && !liveSetup ? "bg-accent text-bg" : "text-ink-muted hover:text-ink"}`}>Manual</button>
          <button onClick={() => setLiveSetup("sleeper")} className={`rounded-full px-3 py-1 transition ${mode === "sleeper" || liveSetup === "sleeper" ? "bg-accent text-bg" : "text-ink-muted hover:text-ink"}`}>Sleeper Live</button>
          <button onClick={() => setLiveSetup("espn")} className={`rounded-full px-3 py-1 transition ${mode === "espn" || liveSetup === "espn" ? "bg-accent text-bg" : "text-ink-muted hover:text-ink"}`}>ESPN Live</button>
        </div>
        {/* 4.7: the live id input belongs to the Sleeper/ESPN option, revealed on select — not the manual board. */}
        {liveSetup && (
          <div className="flex items-center gap-2">
            <input value={idInput} onChange={(e) => setIdInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && connect(liveSetup)}
              autoFocus
              placeholder={liveSetup === "espn" ? "ESPN league_id" : "Sleeper draft_id…"}
              className="w-48 rounded-full border border-hairline bg-surface px-3 py-1.5 text-label outline-none focus:border-accent" />
            <button onClick={() => connect(liveSetup)} disabled={!idInput.trim()}
              className="rounded-full bg-accent px-3 py-1.5 text-label text-bg transition hover:opacity-90 disabled:opacity-40">
              Connect {liveSetup === "espn" ? "ESPN" : "Sleeper"}
            </button>
          </div>
        )}
        {live && <SyncBadge source={mode} status={live.status} lastSync={live.lastSync} draftStatus={liveDraftStatus} />}
        {mode !== "manual" && (
          <button onClick={fallbackToManual} className="ml-auto rounded-full border border-hairline px-3 py-1.5 text-label transition hover:bg-surface-elevated">
            ↩ Switch to manual (keep picks)
          </button>
        )}
      </div>
      )}

      {live && live.status === "error" && (
        <div className="mb-4 rounded-xl border border-red-400/40 bg-red-400/5 p-3 text-label text-red-300">
          {mode.toUpperCase()} feed stalled ({live.error}). Still retrying — or switch to manual to keep drafting.
        </div>
      )}

      {/* view tabs */}
      <div className="mb-4 inline-flex rounded-full border border-hairline p-1 text-label">
        {(["board", "teams", "analysis"] as View[]).map((v) => (
          <button key={v} onClick={() => setView(v)}
            className={`rounded-full px-4 py-1 capitalize transition ${view === v ? "bg-accent text-bg" : "text-ink-muted hover:text-ink"}`}>
            {v === "teams" ? "All teams" : v}
          </button>
        ))}
      </div>

      {/* end card */}
      {complete && !endDismissed && (
        <DraftEndCard
          picks={picks}
          config={config}
          mySlot={mySlot}
          onViewAnalysis={() => setView("analysis")}
          onDismiss={() => setEndDismissed(true)}
        />
      )}

      {view === "teams" && <AllTeamsBoard config={config} picks={picks} mySlot={mySlot} onRename={renameTeam} />}
      {view === "analysis" && <DraftAnalysis picks={picks} config={config} mySlot={mySlot} />}

      {view === "board" && (
        <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
          <div>
            {/* status */}
            <div className="glass mb-4 flex flex-wrap items-center gap-4 p-4">
              <div>
                <div className="text-label text-ink-muted">ROUND {round} · PICK {currentPickNo}</div>
                <div className={`font-display text-heading ${isMyPick ? "text-accent" : ""}`}>
                  {complete ? "Draft complete" : isMyPick ? "YOUR PICK" : `${config.teams.find((t) => t.slot === onClock)?.name ?? `Team ${onClock}`} on the clock`}
                </div>
              </div>
              {picksUntilMe != null && !isMyPick && !complete && <div className="text-label text-ink-muted">your pick in {picksUntilMe}</div>}
              {mode === "manual" && (
                <div className="ml-auto flex items-center gap-2">
                  <button onClick={() => runSim(true)} disabled={complete} className="rounded-full border border-hairline px-3 py-1.5 text-label transition hover:bg-surface-elevated disabled:opacity-40">Sim to my pick</button>
                  <button onClick={() => runSim(false)} disabled={complete} className="rounded-full border border-hairline px-3 py-1.5 text-label transition hover:bg-surface-elevated disabled:opacity-40">Auto-draft all</button>
                  <button onClick={undo} disabled={!manualPicks.length} className="rounded-full border border-hairline px-3 py-1.5 text-label transition hover:bg-surface-elevated disabled:opacity-40">Undo</button>
                  <button onClick={reset} disabled={!manualPicks.length} className="rounded-full border border-hairline px-3 py-1.5 text-label transition hover:bg-surface-elevated disabled:opacity-40">Reset</button>
                </div>
              )}
            </div>

            {/* controls */}
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search…"
                className="w-44 rounded-full border border-hairline bg-surface px-4 py-2 text-body outline-none focus:border-accent" />
              {POSITIONS.map((p) => (
                <button key={p} onClick={() => setPos(p)}
                  className={`rounded-full px-3 py-1.5 text-label transition ${pos === p ? "bg-accent text-bg" : "border border-hairline text-ink-muted hover:text-ink"}`}>{p}</button>
              ))}
              <div className="relative ml-auto">
                <button onClick={() => setShowCols((s) => !s)}
                  className="rounded-full border border-hairline px-3 py-1.5 text-label text-ink-muted transition hover:text-ink">
                  + Stats
                </button>
                {showCols && (
                  <div className="absolute right-0 z-20 mt-2 w-44 rounded-xl border border-hairline bg-surface p-2 shadow-lg" style={{ boxShadow: "var(--glow)" }}>
                    {STAT_COLS.map((c) => (
                      <label key={c.key} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-label transition hover:bg-surface-elevated">
                        <input type="checkbox" checked={cols.includes(c.key)} onChange={() => toggleCol(c.key)} className="accent-[var(--accent)]" />
                        {c.label}
                      </label>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* best available — now a real table with headers (#2) */}
            <div className="glass overflow-hidden">
              <table className="w-full text-left text-body">
                <thead className="border-b border-hairline text-label text-ink-muted">
                  <tr>
                    <th className="px-3 py-2.5 font-normal">#</th>
                    <th className="px-2 py-2.5 font-normal">Player</th>
                    {visibleCols.map((c) => (
                      <th key={c.key} className={`px-2 py-2.5 font-normal ${c.num ? "text-right" : ""}`}>{c.label}</th>
                    ))}
                    <th className="px-3 py-2.5" />
                  </tr>
                </thead>
                <tbody>
                  {shown.map((p, i) => (
                    <tr key={p.id} className="border-b border-hairline/50 transition hover:bg-surface-elevated">
                      <td className="px-3 py-2 font-mono text-ink-muted">{p.value?.rank ?? i + 1}</td>
                      <td className="px-2 py-2">
                        <Link href={`/players/${p.id}`} className="font-medium transition hover:text-accent">{p.full_name}</Link>
                      </td>
                      {visibleCols.map((c) => (
                        <td key={c.key} className={`px-2 py-2 text-label ${c.num ? "text-right font-mono" : "text-ink-muted"} ${c.key === "vor" ? "text-accent" : ""}`}>
                          {c.get(p)}
                        </td>
                      ))}
                      <td className="px-3 py-2 text-right">
                        {mode === "manual" ? (
                          <button onClick={() => draft(p)} disabled={complete}
                            className={`rounded-full px-3 py-1 text-label transition disabled:opacity-40 ${isMyPick ? "bg-accent text-bg" : "border border-hairline text-ink hover:bg-surface"}`}>
                            {isMyPick ? "Draft" : `→ ${config.teams.find((t) => t.slot === onClock)?.name ?? `T${onClock}`}`}
                          </button>
                        ) : (
                          <span className="text-label text-ink-muted/60">feed</span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {!shown.length && (
                    <tr><td colSpan={visibleCols.length + 3} className="px-4 py-8 text-center text-label text-ink-muted">No players match.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* SIDEBAR */}
          <aside className="space-y-6">
            {/* Recommended picks (#4): the shared v2 policy's top suggestions for your next
                pick, with a legible why (need / scarcity / upside). Manual + synced boards
                render this identically — same policy, same data (D7). */}
            {!complete && recs.length > 0 && (
              <div className="glass p-4">
                <h3 className="mb-3 text-label text-ink-muted">
                  RECOMMENDED{isMyPick ? " · YOUR PICK" : picksUntilMe != null ? ` · IN ${picksUntilMe}` : ""}
                </h3>
                <ol className="space-y-3">
                  {recs.map(({ player }, idx) => (
                    <li key={player.id} className="flex flex-col gap-1.5">
                      <div className="flex items-center gap-2">
                        <span className="w-4 shrink-0 font-mono text-label text-ink-muted">{idx + 1}</span>
                        <Link href={`/players/${player.id}`} className="min-w-0 flex-1 truncate font-medium transition hover:text-accent">
                          {player.full_name}
                        </Link>
                        <span className="shrink-0 text-label text-ink-muted/70">{player.position === "DEF" ? "DST" : player.position}</span>
                        {mode === "manual" && isMyPick && (
                          <button onClick={() => draft(player)} disabled={complete}
                            className="shrink-0 rounded-full bg-accent px-2.5 py-0.5 text-label text-bg transition hover:opacity-90 disabled:opacity-40">
                            Draft
                          </button>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-1 pl-6">
                        {rationaleChips(player).map((c) => (
                          <span key={c} className="rounded-full border border-hairline px-2 py-0.5 text-label text-ink-muted">{c}</span>
                        ))}
                      </div>
                    </li>
                  ))}
                </ol>
              </div>
            )}

            <div className="glass p-4">
              <h3 className="mb-3 text-label text-ink-muted">DRAFT SETTINGS</h3>
              <label className="flex items-center justify-between py-1 text-body">
                Teams
                <input type="number" min={4} max={16} value={numTeams} disabled={mode !== "manual" || config.source !== "manual"}
                  onChange={(e) => setConfig((c) => ({ ...c, numTeams: +e.target.value, teams: defaultTeams(+e.target.value, c.teams) }))}
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
                Bench {myRoster.bench.length}/{config.benchSize} · Proj starters <span className="font-mono text-ink">{myRoster.projectedPoints.toFixed(0)}</span>
              </div>
            </div>

            <div className="glass p-4">
              <h3 className="mb-3 text-label text-ink-muted">POSITIONAL SCARCITY</h3>
              <div className="space-y-2">
                {positionsTracked.map((position) => {
                  const n = scarce[position] ?? 0;
                  const pct = Math.min(100, (n / 30) * 100);
                  const color = n < 6 ? "#E0573A" : n < 14 ? "#E0A33A" : "var(--accent)";
                  const hot = runs.hot.includes(position);
                  return (
                    <div key={position} className="flex items-center gap-2 text-label">
                      <span className="w-9 text-ink-muted">{position}</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-hairline">
                        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
                      </div>
                      {hot && <span title="positional run underway" className="text-[10px] text-[#E0573A]">🔥</span>}
                      <span className="w-7 text-right font-mono text-ink-muted">{n}</span>
                    </div>
                  );
                })}
              </div>
              <div className="mt-2 text-[10px] text-ink-muted/70">starter-caliber left · 🔥 = run underway</div>
            </div>

            <div className="glass p-4">
              <h3 className="mb-3 text-label text-ink-muted">RECENT PICKS</h3>
              <div className="space-y-1 text-label">
                {picks.slice(-8).reverse().map((p) => (
                  <div key={p.pickNo} className="flex items-center gap-2">
                    <span className="font-mono text-ink-muted">{Math.ceil(p.pickNo / numTeams)}.{((p.pickNo - 1) % numTeams) + 1}</span>
                    <span className="flex-1 truncate">{p.player.full_name}</span>
                    <span className={p.team === mySlot ? "text-accent" : "text-ink-muted"}>{config.teams.find((t) => t.slot === p.team)?.name?.slice(0, 8) ?? `T${p.team}`}</span>
                  </div>
                ))}
                {!picks.length && <div className="text-ink-muted">No picks yet.</div>}
              </div>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}

// Pre-draft league-rules editor (4.1/4.3). Default = superflex 2QB. Editing a rule rebuilds the
// roster shape (applyRules) and restarts the board. Imported leagues are read-only here — their
// real rules win — so the editor shows them but defers edits to a re-import.
function RulesEditor({
  config,
  onChange,
  imported,
}: {
  config: LeagueConfig;
  onChange: (patch: Partial<ReturnType<typeof rulesFromConfig>>) => void;
  imported: boolean;
}) {
  const r = rulesFromConfig(config);
  const Toggle = ({ label, on, set }: { label: string; on: boolean; set: (v: boolean) => void }) => (
    <button
      role="switch"
      aria-checked={on}
      aria-label={label}
      disabled={imported}
      onClick={() => set(!on)}
      className={`flex items-center justify-between gap-3 rounded-lg border border-hairline px-3 py-2 text-body transition disabled:opacity-50 ${on ? "bg-surface-elevated" : "hover:bg-surface-elevated"}`}
    >
      <span>{label}</span>
      <span className={`relative h-5 w-9 shrink-0 rounded-full transition ${on ? "bg-accent" : "bg-hairline"}`}>
        <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-bg transition-all ${on ? "left-[18px]" : "left-0.5"}`} />
      </span>
    </button>
  );
  return (
    <div className="glass mb-4 p-4" style={{ boxShadow: "var(--glow)" }}>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-display text-heading">League rules</h3>
        <span className="text-label text-ink-muted">{imported ? `imported from ${config.source} — re-import to change` : "default · superflex 2QB"}</span>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        <Toggle label="Superflex (2QB)" on={r.superflex} set={(v) => onChange({ superflex: v })} />
        <Toggle label="Start a Kicker" on={r.useK} set={(v) => onChange({ useK: v })} />
        <Toggle label="Start a D/ST" on={r.useDST} set={(v) => onChange({ useDST: v })} />
        <label className="flex items-center justify-between gap-3 rounded-lg border border-hairline px-3 py-2 text-body">
          Teams
          <input type="number" min={4} max={16} value={r.numTeams} disabled={imported}
            onChange={(e) => onChange({ numTeams: Math.min(16, Math.max(4, +e.target.value || 4)) })}
            className="w-16 rounded border border-hairline bg-surface px-2 py-1 text-right font-mono disabled:opacity-50" />
        </label>
        <label className="flex items-center justify-between gap-3 rounded-lg border border-hairline px-3 py-2 text-body">
          FLEX spots
          <input type="number" min={0} max={3} value={r.flex} disabled={imported}
            onChange={(e) => onChange({ flex: Math.min(3, Math.max(0, +e.target.value || 0)) })}
            className="w-16 rounded border border-hairline bg-surface px-2 py-1 text-right font-mono disabled:opacity-50" />
        </label>
        <label className="flex items-center justify-between gap-3 rounded-lg border border-hairline px-3 py-2 text-body">
          PPR
          <select value={r.ppr} disabled={imported}
            onChange={(e) => onChange({ ppr: +e.target.value })}
            className="rounded border border-hairline bg-surface px-2 py-1 font-mono disabled:opacity-50">
            <option value={0}>Standard</option>
            <option value={0.5}>Half</option>
            <option value={1}>Full</option>
          </select>
        </label>
      </div>
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
