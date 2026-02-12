#!/usr/bin/env python3
"""
Unit tests for FCA encode and decode functions.
"""

import pytest
import struct
import hashlib
import os
import tempfile
import shutil
from pathlib import Path
import sys

# Add parent directory to path to import fca_encode and fca_decode
sys.path.insert(0, str(Path(__file__).parent.parent))
from fca_encode import encode_fca
from fca_decode import decode_fca


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test output."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def test_data_dir():
    """Path to test data directory."""
    return Path(__file__).parent / 'test_data'


class TestFCAEncode:
    """Tests for FCA encoding."""
    
    def test_encode_single_file(self, temp_dir, test_data_dir):
        """Test encoding a single file."""
        # Create a temp directory with a single file
        single_file_dir = Path(temp_dir) / 'single_file'
        single_file_dir.mkdir()
        shutil.copy(test_data_dir / 'file1.txt', single_file_dir / 'file1.txt')
        
        output_file = Path(temp_dir) / 'output.fca'
        encode_fca(str(single_file_dir), str(output_file))
        
        assert output_file.exists()
        
        # Verify file format
        with open(output_file, 'rb') as f:
            # Check magic bytes
            magic = f.read(3)
            assert magic == b'FCA'
            
            # Check version
            version = struct.unpack('>B', f.read(1))[0]
            assert version == 1
            
            # Read embedded file entry
            total_size = struct.unpack('>I', f.read(4))[0]
            header_size = struct.unpack('>H', f.read(2))[0]
            assert header_size == 2  # Version 1 header is 2 bytes
            
            # Read header bytes
            header_bytes = f.read(header_size)
            assert len(header_bytes) == 2
            assert header_bytes[0] == 0x00  # File type (currently 0)
            assert header_bytes[1] == 0x00  # Reserved (must be 0)
            
            # Read content
            content = f.read(total_size - 2 - header_size)
            # Read the actual file to get expected content
            with open(test_data_dir / 'file1.txt', 'rb') as orig_file:
                expected_content = orig_file.read()
            assert content == expected_content
            
            # Verify total size calculation
            assert total_size == 2 + header_size + len(expected_content)
    
    def test_encode_multiple_files(self, temp_dir, test_data_dir):
        """Test encoding multiple files from a directory."""
        output_file = Path(temp_dir) / 'output.fca'
        encode_fca(str(test_data_dir), str(output_file))
        
        assert output_file.exists()
        
        # Count files in test_data directory (recursively)
        file_count = sum(1 for _ in test_data_dir.rglob('*') if _.is_file())
        
        # Verify file format and count embedded files
        with open(output_file, 'rb') as f:
            # Check magic bytes
            magic = f.read(3)
            assert magic == b'FCA'
            
            # Check version
            version = struct.unpack('>B', f.read(1))[0]
            assert version == 1
            
            # Count embedded files
            embedded_count = 0
            while True:
                total_size_bytes = f.read(4)
                if len(total_size_bytes) < 4:
                    break
                
                total_size = struct.unpack('>I', total_size_bytes)[0]
                header_size = struct.unpack('>H', f.read(2))[0]
                assert header_size == 2  # Version 1 header is 2 bytes
                
                # Read header bytes
                f.read(header_size)
                
                embedded_size = total_size - 2 - header_size
                f.read(embedded_size)
                embedded_count += 1
            
            assert embedded_count == file_count
    
    def test_encode_empty_file(self, temp_dir, test_data_dir):
        """Test encoding an empty file."""
        # Create a temp directory with an empty file
        empty_file_dir = Path(temp_dir) / 'empty_file'
        empty_file_dir.mkdir()
        shutil.copy(test_data_dir / 'empty.txt', empty_file_dir / 'empty.txt')
        
        output_file = Path(temp_dir) / 'output.fca'
        encode_fca(str(empty_file_dir), str(output_file))
        
        assert output_file.exists()
        
        with open(output_file, 'rb') as f:
            magic = f.read(3)
            assert magic == b'FCA'
            
            version = struct.unpack('>B', f.read(1))[0]
            assert version == 1
            
            # Read embedded file entry
            total_size = struct.unpack('>I', f.read(4))[0]
            header_size = struct.unpack('>H', f.read(2))[0]
            assert header_size == 2  # Version 1 header is 2 bytes
            
            # Read header bytes
            header_bytes = f.read(header_size)
            assert len(header_bytes) == 2
            
            # Empty file should have total_size = 2 (header_size field) + 2 (header bytes) = 4
            assert total_size == 4
            
            # Should be at EOF
            remaining = f.read(1)
            assert len(remaining) == 0
    
    def test_encode_nested_directories(self, temp_dir, test_data_dir):
        """Test encoding files from nested directories."""
        output_file = Path(temp_dir) / 'output.fca'
        encode_fca(str(test_data_dir), str(output_file))
        
        assert output_file.exists()
        
        # Verify subdirectory file is included
        with open(output_file, 'rb') as f:
            magic = f.read(3)
            assert magic == b'FCA'
            version = struct.unpack('>B', f.read(1))[0]
            assert version == 1
            
            # Read all embedded files and check for subdir file
            found_subdir_file = False
            while True:
                total_size_bytes = f.read(4)
                if len(total_size_bytes) < 4:
                    break
                
                total_size = struct.unpack('>I', total_size_bytes)[0]
                header_size = struct.unpack('>H', f.read(2))[0]
                embedded_size = total_size - 2 - header_size
                content = f.read(embedded_size)
                
                if b'subdirectory' in content:
                    found_subdir_file = True
            
            assert found_subdir_file
    
    def test_encode_invalid_input(self, temp_dir):
        """Test encoding with invalid input directory."""
        output_file = Path(temp_dir) / 'output.fca'
        
        with pytest.raises(ValueError, match="Input path is not a directory"):
            encode_fca(str(output_file), str(output_file))


