"""CLI entry point for INTERAC e-Transfer export."""

from __future__ import annotations

import argparse
import sys

from .export_job import run_export


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export INTERAC e-Transfer emails from Gmail to CSV."
    )
    parser.add_argument(
        "--output",
        "-o",
        default="output/interac_transfers.csv",
        help="Output CSV path (default: output/interac_transfers.csv)",
    )
    parser.add_argument("--after", help="Gmail after date (YYYY/MM/DD)")
    parser.add_argument("--before", help="Gmail before date (YYYY/MM/DD)")
    parser.add_argument("--max", type=int, default=500, help="Max emails to fetch")
    parser.add_argument("--query", help="Override default Gmail search query")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and parse without writing CSV",
    )
    args = parser.parse_args(argv)

    def progress(msg: str) -> None:
        print(msg)

    try:
        result = run_export(
            output_path=args.output,
            after=args.after,
            before=args.before,
            max_results=args.max,
            query=args.query,
            dry_run=args.dry_run,
            on_progress=progress,
        )
        if args.dry_run:
            print(
                f"\nDry run: {result.messages_found} emails, "
                f"{result.parse_ok_count} fully parsed."
            )
        else:
            print(
                f"\nWrote {result.rows_written} new rows to {result.output_path} "
                f"({result.parse_ok_count}/{result.messages_found} fully parsed)."
            )
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("See README for Google Cloud OAuth setup.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
