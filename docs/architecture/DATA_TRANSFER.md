# Player Data Delivery — killing the 500-player ceiling

## The problem (v1)

The Players tab tops out at ~500 players. Root cause is almost certainly **PostgREST's
default row cap** (`max-rows`, often 1000) compounded by an implicit `.limit()`/single
`.range()` call in `lib/queries.ts` — not a real data limit. The full Sleeper universe is
~2–3k fantasy-relevant players, and the pipeline already computes value for all of them
daily. We're just failing to *deliver* them.

## Principle: precompute once, deliver as a static artifact

The value layer changes **once per day** (cron), is **identical for every anonymous user**
of a given scoring profile, and is **read-only** on the frontend. That is the textbook
profile for a **precomputed, CDN-cached, immutable snapshot** — the strategy large-dataset
sites use (ship a compact static dataset + paginate/virtualize client-side) instead of
hammering a row API per request.

## The delivery design

### 1. Pipeline publishes versioned snapshots
After `value_engine_run.py`, a new `publish_snapshot.py` writes, per `(scoring_profile ×
engine)`:

- `players-<profile>-<engine>-<date>.bin` — the **core list payload**: only the columns the
  table needs (id, name, pos, team, value, vor, rank, tier, boom, bust, predictability,
  trend). Encoded compactly (see below), **brotli-compressed**, uploaded to Supabase Storage
  / a CDN bucket with a content hash in the name → **immutable, `Cache-Control: immutable,
  max-age=31536000`**.
- A tiny `manifest.json` (uncached / short TTL) mapping `profile+engine → current snapshot
  URL + hash + row count`. The client fetches the manifest, then the immutable blob.

### 2. Compact wire format (not verbose JSON)
Per-row JSON like `{"player_id":"4046","full_name":...}` is mostly key bytes. Instead:

- **Columnar / typed arrays**: parallel arrays per column (`pos: Uint8`, `value: Float32`,
  `rank: Uint16`, string columns dictionary-encoded). 2–3k players → tens of KB after brotli,
  vs. hundreds of KB of row-JSON. Decode once into the table model on the client.
- Acceptable simpler interim: a single minified JSON array with short keys + brotli — still
  fits the ≤60KB budget for the core list. Upgrade to columnar if needed.

### 3. Frontend consumes it efficiently
- **Fetch the compact snapshot once** (cached at the edge → most users hit the CDN, never
  the DB). Decode into an in-memory table.
- **Virtualized rows** (`@tanstack/virtual` / `virtua`): render only visible rows, so 2–3k
  players scroll at 60fps with a tiny DOM.
- **Client-side sort/filter/search** over the in-memory dataset (instant — no round trips).
- **Player detail is lazy**: the heavy per-player payload (history, distribution, news,
  splits) is fetched on demand when a card opens (and **prefetched** on hover/focus per the
  design guideline).

### 4. Pagination where a live query is still needed
For any genuinely paginated live query (e.g. authenticated, per-user, or search over a
table that can't be a static snapshot), use **keyset/cursor pagination** (`where (value,id)
< (last_value,last_id) order by value desc, id desc limit N`) — stable and O(1) per page,
unlike `offset` — and raise/parameterize the PostgREST `max-rows` explicitly. Never rely on
a default cap.

## Why this is fast *and* cheap

- The DB serves ~1 cron write + occasional misses; **the CDN serves everyone else**.
- Wire size drops ~5–10× (columnar + brotli) → instant first render on mobile 4G.
- Sort/filter/search are local → zero-latency interaction.
- Snapshots are immutable + content-hashed → perfect caching, trivial rollback, no
  cache-invalidation headaches (new day = new hash = new URL).

## Acceptance (v2.3)

- All fantasy-relevant players load (no 500 cap), initial core payload ≤ 60KB.
- Table scroll 60fps with the full universe; sort/filter/search < 50ms.
- Player detail lazy-loaded + prefetched on intent.
- Snapshot pipeline idempotent; manifest + immutable-blob caching verified at the edge.

## Shipped (v2.3.0) — wire-format note

The compression above landed as **gzip, not brotli**: Supabase Storage does not persist a
`Content-Encoding` header (so a stored brotli blob would reach the browser undeclared and
break parsing), and `DecompressionStream('gzip')` lets the client decode natively — brotli
isn't supported there. The blob is stored octet-stream with `cache-control = <seconds>`
(storage3 emits `max-age=<value>`); content-hashed names give effective immutability. The
row id on the wire is the compact **`sleeper_id`**, not the UUID (UUID entropy alone blew
the budget). Format is **array-of-arrays keyed by a short column header** (minified-JSON
path); gzip hits 45.4KB for ~2,800 players, so the columnar upgrade was unneeded. Full
delta: `docs/archive/v2/v2.3-player-data.md` (As shipped).

Wire format landed **columnar** (one array per column under `data`, `WIRE_VERSION = 2`): the
real universe is 4,254 players, which a row-array snapshot rendered at 78KB — over budget.
Columnar + dropping `boom`/`bust` (list-unused; on the lazy card) + 1dp rounding gives
**58.6KB for the full universe, no cap** (the doc's "upgrade to columnar if needed" path).
