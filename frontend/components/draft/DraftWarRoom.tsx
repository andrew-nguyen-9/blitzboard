"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import type { PlayerTrends, PlayerWithValue } from "@/lib/types";
import { fillRoster, scarcity, teamOnClock, myPickNumbers } from "@/lib/draft";
import {
  defaultConfig,
  defaultTeams,
  applyRules,
  rulesFromConfig,
  type LeagueConfig,
} from "@/lib/leagueConfig";
import {
  pickForTeam,
  detectRuns,
  candidatePool,
  norm,
  proj,
} from "@/lib/draftAI";
import { deriveBenchShapeLeagueKey, scoreBoardWithExplanations } from "@/lib/v6DraftLiveScoring";
import { projectionCeiling } from "@/lib/valueUnits";
import { mapPicks, type MappedPick } from "@/lib/sleeperDraft";
import { mapEspnPicks } from "@/lib/espnDraft";
import { useSleeperSync } from "@/lib/useSleeperSync";
import { useEspnSync } from "@/lib/useEspnSync";
import { saveSnapshot } from "@/lib/draftStore";
import { projPoints } from "@/lib/score";
import AllTeamsBoard from "@/components/AllTeamsBoard";
import DraftPickLog from "./DraftPickLog";
import DraftAnalysis from "@/components/DraftAnalysis";
import DraftEndCard from "@/components/DraftEndCard";
import { rosterHealth, equityImpact } from "./rosterHealth";
import { benchHealth, dropPriority, type BenchCtx } from "@/lib/benchScore";
import BenchPanel from "./BenchPanel";
import { buildPlan, valueFlag, neededPositions, type DraftPlan } from "./plan";
import { reasonChips } from "./reasons";
import { isConsequential } from "./consequential";
import LiveRecommendations, { type Recommendation } from "./LiveRecommendations";
import RosterHealthPanel from "./RosterHealthPanel";
import PreDraftPlan from "./PreDraftPlan";

type Mode = "manual" | "sleeper" | "espn";
type View = "board" | "teams" | "log" | "analysis";
const POSITIONS = ["ALL", "QB", "RB", "WR", "TE", "K", "DST"] as const;

export interface SavedLeague {
  id: string;
  name: string;
  config: LeagueConfig;
}

