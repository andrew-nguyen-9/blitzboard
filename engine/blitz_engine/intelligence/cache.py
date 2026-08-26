"""Compressed content-addressed response cache with per-source request budgets."""
from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class CacheEntry:
    sha256: str
    source: str
    fetched_at: str
    content_type: str
    byte_length: int
    compressed_length: int
    etag: str | None = None
    last_modified: str | None = None


class ResponseCache:
    def __init__(self, root: str | Path, *, source_budgets: dict[str, int] | None = None):
        self.root = Path(root)
        self.objects = self.root / "objects"
        self.ledger = self.root / "ledger.jsonl"
        self.source_budgets = source_budgets or {}

    def _requests_today(self, source: str, day: str) -> int:
        if not self.ledger.exists():
            return 0
        count = 0
        for line in self.ledger.read_text().splitlines():
            item = json.loads(line)
            count += item["source"] == source and item["fetched_at"].startswith(day)
        return count

    def check_budget(self, source: str, fetched_at: datetime) -> None:
        limit = self.source_budgets.get(source)
        used = self._requests_today(source, fetched_at.date().isoformat())
        if limit is not None and used >= limit:
            raise RuntimeError(f"daily request budget exhausted for {source}: {limit}")

    def put(
        self,
        source: str,
        body: bytes,
        *,
        fetched_at: datetime | None = None,
        content_type: str = "application/octet-stream",
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> CacheEntry:
        now = fetched_at or datetime.now(UTC)
        if now.tzinfo is None:
            raise ValueError("fetched_at must be timezone-aware")
        self.check_budget(source, now)
        digest = hashlib.sha256(body).hexdigest()
        target = self.objects / digest[:2] / f"{digest}.gz"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            temp = target.with_suffix(".gz.tmp")
            temp.write_bytes(gzip.compress(body, compresslevel=6, mtime=0))
            temp.replace(target)
        entry = CacheEntry(
            sha256=digest,
            source=source,
            fetched_at=now.astimezone(UTC).isoformat(),
            content_type=content_type,
            byte_length=len(body),
            compressed_length=target.stat().st_size,
            etag=etag,
            last_modified=last_modified,
        )
        self.root.mkdir(parents=True, exist_ok=True)
        with self.ledger.open("a") as stream:
            stream.write(json.dumps(asdict(entry), sort_keys=True) + "\n")
        return entry

    def get(self, sha256: str) -> bytes:
        target = self.objects / sha256[:2] / f"{sha256}.gz"
        body = gzip.decompress(target.read_bytes())
        if hashlib.sha256(body).hexdigest() != sha256:
            raise ValueError(f"cache corruption: {sha256}")
        return body

    def size_bytes(self) -> int:
        return sum(path.stat().st_size for path in self.objects.glob("*/*.gz"))

    def prune_before(self, cutoff: datetime) -> tuple[int, int]:
        """Drop ledger entries before ``cutoff`` and unreferenced response objects.

        A body shared by an older and a retained response remains available.  The compacted
        ledger is replaced atomically before objects are removed, so an interrupted cleanup can
        leave extra bytes but cannot leave retained ledger entries pointing at deleted content.
        Returns ``(entries_removed, objects_removed)``.
        """
        if cutoff.tzinfo is None:
            raise ValueError("cutoff must be timezone-aware")
        if not self.ledger.exists():
            return 0, 0

        entries = [json.loads(line) for line in self.ledger.read_text().splitlines() if line]
        retained = [
            entry
            for entry in entries
            if datetime.fromisoformat(entry["fetched_at"]) >= cutoff
        ]
        temp = self.ledger.with_suffix(".jsonl.tmp")
        temp.write_text(
            "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in retained)
        )
        temp.replace(self.ledger)

        retained_hashes = {entry["sha256"] for entry in retained}
        objects_removed = 0
        if self.objects.exists():
            for path in self.objects.glob("*/*.gz"):
                if path.stem not in retained_hashes:
                    path.unlink()
                    objects_removed += 1
            for directory in self.objects.iterdir():
                if directory.is_dir() and not any(directory.iterdir()):
                    directory.rmdir()
        return len(entries) - len(retained), objects_removed
