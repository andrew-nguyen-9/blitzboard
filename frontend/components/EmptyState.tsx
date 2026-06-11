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
    <div className="glass mx-auto my-16 max-w-xl p-10 text-center" style={{ boxShadow: "var(--glow)" }}>
      {phase && (
        <div className="mb-3 inline-block rounded-full border border-hairline px-3 py-1 text-label text-accent">
          {phase}
        </div>
      )}
      <h2 className="font-display text-display-md">{title}</h2>
      <p className="mt-3 text-body text-ink-muted">
        {children ?? "This section is on the roadmap. Check back as the build progresses."}
      </p>
    </div>
  );
}
