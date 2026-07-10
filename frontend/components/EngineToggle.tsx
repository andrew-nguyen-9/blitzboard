"use client";

import { useRouter, useSearchParams } from "next/navigation";
import type { Engine } from "@/lib/types";

// VORP ⇄ Monte Carlo toggle (P7). Both engines write to player_value; toggle switches engine= param.
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
        className={`flex min-h-11 items-center rounded-full px-4 transition ${active === "vorp" ? "bg-accent text-bg" : "text-ink-muted hover:text-ink"}`}
      >
        VORP
      </button>
      <button
        onClick={() => set("monte_carlo")}
        className={`flex min-h-11 items-center rounded-full px-4 transition ${active === "monte_carlo" ? "bg-accent text-bg" : "text-ink-muted hover:text-ink"}`}
      >
        Monte Carlo
      </button>
    </div>
  );
}
