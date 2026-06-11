"use client";

import { useEffect, useRef, useState } from "react";
import {
  fetchSleeperPicks,
  fetchSleeperDraft,
  type SleeperPick,
  type SleeperDraftMeta,
} from "./sleeperDraft";

export type SyncStatus = "idle" | "connecting" | "live" | "error";

// Polls the Sleeper draft feed while `enabled`. Resilient: a failed poll flips
// status to "error" (so the UI can prompt manual fallback) but keeps polling, so
// a transient blip self-heals without losing the board.
export function useSleeperSync(
  draftId: string,
  enabled: boolean,
  intervalMs = 4000,
) {
  const [picks, setPicks] = useState<SleeperPick[]>([]);
  const [draft, setDraft] = useState<SleeperDraftMeta | null>(null);
  const [status, setStatus] = useState<SyncStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [lastSync, setLastSync] = useState<number | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!enabled || !draftId.trim()) {
      setStatus("idle");
      return;
    }
    let active = true;
    setStatus("connecting");
    fetchSleeperDraft(draftId).then((d) => active && setDraft(d)).catch(() => {});

    async function tick() {
      try {
        const p = await fetchSleeperPicks(draftId);
        if (!active) return;
        setPicks(p);
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
  }, [draftId, enabled, intervalMs]);

  return { picks, draft, status, error, lastSync };
}
