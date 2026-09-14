#!/usr/bin/env python3
"""Small argparse example: greet a user from the command line.

Examples:
    python cli_basics.py Alice
    python cli_basics.py Alice --greeting Hello --times 3
    python cli_basics.py Alice --uppercase
"""

from __future__ import annotations

import argparse


def positive_int(value: str) -> int:
    """Convert *value* to a positive integer for argparse."""
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return number


def build_parser() -> argparse.ArgumentParser:
    """Create and configure the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Print a configurable greeting.",
        epilog="Example: python cli_basics.py Alice --greeting Hi --times 2",
    )
    parser.add_argument("name", help="name of the person to greet")
    parser.add_argument(
        "-g",
        "--greeting",
        default="Hello",
        help="greeting text (default: %(default)s)",
    )
    parser.add_argument(
        "-n",
        "--times",
        type=positive_int,
        default=1,
        help="number of repetitions (default: %(default)s)",
    )
    parser.add_argument(
        "--uppercase",
        action="store_true",
        help="convert the final message to uppercase",
    )
    return parser


def main() -> None:
    """Parse CLI arguments and print the requested greeting."""
    args = build_parser().parse_args()
    message = f"{args.greeting}, {args.name}!"

    if args.uppercase:
        message = message.upper()

    for _ in range(args.times):
        print(message)


if __name__ == "__main__":
    main()
