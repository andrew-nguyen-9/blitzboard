// Sitewide search (Epic 9a) — ranked hits across teams / players / news /
// articles, with a client-side Bloom-filter membership pre-check so obvious
// misses never touch the network (sub-100ms perceived latency; "best indexing
// practices like Google with Bloom filtering").
//
// Two stages:
//   1. PRE-CHECK — decompose the query into trigrams and test them against a
//      Bloom filter built by the pipeline over the whole corpus (search_meta).
//      Bloom filters have no false negatives, so if EVERY query trigram is
//      "definitely absent" there can be no trigram overlap with any indexed
//      row → we skip the DB and return [] immediately. Real hits are never
//      dropped. (Internal 3-grams ⊆ pg_trgm's word trigrams, so the mapping to
//      the server-side similarity match is conservative — see search_index.py.)
//   2. RANK — for anything that survives, one RPC (`search_entities`) does the
//      trigram-similarity + prefix ranking server-side via the GIN index.
//
// Null-safe throughout: no Supabase client, no bloom, or a missing RPC all
// degrade to [] instead of throwing (offline builds render empty states).
//
// The tokenizer + Bloom hashing here are byte-for-byte identical to
// pipeline/search_index.py so a filter built there reads correctly here.
import { getSupabase } from "./supabase";

export type SearchEntity = "team" | "player" | "news" | "article";

export interface SearchHit {
  entityType: SearchEntity;
  entityId: string;
  label: string;
  sublabel: string | null;
  url: string;
  score: number;
}

export interface SearchResult {
  hits: SearchHit[];
  ms: number; // measured latency for this query
  skipped: boolean; // true when the Bloom pre-check short-circuited the DB
}

// ── Tokenizer (mirror of search_index.py) ────────────────────────────────
export function normalize(s: string | null | undefined): string {
  if (!s) return "";
  return s.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

// Length-3 sliding-window substrings of the normalized string.
export function trigrams(s: string): Set<string> {
  const n = normalize(s);
  const out = new Set<string>();
  for (let i = 0; i + 3 <= n.length; i++) out.add(n.slice(i, i + 3));
  return out;
}

// ── FNV-1a (32-bit) — identical arithmetic to the Python side ─────────────
function fnv1a(bytes: Uint8Array): number {
  let h = 0x811c9dc5;
  for (const b of bytes) {
    h ^= b;
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

const enc = new TextEncoder();
function positions(gram: string, m: number, k: number): number[] {
  const data = enc.encode(gram);
  const h1 = fnv1a(data);
  const salted = new Uint8Array(data.length + 1);
  salted.set(data, 1); // leading 0x00
  const h2 = (fnv1a(salted) | 1) >>> 0; // odd stride
  const pos: number[] = [];
  for (let i = 0; i < k; i++) pos.push((h1 + i * h2) % m);
  return pos;
}

export class BloomFilter {
  constructor(
    private bits: Uint8Array,
    readonly m: number,
    readonly k: number,
    readonly n: number,
  ) {}

  static fromMeta(meta: { m: number; k: number; n: number; bits: string }): BloomFilter {
    const raw = atob(meta.bits);
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
    return new BloomFilter(bytes, meta.m, meta.k, meta.n);
  }

  private has(gram: string): boolean {
    for (const p of positions(gram, this.m, this.k)) {
      if (!(this.bits[p >> 3] & (1 << (p & 7)))) return false; // definitely absent
    }
    return true; // possibly present
  }

  // True unless EVERY query trigram is definitely absent. Queries with no
  // trigrams (<3 chars) can't be ruled out → always pass through to the DB.
  mightMatch(query: string): boolean {
    const grams = trigrams(query);
    if (grams.size === 0) return true;
    for (const g of grams) if (this.has(g)) return true;
    return false;
  }
}

// ── Bloom load (fetched once, cached per session) ─────────────────────────
let bloomPromise: Promise<BloomFilter | null> | null = null;

async function loadBloom(): Promise<BloomFilter | null> {
  if (bloomPromise) return bloomPromise;
  bloomPromise = (async () => {
    const sb = getSupabase();
    if (!sb) return null;
    const { data, error } = await sb
      .from("search_meta")
      .select("m,k,n,bits")
      .eq("key", "trgm_bloom")
      .maybeSingle();
    if (error || !data) return null;
    try {
      return BloomFilter.fromMeta(data as any);
    } catch {
      return null;
    }
  })();
  return bloomPromise;
}

// Test/HMR seam: drop the cached filter.
export function _resetSearchCache() {
  bloomPromise = null;
}

const now = () =>
  typeof performance !== "undefined" ? performance.now() : Date.now();

// ── Public API ────────────────────────────────────────────────────────────
export async function searchEntities(query: string, limit = 20): Promise<SearchResult> {
  const t0 = now();
  const q = query.trim();
  if (!q) return { hits: [], ms: 0, skipped: false };

  const bloom = await loadBloom();
  if (bloom && !bloom.mightMatch(q)) {
    return { hits: [], ms: now() - t0, skipped: true };
  }

  const sb = getSupabase();
  if (!sb) return { hits: [], ms: now() - t0, skipped: false };

  const { data, error } = await sb.rpc("search_entities", { q, lim: limit });
  if (error) {
    console.error("[search.searchEntities]", error.message);
    return { hits: [], ms: now() - t0, skipped: false };
  }
  const hits: SearchHit[] = (data ?? []).map((r: any) => ({
    entityType: r.entity_type,
    entityId: r.entity_id,
    label: r.label,
    sublabel: r.sublabel ?? null,
    url: r.url,
    score: r.score,
  }));
  return { hits, ms: now() - t0, skipped: false };
}

// Group ranked hits by entity type (preserves within-group order) for the UI.
export function groupByType(hits: SearchHit[]): Record<SearchEntity, SearchHit[]> {
  const out: Record<SearchEntity, SearchHit[]> = { team: [], player: [], news: [], article: [] };
  for (const h of hits) (out[h.entityType] ??= []).push(h);
  return out;
}
