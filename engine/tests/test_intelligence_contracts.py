from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from blitz_engine.intelligence.cache import ResponseCache
from blitz_engine.intelligence.contracts import SignalCard, audit_registry, load_registry

REGISTRY = Path(__file__).parents[2] / "fixtures" / "intelligence_signals.json"


def test_registry_is_complete_machine_checkable_and_within_storage_budget() -> None:
    cards = load_registry(REGISTRY)
    audit = audit_registry(cards)
    assert audit.total >= 12
    assert {"availability", "opportunity", "environment", "market", "personal_context"} <= set(
        audit.families
    )
    assert "gameday_inactives" in audit.blocked
    assert "private_or_speculative_personal_data" in audit.excluded
    assert audit.estimated_storage_mb <= 10_000
    assert 0 < audit.coverage_rate < 1


def test_sensitive_signal_cannot_receive_model_weight() -> None:
    payload = json.loads(REGISTRY.read_text())["signals"][-2]
    payload["model_eligibility"] = "eligible"
    with pytest.raises(ValueError, match="sensitive signals"):
        SignalCard.from_dict(payload)


def test_implemented_signal_requires_source_and_test() -> None:
    payload = json.loads(REGISTRY.read_text())["signals"][0]
    payload["tests"] = []
    with pytest.raises(ValueError, match="source and tests"):
        SignalCard.from_dict(payload)


def test_cache_deduplicates_bytes_and_replays_exactly(tmp_path) -> None:
    cache = ResponseCache(tmp_path, source_budgets={"nflverse": 3})
    now = datetime(2026, 8, 25, 12, tzinfo=UTC)
    first = cache.put("nflverse", b"same response" * 100, fetched_at=now, etag='"abc"')
    second = cache.put("nflverse", b"same response" * 100, fetched_at=now)
    assert first.sha256 == second.sha256
    assert len(list((tmp_path / "objects").glob("*/*.gz"))) == 1
    assert cache.get(first.sha256) == b"same response" * 100
    assert first.compressed_length < first.byte_length
    assert len((tmp_path / "ledger.jsonl").read_text().splitlines()) == 2


def test_cache_budget_fails_before_write(tmp_path) -> None:
    cache = ResponseCache(tmp_path, source_budgets={"source": 1})
    now = datetime(2026, 8, 25, tzinfo=UTC)
    cache.put("source", b"one", fetched_at=now)
    with pytest.raises(RuntimeError, match="budget exhausted"):
        cache.put("source", b"two", fetched_at=now)
    assert len(list((tmp_path / "objects").glob("*/*.gz"))) == 1


def test_cache_detects_corruption(tmp_path) -> None:
    cache = ResponseCache(tmp_path)
    entry = cache.put("source", b"valid", fetched_at=datetime(2026, 8, 25, tzinfo=UTC))
    target = next((tmp_path / "objects").glob("*/*.gz"))
    target.write_bytes(gzip.compress(b"tampered", mtime=0))
    with pytest.raises(ValueError, match="cache corruption"):
        cache.get(entry.sha256)


def test_cache_rolling_retention_preserves_shared_bytes(tmp_path) -> None:
    cache = ResponseCache(tmp_path)
    old = datetime(2025, 8, 25, tzinfo=UTC)
    cutoff = datetime(2026, 1, 1, tzinfo=UTC)
    current = datetime(2026, 8, 25, tzinfo=UTC)
    shared = cache.put("source", b"shared", fetched_at=old)
    cache.put("source", b"old-only", fetched_at=old)
    cache.put("source", b"shared", fetched_at=current)

    assert cache.prune_before(cutoff) == (2, 1)
    assert cache.get(shared.sha256) == b"shared"
    entries = [json.loads(line) for line in cache.ledger.read_text().splitlines()]
    assert len(entries) == 1
    assert entries[0]["fetched_at"].startswith("2026-08-25")


def test_cache_retention_rejects_naive_cutoff(tmp_path) -> None:
    cache = ResponseCache(tmp_path)
    with pytest.raises(ValueError, match="timezone-aware"):
        cache.prune_before(datetime(2026, 1, 1))
