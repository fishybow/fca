#!/usr/bin/env python3
"""Generate icon_data.py from an image file."""

import argparse
from io import BytesIO
from pathlib import Path

from PIL import Image


def to_ico_bytes(input_file):
    input_path = Path(input_file)
    if not input_path.is_file():
        raise ValueError(f"Input image does not exist: {input_file}")

    if input_path.suffix.lower() == ".ico":
        return input_path.read_bytes()

    with Image.open(input_path) as image:
        image = image.convert("RGBA")
        buffer = BytesIO()
        image.save(
            buffer,
            format="ICO",
            sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )
        return buffer.getvalue()


def write_icon_data_py(output_file, icon_bytes):
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "#!/usr/bin/env python3",
        '"""Embedded ICO bytes used by FCA tools and build scripts."""',
        "",
        "from pathlib import Path",
        "",
        "ICON_ICO_BYTES = bytes([",
    ]

    for index in range(0, len(icon_bytes), 16):
        chunk = icon_bytes[index:index + 16]
        lines.append("    " + ", ".join(str(value) for value in chunk) + ",")

    lines.extend(
        [
            "])",
            "",
            "",
            "def get_icon_bytes():",
            "    return ICON_ICO_BYTES",
            "",
            "",
            "def write_icon_file(output_file):",
            "    output_path = Path(output_file)",
            "    output_path.parent.mkdir(parents=True, exist_ok=True)",
            "    output_path.write_bytes(ICON_ICO_BYTES)",
            "    return output_path",
            "",
        ]
    )

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Generate icon_data.py from an image file")
    parser.add_argument("--input-file", required=True, metavar="<file>", help="Input image file (.png or .ico)")
    parser.add_argument("--output-file", default="icon_data.py", metavar="<file>", help="Output python module path")
    args = parser.parse_args()

    try:
        icon_bytes = to_ico_bytes(args.input_file)
        write_icon_data_py(args.output_file, icon_bytes)
        print(f"Generated {args.output_file} ({len(icon_bytes)} bytes embedded)")
    except Exception as exc:
        print(f"Error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
