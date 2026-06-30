"""v3 Epic 1 — history ingest marker covers/writes correctly (CI skip logic).

Plain asserts (no pytest in the venv):
    python tests/test_history_marker.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from history_ingest import _marker_covers, _write_marker  # noqa: E402

with tempfile.TemporaryDirectory() as d:
    m = Path(d) / "sub" / "marker.json"

    # Missing marker → never covered (parent dir doesn't even exist yet).
    assert not _marker_covers(m, [2022, 2023], weekly=False)

    _write_marker(m, [2023, 2022, 2022], weekly=False)  # dedupes + creates dirs
    assert m.exists()

    # Subset of ingested seasons is covered; same granularity required.
    assert _marker_covers(m, [2022], weekly=False)
    assert _marker_covers(m, [2022, 2023], weekly=False)
    # A new season not yet ingested → not covered (drives re-ingest).
    assert not _marker_covers(m, [2022, 2023, 2024], weekly=False)
    # Granularity mismatch → not covered.
    assert not _marker_covers(m, [2022], weekly=True)

print("ok test_history_marker")
