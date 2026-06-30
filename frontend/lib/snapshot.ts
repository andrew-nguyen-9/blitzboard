// Client data layer for the precomputed CDN player snapshot (DATA_TRANSFER.md).
//
// The full player universe is published once per day as an immutable, content-
// hashed, gzip blob (pipeline/publish_snapshot.py). The browser fetches it from
// the CDN — most loads never touch the DB — decodes it once into an in-memory
// table, then sorts/filters/searches locally (zero round trips). gzip is decoded
// natively with DecompressionStream('gzip'); no JS decompression dependency.
import type { Engine } from "./types";

const STORAGE_BASE =
  (process.env.NEXT_PUBLIC_SUPABASE_URL ?? "").replace(/\/+$/, "") +
  "/storage/v1/object/public/snapshots";
const MANIFEST_URL = `${STORAGE_BASE}/manifest.json`;

// Columnar payload: one array per column under `data` (compresses far better than
// row-arrays). adp/boom/bust/bye ARE shipped — the shared column contract
// (lib/playerColumns.ts) renders them; null when the snapshot predates them.
export interface SnapshotPayload {
  v: number;
  profile: string;
  engine: string;
  cols: string[];
  count: number;
  data: Array<Array<string | number | null>>;
}

// A decoded snapshot row. `id` is the Sleeper id (the compact, stable route key).
export interface SnapshotPlayer {
  id: string;
  full_name: string;
  position: string | null;
  nfl_team: string | null;
  value: number | null;
  vor: number | null;
  rank: number | null;
  predictability: number | null;
  trend: number | null;
  adp: number | null;
  boom: number | null;
  bust: number | null;
  bye: number | null;
}

const NUM = (x: unknown): number | null => (typeof x === "number" ? x : null);
const STR = (x: unknown): string | null => (typeof x === "string" ? x : null);

// Decode columnar data into row objects, resolving columns BY NAME (resilient to
// column reordering or additions), not by fixed position.
export function decodeSnapshot(payload: SnapshotPayload): SnapshotPlayer[] {
  const col = (name: string): Array<string | number | null> | null => {
    const k = payload.cols.indexOf(name);
    return k >= 0 ? payload.data[k] : null;
  };
  const sid = col("sid"), n = col("n"), pos = col("pos"), tm = col("tm");
  const val = col("val"), vor = col("vor"), rnk = col("rnk"), rho = col("rho"), trend = col("trend");
  const adp = col("adp"), boom = col("boom"), bust = col("bust"), bye = col("bye");
  const out: SnapshotPlayer[] = [];
  for (let i = 0; i < payload.count; i++) {
    out.push({
      id: String(sid?.[i] ?? ""),
      full_name: STR(n?.[i]) ?? "",
      position: STR(pos?.[i]),
      nfl_team: STR(tm?.[i]),
      value: NUM(val?.[i]),
      vor: NUM(vor?.[i]),
      rank: NUM(rnk?.[i]),
      predictability: NUM(rho?.[i]),
      trend: NUM(trend?.[i]),
      adp: NUM(adp?.[i]),
      boom: NUM(boom?.[i]),
      bust: NUM(bust?.[i]),
      bye: NUM(bye?.[i]),
    });
  }
  return out;
}

// Decode a gzip blob to JSON using the platform's native stream — supported in
// every evergreen browser and Node 18+ (brotli is NOT, which is why we ship gzip).
export async function gunzipJson(buf: ArrayBuffer): Promise<unknown> {
  const stream = new Response(buf).body!.pipeThrough(new DecompressionStream("gzip"));
  return JSON.parse(await new Response(stream).text());
}

// Immutable snapshot URLs → cache decoded players for the session by URL.
const cache = new Map<string, SnapshotPlayer[]>();

// Resolve the current snapshot from the short-TTL manifest, then fetch + decode
// the immutable blob. Null-safe: returns null with no backend or on any failure,
// so the caller falls back to the live query / empty state.
export async function loadSnapshot(opts?: {
  profile?: string;
  engine?: Engine;
}): Promise<SnapshotPlayer[] | null> {
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL) return null;
  const key = `${opts?.profile ?? "default"}:${opts?.engine ?? "vorp"}`;
  try {
    const manifest = await fetch(MANIFEST_URL, { cache: "no-store" }).then((r) =>
      r.ok ? r.json() : null,
    );
    const url: string | undefined = manifest?.snapshots?.[key]?.url;
    if (!url) return null;
    const hit = cache.get(url);
    if (hit) return hit;
    const buf = await fetch(url).then((r) => (r.ok ? r.arrayBuffer() : null));
    if (!buf) return null;
    const players = decodeSnapshot((await gunzipJson(buf)) as SnapshotPayload);
    cache.set(url, players);
    return players;
  } catch (e) {
    console.error("[snapshot.loadSnapshot]", e);
    return null;
  }
}
