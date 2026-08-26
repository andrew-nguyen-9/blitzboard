"""Idempotent seasonal task runner with a structured ledger and optional notifier."""
from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

Cadence = Literal["daily", "practice", "gameday"]
TaskAction = Callable[[], dict[str, Any]]
Notifier = Callable[[str], None]


@dataclass(frozen=True)
class SeasonalTask:
    id: str
    cadence: Cadence
    action: TaskAction


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    task_id: str
    cadence: Cadence
    started_at_utc: str
    finished_at_utc: str
    elapsed_seconds: float
    status: Literal["succeeded", "failed", "skipped"]
    details: dict[str, Any]
    error: str | None = None


def due(cadence: Cadence, now: datetime) -> bool:
    """NFL-cycle defaults: practice Wed–Fri, gameday Sunday, daily always."""
    weekday = now.astimezone(UTC).weekday()
    return cadence == "daily" or (cadence == "practice" and weekday in {2, 3, 4}) or (
        cadence == "gameday" and weekday == 6
    )


def _read_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def _append_record(path: Path, record: RunRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        stream.write(json.dumps(asdict(record), sort_keys=True, default=str) + "\n")


def _completed(records: list[dict[str, Any]], run_id: str, task_id: str) -> bool:
    return any(
        item["run_id"] == run_id and item["task_id"] == task_id
        and item["status"] == "succeeded"
        for item in records
    )


def run_seasonal_cycle(
    root: str | Path,
    tasks: Sequence[SeasonalTask],
    *,
    now: datetime | None = None,
    notifier: Notifier | None = None,
) -> list[RunRecord]:
    """Run each due task once per UTC day; failures are ledgered and optionally notified."""
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    root = Path(root).expanduser()
    ledger = root / "intelligence" / "runs.jsonl"
    lock = root / "intelligence" / ".runner.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeError(f"intelligence runner already active: {lock}") from exc
    os.close(descriptor)
    try:
        prior = _read_records(ledger)
        run_id = moment.astimezone(UTC).date().isoformat()
        output: list[RunRecord] = []
        for task in tasks:
            if not due(task.cadence, moment) or _completed(prior, run_id, task.id):
                continue
            started = datetime.now(UTC)
            monotonic_start = time.monotonic()
            try:
                details = task.action()
                if not isinstance(details, dict):
                    raise TypeError("task action must return a details dict")
                status, error = "succeeded", None
            except Exception as exc:  # noqa: BLE001 — unattended boundary must ledger all failures
                details = {}
                status, error = "failed", f"{type(exc).__name__}: {exc}"
            finished = datetime.now(UTC)
            record = RunRecord(
                run_id=run_id, task_id=task.id, cadence=task.cadence,
                started_at_utc=started.isoformat(), finished_at_utc=finished.isoformat(),
                elapsed_seconds=time.monotonic() - monotonic_start,
                status=status, details=details, error=error,
            )
            _append_record(ledger, record)
            output.append(record)
            if error and notifier:
                notifier(f"BlitzBoard intelligence task {task.id} failed: {error}")
        return output
    finally:
        lock.unlink(missing_ok=True)


def freshness_report(root: str | Path, *, now: datetime | None = None) -> dict[str, dict[str, Any]]:
    moment = now or datetime.now(UTC)
    records = _read_records(Path(root).expanduser() / "intelligence" / "runs.jsonl")
    latest: dict[str, dict[str, Any]] = {}
    for item in records:
        if item["status"] == "succeeded":
            latest[item["task_id"]] = item
    return {
        task_id: {
            "finished_at_utc": item["finished_at_utc"],
            "age_hours": (
                moment - datetime.fromisoformat(item["finished_at_utc"])
            ).total_seconds() / 3600,
            "details": item["details"],
        }
        for task_id, item in latest.items()
    }

