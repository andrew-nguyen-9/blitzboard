"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import LeagueImport, { type EspnCreds } from "./LeagueImport";
import { defaultConfig, type LeagueConfig } from "@/lib/leagueConfig";
import { connectLeague, setDefaultLeague, disconnectLeague } from "@/app/actions/leagues";
import { saveCredential } from "@/app/actions/credentials";
import { MAX_LEAGUES } from "@/lib/leagueLimits";

export interface ConnectedLeague {
  id: string;
  name: string | null;
  platform: "espn" | "sleeper" | "manual";
  season: string | null;
  is_default: boolean;
}

// The authed Leagues surface: connect up to MAX_LEAGUES leagues (Sleeper username → full rules;
// ESPN id + optional private cookies), pick the active one, disconnect. Reuses LeagueImport.tsx
// and the RLS-scoped server actions — no new import plumbing.
export default function LeagueManager({ leagues }: { leagues: ConnectedLeague[] }) {
  const router = useRouter();
  const [showImport, setShowImport] = useState(leagues.length === 0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const atCap = leagues.length >= MAX_LEAGUES;

  async function onSleeper(config: LeagueConfig) {
    setBusy(true);
    setErr(null);
    const res = await connectLeague(config as unknown as Record<string, unknown>, {
      platform: "sleeper",
      external_league_id: config.leagueId,
      season: String(new Date().getFullYear()),
      name: config.name,
    });
    finish(res);
  }

  async function onEspn(creds: EspnCreds) {
    setBusy(true);
    setErr(null);
    // Private leagues: stash both cookies as one encrypted secret (the pipeline parses the JSON).
    if (creds.s2 && creds.swid) {
      const cred = await saveCredential("espn", JSON.stringify({ s2: creds.s2, swid: creds.swid }));
      if (!cred.ok) return finish(cred);
    }
    // ESPN has no public settings→rules import, so store a default shell tagged to the league.
    // ponytail: rules stay editable in the draft room; upgrade = an ESPN settings proxy → parseEspnRules.
    const shell: LeagueConfig = {
      ...defaultConfig(),
      source: "espn",
      leagueId: creds.leagueId,
      name: `ESPN ${creds.leagueId}`,
    };
    const res = await connectLeague(shell as unknown as Record<string, unknown>, {
      platform: "espn",
      external_league_id: creds.leagueId,
      season: creds.season ?? String(new Date().getFullYear()),
      name: shell.name,
    });
    finish(res);
  }

  function finish(res: { ok: boolean; error?: string }) {
    setBusy(false);
    if (!res.ok) {
      setErr(res.error ?? "Something went wrong");
      return;
    }
    setShowImport(false);
    router.refresh();
  }

  async function makeDefault(id: string) {
    setBusy(true);
    await setDefaultLeague(id);
    setBusy(false);
    router.refresh();
  }

  async function disconnect(id: string) {
    setBusy(true);
    await disconnectLeague(id);
    setBusy(false);
    router.refresh();
  }

  return (
    <div className="space-y-6">
      {leagues.length > 0 && (
        <ul className="glass divide-y divide-hairline/60">
          {leagues.map((l) => (
            <li key={l.id} className="flex flex-wrap items-center gap-3 px-4 py-3 text-body">
              <span className="min-w-0 flex-1 truncate">
                <span className="font-medium">{l.name ?? "League"}</span>{" "}
                <span className="text-label text-ink-muted capitalize">· {l.platform}{l.season ? ` · ${l.season}` : ""}</span>
              </span>
              {l.is_default ? (
                <span className="rounded-full bg-accent px-2.5 py-1 text-label text-bg">Active</span>
              ) : (
                <button onClick={() => makeDefault(l.id)} disabled={busy}
                  className="rounded-full border border-hairline px-2.5 py-1 text-label transition hover:border-accent disabled:opacity-40">
                  Make active
                </button>
              )}
              <button onClick={() => disconnect(l.id)} disabled={busy}
                className="rounded-full border border-hairline px-2.5 py-1 text-label text-ink-muted transition hover:text-red-400 disabled:opacity-40">
                Disconnect
              </button>
            </li>
          ))}
        </ul>
      )}

      {err && <p role="alert" className="text-label text-red-400">{err}</p>}

      {atCap ? (
        <p className="text-label text-ink-muted">You&apos;ve connected the maximum of {MAX_LEAGUES} leagues. Disconnect one to add another.</p>
      ) : showImport ? (
        <LeagueImport onSleeperImport={onSleeper} onEspnConnect={onEspn} onClose={() => setShowImport(false)} />
      ) : (
        <button onClick={() => setShowImport(true)}
          className="rounded-full bg-accent px-4 py-2 text-label font-medium text-bg transition hover:opacity-90">
          ⚡ Connect a league
        </button>
      )}
    </div>
  );
}
