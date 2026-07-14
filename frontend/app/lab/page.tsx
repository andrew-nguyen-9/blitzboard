import { MiniDistribution, RangeBar, gaussianQuantiles } from "@/components/uncertainty";
import DiagnosticsTable from "@/components/lab/DiagnosticsTable";
import ReliabilityDiagram from "@/components/lab/ReliabilityDiagram";
import JobRunner from "@/components/lab/JobRunner";
import WhatIfPanel from "@/components/lab/WhatIfPanel";
import type { McmcDiagnostics, ReliabilityPoint } from "@/components/lab/types";
import type { ScenarioPlayer } from "@/components/lab/whatif";

// Never statically prerender the Lab: keep its component tree out of the prod
// build's static HTML entirely. At request time the layout guard 404s before any
// of this renders (prod build → labEnabled() === false).
export const dynamic = "force-dynamic";

// The Model Lab: trigger engine jobs, inspect MCMC convergence + calibration, run
// what-if scenarios, publish. Server Component shell; interactivity lives in the
// JobRunner / WhatIfPanel client islands. Local-only — the layout 404s this route
// in any prod build. Seed diagnostics below are a static reference sample so the
// page renders meaningfully before a live run wires real snapshot data.

const SEED_MCMC: McmcDiagnostics = {
  draws: 4000,
  divergences: 0,
  params: [
    { name: "team_pace", rhat: 1.002, ess: 3200 },
    { name: "wr_target_share", rhat: 1.008, ess: 1450 },
    { name: "qb_efficiency", rhat: 1.031, ess: 260 },
    { name: "def_adjustment", rhat: 1.0, ess: 3900 },
  ],
};

const SEED_RELIABILITY: ReliabilityPoint[] = [
  { predicted: 0.05, observed: 0.04, count: 120 },
  { predicted: 0.2, observed: 0.18, count: 210 },
  { predicted: 0.4, observed: 0.43, count: 260 },
  { predicted: 0.6, observed: 0.58, count: 240 },
  { predicted: 0.8, observed: 0.83, count: 180 },
  { predicted: 0.95, observed: 0.93, count: 90 },
];

const SEED_ROSTER: ScenarioPlayer[] = [
  { id: "kc-wr1", name: "Rashee Rice", team: "KC", position: "WR", proj: 16.4 },
  { id: "kc-wr2", name: "Xavier Worthy", team: "KC", position: "WR", proj: 11.2 },
  { id: "kc-wr3", name: "JuJu Smith-Schuster", team: "KC", position: "WR", proj: 6.1 },
  { id: "kc-te1", name: "Travis Kelce", team: "KC", position: "TE", proj: 13.8 },
];

function Section({
  title,
  note,
  children,
}: {
  title: string;
  note?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-t border-line py-8">
      <div className="mb-5 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 className="font-display text-display-md text-ink">{title}</h2>
        {note && <span className="text-label uppercase text-ink-2">{note}</span>}
      </div>
      {children}
    </section>
  );
}

export default function LabPage() {
  const previewQuantiles = gaussianQuantiles(16.4, 5.2);

  return (
    <div>
      <h1 className="font-display text-display-lg text-ink">Model Lab</h1>
      <p className="mt-3 max-w-2xl text-body-lg text-ink-1">
        Engine-tier console: trigger fit / sim / draft / publish, inspect MCMC convergence and
        calibration, and run what-if scenarios. Never shipped to production.
      </p>

      <Section title="Trigger jobs" note="engine CLI · fit / sim / draft / publish">
        <JobRunner />
      </Section>

      <Section title="MCMC diagnostics" note="R̂ · ESS · divergences">
        <DiagnosticsTable diagnostics={SEED_MCMC} />
      </Section>

      <Section title="Calibration" note="reliability diagram · reuses uncertainty kit">
        <div className="grid gap-8 md:grid-cols-2">
          <ReliabilityDiagram points={SEED_RELIABILITY} />
          <div>
            <span className="text-label uppercase text-ink-2">Projection distribution (sample)</span>
            <MiniDistribution quantiles={previewQuantiles} unit=" pts" className="mt-2" />
            <div className="mt-4">
              <RangeBar quantiles={previewQuantiles} unit=" pts" decimals={1} />
            </div>
          </div>
        </div>
      </Section>

      <Section title="What-if" note="injure a player → downstream deltas">
        <WhatIfPanel players={SEED_ROSTER} />
      </Section>
    </div>
  );
}
