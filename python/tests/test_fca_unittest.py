#!/usr/bin/env python3
"""
Unit tests for FCA encode and decode functions (unittest version).
Run with: python3 -m unittest tests.test_fca_unittest
"""

import unittest
import struct
import hashlib
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add parent directory to path to import fca_encode and fca_decode
sys.path.insert(0, str(Path(__file__).parent.parent))
from fca_encode import encode_fca, detect_file_type
from fca_decode import decode_fca
from fca_tool import encode_fca_from_sources
from constants import (
    FILE_TYPE_AMIIBO_V2,
    FILE_TYPE_AMIIBO_V3,
)


class TestFCAEncode(unittest.TestCase):
    """Tests for FCA encoding."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_data_dir = Path(__file__).parent / 'test_data'
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_encode_single_file(self):
        """Test encoding a single file."""
        # Create a temp directory with a single file
        single_file_dir = Path(self.temp_dir) / 'single_file'
        single_file_dir.mkdir()
        shutil.copy(self.test_data_dir / 'file1.txt', single_file_dir / 'file1.txt')
        
        output_file = Path(self.temp_dir) / 'output.fca'
        encode_fca([str(single_file_dir)], str(output_file))
        
        self.assertTrue(output_file.exists())
        
        # Verify file format
        with open(output_file, 'rb') as f:
            # Check magic bytes
            magic = f.read(3)
            self.assertEqual(magic, b'FCA')
            
            # Check version
            version = struct.unpack('>B', f.read(1))[0]
            self.assertEqual(version, 1)
            
            # Read embedded file entry
            total_size = struct.unpack('>I', f.read(4))[0]
            header_size = struct.unpack('>H', f.read(2))[0]
            self.assertEqual(header_size, 2)  # Version 1 header is 2 bytes
            
            # Read header bytes
            header_bytes = f.read(header_size)
            self.assertEqual(len(header_bytes), 2)
            self.assertEqual(header_bytes[0], 0x00)  # File type (currently 0)
            self.assertEqual(header_bytes[1], 0x00)  # Reserved
            
            # Read content
            content = f.read(total_size - 2 - header_size)
            # Read the actual file to get expected content
            with open(self.test_data_dir / 'file1.txt', 'rb') as orig_file:
                expected_content = orig_file.read()
            self.assertEqual(content, expected_content)
            
            # Verify total size calculation
            self.assertEqual(total_size, 2 + header_size + len(expected_content))
    
    def test_encode_multiple_files(self):
        """Test encoding multiple files from a directory."""
        output_file = Path(self.temp_dir) / 'output.fca'
        encode_fca([str(self.test_data_dir)], str(output_file))
        
        self.assertTrue(output_file.exists())
        
        # Count files in test_data directory (recursively)
        file_count = sum(1 for _ in self.test_data_dir.rglob('*') if _.is_file() and not _.name.startswith('.'))
        
        # Verify file format and count embedded files
        with open(output_file, 'rb') as f:
            # Check magic bytes
            magic = f.read(3)
            self.assertEqual(magic, b'FCA')
            
            # Check version
            version = struct.unpack('>B', f.read(1))[0]
            self.assertEqual(version, 1)
            
            # Count embedded files
            embedded_count = 0
            while True:
                total_size_bytes = f.read(4)
                if len(total_size_bytes) < 4:
                    break
                
                total_size = struct.unpack('>I', total_size_bytes)[0]
                header_size = struct.unpack('>H', f.read(2))[0]
                self.assertEqual(header_size, 2)  # Version 1 header is 2 bytes
                
                # Read header bytes
                f.read(header_size)
                
                embedded_size = total_size - 2 - header_size
                f.read(embedded_size)
                embedded_count += 1
            
            self.assertEqual(embedded_count, file_count)
    
    def test_encode_empty_file(self):
        """Test encoding an empty file."""
        # Create a temp directory with an empty file
        empty_file_dir = Path(self.temp_dir) / 'empty_file'
        empty_file_dir.mkdir()
        shutil.copy(self.test_data_dir / 'empty.txt', empty_file_dir / 'empty.txt')
        
        output_file = Path(self.temp_dir) / 'output.fca'
        encode_fca([str(empty_file_dir)], str(output_file))
        
        self.assertTrue(output_file.exists())
        
        with open(output_file, 'rb') as f:
            magic = f.read(3)
            self.assertEqual(magic, b'FCA')
            
            version = struct.unpack('>B', f.read(1))[0]
            self.assertEqual(version, 1)
            
            # Read embedded file entry
            total_size = struct.unpack('>I', f.read(4))[0]
            header_size = struct.unpack('>H', f.read(2))[0]
            self.assertEqual(header_size, 2)  # Version 1 header is 2 bytes
            
            # Read header bytes
            header_bytes = f.read(header_size)
            self.assertEqual(len(header_bytes), 2)
            
            # Empty file should have total_size = 2 (header_size field) + 2 (header bytes) = 4
            self.assertEqual(total_size, 4)
            
            # Should be at EOF
            remaining = f.read(1)
            self.assertEqual(len(remaining), 0)
    
    def test_encode_invalid_input(self):
        """Test encoding with invalid input directory."""
        output_file = Path(self.temp_dir) / 'output.fca'
        
        with self.assertRaises(ValueError):
            encode_fca([str(output_file)], str(output_file))

    def test_encode_exclude_pattern(self):
        """Test that exclude_pattern excludes files whose relative path contains the string."""
        src_dir = Path(self.temp_dir) / 'src'
        src_dir.mkdir()
        (src_dir / 'subdir').mkdir()
        shutil.copy(self.test_data_dir / 'file1.txt', src_dir / 'top.txt')
        shutil.copy(self.test_data_dir / 'file2.bin', src_dir / 'subdir' / 'nested.bin')

        output_file = Path(self.temp_dir) / 'output.fca'
        encode_fca([str(src_dir)], str(output_file), exclude_pattern='subdir')

        self.assertTrue(output_file.exists())
        with open(output_file, 'rb') as f:
            f.read(4)  # magic + version
            count = 0
            while True:
                total_size_bytes = f.read(4)
                if len(total_size_bytes) < 4:
                    break
                total_size = struct.unpack('>I', total_size_bytes)[0]
                header_size = struct.unpack('>H', f.read(2))[0]
                f.read(header_size)
                embedded_size = total_size - 2 - header_size
                f.read(embedded_size)
                count += 1
        self.assertEqual(count, 1)
        with open(output_file, 'rb') as f:
            f.read(4)
            total_size = struct.unpack('>I', f.read(4))[0]
            header_size = struct.unpack('>H', f.read(2))[0]
            f.read(header_size)
            content = f.read(total_size - 2 - header_size)
        with open(self.test_data_dir / 'file1.txt', 'rb') as f:
            expected = f.read()
        self.assertEqual(content, expected)


class TestFCADecode(unittest.TestCase):
    """Tests for FCA decoding."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_data_dir = Path(__file__).parent / 'test_data'
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_decode_single_file(self):
        """Test decoding a single file archive."""
        # Create a temp directory with a single file
        single_file_dir = Path(self.temp_dir) / 'single_file'
        single_file_dir.mkdir()
        shutil.copy(self.test_data_dir / 'file1.txt', single_file_dir / 'file1.txt')
        
        # Create FCA file
        fca_file = Path(self.temp_dir) / 'test.fca'
        encode_fca([str(single_file_dir)], str(fca_file))
        
        # Decode it
        output_dir = Path(self.temp_dir) / 'output'
        decode_fca(str(fca_file), str(output_dir))
        
        # Verify output
        self.assertTrue(output_dir.is_dir())
        
        # Verify content
        expected_content = b'Hello, World!\nThis is a test file.\n'
        expected_md5 = hashlib.md5(expected_content).hexdigest()
        
        extracted_file = output_dir / expected_md5
        self.assertTrue(extracted_file.exists())
        
        with open(extracted_file, 'rb') as f:
            self.assertEqual(f.read(), expected_content)
    
    def test_decode_multiple_files(self):
        """Test decoding multiple files."""
        # Create FCA file
        fca_file = Path(self.temp_dir) / 'test.fca'
        encode_fca([str(self.test_data_dir)], str(fca_file))
        
        # Decode it
        output_dir = Path(self.temp_dir) / 'output'
        decode_fca(str(fca_file), str(output_dir))
        
        # Count files in test_data
        test_files = [f for f in self.test_data_dir.rglob('*') if f.is_file() and not f.name.startswith('.')]
        
        # Verify all files were extracted
        extracted_files = list(output_dir.iterdir())
        self.assertEqual(len(extracted_files), len(test_files))
        
        # Verify MD5 hashes match
        for test_file in test_files:
            with open(test_file, 'rb') as f:
                content = f.read()
            expected_md5 = hashlib.md5(content).hexdigest()
            self.assertTrue((output_dir / expected_md5).exists())
    
    def test_decode_empty_file(self):
        """Test decoding an archive with an empty file."""
        # Create a temp directory with an empty file
        empty_file_dir = Path(self.temp_dir) / 'empty_file'
        empty_file_dir.mkdir()
        shutil.copy(self.test_data_dir / 'empty.txt', empty_file_dir / 'empty.txt')
        
        # Create FCA file with empty file
        fca_file = Path(self.temp_dir) / 'test.fca'
        encode_fca([str(empty_file_dir)], str(fca_file))
        
        # Decode it
        output_dir = Path(self.temp_dir) / 'output'
        decode_fca(str(fca_file), str(output_dir))
        
        # Verify empty file was extracted
        expected_md5 = hashlib.md5(b'').hexdigest()
        extracted_file = output_dir / expected_md5
        self.assertTrue(extracted_file.exists())
        
        with open(extracted_file, 'rb') as f:
            self.assertEqual(f.read(), b'')
    
    def test_decode_invalid_magic(self):
        """Test decoding with invalid magic bytes."""
        invalid_file = Path(self.temp_dir) / 'invalid.fca'
        with open(invalid_file, 'wb') as f:
            f.write(b'XXX')  # Invalid magic
            f.write(struct.pack('>B', 1))
        
        output_dir = Path(self.temp_dir) / 'output'
        
        with self.assertRaises(ValueError):
            decode_fca(str(invalid_file), str(output_dir))
    
    def test_decode_nonexistent_file(self):
        """Test decoding a nonexistent file."""
        output_dir = Path(self.temp_dir) / 'output'
        
        with self.assertRaises(ValueError):
            decode_fca('/nonexistent/file.fca', str(output_dir))


