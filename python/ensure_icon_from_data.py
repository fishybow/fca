#!/usr/bin/env python3
"""Materialize embedded ICO icon bytes to disk for PyInstaller --icon usage."""

import argparse

from icon_data import get_icon_bytes, write_icon_file


def ensure_icon(output_file):
    output_path = write_icon_file(output_file)
    data = get_icon_bytes()
    print(f"Wrote icon: {output_path} ({len(data)} bytes)")


def main():
    parser = argparse.ArgumentParser(description="Write embedded ICO bytes to a file")
    parser.add_argument("--output-file", required=True, metavar="<file>", help="Output ICO file path")
    args = parser.parse_args()

    ensure_icon(args.output_file)


if __name__ == "__main__":
    main()
