import EmptyState from "@/components/EmptyState";

export const metadata = { title: "Waiver Wire" };

export default function WaiversPage() {
  return (
    <EmptyState title="Waiver Wire Tool" phase="Phase 4">
      FAAB bid recommendations (% of remaining budget) blended with the trending signal —
      news sentiment ⊕ Sleeper add/drop velocity. Powered by the waiver-window sentiment cron.
    </EmptyState>
  );
}