class TestFCARoundTrip(unittest.TestCase):
    """Tests for round-trip encoding and decoding."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_data_dir = Path(__file__).parent / 'test_data'
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_round_trip_single_file(self):
        """Test encoding and then decoding a single file."""
        # Create a temp directory with a single file
        single_file_dir = Path(self.temp_dir) / 'single_file'
        single_file_dir.mkdir()
        shutil.copy(self.test_data_dir / 'file1.txt', single_file_dir / 'file1.txt')
        
        # Encode
        fca_file = Path(self.temp_dir) / 'test.fca'
        encode_fca([str(single_file_dir)], str(fca_file))
        
        # Decode
        output_dir = Path(self.temp_dir) / 'output'
        decode_fca(str(fca_file), str(output_dir))
        
        # Verify content matches
        original_content = b'Hello, World!\nThis is a test file.\n'
        expected_md5 = hashlib.md5(original_content).hexdigest()
        
        extracted_file = output_dir / expected_md5
        with open(extracted_file, 'rb') as f:
            self.assertEqual(f.read(), original_content)
    
    def test_round_trip_multiple_files(self):
        """Test encoding and decoding multiple files."""
        # Encode
        fca_file = Path(self.temp_dir) / 'test.fca'
        encode_fca([str(self.test_data_dir)], str(fca_file))
        
        # Decode
        output_dir = Path(self.temp_dir) / 'output'
        decode_fca(str(fca_file), str(output_dir))
        
        # Verify all files match
        for test_file in self.test_data_dir.rglob('*'):
            if not test_file.is_file() or test_file.name.startswith('.'):
                continue
            
            with open(test_file, 'rb') as f:
                original_content = f.read()
            
            expected_md5 = hashlib.md5(original_content).hexdigest()
            extracted_file = output_dir / expected_md5
            
            self.assertTrue(extracted_file.exists(), f"File {test_file} not found in output")
            
            with open(extracted_file, 'rb') as f:
                self.assertEqual(f.read(), original_content)
    
    def test_round_trip_binary_files(self):
        """Test round-trip with binary files."""
        # Create a temp directory with a binary file
        binary_file_dir = Path(self.temp_dir) / 'binary_file'
        binary_file_dir.mkdir()
        shutil.copy(self.test_data_dir / 'file2.bin', binary_file_dir / 'file2.bin')
        
        # Encode binary file
        fca_file = Path(self.temp_dir) / 'test.fca'
        encode_fca([str(binary_file_dir)], str(fca_file))
        
        # Decode
        output_dir = Path(self.temp_dir) / 'output'
        decode_fca(str(fca_file), str(output_dir))
        
        # Verify binary content matches
        with open(self.test_data_dir / 'file2.bin', 'rb') as f:
            original_content = f.read()
        expected_md5 = hashlib.md5(original_content).hexdigest()
        
        extracted_file = output_dir / expected_md5
        self.assertTrue(extracted_file.exists(), f"File with MD5 {expected_md5} not found")
        with open(extracted_file, 'rb') as f:
            self.assertEqual(f.read(), original_content)
    
    def test_round_trip_amiibo_files(self):
        """Test round-trip with amiibo binary fixtures (test-amiibo-v2, test-amiibo-v3)."""
        amiibo_dir = Path(self.temp_dir) / 'amiibo'
        amiibo_dir.mkdir()
        for name in ('test-amiibo-v2.bin', 'test-amiibo-v3.bin'):
            shutil.copy(self.test_data_dir / name, amiibo_dir / name)
        fca_file = Path(self.temp_dir) / 'test.fca'
        encode_fca([str(amiibo_dir)], str(fca_file))
        output_dir = Path(self.temp_dir) / 'output'
        decode_fca(str(fca_file), str(output_dir))
        for name in ('test-amiibo-v2.bin', 'test-amiibo-v3.bin'):
            with open(self.test_data_dir / name, 'rb') as f:
                original_content = f.read()
            expected_md5 = hashlib.md5(original_content).hexdigest()
            extracted_file = output_dir / expected_md5
            self.assertTrue(extracted_file.exists(), f"File {name} (MD5 {expected_md5}) not found")
            with open(extracted_file, 'rb') as f:
                self.assertEqual(f.read(), original_content)


class TestFCAToolParity(unittest.TestCase):
    """Parity tests between standalone scripts and unified fca_tool behavior."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_data_dir = Path(__file__).parent / 'test_data'

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_tool_encode_decode_matches_standalone(self):
        """Ensure tool encode/decode behavior matches standalone encode/decode."""
        encode_output = Path(self.temp_dir) / 'standalone.fca'
        tool_output = Path(self.temp_dir) / 'tool.fca'

        encode_fca([str(self.test_data_dir)], str(encode_output))
        encode_fca_from_sources(output_file=str(tool_output), input_dirs=[str(self.test_data_dir)])

        with open(encode_output, 'rb') as f:
            standalone_bytes = f.read()
        with open(tool_output, 'rb') as f:
            tool_bytes = f.read()

        self.assertEqual(standalone_bytes, tool_bytes)
        self.assertGreaterEqual(standalone_bytes.count(b'FCA'), 1)
        self.assertEqual(standalone_bytes[:3], b'FCA')

        decode_output_standalone = Path(self.temp_dir) / 'decode_standalone'
        decode_output_tool = Path(self.temp_dir) / 'decode_tool'

        decode_fca(str(encode_output), str(decode_output_standalone))
        decode_fca(str(tool_output), str(decode_output_tool))

        standalone_names = sorted(p.name for p in decode_output_standalone.iterdir() if p.is_file())
        tool_names = sorted(p.name for p in decode_output_tool.iterdir() if p.is_file())
        self.assertEqual(standalone_names, tool_names)


