"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import DraftAnalysis from "@/components/DraftAnalysis";
import { loadSnapshot, type DraftSnapshot } from "@/lib/draftStore";

// Standalone analysis page (#4). Hydrates from the localStorage snapshot the
// draft room writes on every pick, so it works as its own shareable route.
export default function DraftAnalysisPage() {
  const [snap, setSnap] = useState<DraftSnapshot | null | undefined>(undefined);

  useEffect(() => {
    setSnap(loadSnapshot());
  }, []);

  return (
    <div className="py-10">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-display-md">Draft Analysis</h1>
          <p className="mt-2 text-body text-ink-muted">
            Grades, projected finishes, the players that matter, and each team&apos;s strategy.
          </p>
        </div>
        <Link href="/draft" className="rounded-full border border-hairline px-4 py-2 text-label transition hover:bg-surface-elevated">
          ← Back to draft
        </Link>
      </div>

      {snap === undefined ? (
        <div className="glass p-10 text-center text-body text-ink-muted">Loading your board…</div>
      ) : snap && snap.picks.length ? (
        <>
          <p className="mb-4 text-label text-ink-muted">
            {snap.config.name} · {snap.config.numTeams} teams · last updated {new Date(snap.updatedAt).toLocaleString()}
          </p>
          <DraftAnalysis picks={snap.picks} config={snap.config} mySlot={snap.mySlot} />
        </>
      ) : (
        <div className="glass p-10 text-center text-body text-ink-muted">
          No draft in progress yet. Head to the{" "}
          <Link href="/draft" className="text-accent">draft board</Link> and make some picks first.
        </div>
      )}
    </div>
  );
}
