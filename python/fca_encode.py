#!/usr/bin/env python3
"""
FCA Encoder - Creates FCA archives from directory contents.

Usage:
    python fca_encode.py <input_directory> <output_file>
"""

import argparse
import struct
import os
from pathlib import Path


def encode_fca(input_dir, output_file):
    """
    Recursively concatenate all files in input_dir into an FCA archive.
    
    Args:
        input_dir: Path to input directory
        output_file: Path to output FCA file
    """
    input_path = Path(input_dir)
    output_path = Path(output_file)
    
    if not input_path.is_dir():
        raise ValueError(f"Input path is not a directory: {input_dir}")
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Collect all files recursively
    files = []
    for root, dirs, filenames in os.walk(input_path):
        for filename in filenames:
            file_path = Path(root) / filename
            files.append(file_path)
    
    # Sort files for consistent output
    files.sort()
    
    with open(output_path, 'wb') as f:
        # Write global header
        # Magic bytes: "FCA"
        f.write(b'FCA')
        # Version: 1
        f.write(struct.pack('>B', 1))
        
        # Write each embedded file
        for file_path in files:
            # Read file content
            with open(file_path, 'rb') as file_content:
                content = file_content.read()
            
            # Calculate sizes
            header_size = 2  # Version 1 header: 2 bytes (file type + reserved)
            embedded_size = len(content)
            total_size = 2 + header_size + embedded_size  # 2 bytes for header_size field
            
            # Write total size (4 bytes, big-endian)
            f.write(struct.pack('>I', total_size))
            
            # Write header size (2 bytes, big-endian)
            f.write(struct.pack('>H', header_size))
            
            # Write header bytes (version 1 format)
            # Byte 0: File type (currently 0x00, to be defined later)
            # Byte 1: Reserved (must be 0x00)
            f.write(struct.pack('>BB', 0x00, 0x00))
            
            # Write embedded file content
            f.write(content)
    
    print(f"Created FCA archive: {output_path}")
    print(f"Embedded {len(files)} files")


def main():
    parser = argparse.ArgumentParser(
        description='Encode files from a directory into an FCA archive'
    )
    parser.add_argument(
        'input_dir',
        help='Input directory containing files to archive'
    )
    parser.add_argument(
        'output_file',
        help='Output FCA file path'
    )
    
    args = parser.parse_args()
    
    try:
        encode_fca(args.input_dir, args.output_file)
    except Exception as e:
        print(f"Error: {e}", file=os.sys.stderr)
        os.sys.exit(1)


if __name__ == '__main__':
    main()