// The upgraded live war room: live ranked recommendations + why + roster-health +
// equity + a robust strategy tree (only consequential picks re-plan). Manual-first
// input with optional Sleeper/ESPN sync (reuses the existing adapters/hooks). The
// board + recommendations update instantly per pick; only the plan is gated.
export default function DraftWarRoom({
  players,
  savedLeagues,
  trends,
}: {
  players: PlayerWithValue[];
  savedLeagues?: SavedLeague[];
  // player_id → E1 trends (queries.getPlayerTrends). Absent → bench scores use
  // neutral fills and the panel's checklist flags the degraded signals.
  trends?: Record<string, PlayerTrends>;
}) {
  const authed = !!savedLeagues?.length;
  const [config, setConfig] = useState<LeagueConfig>(() => savedLeagues?.[0]?.config ?? defaultConfig(12));
  const [leagueId, setLeagueId] = useState(savedLeagues?.[0]?.id ?? "");
  const numTeams = config.numTeams;
  const roster = config.rosterSlots;
  const ROSTER_SPOTS = roster.length + config.benchSize;
  const totalSpots = numTeams * ROSTER_SPOTS;

  const [mySlot, setMySlot] = useState(6);
  const [manualPicks, setManualPicks] = useState<MappedPick[]>([]);
  const [q, setQ] = useState("");
  const [pos, setPos] = useState<(typeof POSITIONS)[number]>("ALL");
  const [view, setView] = useState<View>("board");
  const [endDismissed, setEndDismissed] = useState(false);

  // ── live sync ──────────────────────────────────────────────────────────────
  const [mode, setMode] = useState<Mode>("manual");
  const [liveSetup, setLiveSetup] = useState<Exclude<Mode, "manual"> | null>(null);
  const [idInput, setIdInput] = useState("");
  const [connectedId, setConnectedId] = useState("");
  const sleeperSync = useSleeperSync(mode === "sleeper" ? connectedId : "", mode === "sleeper");
  const espnSync = useEspnSync(mode === "espn", mode === "espn" ? connectedId || undefined : undefined);

  const sleeperMap = useMemo(() => new Map(players.filter((p) => p.sleeper_id).map((p) => [p.sleeper_id, p])), [players]);
  const espnMap = useMemo(() => new Map(players.filter((p) => p.espn_id).map((p) => [p.espn_id as string, p])), [players]);

  const live = mode === "sleeper" ? sleeperSync : mode === "espn" ? espnSync : null;
  const syncedPicks = useMemo<MappedPick[]>(() => {
    if (mode === "sleeper") return mapPicks(sleeperSync.picks, sleeperMap);
    if (mode === "espn") return mapEspnPicks(espnSync.picks, espnMap, numTeams);
    return [];
  }, [mode, sleeperSync.picks, espnSync.picks, sleeperMap, espnMap, numTeams]);

  const picks = mode === "manual" ? manualPicks : syncedPicks;

  const draftedIds = useMemo(() => new Set(picks.map((p) => p.player.id)), [picks]);
  const currentPickNo = picks.length + 1;
  const onClock = teamOnClock(currentPickNo, numTeams);
  const round = Math.ceil(currentPickNo / numTeams);
  const myUpcoming = myPickNumbers(numTeams, mySlot, ROSTER_SPOTS).find((p) => p >= currentPickNo);
  const picksUntilMe = myUpcoming ? myUpcoming - currentPickNo : null;
  const isMyPick = onClock === mySlot;
  const complete = picks.length >= totalSpots;

  const available = useMemo(() => players.filter((p) => !draftedIds.has(p.id)), [players, draftedIds]);
  const myTeamPicks = useMemo(() => picks.filter((p) => p.team === mySlot).map((p) => p.player), [picks, mySlot]);
  const myRoster = useMemo(() => fillRoster(myTeamPicks, roster), [myTeamPicks, roster]);
  const scarce = useMemo(() => scarcity(available), [available]);
  const runs = useMemo(() => detectRuns(picks, numTeams), [picks, numTeams]);
  const health = useMemo(() => rosterHealth(myTeamPicks, roster), [myTeamPicks, roster]);
  const needed = useMemo(() => neededPositions(myTeamPicks, roster), [myTeamPicks, roster]);
  const benchShapeKey = useMemo(() => deriveBenchShapeLeagueKey(config), [config]);

  // Bench value: score every reserve body (E4), aggregate its health, and rank
  // drop priority. ctx carries the FULL roster (handcuff/dup logic) + config
  // (derives superflex) + E1 trends. superflex also drives the panel badge.
  const superflex = useMemo(() => rulesFromConfig(config).superflex, [config]);
  const benchCtx = useMemo<BenchCtx>(
    () => ({ roster: myTeamPicks, config, trends }),
    [myTeamPicks, config, trends],
  );
  const benchHp = useMemo(() => benchHealth(myRoster.bench, benchCtx), [myRoster.bench, benchCtx]);
  const benchDrops = useMemo(() => dropPriority(myRoster.bench, benchCtx), [myRoster.bench, benchCtx]);

  // Equity the LAST pick of mine added (marginal starting-lineup points).
  const lastEquity = useMemo(() => {
    if (myTeamPicks.length === 0) return null;
    const prior = myTeamPicks.slice(0, -1);
    return equityImpact(prior, myTeamPicks[myTeamPicks.length - 1], roster);
  }, [myTeamPicks, roster]);

  // Live ranked recommendations — recompute every pick (the board is always live).
  const recs = useMemo<Recommendation[]>(() => {
    if (complete) return [];
    const myNos = myPickNumbers(numTeams, mySlot, ROSTER_SPOTS);
    const myPickNo = myNos.find((n) => n >= currentPickNo) ?? currentPickNo;
    const after = myNos.find((n) => n > myPickNo) ?? myPickNo + numTeams;
    const scored = scoreBoardWithExplanations({
      pool: candidatePool(available),
      teamPicks: myTeamPicks,
      roster,
      benchSize: config.benchSize,
      allPicks: picks,
      numTeams,
      picksUntilNext: after - myPickNo,
      round: Math.ceil(myPickNo / numTeams),
      totalRounds: ROSTER_SPOTS,
      randomness: 0,
    }, { leagueConfigKey: benchShapeKey }).slice(0, 4);
    return scored.map((sp) => {
      const p = sp.player;
      const ppos = norm(p.position);
      const equity = equityImpact(myTeamPicks, p, roster);
      const mean = proj(p);
      const boom = projectionCeiling(p) ?? mean; // C01 unit fix: raw ceiling vs raw mean
      const nextTurnEdge = sp.explanation.components.find((component) => component.name === "immediate_lineup")?.value ?? 0;
      return {
        player: p,
        equity,
        explanation: sp.explanation,
        reasons: reasonChips({
          need: needed.has(ppos),
          scarce: (scarce[ppos] ?? 99) <= numTeams,
          run: runs.hot.includes(ppos),
          vona: nextTurnEdge >= 10,
          upside: mean > 0 && boom > mean * 1.12,
          value: valueFlag(p) === "value",
        }),
      };
    });
  }, [available, myTeamPicks, picks, roster, numTeams, mySlot, ROSTER_SPOTS, currentPickNo, config.benchSize, benchShapeKey, needed, scarce, runs, complete]);

  // ── robust strategy tree: re-plan ONLY on a consequential pick ───────────────
  const [plan, setPlan] = useState<DraftPlan | null>(null);
  const [replanCount, setReplanCount] = useState(0);
  const [lastTrigger, setLastTrigger] = useState<string>();
  useEffect(() => {
    if (complete) return;
    const starterCaliberIds = new Set(
      available.filter((p) => (p.value?.vor ?? 0) > 0 && needed.has(norm(p.position))).map((p) => p.id),
    );
    const targetIds = new Set(
      plan ? plan.rounds.flatMap((r) => [...r.primary, ...r.contingency]).map((t) => t.id) : [],
    );
    const ctx = { mySlot, needed, targetIds, starterCaliberIds };
    const since = plan ? picks.slice(plan.builtAtPickCount) : picks;
    const trigger = plan ? since.map((p) => isConsequential(p, ctx)).find((r) => r.consequential)?.reason : "initial plan";
    if (!plan || trigger) {
      setPlan(buildPlan(available, myTeamPicks, roster, numTeams, mySlot, currentPickNo, picks.length));
      if (plan) setReplanCount((n) => n + 1);
      setLastTrigger(trigger ?? "initial plan");
    }
  }, [picks, available, myTeamPicks, needed, roster, numTeams, mySlot, currentPickNo, complete, plan]);

  const shown = useMemo(() => {
    let r = available;
    if (pos !== "ALL") r = r.filter((p) => (p.position === "DEF" ? "DST" : p.position ?? "") === pos);
    if (q.trim()) {
      const n = q.toLowerCase();
      r = r.filter((p) => p.full_name.toLowerCase().includes(n) || (p.nfl_team ?? "").toLowerCase().includes(n));
    }
    return r.slice(0, 60);
  }, [available, q, pos]);

  useEffect(() => {
    saveSnapshot({ config, picks, mySlot });
  }, [config, picks, mySlot]);
  useEffect(() => {
    if (!complete) setEndDismissed(false);
  }, [complete]);

  // ── actions ──────────────────────────────────────────────────────────────
  function draft(player: PlayerWithValue, team = onClock) {
    setManualPicks((cur) => [...cur, { pickNo: cur.length + 1, team, player }]);
  }
  const undo = () => setManualPicks((cur) => cur.slice(0, -1));
  const reset = () => setManualPicks([]);

  function nextPickAfter(team: number, fromPick: number): number {
    let n = fromPick + 1;
    while (n <= totalSpots) {
      if (teamOnClock(n, numTeams) === team) return n;
      n++;
    }
    return totalSpots + 1;
  }
  // AI-driven auto-pick. `stopAtMe` powers "Sim to my pick"; false runs the whole draft
  // ("Auto-draft all"). Both drive every rival team off the shared v2 policy (pickForTeam).
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
        const pool = candidatePool(players.filter((p) => !taken.has(p.id)));
        if (!pool.length) break;
        const player =
          pickForTeam({
            pool,
            teamPicks: next.filter((p) => p.team === team).map((p) => p.player),
            roster,
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

  function connect(source: Exclude<Mode, "manual">) {
    if (!idInput.trim()) return;
    setConnectedId(idInput.trim());
    setMode(source);
    setLiveSetup(null);
  }
  function fallbackToManual() {
    setManualPicks(syncedPicks);
    setMode("manual");
    setConnectedId("");
    setLiveSetup(null);
  }
  function updateRules(patch: Partial<ReturnType<typeof rulesFromConfig>>) {
    setConfig((c) => applyRules(c, { ...rulesFromConfig(c), ...patch }));
    setManualPicks([]);
  }
  function renameTeam(slot: number, name: string) {
    setConfig((c) => ({ ...c, teams: c.teams.map((t) => (t.slot === slot ? { ...t, name } : t)) }));
  }
  function pickLeague(id: string) {
    const lg = savedLeagues?.find((l) => l.id === id);
    if (!lg) return;
    setLeagueId(id);
    setConfig(lg.config);
    setManualPicks([]);
  }

  const teamName = (slot: number) => config.teams.find((t) => t.slot === slot)?.name ?? `Team ${slot}`;

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
      </div>

      {/* authed league toggle */}
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

      {/* sync bar (unauth) */}
      {!authed && (
        <div className="glass mb-4 flex flex-wrap items-center gap-3 p-3">
          <div className="inline-flex rounded-full border border-hairline p-1 text-label" role="group" aria-label="Draft input source">
            <button aria-pressed={mode === "manual" && !liveSetup} onClick={() => { setMode("manual"); setLiveSetup(null); }} className={`rounded-full px-3 py-1 transition ${mode === "manual" && !liveSetup ? "bg-accent text-bg" : "text-ink-muted hover:text-ink"}`}>Manual</button>
            <button aria-pressed={mode === "sleeper" || liveSetup === "sleeper"} onClick={() => setLiveSetup("sleeper")} className={`rounded-full px-3 py-1 transition ${mode === "sleeper" || liveSetup === "sleeper" ? "bg-accent text-bg" : "text-ink-muted hover:text-ink"}`}>Sleeper Live</button>
            <button aria-pressed={mode === "espn" || liveSetup === "espn"} onClick={() => setLiveSetup("espn")} className={`rounded-full px-3 py-1 transition ${mode === "espn" || liveSetup === "espn" ? "bg-accent text-bg" : "text-ink-muted hover:text-ink"}`}>ESPN Live</button>
          </div>
          {liveSetup && (
            <div className="flex items-center gap-2">
              <label htmlFor="draft-source-id" className="sr-only">{liveSetup === "espn" ? "ESPN league ID" : "Sleeper draft ID"}</label>
              <input id="draft-source-id" value={idInput} onChange={(e) => setIdInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && connect(liveSetup)} autoFocus
                placeholder={liveSetup === "espn" ? "ESPN league_id" : "Sleeper draft_id…"}
                className="w-48 rounded-full border border-hairline bg-surface px-3 py-1.5 text-label outline-none focus:border-accent" />
              <button onClick={() => connect(liveSetup)} disabled={!idInput.trim()}
                className="rounded-full bg-accent px-3 py-1.5 text-label text-bg transition hover:opacity-90 disabled:opacity-40">
                Connect {liveSetup === "espn" ? "ESPN" : "Sleeper"}
              </button>
            </div>
          )}
          {live && (
            <span className="inline-flex items-center gap-2 rounded-full border border-hairline px-3 py-1.5 text-label" aria-live="polite">
              <span aria-hidden="true" className="h-2 w-2 rounded-full" style={{ background: live.status === "live" ? "#33D17A" : live.status === "error" ? "#E0573A" : "#E0A33A" }} />
              {mode === "espn" ? "ESPN" : "Sleeper"} {live.status}
            </span>
          )}
          {mode !== "manual" && (
            <button onClick={fallbackToManual} className="ml-auto rounded-full border border-hairline px-3 py-1.5 text-label transition hover:bg-surface-elevated">
              ↩ Switch to manual (keep picks)
            </button>
          )}
        </div>
      )}

      {live && live.status === "error" && (
        <div role="alert" className="mb-4 rounded-xl border border-red-400/40 bg-red-400/5 p-3 text-label text-red-300">
          {mode.toUpperCase()} feed stalled ({live.error}). Still retrying — or switch to manual to keep drafting.
        </div>
      )}

      {/* view tabs */}
      <div className="mb-4 flex w-fit max-w-full flex-wrap rounded-full border border-hairline p-1 text-label" role="group" aria-label="Draft board view">
        {(["board", "teams", "log", "analysis"] as View[]).map((v) => (
          <button key={v} aria-pressed={view === v} onClick={() => setView(v)}
            className={`rounded-full px-4 py-1 capitalize transition ${view === v ? "bg-accent text-bg" : "text-ink-muted hover:text-ink"}`}>
            {v === "teams" ? "All teams" : v === "log" ? "Pick log" : v}
          </button>
        ))}
      </div>

      {complete && !endDismissed && (
        <DraftEndCard picks={picks} config={config} mySlot={mySlot} onViewAnalysis={() => setView("analysis")} onDismiss={() => setEndDismissed(true)} />
      )}

      {view === "teams" && <AllTeamsBoard config={config} picks={picks} mySlot={mySlot} onRename={renameTeam} />}
      {view === "log" && <DraftPickLog picks={picks} config={config} mySlot={mySlot} />}
      {view === "analysis" && <DraftAnalysis picks={picks} config={config} mySlot={mySlot} />}

      {view === "board" && (
        <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
          <section aria-label="Draft recommendations" className="min-w-0 lg:col-start-2 lg:row-start-1">
            {!complete && <LiveRecommendations recs={recs} isMyPick={isMyPick} picksUntilMe={picksUntilMe} onDraft={mode === "manual" ? draft : undefined} />}
          </section>

          <div className="min-w-0 lg:col-start-1 lg:row-start-1 lg:row-span-2">
            {/* status */}
            <div className="glass mb-4 flex flex-wrap items-center gap-4 p-4">
              <div role="status" aria-live="polite" aria-atomic="true" aria-label="Draft status">
                <div aria-hidden="true" className="text-label text-ink-muted">ROUND {round} · PICK {currentPickNo}</div>
                <div className={`font-display text-heading ${isMyPick ? "text-accent" : ""}`}>
                  {complete ? "Draft complete" : isMyPick ? "YOUR PICK" : `${teamName(onClock)} on the clock`}
                </div>
                {picksUntilMe != null && !isMyPick && !complete && <div className="text-label text-ink-muted">your pick in {picksUntilMe}</div>}
              </div>
              {mode === "manual" && (
                <div className="ml-auto flex flex-wrap items-center justify-end gap-2">
                  <button onClick={() => runSim(true)} disabled={complete} className="rounded-full border border-hairline px-3 py-1.5 text-label transition hover:bg-surface-elevated disabled:opacity-40">Sim to my pick</button>
                  <button onClick={undo} disabled={!manualPicks.length} className="rounded-full border border-hairline px-3 py-1.5 text-label transition hover:bg-surface-elevated disabled:opacity-40">Undo</button>
                  <button onClick={reset} disabled={!manualPicks.length} className="rounded-full border border-hairline px-3 py-1.5 text-label transition hover:bg-surface-elevated disabled:opacity-40">Reset</button>
                  <details className="text-label">
                    <summary>Simulation tools</summary>
                    <div className="mt-2 max-w-64 rounded-xl border border-hairline bg-surface p-3">
                      <p className="mb-2 text-ink-muted">Completes every remaining pick with the local simulation policy; this is not a forecast or recommendation authority.</p>
                      <button onClick={() => runSim(false)} disabled={complete} className="rounded-full border border-hairline px-3 py-1.5 transition hover:bg-surface-elevated disabled:opacity-40">Auto-draft all</button>
                    </div>
                  </details>
                </div>
              )}
            </div>

            {/* controls */}
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <label htmlFor="available-player-search" className="sr-only">Search available players</label>
              <input id="available-player-search" type="search" aria-label="Search available players" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search…"
                className="w-44 rounded-full border border-hairline bg-surface px-4 py-2 text-body outline-none focus:border-accent" />
              <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Filter by position">
                {POSITIONS.map((p) => (
                  <button key={p} aria-pressed={pos === p} onClick={() => setPos(p)}
                    className={`rounded-full px-3 py-1.5 text-label transition ${pos === p ? "bg-accent text-bg" : "border border-hairline text-ink-muted hover:text-ink"}`}>{p}</button>
                ))}
              </div>
            </div>

            {/* best available */}
            <div className="glass min-w-0">
              <div role="region" aria-label="Available player table" tabIndex={0} className="overflow-x-auto">
              <table className="w-full text-left text-body">
                <caption className="sr-only">Available players ranked by BlitzBoard</caption>
                <thead className="border-b border-hairline text-label text-ink-muted">
                  <tr>
                    <th scope="col" className="px-3 py-2.5 font-normal"><span aria-hidden="true">Rank</span><span className="sr-only">BlitzBoard rank</span></th>
                    <th scope="col" className="px-2 py-2.5 font-normal">Player</th>
                    <th scope="col" className="px-2 py-2.5 font-normal">Pos</th>
                    <th scope="col" className="px-2 py-2.5 text-right font-normal"><span aria-hidden="true">Proj pts</span><span className="sr-only">Projected fantasy points</span></th>
                    <th scope="col" className="px-3 py-2.5"><span className="sr-only">Draft action</span></th>
                  </tr>
                </thead>
                <tbody>
                  {shown.map((p) => (
                    <tr key={p.id} className="border-b border-hairline/50 transition hover:bg-surface-elevated">
                      <td className="px-3 py-2 font-mono text-ink-muted">
                        {p.value?.rank ?? <><span aria-hidden="true">—</span><span className="sr-only">BlitzBoard rank unavailable</span></>}
                      </td>
                      <th scope="row" className="px-2 py-2 text-left font-normal"><Link href={`/players/${p.id}`} className="font-medium transition hover:text-accent">{p.full_name}</Link></th>
                      <td className="px-2 py-2 text-label text-ink-muted">{p.position === "DEF" ? "DST" : p.position ?? "—"}</td>
                      <td className="px-2 py-2 text-right font-mono text-label">{projPoints(p) > 0 ? projPoints(p).toFixed(0) : "—"}</td>
                      <td className="px-3 py-2 text-right">
                        {mode === "manual" ? (
                          <button aria-label={isMyPick ? `Draft ${p.full_name} to my team` : `Assign ${p.full_name} to ${teamName(onClock)}`} onClick={() => draft(p)} disabled={complete}
                            className={`min-h-11 min-w-11 rounded-full px-3 py-1 text-label transition disabled:opacity-40 ${isMyPick ? "bg-accent text-bg" : "border border-hairline text-ink hover:bg-surface"}`}>
                            {isMyPick ? "Draft" : `→ ${teamName(onClock).slice(0, 6)}`}
                          </button>
                        ) : (
                          <span className="text-label text-ink-muted/60">feed</span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {!shown.length && (
                    <tr><td colSpan={5} className="px-4 py-8 text-center text-label text-ink-muted">No players match.</td></tr>
                  )}
                </tbody>
              </table>
              </div>
            </div>
          </div>

          {/* SIDEBAR — secondary support panels */}
          <aside aria-label="Draft support panels" className="min-w-0 space-y-6 lg:col-start-2 lg:row-start-2">
            <RosterHealthPanel health={health} projectedPoints={myRoster.projectedPoints} lastEquity={lastEquity} />

            <BenchPanel health={benchHp} drops={benchDrops} superflex={superflex} />

            {!complete && <PreDraftPlan plan={plan} replanCount={replanCount} lastTrigger={lastTrigger} />}

            <div className="glass p-4">
              <h2 className="mb-3 text-label text-ink-muted">MY ROSTER</h2>
              <div className="space-y-1.5 text-body">
                {myRoster.starters.map((s, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <span className="text-ink-muted">{s.slot}</span>
                    {s.player ? <span className="truncate">{s.player.full_name}</span> : <span className="text-accent">— need —</span>}
                  </div>
                ))}
              </div>
              <div className="mt-3 border-t border-hairline pt-3 text-label text-ink-muted">
                Bench {myRoster.bench.length}/{config.benchSize}
              </div>
            </div>

            <div className="glass p-4">
              <h2 className="mb-3 text-label text-ink-muted">SETTINGS</h2>
              <label className="flex items-center justify-between py-1 text-body">
                My slot
                <input type="number" min={1} max={numTeams} value={mySlot} onChange={(e) => setMySlot(+e.target.value)}
                  className="w-16 rounded border border-hairline bg-surface px-2 py-1 text-right font-mono" />
              </label>
              <label className="flex items-center justify-between py-1 text-body">
                Teams
                <input type="number" min={4} max={16} value={numTeams} disabled={mode !== "manual" || config.source !== "manual"}
                  onChange={(e) => updateRules({ numTeams: Math.min(16, Math.max(4, +e.target.value || 4)) })}
                  className="w-16 rounded border border-hairline bg-surface px-2 py-1 text-right font-mono disabled:opacity-50" />
              </label>
            </div>

            <div className="glass p-4">
              <h2 className="mb-3 text-label text-ink-muted">RECENT PICKS</h2>
              <div className="space-y-1 text-label">
                {picks.slice(-8).reverse().map((p) => (
                  <div key={p.pickNo} className="flex items-center gap-2">
                    <span className="font-mono text-ink-muted">{Math.ceil(p.pickNo / numTeams)}.{((p.pickNo - 1) % numTeams) + 1}</span>
                    <span className="flex-1 truncate">{p.player.full_name}</span>
                    <span className={p.team === mySlot ? "text-accent" : "text-ink-muted"}>{teamName(p.team).slice(0, 8)}</span>
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
