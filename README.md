# Flexible Concatenated Archive (FCA)

A flexible container format for embedding multiple files within a single archive file. The FCA format supports version-specific header formats, allowing for extensibility and future enhancements.

## Purpose

The Flexible Concatenated Archive (FCA) format is designed to efficiently store and organize multiple embedded files within a single archive. It is optimized for use on extremely low-resource devices, making it ideal for embedded systems, IoT devices, and other constrained environments where memory and processing power are limited.

The format is particularly well-suited for storing collections of related files such as:
- Amiibo dumps (v2 and v3 formats)
- Skylander dumps
- Destiny Infinity dumps
- Lego Dimensions dumps
- Other binary file collections

## Design Goals

The FCA format was designed with the following principles in mind:

- **Simple** - The format is straightforward and easy to understand, with a clear structure that can be implemented with minimal code complexity.

- **Efficient** - The format wastes as little space as possible, avoiding unnecessary padding or overhead. Every byte serves a purpose.

- **Flexible** - The format allows room for growth and future expansion through versioning and dynamic header sizes. Different file types can be stored with type-specific metadata.

- **Identifiable** - The format uses a dedicated file extension (`.fca`) and magic bytes ("FCA") at the beginning of each file for easy identification.

## Overview

FCA files (`.fca` extension) consist of:
- A global header with magic bytes "FCA" and a version number
- One or more embedded files, each with version-dependent headers containing file type and metadata

See [SPEC.md](SPEC.md) for the complete format specification.

## Build self-contained Windows executables

You can package both Python tools as standalone `.exe` files using PyInstaller.

### Prerequisites

- Windows with Python installed
- build dependencies installed in your Python environment

Install build dependencies:

```bash
python -m pip install -r python/requirements-build.txt
```

### Icon data generation

Generate `python/icon_data.py` from an image (`.png` or `.ico`):

```bash
python python/generate_icon_data.py --input-file python/small-logo.png --output-file python/icon_data.py
```

`icon_data.py` contains embedded icon bytes that are used by:

- `fca_tool.py` for GUI window icon (top-left)
- build/export flow for executable icon embedding

### Build both executables

From the repository root:

```bash
make build-exes
```

This generates:

- `dist/windows/fca-encode.exe`
- `dist/windows/fca-decode.exe`
- `dist/windows/fca-tool.exe`

### Build individually

```bash
make build-exe-encode
make build-exe-decode
make build-exe-tool
```

If you want to build newer versions of `fca-tool.exe`, build to a unique filename instead:

```bash
make build-exe-tool-unique
```

This creates `dist/windows/fca-tool-<timestamp>.exe` and avoids overwriting files.

### Clean build artifacts

```bash
make clean-build
```

## Unified CLI + GUI tool

Use `python/fca_tool.py` to run encoding and decoding from a single script.

### CLI mode

Encode from an explicit list of files:

```bash
python python/fca_tool.py encode --output-file out.fca --input-files file1.bin file2.bin
```

Encode recursively from one or more directories:

```bash
python python/fca_tool.py encode --output-file out.fca --input-dirs dumps/ more_dumps/
```

You can also combine both:

```bash
python python/fca_tool.py encode --output-file out.fca --input-files file1.bin --input-dirs dumps/
```

Decode an archive:

```bash
python python/fca_tool.py decode --input-file out.fca --output-dir extracted
```

### GUI mode

Launch GUI directly:

```bash
python python/fca_tool.py --gui
```

If run without subcommands, GUI mode starts automatically.
In the GUI Encode tab, you can add individual files or add a folder recursively.

## GitHub Actions build

This repository includes a workflow at [.github/workflows/build-exes.yml](.github/workflows/build-exes.yml) that builds:

- `fca-encode.exe`
- `fca-decode.exe`
- `fca-tool.exe`

Targets:

- `windows-x64` on GitHub-hosted `windows-latest`
- `windows-arm64` on a self-hosted runner labeled `self-hosted`, `Windows`, `ARM64` (manual workflow dispatch only)

The workflow runs `windows-x64` on `push`, `pull_request`, and `workflow_dispatch`.
The `windows-arm64` job runs only when manually triggered with `build_arm64=true`.

Executable icons in CI are generated via:

```bash
python fca_tool.py --export-icon .build-icon.ico
```

This uses embedded bytes from `python/icon_data.py`, so builds do not depend on external image files.
