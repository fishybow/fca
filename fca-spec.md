# Flexible Concatenated Archive (FCA) Format Specification

## Overview

The Flexible Concatenated Archive (FCA) format is a container format that allows embedding multiple files within a single archive file. The format is designed to be flexible, allowing version-specific header formats for each embedded file.

Aiming to be consumed on extremely low-resource devices, the design goals are
 * Simple -- straightforward, easy to understand.
 * Efficient -- wastes as little bytes as possible, e.g. no paddings.
 * Flexible -- allows room for growth and future expansion, with versioning and dynamic header size.
 * Identifiable -- the dedicated extension and marker bytes at the beginning.

**File Extension:** `.fca`

## File Structure

### Global Header

The file begins with a fixed global header:

```
Offset  Size  Description
------  ----  -----------
0       3     Magic bytes: "FCA" (ASCII)
3       1     Version number (unsigned byte, 0-255)
```

### Embedded Files

Following the global header, the file contains N embedded files, where N ≥ 0. Each embedded file is structured as follows:

```
Offset  Size  Description
------  ----  -----------
0       4     Total size (network byte order / big-endian)
              This represents the total number of bytes following this field,
              including the header size field, header bytes, and embedded file bytes.
4       2     Header size (network byte order / big-endian)
              Number of bytes in the header. Can be zero (0x0000).
6       H     Header bytes (H = header size from previous field)
6+H     E     Embedded file bytes (E = total size - 2 - H)
```

**Size Calculation:**
- Total size = 2 (header size field) + H (header bytes) + E (embedded file bytes)
- Embedded file bytes = Total size - 2 - H

### Endianness

All multi-byte integer values use **network byte order (big-endian)**:
- The 4-byte total size field
- The 2-byte header size field

## Version-Dependent Header Format

The format of the header bytes for each embedded file is determined by the version number specified in the global header (byte at offset 3).

### Version 1 Header Format

For FCA files with version 1, each embedded file header consists of exactly 2 bytes:

```
Offset  Size  Description
------  ----  -----------
0       1     File type (unsigned byte, 0-255)
              Indicates the type of the embedded file.
              File types will be defined in a future revision.
1       1     Purpose (unsigned byte, 0-255)
              Indicates the purpose or usage of the embedded file.
              Purpose values will be defined in a future revision.
```

**Current Implementation:**
- Both bytes are currently set to `0x00` (file type = 0, purpose = 0)
- File type and purpose definitions will be added in a future revision

## File Layout Diagram

```
┌─────────────────────────────────────────┐
│ Global Header                           │
│ ┌─────────┬──────────┐                  │
│ │ "FCA"   │ Version  │                  │
│ │ (3 B)   │ (1 B)    │                  │
│ └─────────┴──────────┘                  │
├─────────────────────────────────────────┤
│ Embedded File 1                         │
│ ┌──────┬──────┬────────┬──────────────┐ │
│ │ Total│Header│ Header │ Embedded     │ │
│ │ Size │ Size │ Bytes  │ File Bytes   │ │
│ │ (4 B)│ (2 B)│ (H B)  │ (E B)        │ │
│ └──────┴──────┴────────┴──────────────┘ │
├─────────────────────────────────────────┤
│ Embedded File 2                         │
│ ┌──────┬──────┬────────┬──────────────┐ │
│ │ Total│Header│ Header │ Embedded     │ │
│ │ Size │ Size │ Bytes  │ File Bytes   │ │
│ │ (4 B)│ (2 B)│ (H B)  │ (E B)        │ │
│ └──────┴────────┴────────┴─────────────┘│
├─────────────────────────────────────────┤
│ ... (more embedded files)               │
└─────────────────────────────────────────┘
```

## Example

For a file containing one embedded file with:
- Version: 1
- Header size: 2 bytes
- Header: `[0x00, 0x00]` (file type = 0, purpose = 0)
- Embedded file: `[0xAA, 0xBB, 0xCC]` (3 bytes)

The file structure would be:
```
Bytes 0-2:   "FCA" (0x46, 0x43, 0x41)
Byte 3:      0x01 (version 1)
Bytes 4-7:   0x00000007 (total size = 2 + 2 + 3 = 7, big-endian)
Bytes 8-9:   0x0002 (header size = 2, big-endian)
Bytes 10-11: [0x00, 0x00] (header: file type = 0, purpose = 0)
Bytes 12-14: [0xAA, 0xBB, 0xCC] (embedded file)
```

## Notes

- The format supports zero embedded files (empty archive)
- For version 1, header size is always 2 bytes
- The total size field includes all bytes following it (header size field + header bytes + embedded file bytes)
- All multi-byte integers are stored in network byte order (big-endian)
- The version number determines the interpretation of header bytes for all embedded files in the archive

## Revision History

| Date       | Version | Description |
|------------|---------|-------------|
| 2026-02-12 | 1.0     | Initial specification. Defined basic FCA format structure with global header and embedded file format. |
| 2026-02-12 | 1.1     | Added version 1 header format: 2-byte header with file type (byte 0) and purpose (byte 1). Both bytes currently set to 0x00. |
