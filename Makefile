.PHONY: venv install build test test-all lint format clean

venv:
	uv venv

install:
	uv pip install -e ".[dev]"

build:
	uv run build

test:
	uv run pytest

test-all:
	uv run pytest -v

lint:
	uv run ruff check .

format:
	uv run ruff format .

clean:
	rm -rf dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +