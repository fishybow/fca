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
import json
import sys
from pathlib import Path
import requests

# Enable UTF-8 output on Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from constants import (
    FILE_TYPE_UNKNOWN,
    FILE_TYPE_AMIIBO_V2,
    FILE_TYPE_AMIIBO_V3,
    FILE_TYPE_SKYLANDER,
    FILE_TYPE_DISNEY_INFINITY,
    FILE_TYPE_LEGO_DIMENSIONS,
)

# Global cache for amiibo database
_AMIIBO_DATABASE = None
_DATABASE_LOAD_ATTEMPTED = False

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


def load_amiibo_database(custom_database_path=None):
    """
    Load the amiibo database from local file if available.
    
    Args:
        custom_database_path: Optional path to a custom database file. If provided, this path is used.
    
    Returns:
        Dictionary with amiibo data, or None if file not found
    """
    global _AMIIBO_DATABASE, _DATABASE_LOAD_ATTEMPTED
    
    # If custom database specified, don't use cache
    if custom_database_path:
        try:
            db_path = Path(custom_database_path)
            if db_path.is_file():
                with open(db_path, 'r', encoding='utf-8') as f:
                    database = json.load(f)
                    print(f"Loaded amiibo database from: {db_path}")
                    return database
            else:
                print(f"Custom database file not found: {db_path}")
                return None
        except Exception as e:
            print(f"Error loading custom database: {e}")
            return None
    
    # Use cached result if already attempted
    if _DATABASE_LOAD_ATTEMPTED:
        return _AMIIBO_DATABASE
    
    _DATABASE_LOAD_ATTEMPTED = True
    
    try:
        # Try multiple possible locations for the database file
        possible_paths = [
            Path(__file__).with_name("amiibo_database.json"),
            Path.cwd() / "amiibo_database.json",
            Path.cwd() / "python" / "amiibo_database.json",
        ]
        
        for db_path in possible_paths:
            if db_path.is_file():
                with open(db_path, 'r', encoding='utf-8') as f:
                    _AMIIBO_DATABASE = json.load(f)
                    print(f"Loaded amiibo database from: {db_path}")
                    return _AMIIBO_DATABASE
    except Exception as e:
        # Silently continue if database can't be loaded
        pass
    
    return None


def extract_amiibo_id(content):
    """
    Extract amiibo ID (head and tail) from file content.
    For NTAG215 amiibo chips, the ID is stored in the user data section.
    Head: bytes 0x54-0x57 (4 bytes = 8 hex chars)
    Tail: bytes 0x58-0x5B (4 bytes = 8 hex chars)
    
    Args:
        content: The file content bytes
        
    Returns:
        A tuple of (head_id, tail_id) as hex strings, or (None, None) if not found
    """
    if len(content) < 0x5C:  # Need at least 0x5C bytes
        return None, None
    
    try:
        head_bytes = content[0x54:0x58]
        tail_bytes = content[0x58:0x5C]
        
        # Ensure tail is not all zeros (some amiibo have head=00000000 but valid tail)
        if any(b != 0 for b in tail_bytes):
            head_id = head_bytes.hex()
            tail_id = tail_bytes.hex()
            return head_id, tail_id
    except Exception:
        pass
    
    return None, None


def lookup_amiibo_data(head_id=None, tail_id=None, custom_database_path=None):
    """
    Lookup amiibo information from local database only.
    No online API calls - uses only the cached local database.
    
    Args:
        head_id: The amiibo head ID as a hex string
        tail_id: The amiibo tail ID as a hex string
        custom_database_path: Optional path to a custom database file
        
    Returns:
        A tuple of (series_name, amiibo_type, amiibo_name, lookup_method) 
        or (None, None, None, None) if not found
        lookup_method is "database_head+tail", "database_tail", or "not_found"
    """
    if not head_id or not tail_id:
        return None, None, None, None
    
    # Try local database only (no online API calls)
    db = load_amiibo_database(custom_database_path=custom_database_path)
    if db:
        amiibo_list = db.get("amiibo", [])
        
        # Search by head+tail in database
        for amiibo in amiibo_list:
            if amiibo.get("head") == head_id and amiibo.get("tail") == tail_id:
                series_name = amiibo.get("amiiboSeries", "Unknown")
                amiibo_type = amiibo.get("type", "Unknown")
                amiibo_name = amiibo.get("name", "Unknown")
                return series_name, amiibo_type, amiibo_name, "database_head+tail"
        
        # Search by tail only in database
        for amiibo in amiibo_list:
            if amiibo.get("tail") == tail_id:
                series_name = amiibo.get("amiiboSeries", "Unknown")
                amiibo_type = amiibo.get("type", "Unknown")
                amiibo_name = amiibo.get("name", "Unknown")
                return series_name, amiibo_type, amiibo_name, "database_tail"
    
    # Database not available or amiibo not found - return None (will use MD5 fallback)
    return None, None, None, "not_found"


