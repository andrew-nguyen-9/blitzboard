import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getArticleBySlug } from "@/lib/queries";
import { articleBlocks, articleDate } from "@/lib/articles";

type Params = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug } = await params;
  const article = await getArticleBySlug(slug);
  if (!article) return { title: "Article" };
  return { title: article.title, description: article.summary };
}

// Article detail (Epic 9b). Renders the pipeline-written body as typed blocks
// (lib/articles) — plain text nodes + lists, React-escaped (no markdown dep, no
// dangerouslySetInnerHTML). Null-safe: an unknown slug (or offline) → notFound().
export default async function ArticlePage({ params }: Params) {
  const { slug } = await params;
  const article = await getArticleBySlug(slug);
  if (!article) notFound();

  const date = articleDate(article.published_at);
  const blocks = articleBlocks(article.body);

  return (
    <article className="mx-auto max-w-3xl px-5 py-16 md:px-8">
      <Link href="/articles" className="text-label text-ink-muted link-wipe">
        ← All findings
      </Link>

      <header className="mt-6">
        <div className="flex items-center gap-3 text-label text-ink-muted">
          <span className="rounded-full border border-neon-dim px-2.5 py-0.5 text-neon">
            {article.category}
          </span>
          {date && <time dateTime={article.published_at ?? undefined}>{date}</time>}
        </div>
        <h1 className="mt-3 font-display text-display-md text-ink">{article.title}</h1>
        <p className="mt-3 text-body-lg text-ink-2">{article.summary}</p>
      </header>

      <div className="mt-8 space-y-5 text-body-lg leading-relaxed text-ink-2">
        {blocks.map((block, i) =>
          block.kind === "list" ? (
            <ul key={i} className="list-disc space-y-1 pl-6 marker:text-neon">
              {block.items.map((item, j) => (
                <li key={j}>{item}</li>
              ))}
            </ul>
          ) : (
            <p key={i}>{block.text}</p>
          ),
        )}
      </div>

      {article.source && (
        <footer className="mt-10 border-t border-hairline pt-4 text-label text-ink-muted">
          Source: {article.source}
        </footer>
      )}
    </article>
  );
}
