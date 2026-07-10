"""E6 — news auto-refresh: the stale-fallback degrade path is the tested default.

Everything here runs with NO keys, NO Supabase and NO network: sources are plain
callables (a healthy one, and simulated "down" ones that raise or return nothing),
so what gets exercised is the E6 contract — a down source degrades to its last-good
cached batch (or is skipped), and `collect()` NEVER raises. Also asserts the keyless
Reddit `.rss` coverage and cache round-trip idempotence.

    cd pipeline && python -m pytest tests/test_news_sentiment.py    # (or: python tests/test_news_sentiment.py)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import news_sentiment as ns  # noqa: E402

_ART = {"source": "X", "url": "https://x/1", "title": "t", "body": "b", "published_at": None}


def _src(name, fetch):
    return ns.NewsSource(name, fetch)


def test_normalize_entry_is_pure_on_fixture():
    entry = {"link": "https://e/1", "title": "Star RB questionable",
             "summary": "hamstring", "published_parsed": (2026, 7, 9, 12, 0, 0, 0, 0, 0)}
    row = ns._normalize_entry("ESPN NFL", entry)
    assert row["source"] == "ESPN NFL"
    assert row["url"] == "https://e/1"
    assert row["body"] == "hamstring"
    assert row["published_at"].startswith("2026-07-09")
    # summary missing → falls back to title, and no timestamp → None (still valid)
    bare = ns._normalize_entry("PFT", {"link": "https://e/2", "title": "only title"})
    assert bare["body"] == "only title" and bare["published_at"] is None


def test_healthy_source_populates_cache():
    cache = {}
    out = ns.collect([_src("live", lambda: [_ART])], cache)
    assert out == [_ART]
    assert cache["live"] == [_ART]  # fresh pull recorded as last-good


def test_down_source_that_raises_uses_stale_cache():
    def boom():
        raise RuntimeError("feed 503")
    cache = {"flaky": [_ART]}                      # a previous good batch
    out = ns.collect([_src("flaky", boom)], cache)
    assert out == [_ART]                            # degraded to last-good, no raise
    assert cache["flaky"] == [_ART]                 # cache untouched by the failure


def test_empty_source_falls_back_to_stale():
    cache = {"quiet": [_ART]}
    out = ns.collect([_src("quiet", lambda: [])], cache)
    assert out == [_ART]                            # empty pull → reuse last-good


def test_down_source_with_no_cache_is_skipped_not_fatal():
    def boom():
        raise ValueError("dns fail")
    cache = {}
    out = ns.collect([_src("cold", boom)], cache)   # no prior good batch
    assert out == []                                # skipped, run survives
    assert "cold" not in cache


def test_collect_never_fails_the_run_when_all_sources_down():
    def boom():
        raise RuntimeError("everything is on fire")
    out = ns.collect([_src("a", boom), _src("b", lambda: [])], {})
    assert out == []                                # run completes, zero articles


def test_build_sources_keyless_reddit_praw_degrades_to_empty(monkeypatch):
    # No creds → the optional praw source must yield [] (keyless .rss covers Reddit).
    for k in ("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"):
        monkeypatch.delenv(k, raising=False)
    srcs = ns.build_sources(max_articles=50, use_reddit=True)
    praw_src = [s for s in srcs if "praw" in s.name][0]
    assert praw_src.fetch() == []                   # degrade, not error
    # keyless Reddit .rss is a first-class source in the list
    assert any("reddit.com" in u for _, u in ns.FEEDS)
    assert any(s.name == "r/fantasyfootball" for s in srcs)
    # --no-reddit drops only the keyed praw source, keeps RSS (incl. Reddit .rss)
    assert not any("praw" in s.name for s in ns.build_sources(50, use_reddit=False))


def test_cache_roundtrip_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(ns, "STALE_CACHE", str(tmp_path / ".news_cache.json"))
    assert ns._load_cache() == {}                   # missing file → empty, no raise
    ns._save_cache({"live": [_ART]})
    ns._save_cache({"live": [_ART]})                # re-save = same content
    assert ns._load_cache() == {"live": [_ART]}


if __name__ == "__main__":  # plain-assert fallback (mirrors repo convention)
    import types
    _mp = types.SimpleNamespace(delenv=lambda *a, **k: os.environ.pop(a[0], None),
                                setattr=setattr)
    test_normalize_entry_is_pure_on_fixture()
    test_healthy_source_populates_cache()
    test_down_source_that_raises_uses_stale_cache()
    test_empty_source_falls_back_to_stale()
    test_down_source_with_no_cache_is_skipped_not_fatal()
    test_collect_never_fails_the_run_when_all_sources_down()
    print("news_sentiment E6 stale-fallback: OK")
