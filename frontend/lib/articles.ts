// Pure rendering helper for article bodies (Epic 9b). The pipeline writes plain
// prose: blank-line-separated paragraphs, with `- ` lines forming bullet lists.
// We parse to typed blocks and let React render text nodes (auto-escaped — no
// markdown dependency, no dangerouslySetInnerHTML, so no XSS surface).

export type ArticleBlock =
  | { kind: "text"; text: string }
  | { kind: "list"; items: string[] };

// Split a stored article `body` into ordered text/list blocks. Consecutive
// `- ` lines coalesce into one list; a non-bullet line within a paragraph (e.g.
// a "Fastest:" lead-in) renders as its own text block before the list.
export function articleBlocks(body: string): ArticleBlock[] {
  const blocks: ArticleBlock[] = [];
  for (const para of (body ?? "").split(/\n{2,}/)) {
    let text: string[] = [];
    let list: string[] = [];
    const flushText = () => {
      if (text.length) blocks.push({ kind: "text", text: text.join(" ") });
      text = [];
    };
    const flushList = () => {
      if (list.length) blocks.push({ kind: "list", items: list });
      list = [];
    };
    for (const raw of para.split("\n")) {
      const line = raw.trimEnd();
      if (!line.trim()) continue;
      if (line.startsWith("- ")) {
        flushText();
        list.push(line.slice(2).trim());
      } else {
        flushList();
        text.push(line.trim());
      }
    }
    flushText();
    flushList();
  }
  return blocks;
}

// Short, locale-stable date label for cards/headers ("Sep 10, 2025"). Falsy → "".
export function articleDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}
