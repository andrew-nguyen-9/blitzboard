"use client";

import { useEffect, useRef, useState } from "react";
import { fetchEspnDraft, type EspnNormPick, type EspnCreds } from "./espnDraft";
import type { SyncStatus } from "./useSleeperSync";

// Polls our ESPN proxy while `enabled`. Same resilience contract as Sleeper:
// a failed poll → status "error" (board prompts manual fallback) but keeps trying.
// ESPN is the fragile path (D7), so this WILL flip to error more often — by design
// the manual board is one tap away.
export function useEspnSync(
  enabled: boolean,
  leagueId?: string,
  season?: string,
  creds?: EspnCreds,
  intervalMs = 5000,
) {
  const [picks, setPicks] = useState<EspnNormPick[]>([]);
  const [meta, setMeta] = useState<{ teams: number | null; status: string } | null>(null);
  const [status, setStatus] = useState<SyncStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [lastSync, setLastSync] = useState<number | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!enabled) {
      setStatus("idle");
      return;
    }
    let active = true;
    setStatus("connecting");

    async function tick() {
      try {
        const d = await fetchEspnDraft(leagueId, season, creds);
        if (!active) return;
        setPicks(d.picks);
        setMeta(d.meta);
        setStatus("live");
        setError(null);
        setLastSync(Date.now());
      } catch (e: any) {
        if (!active) return;
        setStatus("error");
        setError(e?.message ?? "sync failed");
      }
      if (active) timer.current = setTimeout(tick, intervalMs);
    }
    tick();

    return () => {
      active = false;
      if (timer.current) clearTimeout(timer.current);
    };
    // creds spread to primitives so identity churn doesn't restart the poller
  }, [enabled, leagueId, season, creds?.s2, creds?.swid, intervalMs]);

  return { picks, meta, status, error, lastSync };
}
