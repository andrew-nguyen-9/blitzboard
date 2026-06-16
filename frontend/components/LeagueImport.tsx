"use client";

import { useState } from "react";
import {
  lookupSleeperUser,
  importSleeperLeague,
  type SleeperLeagueLite,
} from "@/lib/leagueImport";
import type { LeagueConfig } from "@/lib/leagueConfig";

export interface EspnCreds {
  leagueId: string;
  season?: string;
  s2?: string;
  swid?: string;
}

// Minimal-setup league import. Sleeper needs only a username (its read API is
// public — no OAuth exists, and none is needed): username → league → a fully
// normalized config (roster, scoring, team names, draft id). ESPN has no public
// OAuth; a public league works with just its id, private leagues also need the
// espn_s2 + SWID cookies pasted from the browser.
export default function LeagueImport({
  onSleeperImport,
  onEspnConnect,
  onClose,
}: {
  onSleeperImport: (config: LeagueConfig, liveDraftId: string | null) => void;
  onEspnConnect: (creds: EspnCreds) => void;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<"sleeper" | "espn">("sleeper");

  return (
    <div className="glass mb-4 p-4" style={{ boxShadow: "var(--glow)" }}>
      <div className="mb-4 flex items-center justify-between">
        <div className="inline-flex rounded-full border border-hairline p-1 text-label">
          {(["sleeper", "espn"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`rounded-full px-4 py-1 capitalize transition ${
                tab === t ? "bg-accent text-bg" : "text-ink-muted hover:text-ink"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <button onClick={onClose} className="text-label text-ink-muted transition hover:text-ink">
          ✕ close
        </button>
      </div>
      {tab === "sleeper" ? (
        <SleeperImport onImport={onSleeperImport} />
      ) : (
        <EspnImport onConnect={onEspnConnect} />
      )}
    </div>
  );
}

function SleeperImport({
  onImport,
}: {
  onImport: (config: LeagueConfig, liveDraftId: string | null) => void;
}) {
  const [username, setUsername] = useState("");
  const [season, setSeason] = useState(String(new Date().getFullYear()));
  const [leagues, setLeagues] = useState<SleeperLeagueLite[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function find() {
    if (!username.trim()) return;
    setBusy(true);
    setErr(null);
    setLeagues(null);
    try {
      const res = await lookupSleeperUser(username, season);
      setLeagues(res.leagues);
      if (!res.leagues.length) setErr(`No NFL leagues for "${username}" in ${season}.`);
    } catch (e: any) {
      setErr(e?.message ?? "lookup failed");
    } finally {
      setBusy(false);
    }
  }

  async function pick(l: SleeperLeagueLite) {
    setBusy(true);
    setErr(null);
    try {
      const config = await importSleeperLeague(l.leagueId);
      onImport(config, config.draftId ?? null);
    } catch (e: any) {
      setErr(e?.message ?? "import failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-label text-ink-muted">
        Enter your Sleeper <span className="text-ink">username</span> (not a league or draft id). We pull
        your leagues, roster rules, scoring, team names, and draft automatically.
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && find()}
          placeholder="sleeper username"
          className="w-56 rounded-full border border-hairline bg-surface px-4 py-2 text-body outline-none focus:border-accent"
        />
        <input
          value={season}
          onChange={(e) => setSeason(e.target.value)}
          className="w-20 rounded-full border border-hairline bg-surface px-3 py-2 text-center font-mono text-body outline-none focus:border-accent"
        />
        <button
          onClick={find}
          disabled={busy || !username.trim()}
          className="rounded-full bg-accent px-4 py-2 text-label font-medium text-bg transition hover:opacity-90 disabled:opacity-40"
        >
          {busy ? "…" : "Find leagues"}
        </button>
      </div>
      {err && <div className="text-label text-red-400">{err}</div>}
      {leagues && leagues.length > 0 && (
        <div className="divide-y divide-hairline/60 rounded-xl border border-hairline">
          {leagues.map((l) => (
            <button
              key={l.leagueId}
              onClick={() => pick(l)}
              disabled={busy}
              className="flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-surface-elevated disabled:opacity-40"
            >
              <span className="min-w-0 flex-1 truncate font-medium">{l.name}</span>
              <span className="text-label text-ink-muted">{l.numTeams} teams</span>
              <span className="rounded-full border border-hairline px-2 py-0.5 text-label text-ink-muted">
                {l.draftId ? "draft ready" : l.status}
              </span>
              <span className="text-accent">→</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function EspnImport({ onConnect }: { onConnect: (creds: EspnCreds) => void }) {
  const [leagueId, setLeagueId] = useState("");
  const [season, setSeason] = useState(String(new Date().getFullYear()));
  const [s2, setS2] = useState("");
  const [swid, setSwid] = useState("");

  return (
    <div className="space-y-3">
      <p className="text-label text-ink-muted">
        ESPN has no public login/OAuth. A <span className="text-ink">public</span> league connects with
        just its League ID. A <span className="text-ink">private</span> league also needs your{" "}
        <code className="text-ink">espn_s2</code> and <code className="text-ink">SWID</code> cookies
        (DevTools → Application → Cookies on fantasy.espn.com).
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <input
          value={leagueId}
          onChange={(e) => setLeagueId(e.target.value)}
          placeholder="ESPN League ID"
          className="w-44 rounded-full border border-hairline bg-surface px-4 py-2 text-body outline-none focus:border-accent"
        />
        <input
          value={season}
          onChange={(e) => setSeason(e.target.value)}
          className="w-20 rounded-full border border-hairline bg-surface px-3 py-2 text-center font-mono text-body outline-none focus:border-accent"
        />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <input
          value={swid}
          onChange={(e) => setSwid(e.target.value)}
          placeholder="SWID {…} (private only)"
          className="w-56 rounded-full border border-hairline bg-surface px-4 py-2 text-label outline-none focus:border-accent"
        />
        <input
          value={s2}
          onChange={(e) => setS2(e.target.value)}
          placeholder="espn_s2 (private only)"
          className="w-56 rounded-full border border-hairline bg-surface px-4 py-2 text-label outline-none focus:border-accent"
        />
      </div>
      <button
        onClick={() => leagueId.trim() && onConnect({ leagueId: leagueId.trim(), season, s2: s2.trim() || undefined, swid: swid.trim() || undefined })}
        disabled={!leagueId.trim()}
        className="rounded-full bg-accent px-4 py-2 text-label font-medium text-bg transition hover:opacity-90 disabled:opacity-40"
      >
        Connect ESPN live
      </button>
    </div>
  );
}
