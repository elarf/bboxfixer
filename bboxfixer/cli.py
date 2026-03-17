"""Command-line interface for bboxfixer."""

from __future__ import annotations

import argparse
import sys

from .generator import BatFileGenerator
from .models import load_receipts
from . import __version__


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="bboxfixer",
        description=(
            "Generate Windows .bat files that reprint or storno receipts "
            "on a BBOX fiscal printer."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    parser.add_argument(
        "input",
        metavar="INPUT_FILE",
        help="Path to a CSV or JSON file containing receipt data.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="output",
        metavar="DIR",
        help="Directory where .bat files will be written (default: %(default)s).",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        metavar="HOST",
        help="BBOX printer host/IP (default: %(default)s).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5618,
        metavar="PORT",
        help="BBOX printer HTTP port (default: %(default)s).",
    )
    parser.add_argument(
        "--mode",
        choices=["reprint", "storno", "both"],
        default="both",
        help=(
            "Type of bat files to generate: "
            "'reprint' (reprint only), 'storno' (storno only), "
            "or 'both' (default: %(default)s)."
        ),
    )
    parser.add_argument(
        "--storno-reason",
        default="Cancellation",
        metavar="REASON",
        help="Reason text written into every storno document (default: %(default)s).",
    )

    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    try:
        receipts = load_receipts(args.input)
    except FileNotFoundError:
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error reading input file: {exc}", file=sys.stderr)
        return 1

    if not receipts:
        print("No receipts found in input file.", file=sys.stderr)
        return 1

    generator = BatFileGenerator(
        host=args.host,
        port=args.port,
        output_dir=args.output_dir,
    )

    paths = generator.generate_all(
        receipts,
        mode=args.mode,
        storno_reason=args.storno_reason,
    )

    for path in paths:
        print(f"  Written: {path}")

    print(f"\n{len(paths)} bat file(s) generated in '{args.output_dir}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
