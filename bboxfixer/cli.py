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
