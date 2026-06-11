"use client";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="py-32 text-center">
      <div className="font-display text-display-md">Something fumbled.</div>
      <p className="mt-3 text-body text-ink-muted">An unexpected error occurred.</p>
      <button onClick={reset} className="mt-8 rounded-full bg-accent px-5 py-2.5 font-semibold text-bg">
        Try again
      </button>
    </div>
  );
}
