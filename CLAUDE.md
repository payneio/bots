# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- Build: `make build` (build the package)
- Test: `make test` (all tests)
- Single test: `uv run pytest tests/test_file.py::TestClass::test_name -v`
- Lint: `make lint`
- Format: `make format`

## Code Style

- Use [Ruff](https://docs.astral.sh/ruff/) for linting/formatting
- Line length: 100 chars (E501 ignored)
- Imports: Sort imports using isort rules (I)
- Types: Use type annotations everywhere
- Naming: snake_case for variables/functions, PascalCase for classes
- Async: Use pytest.mark.asyncio for async tests
- Error handling: Catch specific exceptions, log appropriately
- Document all public functions/classes with docstrings (Google style)
- Use Pydantic models for data validation
- Prefer short code to long.
- Prefer clear code to short.
- Code with clear abstractions.
- Comment only when an experienced dev would be confused by a block of code.
