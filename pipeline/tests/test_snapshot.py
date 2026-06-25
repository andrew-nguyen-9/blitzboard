"""
Unit tests for the player-snapshot publisher (v2.3.1 / DATA_TRANSFER.md).

The publisher's pure core — payload shaping, compact encode, gzip compress,
content-hashing, manifest — is tested offline (no DB, no network). The 60KB
wire-format budget (v2.3.1.3) is asserted against a synthetic FULL universe so
the format choice is validated empirically, not assumed.

No pytest in the pipeline venv — plain asserts, runnable two ways:
    python tests/test_snapshot.py
    python -m pytest tests/test_snapshot.py
"""
from __future__ import annotations

import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import publish_snapshot as ps  # noqa: E402


def _row(sid, name, pos, tm, rank):
    """A value-engine row as the publisher receives it (post-join)."""
    return {
        "sleeper_id": sid, "full_name": name, "position": pos, "nfl_team": tm,
        "value": 120.5 - rank * 0.1, "vor": 88.3 - rank * 0.1, "rank": rank,
        "tier": 1 + rank // 12, "boom": 140.0, "bust": 30.0,
        "predictability": 0.73, "trend": 0,
    }


def _universe(n: int) -> list[dict]:
    """A realistic synthetic universe: 4–7 digit sleeper ids, real-length names."""
    rnd = random.Random(42)
    first = ["Patrick", "Christian", "Justin", "Tyreek", "Josh", "Bijan", "Amon-Ra", "Ja'Marr"]
    last = ["Mahomes", "McCaffrey", "Jefferson", "Hill", "Allen", "Robinson", "Chase", "Brown"]
    pos = ["QB", "RB", "WR", "TE", "K", "DST"]
    teams = ["KC", "SF", "MIN", "MIA", "BUF", "ATL", "CIN", "DAL", "PHI", "LAR"]
    rows = []
    for i in range(n):
        sid = str(rnd.randint(1000, 9999999))
        nm = f"{rnd.choice(first)} {rnd.choice(last)}"
        rows.append(_row(sid, nm, rnd.choice(pos), rnd.choice(teams), i + 1))
    return rows


def test_payload_is_columnar_and_roundtrips():
    """Columnar layout: one array per column (better gzip than row-arrays), and
    boom/bust are NOT shipped (the list never uses them — the lazy card does)."""
    rows = [_row("4046", "Patrick Mahomes", "QB", "KC", 1),
            _row("6794", "Bijan Robinson", "RB", "ATL", 2)]
    payload = ps.build_payload(rows, profile="default", engine="vorp")
    assert payload["cols"][0] == "sid"
    assert "data" in payload and "rows" not in payload          # columnar, not row-arrays
    assert len(payload["data"]) == len(payload["cols"])         # one array per column
    assert "boom" not in payload["cols"] and "bust" not in payload["cols"]
    assert payload["count"] == 2
    decoded = ps.decode_payload(payload)
    assert decoded[0]["sid"] == "4046"
    assert decoded[0]["n"] == "Patrick Mahomes"
    assert decoded[1]["pos"] == "RB"
    assert decoded[0]["rnk"] == 1
    print("✓ payload is columnar (no boom/bust) and round-trips through build → decode")


def test_floats_are_rounded_for_the_wire():
    """val/vor round to 1dp, rho/trend to 2dp — ~9KB off the full universe."""
    row = {"sleeper_id": "4046", "full_name": "P M", "position": "QB", "nfl_team": "KC",
           "value": 199.6789, "vor": 141.1349, "rank": 1, "predictability": 0.7156, "trend": 0.3742}
    [r] = ps.decode_payload(ps.build_payload([row], "default", "vorp"))
    assert r["val"] == 199.7 and r["vor"] == 141.1   # 1dp
    assert r["rho"] == 0.72 and r["trend"] == 0.37    # 2dp
    print("✓ wire floats rounded (val/vor 1dp, rho/trend 2dp)")


def test_compress_decompress_roundtrip():
    """gzip(raw) decompresses back to the exact encoded bytes (client decodes
    with DecompressionStream('gzip') — natively supported, no JS dep)."""
    payload = ps.build_payload(_universe(50), profile="default", engine="vorp")
    raw = ps.encode(payload)
    comp = ps.compress(raw)
    assert ps.decompress(comp) == raw
    assert len(comp) < len(raw)  # a non-trivial payload should shrink
    print(f"✓ gzip round-trips ({len(raw)}B → {len(comp)}B)")


def test_content_hash_idempotent_and_sensitive():
    """Same bytes → same name (idempotent re-run); changed data → new hash/URL."""
    a = ps.compress(ps.encode(ps.build_payload([_row("4046", "P M", "QB", "KC", 1)], "default", "vorp")))
    b = ps.compress(ps.encode(ps.build_payload([_row("4046", "P M", "QB", "KC", 1)], "default", "vorp")))
    c = ps.compress(ps.encode(ps.build_payload([_row("4046", "P M", "QB", "KC", 2)], "default", "vorp")))
    assert ps.content_hash(a) == ps.content_hash(b)
    assert ps.content_hash(a) != ps.content_hash(c)
    name = ps.snapshot_name("default", "vorp", ps.content_hash(a))
    assert name.startswith("players-default-vorp-") and name.endswith(".json.gz")
    print(f"✓ content hash idempotent + sensitive ({name})")


def test_full_universe_under_60kb():
    """v2.3.1.3 budget: the full universe core payload ≤ 60KB after brotli."""
    rows = _universe(2800)
    comp = ps.compress(ps.encode(ps.build_payload(rows, "default", "vorp")))
    kb = len(comp) / 1024
    assert kb <= 60, f"snapshot {kb:.1f}KB exceeds the 60KB budget for {len(rows)} players"
    print(f"✓ full universe ({len(rows)} players) = {kb:.1f}KB ≤ 60KB after gzip")


def test_manifest_entry_shape():
    """Manifest maps profile+engine → url + hash + count (client resolves current)."""
    comp = ps.compress(ps.encode(ps.build_payload([_row("4046", "P M", "QB", "KC", 1)], "default", "vorp")))
    digest = ps.content_hash(comp)
    entry = ps.manifest_entry("default", "vorp", digest, count=1, base_url="https://cdn.example/snap")
    assert entry["hash"] == digest
    assert entry["count"] == 1
    assert entry["url"].endswith(ps.snapshot_name("default", "vorp", digest))
    print("✓ manifest entry shape (url/hash/count)")


def main():
    test_payload_is_columnar_and_roundtrips()
    test_floats_are_rounded_for_the_wire()
    test_compress_decompress_roundtrip()
    test_content_hash_idempotent_and_sensitive()
    test_full_universe_under_60kb()
    test_manifest_entry_shape()
    print("\nALL SNAPSHOT TESTS PASSED ✅")


if __name__ == "__main__":
    main()
