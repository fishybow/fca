#!/usr/bin/env python3
"""
FCA Tool - Unified encoder/decoder CLI and GUI.

CLI usage:
    python fca_tool.py encode --output-file <file> --input-files <file1> [<file2> ...]
    python fca_tool.py decode --input-file <file> --output-dir <dir>
    python fca_tool.py --gui

If no command is provided, GUI mode is started.
"""

import argparse
import os
import struct
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from constants import (
    FILE_TYPE_UNKNOWN,
    FILE_TYPE_AMIIBO_V2,
    FILE_TYPE_AMIIBO_V3,
    FILE_TYPE_SKYLANDER,
    FILE_TYPE_DISNEY_INFINITY,
    FILE_TYPE_LEGO_DIMENSIONS,
)
from fca_encode import detect_file_type
from fca_decode import decode_fca

# File type names mapping
FILE_TYPE_NAMES = {
    FILE_TYPE_UNKNOWN: "Unknown",
    FILE_TYPE_AMIIBO_V2: "amiibo v2",
    FILE_TYPE_AMIIBO_V3: "amiibo v3",
    FILE_TYPE_SKYLANDER: "Skylander",
    FILE_TYPE_DISNEY_INFINITY: "Disney Infinity",
    FILE_TYPE_LEGO_DIMENSIONS: "Lego Dimensions",
}


def get_file_type_name(file_type):
    """Get human-readable name for a file type."""
    return FILE_TYPE_NAMES.get(file_type, f"Reserved ({file_type})")


