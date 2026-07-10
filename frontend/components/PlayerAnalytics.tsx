import type { ReactNode } from "react";
import Tooltip from "@/components/Tooltip";
import { StatCell } from "@/components/StatTable";
import {
  advancedMetrics,
  collegeContext,
  isRookieOrNew,
  positionEligibility,
  type SeasonRow,
} from "@/lib/playerStats";
import type { Player } from "@/lib/types";

// PlayerAnalytics (E2) — advanced per-player metrics, rookie college context, and
// multi-position analysis for the player detail page. Server component (pure
// render, no interactivity). It only COMPOSES shipped primitives — the `.glass`
// surface (NORTH_STAR.md §Primitives → Glass), `.neon-text` accent (NORTH_STAR.md
// §Primitives), the shared StatCell (no-clip tabular numerals) and the Tooltip
// definition bubble — so it adds ZERO globals.css / token surface (E10-owned).
//
// Everything degrades: no advanced metrics → the block is omitted; no college
// context → the rookie card is omitted; single-position → the eligibility strip
// is omitted. So a fully-loaded WR and a keyless empty state both render cleanly.

function MetricTile({
  id,
  label,
  value,
  tip,
  decimals,
  suffix,
}: {
  id: string;
  label: string;
  value: number | null;
  tip: ReactNode;
  decimals?: number;
  suffix?: string;
}) {
  return (
    <div
      tabIndex={0}
      aria-describedby={id}
      className="group relative flex flex-col gap-1 rounded-lg border border-hairline bg-surface p-3 outline-none focus-visible:ring-2 focus-visible:ring-accent"
    >
      <StatCell value={value} size="sm" decimals={decimals} suffix={suffix} align="start" />
      <span className="text-label uppercase text-ink-2">{label}</span>
      <Tooltip id={id} side="bottom" content={tip} />
    </div>
  );
}

export default function PlayerAnalytics({
  player,
  history,
}: {
  player: Player;
  history: SeasonRow[];
}) {
  const metrics = advancedMetrics(history, player.position);
  const college = isRookieOrNew(player) ? collegeContext(player) : null;
  const eligible = positionEligibility(player);
  const multi = eligible.length > 1;
  const primary = player.position ?? eligible[0] ?? null;

  // Nothing to show at all → render nothing (keeps the page clean for K/DEF or an
  // unloaded player).
  if (!metrics.length && !college && !multi) return null;

  return (
    <div className="glass mt-6 p-6" style={{ boxShadow: "var(--glow)" }}>
      <h3 className="text-label uppercase text-ink-2">
        <span className="neon-text">Advanced</span> Analytics
      </h3>

      {metrics.length > 0 && (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {metrics.map((m) => (
            <MetricTile
              key={m.key}
              id={`am-${m.key}`}
              label={m.label}
              value={m.value}
              decimals={m.format.decimals}
              suffix={m.format.suffix}
              tip={m.tip}
            />
          ))}
        </div>
      )}

      {/* Multi-position analysis — the slots this player is eligible at. Value is
          assessed at the scarcer slot (per-position VORP lives in the pipeline;
          see pipeline/models/multipos.py). */}
      {multi && (
        <div className="mt-6">
          <p className="mb-2 text-label uppercase text-ink-2">Position eligibility</p>
          <div className="flex flex-wrap gap-2">
            {eligible.map((pos) => {
              const isPrimary = pos === primary;
              return (
                <span
                  key={pos}
                  className={`rounded-full border px-3 py-1 text-label ${
                    isPrimary
                      ? "neon-edge text-ink"
                      : "border-hairline text-ink-muted"
                  }`}
                >
                  {pos}
                  {isPrimary ? " · primary" : ""}
                </span>
              );
            })}
          </div>
          <p className="mt-2 text-label text-ink-muted">
            Dual-eligible: draft at the scarcer slot to bank the higher value over replacement.
          </p>
        </div>
      )}

      {/* Rookie / new-player college context — the prospect signal that shades the
          projection (pipeline CollegeProspectFactor). Omitted when unavailable. */}
      {college && (
        <div className="mt-6">
          <p className="mb-2 text-label uppercase text-ink-2">College context</p>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            {college.college && (
              <span className="text-body text-ink">
                {college.college}
                {college.season ? (
                  <span className="text-ink-muted"> · {college.season}</span>
                ) : null}
              </span>
            )}
            {college.prospectScore != null && (
              <span
                tabIndex={0}
                aria-describedby="am-prospect"
                className="group relative inline-flex items-center gap-2 rounded outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                <span className="text-label uppercase text-ink-2">Prospect</span>
                <span className="h-2 w-24 overflow-hidden rounded-full border border-hairline bg-surface">
                  <span
                    className="block h-full bg-accent"
                    style={{ width: `${Math.round(college.prospectScore * 100)}%` }}
                  />
                </span>
                <span className="font-mono text-ink">
                  {Math.round(college.prospectScore * 100)}
                </span>
                <Tooltip
                  id="am-prospect"
                  side="bottom"
                  content="College prospect score (0–100, 50 neutral) condensed from CollegeFootballData production. Shades the rookie projection up or down by up to ±12%. See docs/research/ANALYTICS_SURVEY.md."
                />
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
