"use client";

import { useMemo, useState } from "react";
import { applyInjury, type ScenarioPlayer } from "./whatif";

// What-if scenario surface: pick a player to injure → downstream projection
// deltas. Client Component (interactive select). Delta magnitude is drawn as a
// simple bar scaled to the run's max swing — no chart lib. Direction is encoded by
// SIGN + side + colour (never colour alone → colourblind-safe). The bars are pure
// width (no transition) → reduced-motion safe.
export default function WhatIfPanel({
  players,
  className,
}: {
  players: ScenarioPlayer[];
  className?: string;
}) {
  const [injuredId, setInjuredId] = useState(players[0]?.id ?? "");

  const deltas = useMemo(() => applyInjury(players, injuredId), [players, injuredId]);
  const maxAbs = Math.max(1, ...deltas.map((d) => Math.abs(d.delta)));

  return (
    <div className={className}>
      <label className="block text-label uppercase text-ink-2" htmlFor="whatif-injure">
        Injure a player
      </label>
      <select
        id="whatif-injure"
        value={injuredId}
        onChange={(e) => setInjuredId(e.target.value)}
        className="mt-2 w-full max-w-sm rounded-[var(--radius,0.5rem)] border border-line bg-surface px-3 py-2 text-body text-ink"
      >
        {players.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name} · {p.team} {p.position} · {p.proj.toFixed(1)} pts
          </option>
        ))}
      </select>

      {deltas.length === 0 ? (
        <p className="mt-4 text-body text-ink-2">No downstream effects.</p>
      ) : (
        <ul className="mt-4 space-y-2" aria-label="Downstream projection deltas">
          {deltas.map((d) => {
            const positive = d.delta >= 0;
            const width = `${(Math.abs(d.delta) / maxAbs) * 100}%`;
            return (
              <li key={d.id} className="grid grid-cols-[1fr_auto] items-center gap-3">
                <div>
                  <div className="flex justify-between text-body">
                    <span className="text-ink-1">
                      {d.name} <span className="text-ink-2">· {d.position}</span>
                    </span>
                    <span className={`font-mono tabular-nums ${positive ? "text-pos" : "text-neg"}`}>
                      {positive ? "+" : "−"}
                      {Math.abs(d.delta).toFixed(1)}
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 w-full rounded-full bg-line" aria-hidden>
                    <div
                      className={`h-full rounded-full ${positive ? "bg-pos" : "bg-neg"}`}
                      style={{ width }}
                    />
                  </div>
                </div>
                <span className="font-mono text-label tabular-nums text-ink-2">
                  {d.before.toFixed(1)} → {d.after.toFixed(1)}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
