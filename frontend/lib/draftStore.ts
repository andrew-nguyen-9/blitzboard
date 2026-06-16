// Lightweight localStorage snapshot of the live draft so the standalone
// /draft/analysis route (a separate page, no shared React state) can hydrate the
// exact board the user was just on. Written by DraftRoom on every change.
"use client";

import type { MappedPick } from "./sleeperDraft";
import type { LeagueConfig } from "./leagueConfig";

export interface DraftSnapshot {
  config: LeagueConfig;
  picks: MappedPick[];
  mySlot: number;
  updatedAt: number;
}

const KEY = "ffdt:draft:v1";

export function saveSnapshot(s: Omit<DraftSnapshot, "updatedAt">): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(KEY, JSON.stringify({ ...s, updatedAt: Date.now() }));
  } catch {
    /* quota / serialization — analysis page just shows its empty state */
  }
}

export function loadSnapshot(): DraftSnapshot | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as DraftSnapshot) : null;
  } catch {
    return null;
  }
}
