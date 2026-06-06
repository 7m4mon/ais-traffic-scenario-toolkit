from __future__ import annotations

import csv
import json
from pathlib import Path

from .model import CSV_FIELDS, TimelineRecord


def write_timeline_jsonl(records: list[TimelineRecord], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as f:
        for record in records:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False, allow_nan=False) + "\n")


def read_timeline_jsonl(path: str | Path) -> list[TimelineRecord]:
    records: list[TimelineRecord] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(TimelineRecord.from_dict(json.loads(line)))
    return records


def write_timeline_csv(records: list[TimelineRecord], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(_csv_row(record.to_dict()))


def _csv_row(data: dict) -> dict:
    row = {key: data.get(key) for key in CSV_FIELDS}
    for key, value in list(row.items()):
        if value is None:
            row[key] = ""
    return row