class TestFCADecode:
    """Tests for FCA decoding."""
    
    def test_decode_single_file(self, temp_dir, test_data_dir):
        """Test decoding a single file archive."""
        # Create a temp directory with a single file
        single_file_dir = Path(temp_dir) / 'single_file'
        single_file_dir.mkdir()
        shutil.copy(test_data_dir / 'file1.txt', single_file_dir / 'file1.txt')
        
        # Create FCA file
        fca_file = Path(temp_dir) / 'test.fca'
        encode_fca(str(single_file_dir), str(fca_file))
        
        # Decode it
        output_dir = Path(temp_dir) / 'output'
        decode_fca(str(fca_file), str(output_dir))
        
        # Verify output
        assert output_dir.is_dir()
        
        # Find the extracted file (by MD5)
        files = list(output_dir.iterdir())
        assert len(files) == 1
        
        # Verify content
        expected_content = b'Hello, World!\nThis is a test file.\n'
        expected_md5 = hashlib.md5(expected_content).hexdigest()
        
        extracted_file = output_dir / expected_md5
        assert extracted_file.exists()
        
        with open(extracted_file, 'rb') as f:
            assert f.read() == expected_content
    
    def test_decode_multiple_files(self, temp_dir, test_data_dir):
        """Test decoding multiple files."""
        # Create FCA file
        fca_file = Path(temp_dir) / 'test.fca'
        encode_fca(str(test_data_dir), str(fca_file))
        
        # Decode it
        output_dir = Path(temp_dir) / 'output'
        decode_fca(str(fca_file), str(output_dir))
        
        # Count files in test_data
        test_files = list(test_data_dir.rglob('*'))
        test_files = [f for f in test_files if f.is_file()]
        
        # Verify all files were extracted
        extracted_files = list(output_dir.iterdir())
        assert len(extracted_files) == len(test_files)
        
        # Verify MD5 hashes match
        for test_file in test_files:
            with open(test_file, 'rb') as f:
                content = f.read()
            expected_md5 = hashlib.md5(content).hexdigest()
            assert (output_dir / expected_md5).exists()
    
    def test_decode_empty_file(self, temp_dir, test_data_dir):
        """Test decoding an archive with an empty file."""
        # Create a temp directory with an empty file
        empty_file_dir = Path(temp_dir) / 'empty_file'
        empty_file_dir.mkdir()
        shutil.copy(test_data_dir / 'empty.txt', empty_file_dir / 'empty.txt')
        
        # Create FCA file with empty file
        fca_file = Path(temp_dir) / 'test.fca'
        encode_fca(str(empty_file_dir), str(fca_file))
        
        # Decode it
        output_dir = Path(temp_dir) / 'output'
        decode_fca(str(fca_file), str(output_dir))
        
        # Verify empty file was extracted
        expected_md5 = hashlib.md5(b'').hexdigest()
        extracted_file = output_dir / expected_md5
        assert extracted_file.exists()
        
        with open(extracted_file, 'rb') as f:
            assert f.read() == b''
    
    def test_decode_invalid_magic(self, temp_dir):
        """Test decoding with invalid magic bytes."""
        invalid_file = Path(temp_dir) / 'invalid.fca'
        with open(invalid_file, 'wb') as f:
            f.write(b'XXX')  # Invalid magic
            f.write(struct.pack('>B', 1))
        
        output_dir = Path(temp_dir) / 'output'
        
        with pytest.raises(ValueError, match="Invalid FCA file"):
            decode_fca(str(invalid_file), str(output_dir))
    
    def test_decode_nonexistent_file(self, temp_dir):
        """Test decoding a nonexistent file."""
        output_dir = Path(temp_dir) / 'output'
        
        with pytest.raises(ValueError, match="Input file does not exist"):
            decode_fca('/nonexistent/file.fca', str(output_dir))


