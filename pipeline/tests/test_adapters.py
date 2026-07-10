"""F2 — the external-data adapter framework, with the DEGRADE path as the default.

Everything here runs with NO keys and NO Supabase, so the graceful-degrade
contract (no key / no backend → empty, no writes, no error, idempotent) is what
gets exercised. No network is touched: `fetch` is either skipped (degrade) or
monkeypatched to a fixture.

    cd pipeline && python -m pytest tests/test_adapters.py    # (or: python tests/test_adapters.py)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import common  # noqa: E402
from adapters.base import Adapter, discover, run_all  # noqa: E402
from adapters.sleeper_state import SleeperStateAdapter  # noqa: E402

# A canned Sleeper /state/nfl payload — normalize is pure, so no network needed.
_FIXTURE = {
    "season": "2025",
    "season_type": "regular",
    "week": 2,
    "display_week": 3,
    "previous_season": "2024",
}


class _KeyedAdapter(Adapter):
    """Test double: needs a key that is guaranteed absent → must degrade."""

    name = "keyed_double"
    table = "nowhere"
    on_conflict = "id"
    requires_key = "F2_TEST_ABSENT_KEY"

    def fetch(self):  # pragma: no cover - must never be reached in degrade
        raise AssertionError("fetch() called while key absent — degrade contract broken")

    def normalize(self, raw):  # pragma: no cover
        raise AssertionError("normalize() reached while key absent")


def _no_supabase():
    """Force the offline path: no Supabase env, cleared client cache."""
    os.environ.pop("NEXT_PUBLIC_SUPABASE_URL", None)
    os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
    common.get_supabase.cache_clear()


def test_discovery_finds_reference_adapter():
    names = {a.name for a in discover()}
    assert "sleeper_state" in names, names
    # base is never treated as a source
    assert "base" not in names


def test_reference_is_keyless_and_enabled():
    a = SleeperStateAdapter()
    assert a.requires_key is None
    assert a.enabled is True


def test_missing_key_degrades_without_fetch():
    os.environ.pop("F2_TEST_ABSENT_KEY", None)
    a = _KeyedAdapter()
    assert a.enabled is False
    # run() must short-circuit: no fetch, no normalize, empty result, no raise.
    assert a.run() == []


def test_normalize_is_pure_on_fixture():
    rows = SleeperStateAdapter().normalize(_FIXTURE)
    assert rows == [{
        "season": "2025",
        "season_type": "regular",
        "week": 2,
        "display_week": 3,
        "previous_season": "2024",
    }]
    # Empty / malformed payload degrades to no rows.
    assert SleeperStateAdapter().normalize({}) == []
    assert SleeperStateAdapter().normalize(None) == []


def test_persist_noops_without_supabase_and_is_idempotent(monkeypatch):
    _no_supabase()
    a = SleeperStateAdapter()
    monkeypatch.setattr(a, "fetch", lambda: _FIXTURE)  # avoid network
    # persist() dry-runs (upsert returns 0 rows sent) — no partial writes.
    assert a.persist(a.normalize(_FIXTURE)) == 0
    # Full run twice: same rows, no error, nothing written either time.
    first = a.run()
    second = a.run()
    assert first == second
    assert len(first) == 1


def test_run_all_is_degrade_safe():
    _no_supabase()
    # No network reached because the only real adapter's fetch would need it, so
    # neutralize it; run_all must complete without raising and report per source.
    import adapters.sleeper_state as ss
    monkey = getattr(ss.SleeperStateAdapter, "fetch")
    ss.SleeperStateAdapter.fetch = lambda self: _FIXTURE  # type: ignore[assignment]
    try:
        result = run_all()
        assert result.get("sleeper_state") == 1, result
    finally:
        ss.SleeperStateAdapter.fetch = monkey  # type: ignore[assignment]


if __name__ == "__main__":
    # Standalone runner (repo convention: some suites have no pytest in the venv).
    class _MP:
        def setattr(self, obj, name, val):
            setattr(obj, name, val)

    test_discovery_finds_reference_adapter()
    test_reference_is_keyless_and_enabled()
    test_missing_key_degrades_without_fetch()
    test_normalize_is_pure_on_fixture()
    test_persist_noops_without_supabase_and_is_idempotent(_MP())
    test_run_all_is_degrade_safe()
    print("ok test_adapters")
