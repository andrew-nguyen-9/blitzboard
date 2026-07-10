import Link from "next/link";
import { articleDate } from "@/lib/articles";
import type { ArticleSummary } from "@/lib/types";

// One article tile in the Articles feed (Epic 9b). Server component — no
// interactivity, so no client island. Composes F1 glass + neon primitives
// (NORTH_STAR §Primitives): rationed neon rides in on hover/focus only (the
// E10 "ignite, don't rest" rule — glass at rest, neon rim + glow on intent).
export default function ArticleCard({ article }: { article: ArticleSummary }) {
  const date = articleDate(article.published_at);
  return (
    <Link
      href={`/articles/${article.slug}`}
      data-cursor="open"
      className="group relative block h-full focus:outline-none"
    >
      <div className="glass flex h-full flex-col overflow-hidden p-6 transition-[box-shadow,border-color] duration-300 group-hover:border-neon-dim group-hover:shadow-neon group-focus-visible:border-neon-dim group-focus-visible:shadow-neon">
        <div className="flex items-center gap-3 text-label text-ink-muted">
          <span className="rounded-full border border-neon-dim px-2.5 py-0.5 text-neon">
            {article.category}
          </span>
          {date && <time dateTime={article.published_at ?? undefined}>{date}</time>}
        </div>
        <h3 className="mt-3 font-display text-heading link-wipe">{article.title}</h3>
        <p className="mt-2 flex-1 text-body text-ink-2">{article.summary}</p>
        <span className="mt-4 text-label text-neon opacity-0 transition group-hover:opacity-100 group-focus-visible:opacity-100">
          Read finding ↗
        </span>
      </div>
    </Link>
  );
}
