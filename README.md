# Flexible Concatenated Archive (FCA)

A flexible container format for embedding multiple files within a single archive file. The FCA format supports version-specific header formats, allowing for extensibility and future enhancements.

## Overview

FCA files (`.fca` extension) consist of:
- A global header with magic bytes "FCA" and a version number
- One or more embedded files, each with optional version-dependent headers

See [fca-spec.md](fca-spec.md) for the complete format specification.
