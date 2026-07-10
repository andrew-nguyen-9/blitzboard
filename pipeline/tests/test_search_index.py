"""Unit tests for the sitewide search index builder (Epic 9a).

Covers the two claims that matter: (1) the Bloom filter the pipeline WRITES is
byte-for-byte the one the TS reader (frontend/lib/search.ts) EXPECTS — the golden
vector below is asserted verbatim in frontend/lib/search.test.ts; (2) build() is
degrade-safe + idempotent (no Supabase → empty sources → deterministic shape).

Plain asserts (no pytest in the venv):  python tests/test_search_index.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import search_index as si  # noqa: E402


def test_normalize_and_trigrams():
    assert si.normalize("  Jalen   HURTS! ") == "jalen hurts"
    assert si.normalize(None) == ""
    assert sorted(si.trigrams("jalen")) == ["ale", "jal", "len"]
    assert si.trigrams("jo") == set()  # <3 chars → no trigrams
    print("✓ normalize + trigrams")


def test_bloom_golden_parity():
    """LOCKS cross-language parity with frontend/lib/search.test.ts GOLDEN."""
    grams = set()
    for c in ["Jalen Hurts", "Dallas Cowboys", "Patrick Mahomes"]:
        grams |= si.trigrams(c)
    b = si.build_bloom(grams)
    assert (b["m"], b["k"], b["n"]) == (328, 7, 34), (b["m"], b["k"], b["n"])
    assert b["bits"] == "lZ8P7l/n3/50mUVIwrHZ7IdZEDMnAhrOomx6mG3Za5X5MhltsxXzDjE=", b["bits"]

    # No false negatives: every inserted gram must test present.
    import base64
    raw = base64.b64decode(b["bits"])
    def has(g):
        return all(raw[p >> 3] & (1 << (p & 7)) for p in si._positions(g, b["m"], b["k"]))
    assert all(has(g) for g in grams)
    assert not has("zzz")  # absent term the fixture skips (asserted in TS too)
    print("✓ bloom golden parity + no false negatives")


def test_bloom_empty_corpus():
    b = si.build_bloom(set())
    assert b["n"] == 0 and b["m"] == 8 and b["k"] == 1
    print("✓ empty-corpus bloom is well-formed")


def test_team_rows_static():
    rows = si.team_rows()
    assert len(rows) == 32
    dal = next(r for r in rows if r["entity_id"] == "DAL")
    assert dal["entity_type"] == "team"
    assert "dallas cowboys" in dal["search_text"]
    assert dal["url"] == "/players?team=DAL"
    assert dal["weight"] == si.WEIGHTS["team"]
    print("✓ 32 static team rows, well-formed")


def test_build_degrades_offline():
    """No Supabase env → player/news/article sources are empty; build() still
    yields the static team rows + a deterministic bloom, and is idempotent."""
    for k in ("NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        os.environ.pop(k, None)
    rows1, bloom1 = si.build()
    rows2, bloom2 = si.build()
    assert [r["entity_id"] for r in rows1] == [r["entity_id"] for r in rows2]  # idempotent
    assert bloom1 == bloom2
    assert all(r["entity_type"] == "team" for r in rows1)  # only static source offline
    assert len(rows1) == 32
    print("✓ offline degrade + idempotent build")


if __name__ == "__main__":
    test_normalize_and_trigrams()
    test_bloom_golden_parity()
    test_bloom_empty_corpus()
    test_team_rows_static()
    test_build_degrades_offline()
    print("\nall search_index tests passed")
