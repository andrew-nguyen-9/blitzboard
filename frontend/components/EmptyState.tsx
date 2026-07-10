// Graceful "coming soon" / no-data state (inherited degradation pattern).
// Used for not-yet-built sections and for live sections before keys exist.
export default function EmptyState({
  title,
  phase,
  children,
}: {
  title: string;
  phase?: string;
  children?: React.ReactNode;
}) {
  return (
    // v4 E10: an empty/roadmap surface is exactly the "hero/empty" case the neon
    // circuit grid is for (NORTH_STAR.md §Primitives → Texture). Grid is decorative
    // (aria-hidden, alpha well under the text plane); overflow-hidden clips it to the
    // rounded glass. Badge accent→neon (dark 9.60→12.62, light 4.96→5.52 on bg-1) and
    // body ink-2→ink-1 (dark 5.60→9.05, light 6.91→8.93) — both measurably clearer, AA.
    <div className="glass relative mx-auto my-16 max-w-xl overflow-hidden p-10 text-center" style={{ boxShadow: "var(--glow)" }}>
      <div aria-hidden className="neon-grid pointer-events-none absolute inset-0" />
      <div className="relative">
        {phase && (
          <div className="mb-3 inline-block rounded-full border border-neon-dim px-3 py-1 text-label text-neon">
            {phase}
          </div>
        )}
        <h2 className="font-display text-display-md">{title}</h2>
        <p className="mt-3 text-body text-ink-1">
          {children ?? "This section is on the roadmap. Check back as the build progresses."}
        </p>
      </div>
    </div>
  );
}
