"""Shared export pipeline for GUI and CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import gmail_client, parser
from .exporter import write_csv


@dataclass
class ExportResult:
    messages_found: int
    rows_written: int
    parse_ok_count: int
    output_path: Path


def run_export(
    output_path: str | Path,
    after: str | None = None,
    before: str | None = None,
    max_results: int = 500,
    query: str | None = None,
    dry_run: bool = False,
    on_progress: Callable[[str], None] | None = None,
) -> ExportResult:
    def progress(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    output = Path(output_path)
    search_query = gmail_client.build_search_query(
        base_query=query or gmail_client.DEFAULT_QUERY,
        after=after or None,
        before=before or None,
    )

    progress("Authenticating with Gmail…")
    service = gmail_client.build_gmail_service()

    progress(f"Searching: {search_query[:80]}…")
    messages = gmail_client.fetch_messages(
        service, search_query, max_results=max_results, on_progress=progress
    )

    progress(f"Parsing {len(messages)} emails…")
    records = [parser.parse_message(m) for m in messages]
    parse_ok_count = sum(1 for r in records if r.parse_ok)

    if dry_run:
        sample = next((r for r in records if r.parse_ok), records[0] if records else None)
        if sample:
            progress(
                f"Dry run sample: {sample.direction} | {sample.name} | "
                f"${sample.amount} | ref {sample.reference_number}"
            )
        progress(f"Dry run complete: {len(messages)} emails, {parse_ok_count} fully parsed.")
        return ExportResult(
            messages_found=len(messages),
            rows_written=0,
            parse_ok_count=parse_ok_count,
            output_path=output,
        )

    progress(f"Writing CSV to {output}…")
    rows_written = write_csv(records, output, append=True)
    progress(
        f"Done: {len(messages)} emails, {parse_ok_count} fully parsed, "
        f"{rows_written} new rows written."
    )

    return ExportResult(
        messages_found=len(messages),
        rows_written=rows_written,
        parse_ok_count=parse_ok_count,
        output_path=output,
    )
