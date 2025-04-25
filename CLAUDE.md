# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- Build: `make build` (build the package)
- Test: `make test` (all tests)
- Single test: `uv run pytest tests/test_file.py::TestClass::test_name -v`
- Lint: `make lint`
- Format: `make format`
- Type check: `make typecheck` (using pyright)
- Diagnose: `uv run python scripts/diagnose_system.py` (check system compatibility)
- Test pydantic-ai: `uv run python scripts/check_pydantic_ai.py` (verify pydantic-ai integration)
- Test full system: `uv run python scripts/test_full_system.py` (end-to-end test)

## CLI Commands

- Init a bot: `bots init <name> [--local]`
- Run interactive session: `bots run --name <name>` or `bots run -n <name>`
- Run interactive session with debug info: `bots run --name <name> --debug`
- Run one-shot mode: `bots run --name <name> --one-shot` (reads from stdin)
- List bots: `bots list`
- Rename a bot: `bots mv <old-name> <new-name>`

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
- python is not installed on the system. You MUST use `uv run python` to use python properly.

## Pydantic-AI Integration

- The bot uses pydantic-ai for structured LLM outputs
- Requirements: Python 3.10+, pydantic-ai 0.1.3+, OpenAI API key
- Creates a new Agent for each request (per pydantic-ai recommendation)
- Uses the gpt-4o model for optimal structured output generation
- Format: BotResponse with 'reply' and 'commands' fields
- See dev_docs/example_pydantic_ai_code.md for more examples