def collect_input_files(input_files=None, input_dirs=None):
    """Collect input files from explicit files and/or directories recursively."""
    input_files = input_files or []
    input_dirs = input_dirs or []

    resolved_files = []
    seen_paths = set()

    for file_path in input_files:
        path = Path(file_path)
        if not path.is_file():
            raise ValueError(f"Input file does not exist: {file_path}")
        resolved = str(path.resolve())
        if resolved not in seen_paths:
            seen_paths.add(resolved)
            resolved_files.append(path)

    for input_dir in input_dirs:
        input_path = Path(input_dir)
        if not input_path.is_dir():
            raise ValueError(f"Input path is not a directory: {input_dir}")

        for root, dirs, filenames in os.walk(input_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for filename in filenames:
                if filename.startswith('.'):
                    continue
                file_path = Path(root) / filename
                resolved = str(file_path.resolve())
                if resolved not in seen_paths:
                    seen_paths.add(resolved)
                    resolved_files.append(file_path)

    if not resolved_files:
        raise ValueError("At least one input file is required")

    return resolved_files


def encode_fca_from_sources(output_file, input_files=None, input_dirs=None):
    """Create an FCA archive from explicit files and/or recursive directories."""
    resolved_files = collect_input_files(input_files=input_files, input_dirs=input_dirs)

    # Stable ordering for deterministic archives
    resolved_files.sort()

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f:
        f.write(b"FCA")
        f.write(struct.pack(">B", 1))

        for file_path in resolved_files:
            with open(file_path, "rb") as file_content:
                content = file_content.read()

            header_size = 2
            embedded_size = len(content)
            total_size = 2 + header_size + embedded_size

            f.write(struct.pack(">I", total_size))
            f.write(struct.pack(">H", header_size))

            file_type = detect_file_type(content)
            f.write(struct.pack(">BB", file_type, 0x00))
            f.write(content)

    print(f"Created FCA archive: {output_path}")
    print(f"Embedded {len(resolved_files)} files")


def run_gui():
    """Launch GUI mode for FCA encode/decode operations."""

    root = tk.Tk()
    root.title("FCA Tool")
    root.geometry("760x500")

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    status_var = tk.StringVar(value="Ready")

    # Encode tab
    encode_tab = ttk.Frame(notebook)
    notebook.add(encode_tab, text="Encode")

    ttk.Label(encode_tab, text="Input files (and recursive folders)").pack(anchor="w", padx=10, pady=(10, 4))

    list_frame = ttk.Frame(encode_tab)
    list_frame.pack(fill=tk.BOTH, expand=True, padx=10)

    input_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED)
    input_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    list_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=input_listbox.yview)
    list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    input_listbox.configure(yscrollcommand=list_scrollbar.set)

    buttons_frame = ttk.Frame(encode_tab)
    buttons_frame.pack(fill=tk.X, padx=10, pady=8)

    def add_files():
        files = filedialog.askopenfilenames(title="Select input files")
        for file_path in files:
            if file_path not in input_listbox.get(0, tk.END):
                input_listbox.insert(tk.END, file_path)
        status_var.set(f"Added {len(files)} file(s)")

    def add_folder_recursive():
        input_dir = filedialog.askdirectory(title="Select input folder (recursive)")
        if not input_dir:
            return
        try:
            files = collect_input_files(input_dirs=[input_dir])
        except Exception as e:
            messagebox.showerror("Encode", f"Error: {e}")
            return

        existing = set(input_listbox.get(0, tk.END))
        added = 0
        for file_path in files:
            file_str = str(file_path)
            if file_str not in existing:
                input_listbox.insert(tk.END, file_str)
                existing.add(file_str)
                added += 1

        status_var.set(f"Added {added} file(s) from folder")

    def remove_selected_files():
        selected = list(input_listbox.curselection())
        selected.reverse()
        for index in selected:
            input_listbox.delete(index)
        status_var.set("Removed selected file(s)")

    def clear_files():
        input_listbox.delete(0, tk.END)
        status_var.set("Cleared file list")

    ttk.Button(buttons_frame, text="Add files", command=add_files).pack(side=tk.LEFT, padx=(0, 6))
    ttk.Button(buttons_frame, text="Add folder (recursive)", command=add_folder_recursive).pack(side=tk.LEFT, padx=(0, 6))
    ttk.Button(buttons_frame, text="Remove selected", command=remove_selected_files).pack(side=tk.LEFT, padx=(0, 6))
    ttk.Button(buttons_frame, text="Clear", command=clear_files).pack(side=tk.LEFT)

    output_frame = ttk.Frame(encode_tab)
    output_frame.pack(fill=tk.X, padx=10, pady=(6, 10))

    ttk.Label(output_frame, text="Output FCA file:").pack(anchor="w")
    encode_output_var = tk.StringVar()
    encode_output_entry = ttk.Entry(output_frame, textvariable=encode_output_var)
    encode_output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=(4, 0))

    def choose_encode_output():
        output_file = filedialog.asksaveasfilename(
            title="Choose output FCA file",
            defaultextension=".fca",
            filetypes=[("FCA files", "*.fca"), ("All files", "*.*")],
        )
        if output_file:
            encode_output_var.set(output_file)

    ttk.Button(output_frame, text="Browse", command=choose_encode_output).pack(side=tk.LEFT, padx=(6, 0), pady=(4, 0))

    def encode_from_gui():
        input_files = list(input_listbox.get(0, tk.END))
        output_file = encode_output_var.get().strip()

        if not input_files:
            messagebox.showerror("Encode", "Please add at least one input file.")
            return
        if not output_file:
            messagebox.showerror("Encode", "Please choose an output FCA file.")
            return

        try:
            encode_fca_from_sources(output_file=output_file, input_files=input_files)
            status_var.set(f"Created archive: {output_file}")
            messagebox.showinfo("Encode", f"Archive created successfully:\n{output_file}")
        except Exception as e:
            status_var.set("Encode failed")
            messagebox.showerror("Encode", f"Error: {e}")

    ttk.Button(encode_tab, text="Create FCA archive", command=encode_from_gui).pack(anchor="e", padx=10, pady=(0, 10))

    # Decode tab
    decode_tab = ttk.Frame(notebook)
    notebook.add(decode_tab, text="Decode")

    decode_input_frame = ttk.Frame(decode_tab)
    decode_input_frame.pack(fill=tk.X, padx=10, pady=(10, 8))

    ttk.Label(decode_input_frame, text="Input FCA file:").pack(anchor="w")
    decode_input_var = tk.StringVar()
    decode_input_entry = ttk.Entry(decode_input_frame, textvariable=decode_input_var)
    decode_input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=(4, 0))

    def choose_decode_input():
        input_file = filedialog.askopenfilename(
            title="Choose input FCA file",
            filetypes=[("FCA files", "*.fca"), ("All files", "*.*")],
        )
        if input_file:
            decode_input_var.set(input_file)

    ttk.Button(decode_input_frame, text="Browse", command=choose_decode_input).pack(side=tk.LEFT, padx=(6, 0), pady=(4, 0))

    decode_output_frame = ttk.Frame(decode_tab)
    decode_output_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

    ttk.Label(decode_output_frame, text="Output directory:").pack(anchor="w")
    decode_output_var = tk.StringVar()
    decode_output_entry = ttk.Entry(decode_output_frame, textvariable=decode_output_var)
    decode_output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=(4, 0))

    def choose_decode_output():
        output_dir = filedialog.askdirectory(title="Choose output directory")
        if output_dir:
            decode_output_var.set(output_dir)

    ttk.Button(decode_output_frame, text="Browse", command=choose_decode_output).pack(side=tk.LEFT, padx=(6, 0), pady=(4, 0))

    def decode_from_gui():
        input_file = decode_input_var.get().strip()
        output_dir = decode_output_var.get().strip()

        if not input_file:
            messagebox.showerror("Decode", "Please choose an input FCA file.")
            return
        if not output_dir:
            messagebox.showerror("Decode", "Please choose an output directory.")
            return

        try:
            decode_fca(input_file, output_dir)
            status_var.set(f"Extracted files to: {output_dir}")
            messagebox.showinfo("Decode", f"Archive extracted successfully:\n{output_dir}")
        except Exception as e:
            status_var.set("Decode failed")
            messagebox.showerror("Decode", f"Error: {e}")

    ttk.Button(decode_tab, text="Extract FCA archive", command=decode_from_gui).pack(anchor="e", padx=10, pady=(0, 10))

    status_bar = ttk.Label(root, textvariable=status_var, anchor="w")
    status_bar.pack(fill=tk.X, padx=10, pady=(0, 10))

    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Unified FCA encoder/decoder tool (CLI + GUI)")
    parser.add_argument("--gui", action="store_true", help="Launch GUI mode")

    subparsers = parser.add_subparsers(dest="command")

    encode_parser = subparsers.add_parser("encode", help="Create FCA archive from input files")
    encode_parser.add_argument(
        "--output-file",
        required=True,
        metavar="<file>",
        help="Output FCA file path",
    )
    encode_parser.add_argument(
        "--input-files",
        nargs="+",
        metavar="<file>",
        help="Input file(s) to include in the archive",
    )
    encode_parser.add_argument(
        "--input-dirs",
        nargs="+",
        metavar="<dir>",
        help="Input directory(ies) to search recursively for files",
    )

    decode_parser = subparsers.add_parser("decode", help="Extract files from FCA archive")
    decode_parser.add_argument(
        "--input-file",
        required=True,
        metavar="<file>",
        help="Input FCA file path",
    )
    decode_parser.add_argument(
        "--output-dir",
        required=True,
        metavar="<dir>",
        help="Output directory for extracted files",
    )

    args = parser.parse_args()

    if args.gui or args.command is None:
        run_gui()
        return

    try:
        if args.command == "encode":
            if not args.input_files and not args.input_dirs:
                raise ValueError("Provide at least one of --input-files or --input-dirs")
            encode_fca_from_sources(
                output_file=args.output_file,
                input_files=args.input_files,
                input_dirs=args.input_dirs,
            )
        elif args.command == "decode":
            decode_fca(args.input_file, args.output_dir)
        else:
            parser.print_help()
            os.sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=os.sys.stderr)
        os.sys.exit(1)


if __name__ == "__main__":
    main()
