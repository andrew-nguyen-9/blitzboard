"use client";

// Shared league context control for the authed waiver/trade surfaces. A pill toggle when
// 2-3 leagues, a static chip for one. Replaces the unauth "Scope: All NFL" insertion point.
export interface LeagueOpt {
  id: string;
  name: string;
}

export default function LeagueSelector({
  leagues,
  value,
  onChange,
}: {
  leagues: LeagueOpt[];
  value: string;
  onChange: (id: string) => void;
}) {
  if (leagues.length <= 1) {
    return (
      <span className="rounded-full border border-hairline px-3 py-1.5 text-label text-ink-muted">
        League: <span className="text-ink">{leagues[0]?.name ?? "—"}</span>
      </span>
    );
  }
  return (
    <div className="inline-flex rounded-full border border-hairline p-1 text-label" role="group" aria-label="Select league">
      {leagues.map((l) => (
        <button
          key={l.id}
          type="button"
          onClick={() => onChange(l.id)}
          aria-pressed={value === l.id}
          className={`max-w-[10rem] truncate rounded-full px-3 py-1 transition ${
            value === l.id ? "bg-accent text-bg" : "text-ink-muted hover:text-ink"
          }`}
        >
          {l.name}
        </button>
      ))}
    </div>
  );
}
