"""
publish_snapshot.py — v2.3.1 player-snapshot publisher (DATA_TRANSFER.md).

The value layer changes once per day, is identical for every anonymous user of a
scoring profile, and is read-only on the frontend — the textbook profile for a
precomputed, CDN-cached, immutable snapshot. After value_engine_run.py, this
emits per (scoring_profile × engine):

  • players-<profile>-<engine>-<hash>.json.gz — the compact core list, gzip-
    compressed, content-hashed → effectively immutable (the URL changes only when
    the bytes do; served Cache-Control: max-age=1y). gzip (not brotli) because the
    client decodes it natively with DecompressionStream('gzip') — no JS dep, and
    no reliance on the CDN persisting a Content-Encoding header (Supabase Storage
    does not). Stored as octet-stream so the edge never re-compresses it.
  • manifest.json (short TTL) — maps profile+engine → current url+hash+count.

The pure core (build/encode/compress/hash/manifest) is import-clean and unit-
tested offline; the Storage upload is null-safe (dry-run when Supabase is
unconfigured), mirroring common.upsert. Re-running is idempotent: identical data
hashes to the same object name, so the upload is a no-op overwrite.

Usage:
    python publish_snapshot.py                       # vorp
    python publish_snapshot.py --engines vorp monte_carlo
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json

from common import console, get_supabase, fetch_all

# Compact wire format (DATA_TRANSFER.md §2): array-of-arrays keyed by a short
# column header — kills per-row JSON key repetition. `sid` (Sleeper id) is the
# row id: compact + stable, where UUIDs are high-entropy and blow the budget.
# Tiers are intentionally NOT shipped — the client derives them from rank (single
# source of truth in lib/tiers.ts), so there's no cross-language tier drift.
COLS = ["sid", "n", "pos", "tm", "val", "vor", "rnk", "boom", "bust", "rho", "trend"]
WIRE_VERSION = 1
BUCKET = "snapshots"
MANIFEST_NAME = "manifest.json"
# Cache-control is the max-age in SECONDS (storage3 emits `max-age=<value>` and
# persists it as the object's cacheControl). Content-hashed names make snapshots
# effectively immutable for a year; the manifest is short-lived so new data shows.
IMMUTABLE_CACHE = "31536000"  # 1 year
MANIFEST_CACHE = "60"

# wire column → source-row key (post-join shape from load_value_rows)
_SRC = {
    "sid": "sleeper_id", "n": "full_name", "pos": "position", "tm": "nfl_team",
    "val": "value", "vor": "vor", "rnk": "rank",
    "boom": "boom", "bust": "bust", "rho": "predictability", "trend": "trend",
}


def _num(x):
    """Keep the wire small: round floats to 2dp; ints/None pass through."""
    return round(x, 2) if isinstance(x, float) else x


def build_payload(rows: list[dict], profile: str, engine: str) -> dict:
    out = [[_num(r.get(_SRC[c])) for c in COLS] for r in rows]
    return {"v": WIRE_VERSION, "profile": profile, "engine": engine,
            "cols": COLS, "count": len(out), "rows": out}


def decode_payload(payload: dict) -> list[dict]:
    """Inverse of build_payload — rows back to dicts (parity check for tests)."""
    cols = payload["cols"]
    return [dict(zip(cols, row)) for row in payload["rows"]]


def encode(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compress(raw: bytes) -> bytes:
    # mtime=0 → deterministic bytes (so identical data hashes identically).
    return gzip.compress(raw, compresslevel=9, mtime=0)


def decompress(comp: bytes) -> bytes:
    return gzip.decompress(comp)


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def snapshot_name(profile: str, engine: str, digest: str) -> str:
    return f"players-{profile}-{engine}-{digest}.json.gz"


def manifest_entry(profile: str, engine: str, digest: str, count: int, base_url: str) -> dict:
    return {"profile": profile, "engine": engine, "hash": digest, "count": count,
            "url": f"{base_url.rstrip('/')}/{snapshot_name(profile, engine, digest)}"}


def load_value_rows(engine: str) -> list[dict]:
    """player_value (for `engine`) joined with the columns the list needs, plus
    trend_score from the trending table. Paginates past the 1000-row cap."""
    rows = fetch_all(
        "player_value",
        "rank,value,vor,boom,bust,predictability,player_id,"
        "players!inner(sleeper_id,full_name,position,nfl_team)",
        apply=lambda q: q.eq("engine", engine).order("rank"),
    )
    trend = {t["player_id"]: t.get("trend_score") or 0
             for t in fetch_all("trending", "player_id,trend_score")}
    out: list[dict] = []
    for r in rows:
        p = r.get("players") or {}
        if not p.get("sleeper_id"):
            continue  # no compact id → not addressable on the client
        out.append({
            "sleeper_id": p["sleeper_id"], "full_name": p.get("full_name"),
            "position": p.get("position"), "nfl_team": p.get("nfl_team"),
            "value": r.get("value"), "vor": r.get("vor"), "rank": r.get("rank"),
            "boom": r.get("boom"), "bust": r.get("bust"),
            "predictability": r.get("predictability"),
            "trend": trend.get(r["player_id"], 0),
        })
    return out


def _upload(sb, path: str, data: bytes, *, content_type: str, cache: str) -> None:
    """Idempotent upsert to Storage. cache = max-age in seconds (storage3 wraps it
    as `max-age=<n>` and persists it as the object's cacheControl)."""
    sb.storage.from_(BUCKET).upload(
        path=path, file=data,
        file_options={"content-type": content_type, "cache-control": cache, "upsert": "true"},
    )


def publish(profile: str = "default", engines: tuple[str, ...] = ("vorp",)) -> dict:
    """Build + upload a snapshot per engine; write the manifest. Returns the
    manifest dict (also returned in dry mode so the shape is testable end-to-end)."""
    sb = get_supabase()
    base_url = ""
    if sb is not None:
        base_url = sb.storage.from_(BUCKET).get_public_url("").rstrip("/")

    snapshots: dict[str, dict] = {}
    for engine in engines:
        rows = load_value_rows(engine) if sb is not None else []
        payload = build_payload(rows, profile, engine)
        comp = compress(encode(payload))
        digest = content_hash(comp)
        name = snapshot_name(profile, engine, digest)
        kb = len(comp) / 1024
        if kb > 60:
            console.print(f"[yellow]⚠ {name} is {kb:.1f}KB (> 60KB budget)[/yellow]")
        if sb is None:
            console.print(f"[dim]dry-run: would upload {name} ({kb:.1f}KB, {payload['count']} players)[/dim]")
        else:
            _upload(sb, name, comp, content_type="application/octet-stream", cache=IMMUTABLE_CACHE)
            console.print(f"[green]✓ {name} ({kb:.1f}KB, {payload['count']} players)[/green]")
        snapshots[f"{profile}:{engine}"] = manifest_entry(
            profile, engine, digest, payload["count"], base_url)

    manifest = {"v": WIRE_VERSION, "snapshots": snapshots}
    if sb is None:
        console.print(f"[dim]dry-run: would upload {MANIFEST_NAME}[/dim]")
    else:
        _upload(sb, MANIFEST_NAME, json.dumps(manifest).encode("utf-8"),
                content_type="application/json", cache=MANIFEST_CACHE)
        console.print(f"[green]✓ {MANIFEST_NAME} ({len(snapshots)} entries)[/green]")
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description="Publish CDN player snapshots + manifest.")
    ap.add_argument("--profile", default="default")
    ap.add_argument("--engines", nargs="+", default=["vorp"], choices=["vorp", "monte_carlo"])
    args = ap.parse_args()
    publish(args.profile, tuple(args.engines))


if __name__ == "__main__":
    main()
