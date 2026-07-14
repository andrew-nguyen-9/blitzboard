# Free storage / free-compute survey — v4 engine (research deliverable)

A committed research doc (Q37, E0-survey). It surveys **free-tier-only** options for
the two v4 infra needs the engine actually has, and lands on one recommendation.
Repo policy (`docs/design/v4-engine-architecture.md` §"Free storage / free-compute survey"
and §"M1 / 16 GB budget"): **free-tier only, no metered compute/storage.** Heavy compute is
free because it runs **local (M1 / 16 GB)**; storage = local Parquet + DuckDB for
raw / history / samples, with only a **compact snapshot** leaving the box.

The two needs, stated precisely:

- **(a) Snapshot / CDN storage** — the versioned snapshot bundle
  (`{values, quantiles, corr_matrix, mc_probs, strategy_tree, policy}`, per §"Snapshot =
  the hand-off contract") is small and read-often. Raw posterior draws **stay local**;
  only quantiles + correlation ship. This is the surface that wants a real cloud object
  store (and the one place we deliberately gain **cloud-storage experience**).
- **(b) Optional cloud-burst compute** — the escape hatch for a job that won't fit 16 GB
  (§"M1 / 16 GB budget"). **Opt-in only, never the default path**; the CLI always has a
  smaller-scale local variant.

> Free-tier numbers **drift** — every limit below is cited to a source URL. Re-verify at
> the top of any phase that leans on one.

## Scope resolution (user blocker "Confirm free storage / free-compute survey scope")

The user confirmed: evaluate **free cloud options** (R2 / Colab / Kaggle / Oracle-free /
HF Spaces), **not local-only**, and explicitly wants to **gain free cloud-storage
experience** — so the recommendation is weighted toward a concrete free **cloud-storage**
choice with a migration path, over a local-only default. Compute still stays local by
policy; cloud-burst remains opt-in. This doc honors that: it names a cloud store to adopt
now, and treats local-only as the fallback, not the default.

## (a) Snapshot / CDN storage options

| Option | Free-tier limits (cited) | Fit to compact-snapshot model | Egress / metering traps | Verdict |
|--------|--------------------------|-------------------------------|-------------------------|---------|
| **Cloudflare R2** | 10 GB-month storage, 1 M Class A (write) ops/mo, 10 M Class B (read) ops/mo, **egress = Free** [1] | Ideal: S3-compatible object store; snapshot bundle is ≪ 10 GB; reads are free and CDN-frontable | **Zero egress fee** is the whole point — no download meter. Only trap: Class A writes metered past 1 M/mo (snapshot cadence is far under that) | **Recommend** |
| **Supabase Storage** (already in stack) | Free plan: 500 MB DB, **1 GB file storage**, 5 GB egress/mo, **project paused after 1 week inactivity**, 2 active projects [2] | OK for tiny snapshot metadata / pointers, which it already serves | 5 GB egress cap and the **1-week auto-pause** are real availability traps for an intermittently-publishing cron | **Fallback / keep for relational** |
| **Oracle Object Storage** (Always Free) | 20 GB object storage (Always-Free accts), 50 k API req/mo, **10 TB egress/mo** [3] | Works as an S3-ish store, but its native API is clunkier than R2's; overkill for a compact bundle | Credit card required at signup; egress metered beyond 10 TB (irrelevant at our size); Always-Free resources reclaimed if idle | **Fallback** |
| **HF Spaces storage** | Free CPU-Basic Space: 2 vCPU, 16 GB RAM, **50 GB ephemeral (non-persistent) disk**; persistent storage is **paid $5–100/mo** [4] | Poor: ephemeral disk is wiped on restart; persistence costs money → violates no-metered-storage | Persistent tier is a paid meter; ephemeral tier loses data on restart | **Avoid (as a store)** |
| **Colab / Kaggle storage** | Both give only **ephemeral session disk** (Kaggle 20 GB/session; Colab scratch) that is wiped when the session ends [5][6] | Not a store — compute scratch only | Data does not survive the session; no durable object store | **Avoid (as a store)** |
| **Local-only** (Parquet + DuckDB) | No cloud limits; bounded by the M1 SSD | Correct home for **raw / history / posterior draws** (already the design) | None — but it is not reachable by the frontend/CDN, so it can't be the *published* snapshot store | **Keep for raw; not for published snapshot** |

## (b) Optional cloud-burst compute options

Policy: default is **local (M1 / 16 GB, JAX-CPU, chunked/streamed)**. These are the opt-in
escape hatch only, ranked by "free, no card, real accelerator."

| Option | Free-tier limits (cited) | Fit to opt-in cloud-burst | Egress / metering traps | Verdict |
|--------|--------------------------|---------------------------|-------------------------|---------|
| **Kaggle Notebooks** | **30 GPU-hrs/week**, 12-hr max session, **T4×2 = 32 GB VRAM** (or P100 16 GB), 20 GB session disk; no credit card [6] | Best free burst: most VRAM, generous weekly quota, no card | Storage ephemeral (pull inputs / push outputs each run); quota is hard-capped weekly | **Recommend (primary burst)** |
| **Google Colab (free)** | ~12–13 GB RAM, T4 16 GB VRAM, up to 12-hr session, ~90-min idle timeout, **dynamic ~15–30 GPU-hrs/week**, ephemeral disk [5] | Good fallback; familiar notebook flow | GPU access **not guaranteed** at peak; idle disconnect; dynamic (can drop to none) | **Fallback** |
| **Oracle Ampere A1** (Always Free) | **2 OCPU + 12 GB RAM** Arm (always-on), 200 GB block, 10 TB egress/mo [3] | Only always-on free box, but Arm + 12 GB < local 16 GB and **no GPU** → rarely beats local | Card required; A1 capacity errors common; idle reclamation | **Avoid for burst (no headroom over local)** |
| **HF Spaces (free)** | 2 vCPU, 16 GB RAM, no free GPU (GPU tiers paid) [4] | Not a burst target — it's an app-hosting tier | Free tier has no accelerator; GPU is metered | **Avoid for burst** |
| **Local-only** (M1 / 16 GB) | 16 GB unified, JAX-CPU, no GPU assumption | The default path for every job that fits | None | **Default** |

## Recommendation

**Storage:** Adopt **Cloudflare R2** as the published snapshot / CDN object store. The
decisive property is **zero egress fees** [1] — a read-often snapshot behind a CDN never
accrues a bandwidth meter, which is exactly the trap Supabase's 5 GB egress cap and the
paid HF persistent tier represent. R2 is **S3-compatible**, so the migration path is a
one-liner: write the same bundle to a local dir today, to R2 via any S3 client tomorrow,
to any S3 store ever after — no lock-in. This is also the concrete cloud-storage skill the
user asked to gain. Keep **Supabase** for the relational/live tier it already serves
(snapshot metadata, live deltas) and keep **raw history + posterior draws local** in
Parquet + DuckDB (they never need to leave the box). Local-only is the *fallback* if R2
setup slips, not the default.

**Compute:** Unchanged from policy — **local M1 / 16 GB is the default**; every engine job
ships a chunked/streamed local variant. **Cloud-burst is opt-in only**, wired through
`config.py` (§"M1 / 16 GB budget"): **Kaggle** primary (32 GB VRAM, 30 hr/wk, no card [6]),
**Colab** fallback [5]. No always-metered compute is ever the default.

### Cloud-burst opt-in path (the escape hatch, concretely)

1. Default: `blitz_engine` CLI runs the job locally, streamed/chunked, JAX-CPU.
2. If a job is flagged too large (config threshold), the CLI emits a **self-contained
   notebook + input Parquet manifest** instead of running.
3. User opts in: upload to **Kaggle** (or Colab), run, download the result artifact.
4. Result re-enters the local store and the normal snapshot → R2 publish flow. Cloud-burst
   touches **compute only**; it is never a store (both are ephemeral [5][6]).

### Metering-trap flags (for E0 / E3 wiring)

- **HF Spaces persistent storage** — paid $5–100/mo [4]; ephemeral tier wipes on restart.
  **Do not** use as a store.
- **Supabase** — 5 GB egress/mo + **1-week inactivity auto-pause** [2]; fine as relational
  side-tier, wrong as the primary CDN snapshot store.
- **Colab / Kaggle disk** — ephemeral [5][6]; treat as compute scratch, never durable state.
- **Oracle** — card at signup + Always-Free idle reclamation + A1 capacity errors [3].
- **R2** — the safe one; only Class A *writes* meter past 1 M/mo [1], far above snapshot cadence.

## Sources

- [1] Cloudflare R2 pricing (10 GB free, 1 M Class A / 10 M Class B ops, egress Free):
  https://developers.cloudflare.com/r2/pricing/
- [2] Supabase pricing — Free plan (500 MB DB, 1 GB storage, 5 GB egress, 1-week pause):
  https://supabase.com/pricing
- [3] Oracle Cloud Always Free resources (A1 2 OCPU/12 GB, 200 GB block, 20 GB object, 10 TB egress):
  https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- [4] Hugging Face Spaces overview (free CPU-Basic 2 vCPU/16 GB/50 GB ephemeral; persistent paid):
  https://huggingface.co/docs/hub/en/spaces-overview
- [5] Google Colab FAQ (free T4, ~12 GB RAM, 12-hr session, dynamic GPU quota, ephemeral):
  https://research.google.com/colaboratory/faq.html
- [6] Kaggle Notebooks docs (30 GPU-hrs/wk, 12-hr session, T4×2 32 GB VRAM, 20 GB ephemeral disk):
  https://www.kaggle.com/docs/notebooks
