.PHONY: test test-unittest test-pytest clean help build-exes build-exe-encode build-exe-decode build-exe-tool build-exe-tool-unique build-icon clean-build

# Default Python interpreter
PYTHON := python3
EXE_SUFFIX ?= $(shell $(PYTHON) -c "import time; print(time.strftime('%Y%m%d-%H%M%S'))")
ICON_ICO := python/small-logo.ico

# Test directory
TEST_DIR := python/tests

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

build-exes: build-exe-encode build-exe-decode build-exe-tool ## Build self-contained Windows .exe files (requires pyinstaller)

build-icon: ## One-time: generate python/small-logo.ico from python/small-logo.png
	@echo "Generating $(ICON_ICO) once..."
	$(PYTHON) python/build_icon.py --input-file python/small-logo.png --output-file $(ICON_ICO)

build-exe-encode: ## Build fca-encode.exe using PyInstaller onefile mode
	@echo "Building fca-encode.exe..."
	@test -f $(ICON_ICO) || (echo "Missing $(ICON_ICO). Run 'make build-icon' once." && exit 1)
	cd python && $(PYTHON) -m PyInstaller --clean --noconfirm --onefile --icon small-logo.ico --name fca-encode --distpath ../dist/windows fca_encode.py

build-exe-decode: ## Build fca-decode.exe using PyInstaller onefile mode
	@echo "Building fca-decode.exe..."
	@test -f $(ICON_ICO) || (echo "Missing $(ICON_ICO). Run 'make build-icon' once." && exit 1)
	cd python && $(PYTHON) -m PyInstaller --clean --noconfirm --onefile --icon small-logo.ico --name fca-decode --distpath ../dist/windows fca_decode.py

build-exe-tool: ## Build fca-tool.exe (unified CLI + GUI) using PyInstaller onefile mode
	@echo "Building fca-tool.exe..."
	@test -f $(ICON_ICO) || (echo "Missing $(ICON_ICO). Run 'make build-icon' once." && exit 1)
	cd python && $(PYTHON) -m PyInstaller --clean --noconfirm --onefile --icon small-logo.ico --name fca-tool --distpath ../dist/windows fca_tool.py

build-exe-tool-unique: ## Build fca-tool-<timestamp>.exe to avoid locked file overwrite
	@echo "Building fca-tool-$(EXE_SUFFIX).exe..."
	@test -f $(ICON_ICO) || (echo "Missing $(ICON_ICO). Run 'make build-icon' once." && exit 1)
	cd python && $(PYTHON) -m PyInstaller --clean --noconfirm --onefile --icon small-logo.ico --name fca-tool-$(EXE_SUFFIX) --distpath ../dist/windows fca_tool.py

clean-build: ## Clean PyInstaller build artifacts
	@echo "Cleaning build artifacts..."
	rm -rf python/build python/dist python/*.spec dist/windows 2>/dev/null || true
	@echo "Build artifacts cleaned."

t: test-both

test: test-unittest ## Run all tests (defaults to unittest)

test-unittest: ## Run tests using unittest (standard library)
	@echo "Running unittest tests..."
	cd python && $(PYTHON) -m unittest tests.test_fca_unittest -v

test-pytest: ## Run tests using pytest (requires pytest)
	@echo "Running pytest tests..."
	cd python && $(PYTHON) -m pytest tests/test_fca_pytest.py -v

test-both: test-unittest test-pytest ## Run both unittest and pytest tests

clean: ## Clean test artifacts and cache files
	@echo "Cleaning test artifacts..."
	find python -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find python -type f -name "*.pyc" -delete 2>/dev/null || true
	find python -type f -name "*.pyo" -delete 2>/dev/null || true
	find python -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	@echo "Clean complete."

check: ## Check code syntax
	@echo "Checking Python syntax..."
	cd python && $(PYTHON) -m py_compile fca_encode.py fca_decode.py
	cd python && $(PYTHON) -m py_compile tests/test_fca_pytest.py tests/test_fca_unittest.py
	@echo "Syntax check passed."
