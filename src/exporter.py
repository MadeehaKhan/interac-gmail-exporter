"""CSV export for INTERAC transfer records."""

from __future__ import annotations

import csv
from pathlib import Path

from .parser import TransferRecord

CSV_COLUMNS = [
    "date",
    "direction",
    "amount",
    "currency",
    "name",
    "reference_number",
    "subject",
    "from_email",
    "message_id",
    "parse_ok",
]


def record_to_row(record: TransferRecord) -> dict:
    return {
        "date": record.date,
        "direction": record.direction,
        "amount": record.amount,
        "currency": record.currency,
        "name": record.name,
        "reference_number": record.reference_number,
        "subject": record.subject,
        "from_email": record.from_email,
        "message_id": record.message_id,
        "parse_ok": str(record.parse_ok).lower(),
    }


def load_existing_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["message_id"] for row in reader if row.get("message_id")}


def write_csv(
    records: list[TransferRecord],
    output_path: Path,
    append: bool = True,
) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    existing_ids = load_existing_ids(output_path) if append else set()

    new_records = [r for r in records if r.message_id not in existing_ids]
    if not new_records and output_path.exists():
        return 0

    mode = "a" if append and output_path.exists() else "w"
    write_header = mode == "w" or not output_path.exists()

    with output_path.open(mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        for record in new_records:
            writer.writerow(record_to_row(record))

    return len(new_records)
