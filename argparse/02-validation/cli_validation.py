#!/usr/bin/env python3
"""Examples of argparse validation, choices, required options, and defaults.

Examples:
    python cli_validation.py report.csv --format csv
    python cli_validation.py report.csv --format json --limit 50
    python cli_validation.py report.csv --format csv --mode strict --output cleaned.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path


def positive_int(value: str) -> int:
    """Return *value* as a positive integer."""
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("value must be greater than 0")
    return number


def existing_file(value: str) -> Path:
    """Validate that *value* points to an existing file."""
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"file does not exist: {path}")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Demonstrate common argparse validation patterns."
    )
    parser.add_argument(
        "input",
        type=existing_file,
        help="path to an existing input file",
    )
    parser.add_argument(
        "--format",
        choices=("csv", "json"),
        required=True,
        help="input data format",
    )
    parser.add_argument(
        "--mode",
        choices=("lenient", "strict"),
        default="lenient",
        help="validation mode (default: %(default)s)",
    )
    parser.add_argument(
        "--limit",
        type=positive_int,
        default=100,
        help="maximum number of records to process (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output.txt"),
        help="output path (default: %(default)s)",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    print(f"input:  {args.input}")
    print(f"format: {args.format}")
    print(f"mode:   {args.mode}")
    print(f"limit:  {args.limit}")
    print(f"output: {args.output}")


if __name__ == "__main__":
    main()
