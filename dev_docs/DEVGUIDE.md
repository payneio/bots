# `bots` — Modular CLI AI Assistants Development Guide

`bots` is a command-line tool that launches project-specific or global AI assistants using configurable models and behaviors. Each assistant is self-contained, configurable, and can interact with the command line in safe, controlled ways.

---

- The primary user interaction is through the `bots` command, created by this framework (see `./bots/cli.py`).
- Data for created bots are stored in one of two locations:
  - Global bots: `~/.config/bots/<n>/`
  - Local bots: `./.bots/<bot-name>/` (local to a directory or project)
- Important data directory layout:
  ├── config.json # Bot config (model, tags, command rules)
  ├── system_prompt.md # Editable natural language prompt
  └── sessions/
  └── <YYYY-MM-DDTHH-MM-SS>
  ├── conversation.json # Message history
  ├── log.json # Events, commands, errors
  └── session.json # Summary: tokens, runtime, metadata
- Bot configuration (`config.json`) is managed by `bots/config.py`
- A robust permissions system for any bot running command lines is managed by `bots/command/permissions.py` and `bots/command/executor.py`.
- Each bot has a custom system prompt governing much of its behavior. The template for the default prompt is in `bots/default_system_prompt.md`.
- The default system prompt is augmented automatically with session context information about the bot and system.
- Bots can be run in interactive, or one-shot mode.
  - Interactive:
    - `bots run <bot-name>`
    - Multi-turn conversation
    - Logs stored in data directory
    - Supports slash commands, like `/help` and `/code`
  - One-shot:
    - `echo "Summarize this README" | bots run <n>`
    - Reads stdin, outputs single reply to stdout
    - Log output (errors, debug) goes to stderr

## Tooling

- Use `make`.
- Use `uv` for the python environment
  - Use `uv add ...` instead of `pip install ...`
  - Use `uv run ...` for ALL python or other commands that need to be in the project python environment.
- Lint with `ruff`: `make lint` and `make format`
- Type-check with `pylance`: `make typecheck`
- Test with `pytest`: `make test`

## Libraries

- This project uses the latest version of PydanticAI for LLM interaction. See https://ai.pydantic.dev/ for up-to-date docs.

## Best Practices

- When working on a feature, keep any intermediate work artifacts, like docs or scripts in the `tmp` folder.
- Stick with modern python dev practices.
- Unit testing of functions and modules is good.
- For real-world testing, use the testbot (`bots run testbot`). Create it if needed. Change its config as needed.
- Imports: Sort imports using isort rules (I)
- Types: Use type annotations everywhere
- Async: Use pytest.mark.asyncio for async tests
- Error handling: Catch specific exceptions, log appropriately
- Document all public functions/classes with docstrings (Google style)
- Use Pydantic models for data validation
- Keep code maintainable:
  - Prefer short code to long.
  - Prefer clear code to short.
  - Code with clear abstractions.
- Comment only when an experienced dev would be confused by a block of code.
- python is not installed on the system. You MUST use `uv run python` to use python properly.
- ALWAYS run `make lint` and `make typecheck` and `make test` after completing a series of edits and fix any problems found.
- When fixing tests, first determine whether the test failure is due to a bad test or bad code. Fix the appropriate thing.