class TestFCARoundTrip:
    """Tests for round-trip encoding and decoding."""
    
    def test_round_trip_single_file(self, temp_dir, test_data_dir):
        """Test encoding and then decoding a single file."""
        # Create a temp directory with a single file
        single_file_dir = Path(temp_dir) / 'single_file'
        single_file_dir.mkdir()
        shutil.copy(test_data_dir / 'file1.txt', single_file_dir / 'file1.txt')
        
        # Encode
        fca_file = Path(temp_dir) / 'test.fca'
        encode_fca(str(single_file_dir), str(fca_file))
        
        # Decode
        output_dir = Path(temp_dir) / 'output'
        decode_fca(str(fca_file), str(output_dir))
        
        # Verify content matches
        original_content = b'Hello, World!\nThis is a test file.\n'
        expected_md5 = hashlib.md5(original_content).hexdigest()
        
        extracted_file = output_dir / expected_md5
        with open(extracted_file, 'rb') as f:
            assert f.read() == original_content
    
    def test_round_trip_multiple_files(self, temp_dir, test_data_dir):
        """Test encoding and decoding multiple files."""
        # Encode
        fca_file = Path(temp_dir) / 'test.fca'
        encode_fca(str(test_data_dir), str(fca_file))
        
        # Decode
        output_dir = Path(temp_dir) / 'output'
        decode_fca(str(fca_file), str(output_dir))
        
        # Verify all files match
        for test_file in test_data_dir.rglob('*'):
            if not test_file.is_file():
                continue
            
            with open(test_file, 'rb') as f:
                original_content = f.read()
            
            expected_md5 = hashlib.md5(original_content).hexdigest()
            extracted_file = output_dir / expected_md5
            
            assert extracted_file.exists(), f"File {test_file} not found in output"
            
            with open(extracted_file, 'rb') as f:
                assert f.read() == original_content
    
    def test_round_trip_binary_files(self, temp_dir, test_data_dir):
        """Test round-trip with binary files."""
        # Create a temp directory with a binary file
        binary_file_dir = Path(temp_dir) / 'binary_file'
        binary_file_dir.mkdir()
        shutil.copy(test_data_dir / 'file2.bin', binary_file_dir / 'file2.bin')
        
        # Encode binary file
        fca_file = Path(temp_dir) / 'test.fca'
        encode_fca(str(binary_file_dir), str(fca_file))
        
        # Decode
        output_dir = Path(temp_dir) / 'output'
        decode_fca(str(fca_file), str(output_dir))
        
        # Verify binary content matches
        with open(test_data_dir / 'file2.bin', 'rb') as f:
            original_content = f.read()
        expected_md5 = hashlib.md5(original_content).hexdigest()
        
        extracted_file = output_dir / expected_md5
        assert extracted_file.exists(), f"File with MD5 {expected_md5} not found"
        with open(extracted_file, 'rb') as f:
            assert f.read() == original_content
    
    def test_round_trip_large_file(self, temp_dir, test_data_dir):
        """Test round-trip with a larger file."""
        # Encode
        fca_file = Path(temp_dir) / 'test.fca'
        encode_fca(str(test_data_dir / 'large.txt'), str(fca_file))
        
        # Decode
        output_dir = Path(temp_dir) / 'output'
        decode_fca(str(fca_file), str(output_dir))
        
        # Verify content matches
        with open(test_data_dir / 'large.txt', 'rb') as f:
            original_content = f.read()
        
        expected_md5 = hashlib.md5(original_content).hexdigest()
        extracted_file = output_dir / expected_md5
        
        with open(extracted_file, 'rb') as f:
            assert f.read() == original_content


