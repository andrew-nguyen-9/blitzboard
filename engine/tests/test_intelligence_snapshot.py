from __future__ import annotations

from datetime import UTC, datetime

import pytest

from blitz_engine.intelligence.snapshot import (
    create_snapshot,
    snapshot_storage_bytes,
    verify_snapshot,
)

AS_OF = datetime(2026, 8, 25, 23, 59, tzinfo=UTC)
CREATED = datetime(2026, 8, 26, tzinfo=UTC)


def test_snapshot_is_replayable_and_records_versions(tmp_path) -> None:
    source = tmp_path / "players.parquet"
    source.write_bytes(b"fixture parquet bytes")
    manifest_path = create_snapshot(
        tmp_path / "baseline",
        {"players": source},
        snapshot_id="nfl-2026-08-25",
        as_of=AS_OF,
        created_at=CREATED,
        code_version="abc123",
        model_versions={"existing": "v5", "independent": "shadow-1"},
        seeds={"ensemble": 7},
        config={"canonical": "12-team-1qb-ppr"},
        coverage={"implemented": 2, "gaps": ["inactives"]},
    )
    manifest = verify_snapshot(manifest_path.parent)
    assert manifest.snapshot_id == "nfl-2026-08-25"
    assert manifest.as_of_utc == "2026-08-25T23:59:00+00:00"
    assert manifest.seeds == {"ensemble": 7}
    assert manifest.files[0].logical_name == "players"
    assert snapshot_storage_bytes(manifest_path.parent) > source.stat().st_size


def test_snapshot_never_overwrites_an_existing_baseline(tmp_path) -> None:
    source = tmp_path / "data"
    source.write_text("one")
    destination = tmp_path / "baseline"
    create_snapshot(destination, {"data": source}, snapshot_id="id", as_of=AS_OF,
                    code_version="abc")
    with pytest.raises(FileExistsError):
        create_snapshot(destination, {"data": source}, snapshot_id="id", as_of=AS_OF,
                        code_version="def")


def test_snapshot_detects_data_corruption(tmp_path) -> None:
    source = tmp_path / "data"
    source.write_text("original")
    destination = tmp_path / "baseline"
    create_snapshot(destination, {"data": source}, snapshot_id="id", as_of=AS_OF,
                    code_version="abc")
    next((destination / "data").iterdir()).write_text("tampered")
    with pytest.raises(ValueError, match="mismatch"):
        verify_snapshot(destination)


def test_failed_snapshot_leaves_no_partial_destination(tmp_path) -> None:
    destination = tmp_path / "baseline"
    with pytest.raises(FileNotFoundError):
        create_snapshot(destination, {"missing": tmp_path / "nope"}, snapshot_id="id",
                        as_of=AS_OF, code_version="abc")
    assert not destination.exists()
    assert not list(tmp_path.glob(".baseline.tmp-*"))
