#!/usr/bin/env python3
"""Materialize embedded ICO icon bytes to disk for PyInstaller --icon usage."""

import argparse
import base64
from pathlib import Path

from icon_data import ICON_ICO_B64


def ensure_icon(output_file):
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = base64.b64decode(ICON_ICO_B64)
    output_path.write_bytes(data)
    print(f"Wrote icon: {output_path} ({len(data)} bytes)")


def main():
    parser = argparse.ArgumentParser(description="Write embedded ICO bytes to a file")
    parser.add_argument("--output-file", required=True, metavar="<file>", help="Output ICO file path")
    args = parser.parse_args()

    ensure_icon(args.output_file)


if __name__ == "__main__":
    main()
