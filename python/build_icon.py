#!/usr/bin/env python3
"""Convert PNG icon asset to Windows ICO format."""

import argparse
from pathlib import Path

from PIL import Image


def convert_png_to_ico(input_file, output_file):
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.is_file():
        raise ValueError(f"Input PNG does not exist: {input_file}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as image:
        image = image.convert("RGBA")
        image.save(
            output_path,
            format="ICO",
            sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )


def main():
    parser = argparse.ArgumentParser(description="Convert PNG to ICO")
    parser.add_argument("--input-file", required=True, metavar="<file>", help="Input PNG path")
    parser.add_argument("--output-file", required=False, metavar="<file>", help="Output ICO path", default="small-logo.ico")
    args = parser.parse_args()

    try:
        convert_png_to_ico(args.input_file, args.output_file)
        print(f"Created icon: {args.output_file}")
    except Exception as exc:
        print(f"Error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
