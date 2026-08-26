#!/usr/bin/env python3
"""Extract static Player Board cells from the two Smores OOXML workbooks."""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
COLUMNS = {
    "A": "modelRank", "B": "name", "C": "position", "D": "team", "E": "bye",
    "F": "tier", "G": "espnRank", "H": "marketAdp", "I": "ffpcAdp",
    "J": "sleeperAdp", "K": "marketEdge", "L": "risk", "M": "upside",
    "N": "injuryStatus", "R": "note", "S": "siRank", "T": "laserWolvesRank",
    "U": "pfnRank", "V": "pfnPpg", "W": "expertAverage", "X": "modelSpread",
    "Y": "rating", "Z": "confidence",
}
SOURCE_COLUMNS = {"A": "use", "B": "source", "C": "asOf", "D": "weight", "E": "url", "F": "application"}


def value(cell: ET.Element):
    inline = cell.find("x:is/x:t", NS)
    if inline is not None:
        return inline.text or ""
    raw = cell.findtext("x:v", default="", namespaces=NS)
    if not raw:
        return ""
    number = float(raw)
    return int(number) if number.is_integer() else round(number, 2)


def extract(path: Path) -> list[dict]:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("xl/worksheets/sheet2.xml"))
    rows = []
    for row in root.findall("x:sheetData/x:row", NS):
        if int(row.attrib["r"]) < 5:
            continue
        item = {}
        for cell in row.findall("x:c", NS):
            column = re.match(r"[A-Z]+", cell.attrib["r"])[0]
            if column in COLUMNS:
                item[COLUMNS[column]] = value(cell)
        if item.get("name") and item.get("position"):
            rows.append(item)
    if len(rows) != 300:
        raise ValueError(f"{path}: expected 300 Player Board rows, found {len(rows)}")
    return rows


def extract_sources(path: Path) -> list[dict]:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("xl/worksheets/sheet8.xml"))
    sources = []
    for row in root.findall("x:sheetData/x:row", NS):
        if int(row.attrib["r"]) < 5:
            continue
        item = {}
        for cell in row.findall("x:c", NS):
            column = re.match(r"[A-Z]+", cell.attrib["r"])[0]
            if column in SOURCE_COLUMNS:
                item[SOURCE_COLUMNS[column]] = value(cell)
        if item.get("source"):
            sources.append(item)
    return sources


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eleven", required=True, type=Path)
    parser.add_argument("--twelve", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    eleven, twelve = extract(args.eleven), extract(args.twelve)
    payload = {
        "version": 1,
        "asOf": "2026-08-26",
        "provenance": "Smores 2026 live-draft backups; expert and market sources dated 2026-08-19 through 2026-08-26",
        "sources": extract_sources(args.twelve),
        "boards": {"11": "shared", "12": "shared"} if eleven == twelve else {"11": eleven, "12": twelve},
    }
    if eleven == twelve:
        payload["sharedBoard"] = eleven
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {args.output}: 11-team={len(eleven)}, 12-team={len(twelve)}, shared={eleven == twelve}")


if __name__ == "__main__":
    main()
