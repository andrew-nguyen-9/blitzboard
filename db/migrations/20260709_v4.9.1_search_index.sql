-- v4.9.1 — Sitewide search index (Epic 9a)
-- A single denormalized, ranked index over every searchable entity (teams,
-- players, news, and — when E9b lands — articles), plus a Bloom-filter
-- membership pre-check that lets the client skip the DB entirely for queries
-- whose trigrams are absent from the corpus (sub-100ms perceived latency,
-- "best indexing practices like Google with Bloom filtering").
--
-- Two-plane fit (docs/architecture/ARCHITECTURE.md): PUBLIC READ (anon +
-- authenticated) — search hits are already-public catalog data. WRITES are
-- service-role only (pipeline/search_index.py); no anon/auth mutate policy, so
-- RLS denies them. Idempotent + safe to re-run.

create extension if not exists "pg_trgm";

-- ------------------------------------------------------------
-- SEARCH_INDEX — one row per searchable entity, pre-ranked.
-- `search_text` is the normalized haystack (lowercased label + aliases); the
-- GIN trigram index below turns `ILIKE '%q%'` and the `%` similarity operator
-- into index scans instead of sequential scans.
-- ------------------------------------------------------------
create table if not exists public.search_index (
  entity_type text not null,                 -- 'team' | 'player' | 'news' | 'article'
  entity_id   text not null,                 -- source PK (uuid/text), stable per type
  label       text not null,                 -- primary display string
  sublabel    text,                          -- secondary line (position · team, source, …)
  url         text not null,                 -- where a hit navigates
  search_text text not null,                 -- normalized haystack for matching
  weight      real not null default 1,       -- per-type rank multiplier
  updated_at  timestamptz not null default now(),
  primary key (entity_type, entity_id)
);

-- Trigram GIN: powers similarity ranking + substring ILIKE without a seq scan.
create index if not exists search_index_trgm_idx
  on public.search_index using gin (search_text gin_trgm_ops);
-- Prefix path for short (<3 char) queries the trigram operator can't serve.
create index if not exists search_index_prefix_idx
  on public.search_index (lower(label) text_pattern_ops);

alter table public.search_index enable row level security;

drop policy if exists "Public read search_index" on public.search_index;
create policy "Public read search_index"
  on public.search_index for select
  to anon, authenticated
  using (true);
-- (no insert/update/delete policy → service-role writes bypass RLS; anon/auth cannot mutate.)

-- ------------------------------------------------------------
-- SEARCH_META — the Bloom filter blob (membership pre-check).
-- The pipeline builds a Bloom filter over the DISTINCT trigrams of every
-- `search_text`, storing the bit array (base64) + params. The client fetches it
-- once, and BEFORE issuing a query decomposes the query into trigrams: if the
-- filter reports every one as "definitely absent", there can be no trigram
-- overlap with the corpus, so the DB round-trip is skipped and [] returned.
-- Bloom filters have no false negatives, so a real match is never skipped.
-- ------------------------------------------------------------
create table if not exists public.search_meta (
  key         text primary key,              -- 'trgm_bloom'
  m           int  not null,                 -- bit array size
  k           int  not null,                 -- hash count
  n           int  not null,                 -- distinct trigrams inserted
  bits        text not null,                 -- base64 of the m-bit array
  updated_at  timestamptz not null default now()
);

alter table public.search_meta enable row level security;

drop policy if exists "Public read search_meta" on public.search_meta;
create policy "Public read search_meta"
  on public.search_meta for select
  to anon, authenticated
  using (true);

-- ------------------------------------------------------------
-- search_entities(q, lim) — ranked hits across all entity types in one call.
-- STABLE + reads only public data, so anon may invoke it. Ranking blends
-- trigram similarity with a prefix boost so "jal" surfaces "Jalen Hurts" high.
-- The `%` operator uses search_index_trgm_idx; the prefix arm uses ILIKE.
-- ------------------------------------------------------------
create or replace function public.search_entities(q text, lim int default 20)
returns table (
  entity_type text,
  entity_id   text,
  label       text,
  sublabel    text,
  url         text,
  score       real
)
language sql
stable
as $$
  with needle as (select lower(trim(q)) as q)
  select
    s.entity_type,
    s.entity_id,
    s.label,
    s.sublabel,
    s.url,
    (greatest(
       similarity(s.search_text, n.q),
       case
         when s.search_text ilike n.q || '%' then 0.95   -- starts-with (strongest)
         when s.search_text ilike '%' || n.q || '%' then 0.55
         else 0
       end
     ) * s.weight)::real as score
  from public.search_index s, needle n
  where n.q <> ''
    and (s.search_text % n.q or s.search_text ilike '%' || n.q || '%')
  order by score desc, s.label
  limit greatest(1, coalesce(lim, 20));
$$;
