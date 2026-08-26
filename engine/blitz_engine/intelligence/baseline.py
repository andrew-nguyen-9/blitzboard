"""Freeze and verify the compact 2026 intelligence baseline.

Raw public payloads are read into memory and reduced to source-level evidence.  They are never
written beneath the repository.  A failed source is a recorded gap, never an empty success.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from blitz_engine.data.ingest.status_news import (
    ESPN_NEWS,
    NFLVERSE_DEPTH_CHARTS,
    NFLVERSE_INJURIES,
    NFLVERSE_WEEKLY_ROSTERS,
    Feed,
    default_feeds,
)
from blitz_engine.intelligence.model import MODE_BUDGETS
from blitz_engine.intelligence.snapshot import create_snapshot, verify_snapshot

BASELINE_DATE = "2026-08-25"
SEASON = 2026
WINDOW_START = datetime(2026, 1, 1, tzinfo=UTC)
WINDOW_END = datetime(2026, 8, 26, tzinfo=UTC)
CREATED_AT = WINDOW_END
SNAPSHOT_ID = f"intelligence-{BASELINE_DATE}"
DEFAULT_DESTINATION = Path("docs/data/baselines") / BASELINE_DATE


def _source_url(feed: Feed) -> str:
    return {
        "nflverse/injuries": NFLVERSE_INJURIES.format(season=SEASON),
        "nflverse/weekly_rosters": NFLVERSE_WEEKLY_ROSTERS.format(season=SEASON),
        "nflverse/depth_charts": NFLVERSE_DEPTH_CHARTS.format(season=SEASON),
        "ESPN/news": ESPN_NEWS,
    }[feed.source]


def _error_text(exc: Exception) -> str:
    """Keep gap evidence stable and avoid persisting signed redirect URLs."""
    message = str(exc).replace("\n", " ")
    if "404" in message or "not found" in message.lower():
        return "source asset unavailable (HTTP 404)"
    return f"{type(exc).__name__}: {message[:300]}"


def retrieve_sources() -> list[dict[str, Any]]:
    """Retrieve each no-key source independently so one gap cannot mask another."""
    evidence: list[dict[str, Any]] = []
    for feed in default_feeds(SEASON):
        try:
            frame = feed.fetch(WINDOW_START, WINDOW_END)
            evidence.append({
                "source": feed.source,
                "table": feed.table,
                "url": _source_url(feed),
                "status": "available",
                "rows_in_window": len(frame),
            })
        except Exception as exc:  # noqa: BLE001 - source boundary records every failure
            evidence.append({
                "source": feed.source,
                "table": feed.table,
                "url": _source_url(feed),
                "status": "gap",
                "rows_in_window": None,
                "reason": _error_text(exc),
            })
    evidence.append({
        "source": "official/gameday-inactives",
        "table": "status_inactives",
        "url": None,
        "status": "gap",
        "rows_in_window": None,
        "reason": "no stable documented no-key public adapter is available",
    })
    return evidence


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def generate(destination: Path = DEFAULT_DESTINATION) -> Path:
    """Create the immutable baseline; an existing destination is never overwritten."""
    sources = retrieve_sources()
    coverage = {
        "available_sources": sum(item["status"] == "available" for item in sources),
        "gap_sources": sum(item["status"] == "gap" for item in sources),
        "source_count": len(sources),
    }
    evidence_report = {
        "schema_version": 1,
        "as_of_utc": WINDOW_END.isoformat(),
        "window_start_utc": WINDOW_START.isoformat(),
        "policy": "public no-key read-only retrieval; absent or failed sources are gaps",
        "sources": sources,
    }
    model_report = {
        "schema_version": 1,
        "as_of_utc": WINDOW_END.isoformat(),
        "forecast_rows": 0,
        "promotion_evaluated": False,
        "promoted_model": None,
        "reason": (
            "No completed 2026 regular-season outcomes exist at this cutoff; model promotion "
            "requires walk-forward actuals and is intentionally disabled."
        ),
        "availability_is_separate_from_conditional_points": True,
        "budgets": {name: asdict(value) for name, value in MODE_BUDGETS.items()},
    }
    with tempfile.TemporaryDirectory(prefix="blitzboard-baseline-") as raw_tmp:
        stage = Path(raw_tmp)
        evidence_path = stage / "source-evidence.json"
        model_path = stage / "model-status.json"
        _write_json(evidence_path, evidence_report)
        _write_json(model_path, model_report)
        manifest = create_snapshot(
            destination,
            {"source-evidence": evidence_path, "model-status": model_path},
            snapshot_id=SNAPSHOT_ID,
            as_of=WINDOW_END,
            created_at=CREATED_AT,
            code_version="731a36313aaf04dc03e72b6f2fcb6e849c53f00f+live-baseline",
            model_versions={"existing": "shadow", "independent": "shadow"},
            seeds={},
            config={"season": SEASON, "window_start_utc": WINDOW_START.isoformat()},
            coverage=coverage,
        )
    verify_snapshot(destination)
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m blitz_engine.intelligence.baseline")
    parser.add_argument("--output", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--verify-manifest", action="store_true")
    args = parser.parse_args(argv)
    if args.verify_manifest:
        manifest = verify_snapshot(args.output)
        print(json.dumps({"ok": True, "snapshot_id": manifest.snapshot_id}))
        return 0
    manifest = generate(args.output)
    print(json.dumps({"ok": True, "manifest": str(manifest)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
