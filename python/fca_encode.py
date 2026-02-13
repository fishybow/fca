#!/usr/bin/env python3
"""
FCA Encoder - Creates FCA archives from directory contents.

Usage:
    python fca_encode.py --output-file <file> --input-dirs <dir1> [<dir2> ...]
"""

import argparse
import struct
import os
from pathlib import Path
from constants import (
    FILE_TYPE_UNKNOWN,
    FILE_TYPE_AMIIBO_V2,
    FILE_TYPE_AMIIBO_V3,
    FILE_TYPE_SKYLANDER,
    FILE_TYPE_DISNEY_INFINITY,
    FILE_TYPE_LEGO_DIMENSIONS,
)


def detect_file_type(content):
    """Auto-detect file type based on size and content."""
    size = len(content)

    # Lego Dimensions detection
    # Signature observed across all tested Lego Dimensions BIN files.
    if size == 180:
        if content[0] == 0x04 and content[7] == 0x80 and content[8:144] == (b'\x00' * 136):
            return FILE_TYPE_LEGO_DIMENSIONS

    # Disney Infinity detection
    # Signature observed across all tested Disney Infinity BIN files.
    if size == 320:
        if (
            content[0] == 0x04
            and content[7:11] == b'\x89\x44\x00\xC2'
            and content[54:57] == b'\x17\x87\x8E'
        ):
            return FILE_TYPE_DISNEY_INFINITY

    # Skylanders detection
    # Common signatures observed across 1024-byte and 2048-byte Skylanders BIN files.
    if size in (1024, 2048):
        if content[5:8] == b'\x81\x01\x0F' and content[54:58] == b'\x0F\x0F\x0F\x69':
            return FILE_TYPE_SKYLANDER
    
    # Amiibo detection
    if size in (532, 540, 572):
        # Check for NTAG215 signature
        # Byte 0x00C-0x00F: Capability Container (CC)
        cc = content[0x0C:0x10]
        if cc == b'\xF1\x10\xFF\xEE':  # NTAG215 CC
            return FILE_TYPE_AMIIBO_V2
    
    elif size == 2048:
        # NTAG I2C Plus 2K (Kirby)
        cc = content[0x0C:0x10]
        if cc == b'\xF1\x10\xFF\xEE':  # Check if amiibo-like
            return FILE_TYPE_AMIIBO_V3
    
    return FILE_TYPE_UNKNOWN

def encode_fca(input_dirs, output_file):
    """
    Recursively concatenate all files from input_dirs into an FCA archive.
    
    Args:
        input_dirs: Paths to input directories
        output_file: Path to output FCA file
    """
    output_path = Path(output_file)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Collect all files recursively from each input dir (skip hidden files and directories)
    files = []
    for input_dir in input_dirs:
        input_path = Path(input_dir)
        if not input_path.is_dir():
            raise ValueError(f"Input path is not a directory: {input_dir}")
        for root, dirs, filenames in os.walk(input_path):
            # Don't descend into hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for filename in filenames:
                if filename.startswith('.'):
                    continue
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
            # Byte 0: File type (0=Unknown, 1=amiibo v2, 2=amiibo v3, 3=Skylander, 4=Disney Infinity, 5=Lego Dimensions)
            # Byte 1: Reserved (must be 0x00)
    
            # Auto-detect file type
            file_type = detect_file_type(content)
            f.write(struct.pack('>BB', file_type, 0x00))
            
            # Write embedded file content
            f.write(content)
    
    print(f"Created FCA archive: {output_path}")
    print(f"Embedded {len(files)} files")


def main():
    parser = argparse.ArgumentParser(
        description='Encode files from directories into an FCA archive'
    )
    parser.add_argument(
        '--output-file',
        required=True,
        metavar='<file>',
        help='Output FCA file path'
    )
    parser.add_argument(
        '--input-dirs',
        required=True,
        nargs='+',
        metavar='<dir>',
        help='Input directory(ies) containing files to archive'
    )
    
    args = parser.parse_args()
    
    try:
        encode_fca(args.input_dirs, args.output_file)
    except Exception as e:
        print(f"Error: {e}", file=os.sys.stderr)
        os.sys.exit(1)


if __name__ == '__main__':
    main()
