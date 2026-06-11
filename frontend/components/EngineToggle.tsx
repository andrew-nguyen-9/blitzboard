"use client";

import { useRouter, useSearchParams } from "next/navigation";
import type { Engine } from "@/lib/types";

// VORP ⇄ Monte Carlo toggle (D5). Monte Carlo is precomputed in P7; until then
// it's shown disabled so the UI is ready the moment those values land.
export default function EngineToggle({ active }: { active: Engine }) {
  const router = useRouter();
  const params = useSearchParams();

  function set(engine: Engine) {
    const next = new URLSearchParams(params);
    next.set("engine", engine);
    router.push(`?${next.toString()}`);
  }

  return (
    <div className="inline-flex rounded-full border border-hairline bg-surface p-1 text-label">
      <button
        onClick={() => set("vorp")}
        className={`rounded-full px-3 py-1 transition ${active === "vorp" ? "bg-accent text-bg" : "text-ink-muted hover:text-ink"}`}
      >
        VORP
      </button>
      <button
        disabled
        title="Monte Carlo lands in Phase 7"
        className="cursor-not-allowed rounded-full px-3 py-1 text-ink-muted/50"
      >
        Monte Carlo <span className="text-[10px]">soon</span>
      </button>
    </div>
  );
}
