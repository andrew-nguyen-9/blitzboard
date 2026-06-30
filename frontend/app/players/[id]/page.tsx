import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import EmptyState from "@/components/EmptyState";
import ValueDial from "@/components/ValueDial";
import DistributionRidge from "@/components/DistributionRidge";
import DistributionBar from "@/components/DistributionBar";
import EngineToggle from "@/components/EngineToggle";
import PredictabilityMeter from "@/components/PredictabilityMeter";
import Sparkline from "@/components/Sparkline";
import Tooltip from "@/components/Tooltip";
import { StatTable } from "@/components/StatTable";
import { getPlayerDetail } from "@/lib/queries";
import { careerColumns, careerRows, careerSummary } from "@/lib/playerStats";
import { gaussianSamples } from "@/lib/viz";
import { isSupabaseConfigured } from "@/lib/supabase";
import { teamLogoUrl } from "@/lib/teams";
import type { Engine } from "@/lib/types";

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const d = await getPlayerDetail(id);
  const p = d?.player;
  if (!p) return { title: "Player" };
  const where = [p.position, p.nfl_team ?? "Free Agent"].filter(Boolean).join(" · ");
  const description = `${p.full_name} — ${where}. Value, projections, and career production in the BlitzBoard draft war room.`;
  return {
    title: p.full_name,
    description,
    openGraph: { title: `${p.full_name} · BlitzBoard`, description, type: "profile" as const },
  };
}

// A labelled metric whose definition lives in the shared Tooltip (Epic 3.2). The
// host is keyboard-focusable and points its aria-describedby at the bubble, so the
// definition reaches assistive tech, not just hover.
function Metric({
  id,
  label,
  value,
  tip,
}: {
  id: string;
  label: string;
  value: string;
  tip: ReactNode;
}) {
  return (
    <span
      tabIndex={0}
      aria-describedby={id}
      className="group relative inline-flex cursor-help flex-col gap-1 rounded outline-none focus-visible:ring-2 focus-visible:ring-accent"
    >
      <span className="text-label uppercase text-ink-2">{label}</span>
      <span className="font-mono text-ink">{value}</span>
      <Tooltip id={id} side="bottom" content={tip} />
    </span>
  );
}

const fmt = (v: number | null | undefined, d = 1, sign = false) =>
  v == null || !Number.isFinite(v) ? "—" : `${sign && v > 0 ? "+" : ""}${v.toFixed(d)}`;

