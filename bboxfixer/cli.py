import argparse
import os
import sys

from .generator import generate_bat_for_xml_file
from .parser import parse_bbox_xml


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate .bat files with curl commands to reprint BBOX fiscal printer receipts."
    )
    parser.add_argument("xml_files", nargs="+", metavar="XML_FILE", help="BBOX XML file(s) to process")
    parser.add_argument("--host", default="localhost", help="Printer host (default: localhost)")
    parser.add_argument("--port", type=int, default=8080, help="Printer port (default: 8080)")
    parser.add_argument(
        "--output-dir",
        default=None,
        metavar="OUTPUT_DIR",
        help="Directory for output .bat files (default: same directory as input file)",
    )
    args = parser.parse_args()

    for xml_path in args.xml_files:
        if not os.path.isfile(xml_path):
            print(f"Error: file not found: {xml_path}", file=sys.stderr)
            continue

        try:
            with open(xml_path, "r", encoding="utf-8") as f:
                xml_content = f.read()
            parse_bbox_xml(xml_content)
        except Exception as exc:
            print(f"Error parsing {xml_path}: {exc}", file=sys.stderr)
            continue

        output_dir = args.output_dir if args.output_dir is not None else os.path.dirname(os.path.abspath(xml_path))
        os.makedirs(output_dir, exist_ok=True)

        try:
            bat_path = generate_bat_for_xml_file(xml_path, output_dir, args.host, args.port)
            print(f"Generated: {bat_path}")
        except Exception as exc:
            print(f"Error generating bat for {xml_path}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
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