class TestFCAFormat(unittest.TestCase):
    """Tests for FCA file format correctness (including embedded file types)."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_data_dir = Path(__file__).parent / 'test_data'
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_embedded_file_types_match_detection(self):
        """Verify each embedded file's type byte matches encoder detection."""
        output_file = Path(self.temp_dir) / 'output.fca'
        encode_fca([str(self.test_data_dir)], str(output_file))
        with open(output_file, 'rb') as f:
            self.assertEqual(f.read(3), b'FCA')
            version = struct.unpack('>B', f.read(1))[0]
            self.assertEqual(version, 1)
            index = 0
            while True:
                total_size_bytes = f.read(4)
                if len(total_size_bytes) < 4:
                    break
                total_size = struct.unpack('>I', total_size_bytes)[0]
                header_size = struct.unpack('>H', f.read(2))[0]
                header_bytes = f.read(header_size)
                embedded_size = total_size - 2 - header_size
                content = f.read(embedded_size)
                file_type = header_bytes[0]
                reserved = header_bytes[1]
                self.assertEqual(reserved, 0x00, f"Embedded file {index + 1}: reserved byte must be 0")
                expected_type = detect_file_type(content)
                self.assertEqual(
                    file_type, expected_type,
                    f"Embedded file {index + 1}: stored type {file_type} != detected type {expected_type}"
                )
                index += 1
            self.assertGreater(index, 0, "Expected at least one embedded file")
    
    def test_amiibo_fixtures_have_correct_types(self):
        """Verify test-amiibo-v2.bin and test-amiibo-v3.bin get types 1 and 2."""
        amiibo_dir = Path(self.temp_dir) / 'amiibo'
        amiibo_dir.mkdir()
        shutil.copy(self.test_data_dir / 'test-amiibo-v2.bin', amiibo_dir / 'test-amiibo-v2.bin')
        shutil.copy(self.test_data_dir / 'test-amiibo-v3.bin', amiibo_dir / 'test-amiibo-v3.bin')
        output_file = Path(self.temp_dir) / 'output.fca'
        encode_fca([str(amiibo_dir)], str(output_file))
        with open(output_file, 'rb') as f:
            self.assertEqual(f.read(3), b'FCA')
            self.assertEqual(struct.unpack('>B', f.read(1))[0], 1)
            # First embedded file (v2)
            total_size = struct.unpack('>I', f.read(4))[0]
            header_size = struct.unpack('>H', f.read(2))[0]
            header_bytes = f.read(header_size)
            f.read(total_size - 2 - header_size)
            self.assertEqual(header_bytes[0], FILE_TYPE_AMIIBO_V2, "test-amiibo-v2.bin should have type Amiibo v2 (1)")
            self.assertEqual(header_bytes[1], 0x00)
            # Second embedded file (v3)
            total_size = struct.unpack('>I', f.read(4))[0]
            header_size = struct.unpack('>H', f.read(2))[0]
            header_bytes = f.read(header_size)
            f.read(total_size - 2 - header_size)
            self.assertEqual(header_bytes[0], FILE_TYPE_AMIIBO_V3, "test-amiibo-v3.bin should have type Amiibo v3 (2)")
            self.assertEqual(header_bytes[1], 0x00)


if __name__ == '__main__':
    unittest.main()
