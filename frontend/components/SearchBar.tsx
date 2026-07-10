"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { searchEntities, groupByType, type SearchHit, type SearchResult } from "@/lib/search";

// Sitewide search island (Epic 9a). Debounced live query → ranked hits across
// teams / players / news / articles, grouped by type. The Bloom pre-check +
// GIN-backed RPC keep it sub-100ms; we surface the measured latency so the
// "instant" claim is visible, not asserted.
//
// Styling composes F1 primitives only (NORTH_STAR.md §Primitives → Glass):
// `.glass-neon` panel, `.neon-edge` active rim, `.neon-text` on the header.
// No new tokens/utilities are introduced here (E10 owns globals/tailwind).

const TYPE_LABEL: Record<string, string> = {
  team: "Teams",
  player: "Players",
  news: "News",
  article: "Articles",
};
const TYPE_ORDER = ["player", "team", "news", "article"] as const;

export default function SearchBar({ initialQuery = "", autoFocus = true }: { initialQuery?: string; autoFocus?: boolean }) {
  const [q, setQ] = useState(initialQuery);
  const [res, setRes] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const seq = useRef(0); // guards against out-of-order async responses

  useEffect(() => {
    if (autoFocus) inputRef.current?.focus();
  }, [autoFocus]);

  useEffect(() => {
    const query = q.trim();
    if (!query) {
      setRes(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    const id = ++seq.current;
    // Debounce keystrokes; the pre-check makes the fetch cheap when it fires.
    const t = setTimeout(async () => {
      const r = await searchEntities(query, 24);
      if (id === seq.current) {
        setRes(r);
        setLoading(false);
      }
    }, 120);
    return () => clearTimeout(t);
  }, [q]);

  const grouped = useMemo(() => (res ? groupByType(res.hits) : null), [res]);
  const hasHits = !!res && res.hits.length > 0;

  return (
    <div className="mx-auto max-w-2xl">
      <div className="glass-neon neon-edge flex items-center gap-3 rounded-2xl px-4 py-3">
        <svg aria-hidden width="20" height="20" viewBox="0 0 24 24" fill="none" className="shrink-0 text-neon">
          <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
          <path d="m20 20-3.5-3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <input
          ref={inputRef}
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search teams, players, news…"
          aria-label="Search BlitzBoard"
          role="combobox"
          aria-expanded={hasHits}
          aria-controls="search-results"
          className="w-full bg-transparent text-body outline-none placeholder:text-ink-muted"
        />
        {res && (
          <span className="shrink-0 text-label text-ink-muted tabular-nums" aria-live="polite">
            {res.skipped ? "0 · pre-filtered" : `${Math.round(res.ms)} ms`}
          </span>
        )}
      </div>

      <div id="search-results" className="mt-4">
        {q.trim() && !loading && !hasHits && (
          <p className="px-2 py-6 text-center text-body text-ink-muted">
            No matches for “{q.trim()}”.
          </p>
        )}

        {grouped &&
          TYPE_ORDER.filter((t) => grouped[t]?.length).map((t) => (
            <section key={t} className="mb-5">
              <h3 className="mb-2 px-2 text-label uppercase tracking-wide text-ink-muted">{TYPE_LABEL[t]}</h3>
              <ul className="glass overflow-hidden rounded-xl">
                {grouped[t].map((h) => (
                  <HitRow key={`${h.entityType}:${h.entityId}`} hit={h} />
                ))}
              </ul>
            </section>
          ))}
      </div>
    </div>
  );
}

function HitRow({ hit }: { hit: SearchHit }) {
  return (
    <li className="border-b border-hairline/60 last:border-0">
      <Link
        href={hit.url}
        className="flex items-center justify-between gap-3 px-4 py-2.5 transition hover:bg-accent/5"
      >
        <span className="min-w-0">
          <span className="block truncate text-body">{hit.label}</span>
          {hit.sublabel && <span className="block truncate text-label text-ink-muted">{hit.sublabel}</span>}
        </span>
        <span aria-hidden className="shrink-0 text-ink-muted">↗</span>
      </Link>
    </li>
  );
}
