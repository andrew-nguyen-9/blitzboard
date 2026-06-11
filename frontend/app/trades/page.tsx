import EmptyState from "@/components/EmptyState";

export const metadata = { title: "Trade Optimizer" };

export default function TradesPage() {
  return (
    <EmptyState title="Trade Optimizer" phase="Phase 5">
      Finds Pareto-improving swaps across rosters using your league&apos;s scoring and
      positional need. Needs full rosters + computed values, so it lands last.
    </EmptyState>
  );
}
