import SearchBar from "@/components/SearchBar";

export const metadata = { title: "Search" };

// Sitewide search (Epic 9a) — a thin server shell; all matching happens in the
// client island (SearchBar → lib/search.ts), which runs a Bloom pre-check
// before a GIN-backed ranking RPC. `?q=` seeds an initial query so results are
// shareable/deep-linkable.
export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;

  return (
    <div className="py-12">
      <div className="mx-auto max-w-2xl text-center">
        <h1 className="neon-text font-display text-display-md">Search</h1>
        <p className="mt-2 text-body text-ink-muted">
          Teams, players, news — ranked, trigram-indexed, Bloom pre-filtered for instant misses.
        </p>
      </div>

      <div className="mt-8">
        <SearchBar initialQuery={q ?? ""} />
      </div>
    </div>
  );
}