export default async function PlayerDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ engine?: string }>;
}) {
  const { id } = await params;
  const { engine: engineParam } = await searchParams;
  const engine: Engine = engineParam === "monte_carlo" ? "monte_carlo" : "vorp";

  if (!isSupabaseConfigured()) {
    return (
      <EmptyState title="Player Detail" phase="Phase 1">
        Connect Supabase and run the pipeline to view player intelligence.
      </EmptyState>
    );
  }

  let d = await getPlayerDetail(id, engine);
  if (!d) notFound();

  // Monte Carlo per-player rows ship via CI (Epic 12 upload is gated to a manual
  // workflow), so the live DB may have no monte_carlo value yet. Fall back to the
  // VORP row so the page still renders, and flag it for an inline note.
  let mcUnavailable = false;
  if (engine === "monte_carlo" && !d.value) {
    mcUnavailable = true;
    const fallback = await getPlayerDetail(id, "vorp");
    if (fallback) d = fallback;
  }
  const showRidge = engine === "monte_carlo" && !mcUnavailable;

  const { player, value, projection, history } = d;
  const logo = teamLogoUrl(player.nfl_team);
  const vor = value?.vor ?? 0;
  const dialFraction = Math.max(0, Math.min(1, vor / 150)); // VOR scaled to a 150 cap
  const seasonPts = history.map((h) => h.fantasy_pts ?? 0);
  const columns = careerColumns(player.position);
  const rows = careerRows(history);
  const summary = careerSummary(history);
  const depth = player.metadata?.depth_chart_order;

  // The boom/bust band (P90/P10) is computed and stored on every value row, so the
  // simulated outcome range is surfaced in BOTH engine views — not just the ridge.
  const hasBand = value?.boom != null && value?.bust != null;
  const mcSpread = hasBand ? (value!.boom! - value!.bust!) / 2.5631 : 0; // P90−P10 ≈ 2.563σ
  const mcSamples = showRidge ? gaussianSamples(vor, mcSpread, 240) : [];

  return (
    <div className="py-12">
      <Link href="/players" className="text-label text-ink-muted transition hover:text-ink">
        ← Player Explorer
      </Link>

      {/* identity */}
      <div className="mt-6 flex flex-wrap items-center gap-6">
        <div className="grid h-28 w-28 place-items-center rounded-2xl border border-hairline bg-surface-elevated">
          {logo ? (
            <Image src={logo} alt={player.nfl_team ?? ""} width={84} height={84} className="object-contain" />
          ) : (
            <span className="text-label text-ink-muted">FA</span>
          )}
        </div>
        <div>
          <h1 className="font-display text-display-md">{player.full_name}</h1>
          <p className="mt-1 text-body text-ink-muted">
            {player.position ?? "—"} · {player.nfl_team ?? "Free Agent"}
            {player.bye_week ? ` · Bye ${player.bye_week}` : ""}
            {player.age ? ` · Age ${player.age}` : ""}
            {player.years_exp != null ? ` · ${player.years_exp} yr${player.years_exp === 1 ? "" : "s"} exp` : ""}
            {depth ? ` · Depth #${depth}` : ""}
          </p>
          {player.injury_status && (
            <span className="mt-2 inline-block rounded-full border border-red-400/40 px-3 py-1 text-label text-red-400">
              {player.injury_status}
            </span>
          )}
        </div>
      </div>

      {/* instrument panel */}
      <div className="mt-10 grid gap-6 lg:grid-cols-3">
        <div className="glass flex flex-col gap-5 p-6" style={{ boxShadow: "var(--glow)" }}>
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-label text-ink-muted">VALUE · {engine === "monte_carlo" ? "Monte Carlo" : "VORP"}</h3>
            <EngineToggle active={engine} />
          </div>

          {mcUnavailable && (
            <p className="rounded-lg border border-hairline bg-surface px-3 py-2 text-label text-ink-muted">
              Monte Carlo outputs publish via the Epic 12 model workflow — showing VORP with its
              simulated P10–P90 band below.
            </p>
          )}

          {/* engine toggle morphs the instrument: point dial ⇄ outcome ridgeline */}
          {showRidge ? (
            <div className="flex flex-1 flex-col justify-center gap-3">
              <div className="font-mono text-display-md tabular-nums">
                {value?.rank ? `#${value.rank}` : "—"}
                <span className="ml-2 align-middle text-label uppercase text-ink-2">overall</span>
              </div>
              <DistributionRidge samples={mcSamples} label="Value over replacement" decimals={0} />
              <div className="flex justify-between text-label text-ink-muted">
                <span>bust <span className="font-mono text-ink">{fmt(value?.bust, 0)}</span></span>
                <span>E[VOR] <span className="font-mono text-ink">{vor.toFixed(0)}</span></span>
                <span>boom <span className="font-mono text-ink">{fmt(value?.boom, 0)}</span></span>
              </div>
            </div>
          ) : (
            <div className="grid flex-1 place-items-center">
              <ValueDial
                fraction={dialFraction}
                size={220}
                label="OVERALL"
                value={value?.rank ? `#${value.rank}` : "—"}
                sub={value?.vor != null ? `VOR ${value.vor >= 0 ? "+" : ""}${value.vor.toFixed(1)}` : undefined}
              />
            </div>
          )}

          {/* tooltip-defined value metrics (shared Tooltip primitive, Epic 3.2) */}
          <div className="flex flex-wrap gap-x-6 gap-y-3">
            <Metric
              id="m-vor"
              label="VOR"
              value={fmt(value?.vor, 1, true)}
              tip="Value Over Replacement — projected points above a freely-available replacement starter at this position. The core VORP ranking signal."
            />
            <Metric
              id="m-repl"
              label="Repl"
              value={fmt(value?.replacement, 1)}
              tip="Replacement baseline: the projected points of the last startable player at this position. VOR is measured against this line."
            />
            <Metric
              id="m-adp"
              label="ADP"
              value={value?.adp != null ? value.adp.toFixed(1) : "—"}
              tip="Average draft position across public drafts. Compare to the overall rank to spot market mispricings."
            />
          </div>

          {/* simulated outcome band (P10–P90) — computed for every value row */}
          {hasBand && !showRidge && (
            <div>
              <p className="mb-2 text-label uppercase text-ink-2">Simulated outcome band · P10–P90</p>
              <DistributionBar floor={value!.bust!} mean={value!.value ?? vor} ceiling={value!.boom!} />
            </div>
          )}

          {/* predictability: the *why* behind a discounted value (e.g. a streamer K/DEF) */}
          {value?.predictability != null && (
            <PredictabilityMeter score={value.predictability} className="mt-auto" />
          )}
        </div>

        <div className="glass p-6 lg:col-span-2">
          <h3 className="text-label text-ink-muted">SEASON PROJECTION · ensemble</h3>
          {projection ? (
            <>
              <div className="mt-3 font-mono text-display-md">{projection.mean?.toFixed(1)}</div>
              <p className="mb-5 text-label text-ink-muted">projected fantasy points (σ {projection.stdev?.toFixed(1)})</p>
              <DistributionBar floor={projection.floor} mean={projection.mean} ceiling={projection.ceiling} />
              {projection.by_stat?.inputs && (
                <div className="mt-5 flex flex-wrap gap-4 text-label text-ink-muted">
                  {Object.entries(projection.by_stat.inputs).map(([src, v]: [string, any]) => (
                    <span key={src} className="group relative inline-flex cursor-help items-center gap-1">
                      {src}: <span className="font-mono text-ink">{Number(v).toFixed(0)}</span>
                      <Tooltip
                        decorative
                        side="bottom"
                        content={`${src} model input — the ensemble mean blends each source's projection.`}
                      />
                    </span>
                  ))}
                </div>
              )}
            </>
          ) : (
            <p className="mt-3 text-body text-ink-muted">No projection yet — run value_engine_run.py.</p>
          )}
        </div>
      </div>

      {/* career production — the per-season stats jsonb, position-aware */}
      <div className="glass mt-6 p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h3 className="text-label text-ink-muted">CAREER PRODUCTION</h3>
          {summary.seasons > 0 && (
            <div className="flex flex-wrap gap-x-6 gap-y-1 font-mono text-label text-ink-muted">
              <span>career PPG <span className="text-ink">{fmt(summary.careerPpg, 1)}</span></span>
              <span>best <span className="text-ink">{fmt(summary.bestPts, 1)}</span></span>
              {summary.yoyDelta != null && (
                <span>
                  YoY{" "}
                  <span className={summary.yoyDelta >= 0 ? "text-pos" : "text-neg"}>
                    {summary.yoyDelta >= 0 ? "▲" : "▼"} {Math.abs(summary.yoyDelta).toFixed(1)}
                  </span>
                </span>
              )}
            </div>
          )}
        </div>
        {rows.length ? (
          <div className="mt-4 overflow-x-auto">
            <StatTable caption={`${player.full_name} career production by season`} columns={columns} rows={rows} rowKey="season" />
          </div>
        ) : (
          <p className="mt-3 text-body text-ink-muted">No season stats loaded for this player yet.</p>
        )}
      </div>

      {/* fantasy-points trend */}
      <div className="glass mt-6 p-6">
        <h3 className="text-label text-ink-muted">FANTASY POINTS BY SEASON</h3>
        <div className="mt-4 flex flex-wrap items-end gap-10">
          <Sparkline points={seasonPts} />
          <div className="flex gap-6 font-mono text-body">
            {history.map((h) => (
              <div key={h.season} className="text-center">
                <div className="text-ink">{(h.fantasy_pts ?? 0).toFixed(0)}</div>
                <div className="text-label text-ink-muted">{h.season}</div>
              </div>
            ))}
            {!history.length && <span className="text-label text-ink-muted">No history loaded</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
