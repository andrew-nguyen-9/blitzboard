import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import EmptyState from "@/components/EmptyState";
import ValueDial from "@/components/ValueDial";
import Sparkline from "@/components/Sparkline";
import DistributionBar from "@/components/DistributionBar";
import { getPlayerDetail } from "@/lib/queries";
import { isSupabaseConfigured } from "@/lib/supabase";
import { teamLogoUrl } from "@/lib/teams";

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const d = await getPlayerDetail(id);
  return { title: d?.player.full_name ?? "Player" };
}

export default async function PlayerDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  if (!isSupabaseConfigured()) {
    return (
      <EmptyState title="Player Detail" phase="Phase 1">
        Connect Supabase and run the pipeline to view player intelligence.
      </EmptyState>
    );
  }

  const d = await getPlayerDetail(id);
  if (!d) notFound();

  const { player, value, projection, history } = d;
  const logo = teamLogoUrl(player.nfl_team);
  const vor = value?.vor ?? 0;
  const dialFraction = Math.max(0, Math.min(1, vor / 150)); // VOR scaled to a 150 cap
  const seasonPts = history.map((h) => h.fantasy_pts ?? 0);

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
        <div className="glass grid place-items-center p-6" style={{ boxShadow: "var(--glow)" }}>
          <ValueDial
            fraction={dialFraction}
            label="OVERALL"
            value={value?.rank ? `#${value.rank}` : "—"}
            sub={value?.vor != null ? `VOR ${value.vor >= 0 ? "+" : ""}${value.vor.toFixed(1)}` : undefined}
          />
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
                  {Object.entries(projection.by_stat.inputs).map(([src, v]: any) => (
                    <span key={src}>
                      {src}: <span className="font-mono text-ink">{Number(v).toFixed(0)}</span>
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

      {/* history */}
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
