import EmptyState from "@/components/EmptyState";
import ArticleCard from "@/components/ArticleCard";
import { getArticles } from "@/lib/queries";

export const metadata = {
  title: "Articles",
  description: "Auto-published modeling findings — weather, pace, and scheme signals the projection model reads.",
};

// Articles (Epic 9b) — a feed of modeling findings the cron pipeline generates
// from E3's environmental/team-scheme context (pipeline/articles_generate.py).
// Server component: one null-safe read, empty state before any backend/keys.
export default async function ArticlesPage() {
  const articles = await getArticles();

  if (!articles.length) {
    return (
      <EmptyState title="Articles" phase="v4 · E9b">
        Modeling findings publish here automatically once the context pipeline runs — weather,
        pace, pass-rate, and venue signals the projection model reads, written up as they surface.
      </EmptyState>
    );
  }

  return (
    <div className="py-12">
      <div className="max-w-2xl">
        {/* F1 §Primitives → Glow: the accent word carries the charged neon signal. */}
        <h1 className="font-display text-display-md">
          Modeling <span className="neon-text">findings</span>
        </h1>
        <p className="mt-2 text-body text-ink-muted">
          Auto-published from the projection model&apos;s context feed — weather, pace, and scheme
          signals, dated and sourced. No punditry, just what the numbers moved on.
        </p>
      </div>

      <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {articles.map((a) => (
          <ArticleCard key={a.id} article={a} />
        ))}
      </div>
    </div>
  );
}
