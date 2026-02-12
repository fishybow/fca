.PHONY: test test-unittest test-pytest clean help

# Default Python interpreter
PYTHON := python3

# Test directory
TEST_DIR := python/tests

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

test: test-unittest ## Run all tests (defaults to unittest)

test-unittest: ## Run tests using unittest (standard library)
	@echo "Running unittest tests..."
	cd python && $(PYTHON) -m unittest tests.test_fca_unittest -v

test-pytest: ## Run tests using pytest (requires pytest)
	@echo "Running pytest tests..."
	cd python && $(PYTHON) -m pytest tests/test_fca.py -v

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
	cd python && $(PYTHON) -m py_compile tests/test_fca.py tests/test_fca_unittest.py
	@echo "Syntax check passed."