def sanitize_filename(filename):
    """
    Sanitize a filename by removing or replacing invalid characters.
    
    Args:
        filename: The filename to sanitize
        
    Returns:
        A sanitized filename safe for file systems
    """
    # Replace invalid filename characters (including path separators / and \)
    invalid_chars = '<>:"|?*/\\'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    # Limit filename length to 200 characters for safety
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename


def download_amiibo_database_to_script_dir(force=False):
    """
    Download the amiibo database from amiiboapi.org and save to script directory.
    
    Args:
        force: If True, re-download even if the file already exists
        
    Returns:
        True if successful, False otherwise
    """
    try:
        db_path = Path(__file__).with_name("amiibo_database.json")
        
        # Check if file exists and skip if not forcing
        if db_path.is_file() and not force:
            print(f"Database already exists at: {db_path}")
            return True
        
        print(f"Downloading amiibo database from amiiboapi.org...")
        url = "https://amiiboapi.org/api/amiibo/"
        response = requests.get(url, timeout=30)
        
        if response.status_code != 200:
            print(f"Error: API returned status code {response.status_code}")
            return False
        
        data = response.json()
        amiibo_list = data.get("amiibo", [])
        
        if not amiibo_list:
            print("Error: No amiibo data received from API")
            return False
        
        # Save to file
        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Downloaded {len(amiibo_list)} amiibo entries (~{db_path.stat().st_size / 1024 / 1024:.2f} MB)")
        print(f"Saved to: {db_path}")
        return True
        
    except Exception as e:
        print(f"Error downloading database: {e}")
        return False


def make_unique_filename(output_file):
    """
    Ensure a filename is unique by appending a counter if the file already exists.
    
    Args:
        output_file: Path object for the desired output file
        
    Returns:
        A Path object with a unique filename (counter appended if necessary)
    """
    if not output_file.exists():
        return output_file
    
    # File exists, need to append a counter
    # Split filename and extension
    stem = output_file.stem  # name without extension
    suffix = output_file.suffix  # extension including the dot
    parent = output_file.parent
    
    counter = 1
    while True:
        new_name = f"{stem} ({counter}){suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1


def decode_fca(input_file, output_dir, use_pro_names=False, database_file=None):
    """
    Extract all embedded files from an FCA archive.
    Files are named by their MD5 hash, or by amiibo series/name if available.
    
    Args:
        input_file: Path to input FCA file
        output_dir: Path to output directory
        use_pro_names: If True, use "Pro" naming (no extensions) for amiibo files
        database_file: Optional path to a custom amiibo database JSON file
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
            file_type = FILE_TYPE_UNKNOWN
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
            
            # Determine output filename and directory structure
            output_filename = None
            output_subdir = None
            file_type_for_output = get_file_type_name(file_type)
            
            # Try to get amiibo name if it's an amiibo file
            if file_type in (FILE_TYPE_AMIIBO_V2, FILE_TYPE_AMIIBO_V3):
                head_id, tail_id = extract_amiibo_id(content)
                if head_id and tail_id:
                    series_name, amiibo_type, amiibo_name, lookup_method = lookup_amiibo_data(head_id, tail_id, custom_database_path=database_file)
                    if series_name and amiibo_type and amiibo_name:
                        # Sanitize filenames
                        safe_series = sanitize_filename(series_name)
                        safe_type = sanitize_filename(amiibo_type)
                        safe_name = sanitize_filename(amiibo_name)
                        
                        # Create directory structure: Series/Type/
                        output_subdir = Path(safe_series) / safe_type
                        
                        # Use just the name as the filename
                        output_filename = safe_name
                        
                        if use_pro_names:
                            # Pro naming: no extension
                            pass
                        else:
                            # Add file extension based on file type
                            output_filename += ".bin"
            
            # Fallback to MD5 hash if no amiibo name found
            if output_filename is None:
                md5_hash = hashlib.md5(content).hexdigest()
                output_filename = md5_hash
            
            # Create output file path with subdirectories
            if output_subdir is not None:
                full_output_path = output_path / output_subdir
                full_output_path.mkdir(parents=True, exist_ok=True)
                output_file = full_output_path / output_filename
            else:
                output_file = output_path / output_filename
            
            # Handle duplicate filenames by appending a counter
            output_file = make_unique_filename(output_file)
            
            # Write file
            with open(output_file, 'wb') as out_file:
                out_file.write(content)
            
            file_count += 1
            # Show relative path for better readability
            relative_path = output_file.relative_to(output_path)
            if version == 1 and header_size == 2:
                print(f"Extracted file {file_count}: {relative_path} ({embedded_size} bytes, type: {file_type_for_output})")
            else:
                print(f"Extracted file {file_count}: {relative_path} ({embedded_size} bytes)")
    
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
    parser.add_argument(
        '--pro-names',
        action='store_true',
        help='Use Pro file names (no extensions) for amiibo files'
    )
    
    args = parser.parse_args()
    
    try:
        decode_fca(args.input_file, args.output_dir, use_pro_names=args.pro_names)
    except Exception as e:
        print(f"Error: {e}", file=os.sys.stderr)
        os.sys.exit(1)


if __name__ == '__main__':
    main()
