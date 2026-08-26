import importlib.util
import zipfile
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[2] / "scripts" / "extract-expert-board.py"
spec = importlib.util.spec_from_file_location("extract_expert_board", SCRIPT)
extractor = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(extractor)


def workbook(path: Path, count: int = 300) -> Path:
    rows = []
    for row in range(5, 5 + count):
        rows.append(
            f'<row r="{row}"><c r="A{row}" t="n"><v>{row - 4}</v></c>'
            f'<c r="B{row}" t="inlineStr"><is><t>Player {row}</t></is></c>'
            f'<c r="C{row}" t="inlineStr"><is><t>WR</t></is></c></row>'
        )
    xml = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(rows)}</sheetData></worksheet>'
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/worksheets/sheet2.xml", xml)
    return path


def test_extracts_300_static_player_rows_without_excel(tmp_path):
    rows = extractor.extract(workbook(tmp_path / "board.xlsx"))
    assert len(rows) == 300
    assert rows[0] == {"modelRank": 1, "name": "Player 5", "position": "WR"}


def test_rejects_truncated_player_board(tmp_path):
    with pytest.raises(ValueError, match="expected 300"):
        extractor.extract(workbook(tmp_path / "short.xlsx", count=2))
