.PHONY: venv install build test test-all lint format clean

# Dependency tracking files
.venv/bin/python:
	uv venv

.venv/.deps-installed: pyproject.toml .venv/bin/python
	uv sync
	uv pip install -e ".[dev]"
	touch .venv/.deps-installed

# Virtual environment target
venv: .venv/bin/python

# Install dependencies
install: .venv/.deps-installed

# Run tests
test: .venv/.deps-installed
	uv run pytest

# Run tests with verbose output
test-all: .venv/.deps-installed
	uv run pytest -v

# Run linting
lint: .venv/.deps-installed
	uv run ruff check .

# Format code
format: .venv/.deps-installed
	uv run ruff format .

# Clean build artifacts and caches
clean:
	rm -rf dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +