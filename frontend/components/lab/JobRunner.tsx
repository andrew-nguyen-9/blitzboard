"use client";

import { useState } from "react";
import DiagnosticsTable from "./DiagnosticsTable";
import ReliabilityDiagram from "./ReliabilityDiagram";
import type { McmcDiagnostics, ReliabilityPoint } from "./types";

// Job console: fires fit / sim / draft / publish at the engine CLI (POST
// /lab/api/run) and streams back the log + any structured diagnostics receipt,
// which it renders through the same DiagnosticsTable / ReliabilityDiagram the page
// uses. Client Component (fetch + state). No animation → reduced-motion safe.
const JOBS = ["fit", "sim", "draft", "publish"] as const;
type Job = (typeof JOBS)[number];

interface RunResponse {
  ok: boolean;
  job: Job;
  code?: number | null;
  log?: string;
  error?: string;
  diagnostics?: {
    mcmc?: McmcDiagnostics;
    reliability?: ReliabilityPoint[];
  } | null;
}

const BLURB: Record<Job, string> = {
  fit: "Fit the posterior (MCMC).",
  sim: "Monte-Carlo season sim.",
  draft: "Solve draft strategy tree.",
  publish: "Publish a snapshot (calibration-gated).",
};

export default function JobRunner({ className }: { className?: string }) {
  const [running, setRunning] = useState<Job | null>(null);
  const [result, setResult] = useState<RunResponse | null>(null);

  async function run(job: Job) {
    setRunning(job);
    setResult(null);
    try {
      const res = await fetch("/lab/api/run", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ job }),
      });
      setResult((await res.json()) as RunResponse);
    } catch (e) {
      setResult({ ok: false, job, error: e instanceof Error ? e.message : "request failed" });
    } finally {
      setRunning(null);
    }
  }

  return (
    <div className={className}>
      <div className="flex flex-wrap gap-3" role="group" aria-label="Trigger engine jobs">
        {JOBS.map((job) => (
          <button
            key={job}
            type="button"
            onClick={() => run(job)}
            disabled={running != null}
            aria-busy={running === job}
            title={BLURB[job]}
            className="rounded-[var(--radius,0.5rem)] border border-line bg-surface px-4 py-2 text-body uppercase tracking-wide text-ink transition-colors hover:border-accent disabled:opacity-50"
          >
            {running === job ? `${job}…` : job}
          </button>
        ))}
      </div>

      {result && (
        <div className="mt-4" aria-live="polite">
          <p className={`text-label uppercase ${result.ok ? "text-pos" : "text-neg"}`}>
            {result.job}: {result.ok ? "ok" : "failed"}
            {result.code != null && result.code !== 0 ? ` (exit ${result.code})` : ""}
          </p>
          {(result.log || result.error) && (
            <pre className="mt-2 max-h-48 overflow-auto rounded-[var(--radius,0.5rem)] border border-line bg-surface p-3 font-mono text-label text-ink-1 whitespace-pre-wrap">
              {result.error ?? result.log}
            </pre>
          )}
          {result.diagnostics?.mcmc && (
            <DiagnosticsTable diagnostics={result.diagnostics.mcmc} className="mt-4" />
          )}
          {result.diagnostics?.reliability && (
            <ReliabilityDiagram points={result.diagnostics.reliability} className="mt-4" />
          )}
        </div>
      )}
    </div>
  );
}
