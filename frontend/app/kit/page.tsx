import type { Metadata } from "next";
import ValueDial from "@/components/ValueDial";
import DistributionRidge from "@/components/DistributionRidge";
import { StatCell, StatTable, type StatColumn } from "@/components/StatTable";
import Ticker from "@/components/Ticker";
import TierBadge from "@/components/TierBadge";
import PredictabilityMeter from "@/components/PredictabilityMeter";

export const metadata: Metadata = {
  title: "Component Kit",
  description: "v2.1 instrument primitives — reference + QA surface.",
};

// Deterministic pseudo-Monte-Carlo samples (boom/bust) for the ridge demo.
function samples(seed: number, n = 400): number[] {
  let s = seed;
  const out: number[] = [];
  for (let i = 0; i < n; i++) {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    const u = s / 0x7fffffff;
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    const v = s / 0x7fffffff;
    // Box–Muller → normal, recentred to a plausible weekly projection.
    const g = Math.sqrt(-2 * Math.log(u + 1e-9)) * Math.cos(2 * Math.PI * v);
    out.push(14 + g * 6);
  }
  return out;
}

const playerCols: StatColumn[] = [
  { key: "name", label: "Player", numeric: false },
  { key: "vor", label: "VOR", numeric: true, decimals: 1 },
  { key: "proj", label: "Proj", numeric: true, decimals: 1 },
  { key: "delta", label: "Δ Rank", numeric: true, decimals: 0, sign: true },
];

const playerRows = [
  { name: "Player A", vor: 41.2, proj: 312.8, delta: 3 },
  { name: "Player B", vor: 8.0, proj: 1284.5, delta: -12 },
  { name: "Player C", vor: -2.4, proj: 88.0, delta: 0 },
];

function Section({ title, note, children }: { title: string; note?: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-line py-10">
      <div className="mb-6 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 className="font-display text-display-md text-ink">{title}</h2>
        {note && <span className="text-label uppercase text-ink-2">{note}</span>}
      </div>
      {children}
    </section>
  );
}

export default function KitPage() {
  return (
    <div className="pb-24 pt-16">
      <h1 className="font-display text-display-lg text-ink">Component Kit</h1>
      <p className="mt-3 max-w-2xl text-body-lg text-ink-1">
        v2.1 instrument primitives, on canonical OKLCH tokens. Each has a reduced-motion
        fallback and a keyboard/label story. This page doubles as the QA surface.
      </p>

      <Section title="ValueDial" note="radial gauge · animated arc">
        <div className="flex flex-wrap items-center gap-8">
          <ValueDial fraction={0.82} value="41" label="VOR" sub="Tier 1" />
          <ValueDial fraction={0.18} value="2.4" label="VOR" sub="Streamer" />
          <ValueDial fraction={1.4 /* clamps */} value="MAX" label="ceiling" size={160} />
        </div>
      </Section>

      <Section title="DistributionRidge" note="Monte-Carlo boom/bust · bar fallback">
        <div className="grid max-w-3xl gap-8 sm:grid-cols-2">
          <div>
            <span className="text-label uppercase text-ink-2">Normal-ish week</span>
            <DistributionRidge samples={samples(7)} className="mt-2" />
          </div>
          <div>
            <span className="text-label uppercase text-ink-2">Empty (no data)</span>
            <DistributionRidge samples={[]} className="mt-2" />
          </div>
        </div>
      </Section>

      <Section title="StatCell" note="tabular-nums · no-clip width">
        <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
          <StatCell value={1284.5} label="Projected pts" decimals={1} size="lg" />
          <StatCell value={0.5} label="PPR" decimals={1} size="lg" />
          <StatCell value={-12} label="Δ rank" decimals={0} sign size="lg" />
          <StatCell value={null} label="No data" decimals={1} size="lg" />
        </div>
      </Section>

      <Section title="StatTable" note="th scope · stacks < 640px">
        <StatTable caption="Example player stats" columns={playerCols} rows={playerRows} rowKey="name" className="max-w-2xl" />
      </Section>

      <Section title="Ticker" note="lower-third · scrollable when reduced">
        <Ticker
          items={["Player A +18% adds", "Player B questionable", "WR run starting", "DEF streamer: tier shift", "FAAB: 12% median bid"]}
        />
      </Section>

      <Section title="TierBadge & PredictabilityMeter" note="non-colour encoding">
        <div className="flex flex-wrap items-center gap-3">
          <TierBadge tier={1} label="Elite" />
          <TierBadge tier={3} label="Solid" />
          <TierBadge tier={7} />
        </div>
        <div className="mt-8 grid max-w-xl gap-6 sm:grid-cols-3">
          <PredictabilityMeter score={0.9} />
          <PredictabilityMeter score={0.5} />
          <PredictabilityMeter score={0.12} label="K/DEF" />
        </div>
      </Section>
    </div>
  );
}
