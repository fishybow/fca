#!/usr/bin/env python3
"""Validate that Windows executables contain icon resources."""

import argparse
from pathlib import Path

import pefile

RT_ICON = 3
RT_GROUP_ICON = 14


def get_icon_resource_counts(exe_path):
    pe = pefile.PE(str(exe_path), fast_load=False)
    group_count = 0
    icon_count = 0

    if hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
        for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
            resource_type = entry.struct.Id
            if resource_type == RT_GROUP_ICON:
                group_count += len(entry.directory.entries)
            elif resource_type == RT_ICON:
                icon_count += len(entry.directory.entries)

    return group_count, icon_count


def main():
    parser = argparse.ArgumentParser(description="Check icon resources in one or more .exe files")
    parser.add_argument("exe_files", nargs="+", help="Executable paths to inspect")
    args = parser.parse_args()

    failed = False

    for exe in args.exe_files:
        path = Path(exe)
        if not path.is_file():
            print(f"MISSING: {path}")
            failed = True
            continue

        group_count, icon_count = get_icon_resource_counts(path)
        print(f"{path}: RT_GROUP_ICON={group_count}, RT_ICON={icon_count}")

        if group_count == 0 or icon_count == 0:
            failed = True

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
