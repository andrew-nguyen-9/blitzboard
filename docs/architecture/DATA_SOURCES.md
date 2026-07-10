# Data Sources & the Adapter Pattern (F2)

How BlitzBoard ingests **free** external data uniformly, and how every new source
degrades to nothing when its key (if any) is absent. Fits the pipeline plane of
`ARCHITECTURE.md`: `SOURCES → PIPELINE(adapters) → SUPABASE → EDGE → FRONTEND`.

## Hard cost policy (non-negotiable)

- **Free-tier + user-provisioned keys only.** No paid or metered tier, ever.
- Every source must **degrade gracefully with NO key** and document its free-tier
  limits inline (in the adapter module) and in the table below.
- Secrets are **never** committed. They are staged as *commented* placeholders in
  `frontend/.env.local.example` and read at runtime from `pipeline/.env`
  (server/pipeline) or `.env.local` (frontend). See "Env vars" below.

## The adapter shape

One free source = **one module** in `pipeline/adapters/` exposing **one** `Adapter`
subclass (`pipeline/adapters/base.py`). No registry: `discover()` globs the package
(`pkgutil.iter_modules`), so **adding a source is adding a file** — never a central
edit.

```
fetch  → normalize → persist
(net)     (pure)      (idempotent upsert; dry-runs w/o Supabase)
             └──────── wrapped by run(), which enforces the degrade contract
```

Class attributes you set:

| attr           | meaning                                                        |
|----------------|----------------------------------------------------------------|
| `name`         | short id (logs + `run_all()` keys)                             |
| `table`        | Supabase table to upsert into                                  |
| `on_conflict`  | column(s) that make the upsert idempotent                     |
| `requires_key` | env var name the source needs, or `None` if **keyless**       |
| `free_tier`    | one-line documented free-tier limit (inline provenance)       |

Methods:

- `fetch()` — the **only** networked step. Wrap the request in `@common.retry_api`
  (shared 3-attempt exp-backoff). Only ever called when `enabled`.
- `normalize(raw)` — **pure**, I/O-free: raw payload → list of rows for `table`.
  Unit-testable on a fixture with no network. Empty/malformed → `[]`.
- `persist(rows)` — defaults to `common.upsert(table, rows, on_conflict=…)`.
  Override only for non-upsert targets.
- `run()` — `fetch → normalize → persist` with the degrade contract; returns the
  normalized rows (`[]` when disabled).

## The degrade contract (the tested default)

`run()` guarantees, with **no key** and/or **no Supabase**:

1. `requires_key` set but the env var **absent** → `run()` returns `[]` and
   **never fetches or writes**. A missing key is **not** an error.
2. Keyless sources still degrade: `persist()` → `common.upsert`, which **dry-runs**
   (logs, writes nothing, returns 0) when Supabase is unconfigured.
3. Therefore re-running any adapter with no backend writes **no partial rows** and
   **never raises** — idempotent by construction.

This is exactly what `pipeline/tests/test_adapters.py` exercises: every case runs
with no keys and no Supabase, fixtures stand in for the network.

## Adding a source (recipe)

1. Create `pipeline/adapters/<source>.py` with one `Adapter` subclass.
2. Set the class attrs; if it needs a key, set `requires_key="YOUR_ENV_VAR"` and
   add that var as a **commented** placeholder in `frontend/.env.local.example`
   (name + one-line purpose, empty value) — never a real value.
3. Implement `fetch` (networked, `@retry_api`) and `normalize` (pure).
4. Add a row to the table below with the free-tier limit; document limits inline.
5. Add/extend a test that normalizes a fixture and asserts the degrade path.

No wiring, no registry edit — `discover()` / `run_all()` pick it up automatically.

## Sources & free-tier limits

| source          | module                         | key (env var)                 | free-tier limit                                                  | owner (unit) |
|-----------------|--------------------------------|-------------------------------|-----------------------------------------------------------------|--------------|
| Sleeper (state) | `adapters/sleeper_state.py`    | none                          | no key; ~1000 req/min courtesy cap, cache responses             | F2 (reference) |
| Odds            | `adapters/odds.py`             | `ODDS_API_KEY`                | the-odds-api free tier ~500 req/mo; user-provisioned; no popularity field | E5           |
| Injuries        | *(pending)*                    | `INJURY_API_KEY` (optional)   | ESPN/Sleeper injury JSON is keyless; key only if a source needs it | E3        |
| College stats   | *(pending)*                    | `CFBD_API_KEY`                | collegefootballdata.com free tier; free user key, rate-limited  | E2           |

*Pending* rows are the placeholders staged by F2; the owning unit adds the adapter
module using this pattern (F2 does not implement source-specific adapters).
