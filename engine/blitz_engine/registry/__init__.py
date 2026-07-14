"""Model registry — every run reproduces from its version tuple.

Records `{params, data_hash, git_sha, seed}` for each engine run so any result can be
regenerated from the version alone (see docs/design/v4-engine-architecture.md). Storage
is a single append-only JSONL under the store root — `ponytail:` no DB, no ORM.

    reg = ModelRegistry("data/")
    rec = reg.record(params={...}, data_hash="ab12…", seed=cfg.seed)   # -> RunRecord
    same = reg.reproduce(rec.version)   # the tuple needed to re-run deterministically
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

__all__ = ["ModelRegistry", "RunRecord", "current_git_sha"]

_LOG = "registry.jsonl"


def current_git_sha() -> str:
    """Short git SHA of the working tree, or 'unknown' outside a repo."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip() or "unknown"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


@dataclass(frozen=True)
class RunRecord:
    """One reproducible run. `version` is derived from the reproducibility tuple."""

    version: str
    params: dict
    data_hash: str
    git_sha: str
    seed: int
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @staticmethod
    def compute_version(params: dict, data_hash: str, git_sha: str, seed: int) -> str:
        """Deterministic 12-char id over the reproducibility tuple (order-insensitive)."""
        blob = json.dumps(
            {"params": params, "data_hash": data_hash, "git_sha": git_sha, "seed": seed},
            sort_keys=True, default=str,
        )
        return hashlib.sha256(blob.encode()).hexdigest()[:12]


class ModelRegistry:
    """Append-only run ledger backed by a JSONL file under `root`."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        self.log_path = self.root / _LOG

    def record(
        self,
        params: dict,
        data_hash: str,
        seed: int,
        git_sha: str | None = None,
    ) -> RunRecord:
        """Append a run and return its `RunRecord` (with the derived `version`)."""
        sha = git_sha or current_git_sha()
        version = RunRecord.compute_version(params, data_hash, sha, seed)
        rec = RunRecord(version=version, params=params, data_hash=data_hash,
                        git_sha=sha, seed=seed)
        with self.log_path.open("a") as fh:
            fh.write(json.dumps(asdict(rec)) + "\n")
        return rec

    def reproduce(self, version: str) -> RunRecord:
        """Return the recorded tuple for `version` so the run can be re-executed.

        Raises `KeyError` if the version was never recorded.
        """
        for rec in reversed(self.records()):
            if rec.version == version:
                return rec
        raise KeyError(f"no run recorded for version {version!r}")

    def records(self) -> list[RunRecord]:
        """Every recorded run, oldest first."""
        if not self.log_path.exists():
            return []
        return [
            RunRecord(**json.loads(line))
            for line in self.log_path.read_text().splitlines()
            if line.strip()
        ]