class TestFCAFormat:
    """Tests for FCA file format correctness."""
    
    def test_file_format_structure(self, temp_dir, test_data_dir):
        """Test that encoded file follows the exact format specification."""
        # Create a temp directory with a single file
        single_file_dir = Path(temp_dir) / 'single_file'
        single_file_dir.mkdir()
        shutil.copy(test_data_dir / 'file1.txt', single_file_dir / 'file1.txt')
        
        output_file = Path(temp_dir) / 'output.fca'
        encode_fca(str(single_file_dir), str(output_file))
        
        with open(output_file, 'rb') as f:
            # Global header: 3 bytes magic + 1 byte version
            magic = f.read(3)
            assert magic == b'FCA'
            
            version = struct.unpack('>B', f.read(1))[0]
            assert version == 1
            
            # Embedded file structure
            total_size = struct.unpack('>I', f.read(4))[0]  # Big-endian
            header_size = struct.unpack('>H', f.read(2))[0]  # Big-endian
            
            assert header_size == 2  # Version 1 header is 2 bytes
            
            # Read header bytes
            header_bytes = f.read(header_size)
            assert len(header_bytes) == 2
            assert header_bytes[0] == 0x00  # File type
            assert header_bytes[1] == 0x00  # Reserved
            
            # Verify total_size calculation
            embedded_size = total_size - 2 - header_size
            content = f.read(embedded_size)
            
            with open(test_data_dir / 'file1.txt', 'rb') as orig_file:
                expected_content = orig_file.read()
            assert len(content) == len(expected_content)
            assert total_size == 2 + header_size + len(expected_content)
    
    def test_big_endian_encoding(self, temp_dir, test_data_dir):
        """Test that multi-byte integers are big-endian."""
        output_file = Path(temp_dir) / 'output.fca'
        encode_fca(str(test_data_dir / 'file1.txt'), str(output_file))
        
        with open(output_file, 'rb') as f:
            f.read(4)  # Skip magic + version
            
            # Read total_size bytes
            total_size_bytes = f.read(4)
            # Verify it's big-endian by checking byte order
            # For a value > 255, bytes should be in big-endian order
            total_size = struct.unpack('>I', total_size_bytes)[0]
            
            # Verify by unpacking as little-endian would give wrong value
            little_endian_value = struct.unpack('<I', total_size_bytes)[0]
            if total_size > 255:
                assert total_size != little_endian_value


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
