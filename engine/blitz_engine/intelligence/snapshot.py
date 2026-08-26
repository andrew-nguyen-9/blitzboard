"""Immutable snapshot manifests and content verification."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MANIFEST_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class SnapshotFile:
    logical_name: str
    relative_path: str
    sha256: str
    bytes: int


@dataclass(frozen=True)
class SnapshotManifest:
    schema_version: int
    snapshot_id: str
    as_of_utc: str
    created_at_utc: str
    code_version: str
    model_versions: dict[str, str]
    seeds: dict[str, int]
    config: dict[str, Any]
    coverage: dict[str, Any]
    files: tuple[SnapshotFile, ...]


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()


def create_snapshot(
    destination: str | Path,
    files: dict[str, str | Path],
    *,
    snapshot_id: str,
    as_of: datetime,
    code_version: str,
    model_versions: dict[str, str] | None = None,
    seeds: dict[str, int] | None = None,
    config: dict[str, Any] | None = None,
    coverage: dict[str, Any] | None = None,
    created_at: datetime | None = None,
) -> Path:
    """Copy inputs and atomically publish a frozen, self-verifying snapshot directory."""
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(f"snapshot already exists: {destination}")
    stage = destination.with_name(f".{destination.name}.tmp-{os.getpid()}")
    if stage.exists():
        raise FileExistsError(f"snapshot staging path already exists: {stage}")
    stage.mkdir(parents=True)
    entries: list[SnapshotFile] = []
    try:
        data_dir = stage / "data"
        data_dir.mkdir()
        for logical_name, source_value in sorted(files.items()):
            source = Path(source_value)
            if not source.is_file():
                raise FileNotFoundError(source)
            suffix = "".join(source.suffixes)
            target = data_dir / f"{logical_name}{suffix}"
            shutil.copyfile(source, target)
            entries.append(
                SnapshotFile(logical_name, str(target.relative_to(stage)), sha256_file(target),
                             target.stat().st_size)
            )
        now = created_at or datetime.now(UTC)
        manifest = SnapshotManifest(
            schema_version=MANIFEST_SCHEMA_VERSION,
            snapshot_id=snapshot_id,
            as_of_utc=as_of.astimezone(UTC).isoformat(),
            created_at_utc=now.astimezone(UTC).isoformat(),
            code_version=code_version,
            model_versions=model_versions or {},
            seeds=seeds or {},
            config=config or {},
            coverage=coverage or {},
            files=tuple(entries),
        )
        payload = asdict(manifest)
        (stage / "manifest.json").write_bytes(_canonical_json(payload) + b"\n")
        (stage / "manifest.sha256").write_text(
            hashlib.sha256(_canonical_json(payload)).hexdigest() + "\n"
        )
        stage.replace(destination)
        return destination / "manifest.json"
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def verify_snapshot(directory: str | Path) -> SnapshotManifest:
    directory = Path(directory)
    manifest_path = directory / "manifest.json"
    payload = json.loads(manifest_path.read_text())
    expected_manifest_hash = (directory / "manifest.sha256").read_text().strip()
    if hashlib.sha256(_canonical_json(payload)).hexdigest() != expected_manifest_hash:
        raise ValueError("snapshot manifest hash mismatch")
    if payload.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ValueError("snapshot manifest schema drift")
    entries = tuple(SnapshotFile(**item) for item in payload.pop("files"))
    for entry in entries:
        path = directory / entry.relative_path
        if not path.is_file() or path.stat().st_size != entry.bytes:
            raise ValueError(f"snapshot file missing/size mismatch: {entry.logical_name}")
        if sha256_file(path) != entry.sha256:
            raise ValueError(f"snapshot file hash mismatch: {entry.logical_name}")
    return SnapshotManifest(files=entries, **payload)


def snapshot_storage_bytes(directory: str | Path) -> int:
    return sum(path.stat().st_size for path in Path(directory).rglob("*") if path.is_file())

