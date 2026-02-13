#!/usr/bin/env python3
"""
FCA Decoder - Extracts embedded files from FCA archives.

Usage:
    python fca_decode.py --input-file <file> --output-dir <dir>
"""

import argparse
import struct
import os
import hashlib
from pathlib import Path
from constants import (
    FILE_TYPE_UNKNOWN,
    FILE_TYPE_AMIIBO_V2,
    FILE_TYPE_AMIIBO_V3,
    FILE_TYPE_SKYLANDER,
    FILE_TYPE_DISNEY_INFINITY,
    FILE_TYPE_LEGO_DIMENSIONS,
)

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


def decode_fca(input_file, output_dir):
    """
    Extract all embedded files from an FCA archive.
    Files are named by their MD5 hash.
    
    Args:
        input_file: Path to input FCA file
        output_dir: Path to output directory
    """
    input_path = Path(input_file)
    output_path = Path(output_dir)
    
    if not input_path.is_file():
        raise ValueError(f"Input file does not exist: {input_file}")
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    with open(input_path, 'rb') as f:
        # Read and verify magic bytes
        magic = f.read(3)
        if magic != b'FCA':
            raise ValueError(f"Invalid FCA file: magic bytes '{magic}' != 'FCA'")
        
        # Read version
        version = struct.unpack('>B', f.read(1))[0]
        print(f"FCA version: {version}")
        
        file_count = 0
        
        # Read embedded files until EOF
        while True:
            # Read total size (4 bytes, big-endian)
            total_size_bytes = f.read(4)
            if len(total_size_bytes) < 4:
                # EOF reached
                break
            
            total_size = struct.unpack('>I', total_size_bytes)[0]
            
            # Read header size (2 bytes, big-endian)
            header_size = struct.unpack('>H', f.read(2))[0]
            
            # Read header bytes (if any)
            file_type_name = "Unknown"
            if header_size > 0:
                header_bytes = f.read(header_size)
                if len(header_bytes) < header_size:
                    raise ValueError(f"Unexpected EOF while reading header for embedded file {file_count + 1}")
                
                # For version 1, header is 2 bytes: file_type (byte 0) and reserved (byte 1)
                if version == 1 and header_size == 2:
                    file_type = header_bytes[0]
                    reserved = header_bytes[1]
                    # Reserved byte must be 0x00
                    if reserved != 0x00:
                        print(f"Warning: Reserved byte is not 0x00 in embedded file {file_count + 1}")
                    file_type_name = get_file_type_name(file_type)
            
            # Calculate embedded file size
            embedded_size = total_size - 2 - header_size
            
            # Read embedded file content
            content = f.read(embedded_size)
            
            if len(content) < embedded_size:
                raise ValueError(f"Unexpected EOF while reading embedded file {file_count + 1}")
            
            # Compute MD5 hash
            md5_hash = hashlib.md5(content).hexdigest()
            
            # Write file with MD5 hash as filename
            output_file = output_path / md5_hash
            with open(output_file, 'wb') as out_file:
                out_file.write(content)
            
            file_count += 1
            if version == 1 and header_size == 2:
                print(f"Extracted file {file_count}: {md5_hash} ({embedded_size} bytes, type: {file_type_name})")
            else:
                print(f"Extracted file {file_count}: {md5_hash} ({embedded_size} bytes)")
    
    print(f"\nExtracted {file_count} files to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Decode an FCA archive and extract embedded files'
    )
    parser.add_argument(
        '--input-file',
        required=True,
        metavar='<file>',
        help='Input FCA file path'
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        metavar='<dir>',
        help='Output directory for extracted files'
    )
    
    args = parser.parse_args()
    
    try:
        decode_fca(args.input_file, args.output_dir)
    except Exception as e:
        print(f"Error: {e}", file=os.sys.stderr)
        os.sys.exit(1)


if __name__ == '__main__':
    main()
