from __future__ import annotations

import plistlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from blitz_engine.intelligence.runner import (
    SeasonalTask,
    freshness_report,
    run_seasonal_cycle,
)

WEDNESDAY = datetime(2026, 8, 26, 12, tzinfo=UTC)
TEMPLATE = (
    Path(__file__).parents[1]
    / "blitz_engine/intelligence/com.blitzboard.intelligence.plist.template"
)


def test_cycle_is_idempotent_and_obeys_nfl_cadence(tmp_path) -> None:
    calls: list[str] = []
    tasks = [
        SeasonalTask("daily", "daily", lambda: calls.append("daily") or {"rows": 1}),
        SeasonalTask("practice", "practice", lambda: calls.append("practice") or {"rows": 2}),
        SeasonalTask("game", "gameday", lambda: calls.append("game") or {"rows": 3}),
    ]
    first = run_seasonal_cycle(tmp_path, tasks, now=WEDNESDAY)
    second = run_seasonal_cycle(tmp_path, tasks, now=WEDNESDAY)
    assert calls == ["daily", "practice"]
    assert [record.task_id for record in first] == ["daily", "practice"]
    assert second == []


def test_failure_is_ledgered_non_silently_and_notifier_is_optional(tmp_path) -> None:
    notifications: list[str] = []

    def fail() -> dict:
        raise TimeoutError("source timeout")

    records = run_seasonal_cycle(
        tmp_path, [SeasonalTask("fetch", "daily", fail)], now=WEDNESDAY,
        notifier=notifications.append,
    )
    assert records[0].status == "failed"
    assert records[0].error == "TimeoutError: source timeout"
    assert notifications and "fetch failed" in notifications[0]
    assert "source timeout" in (tmp_path / "intelligence/runs.jsonl").read_text()


def test_failed_task_can_retry_but_successful_task_cannot_duplicate(tmp_path) -> None:
    attempts = 0

    def flaky() -> dict:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("first")
        return {"attempt": attempts}

    task = SeasonalTask("flaky", "daily", flaky)
    assert run_seasonal_cycle(tmp_path, [task], now=WEDNESDAY)[0].status == "failed"
    assert run_seasonal_cycle(tmp_path, [task], now=WEDNESDAY)[0].status == "succeeded"
    assert run_seasonal_cycle(tmp_path, [task], now=WEDNESDAY) == []


def test_lock_prevents_overlapping_processes_and_is_not_deleted(tmp_path) -> None:
    lock = tmp_path / "intelligence/.runner.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("someone else")
    with pytest.raises(RuntimeError, match="already active"):
        run_seasonal_cycle(tmp_path, [], now=WEDNESDAY)
    assert lock.read_text() == "someone else"


def test_freshness_report_uses_latest_success(tmp_path) -> None:
    run_seasonal_cycle(
        tmp_path, [SeasonalTask("daily", "daily", lambda: {"rows": 4})], now=WEDNESDAY,
    )
    report = freshness_report(tmp_path, now=datetime.now(UTC))
    assert report["daily"]["details"] == {"rows": 4}
    assert report["daily"]["age_hours"] >= 0


def test_launchd_template_is_valid_uninstalled_and_key_free() -> None:
    text = TEMPLATE.read_text()
    parsed = plistlib.loads(text.encode())
    assert parsed["Label"] == "com.blitzboard.intelligence"
    assert parsed["LowPriorityIO"] is True
    assert "__WORKTREE__" in text and "__DATA_ROOT__" in text and "__PYTHON__" in text
    assert "SUPABASE" not in text and "API_KEY" not in text

