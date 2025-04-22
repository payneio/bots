# Project Status Summary

## What's Implemented
- Core CLI structure and commands (init, list, mv, run)
- Configuration management with Pydantic
- Bot directory structure with sessions
- Session and message history tracking
- Command permission handling
- Simplified placeholder LLM integration
- Interactive and one-shot modes
- Slash commands in interactive mode (/help, /config, /exit)
- Full test suite for config and core functionality
- Comprehensive documentation with docstrings

## Development Infrastructure
- Makefile with common commands (test, lint, format)
- uv for environment and dependency management
- Ruff for code linting and formatting
- pytest with asyncio support for tests
- CLAUDE.md with guidance for AI assistants

## Next Steps
1. Replace placeholder LLM integration with a real provider
2. Add session module tests
3. Implement sandboxed command execution
4. Add support for session resumption
5. Implement advanced features (memory management, file attachments)

## Current Limitations
- LLM integration uses placeholder responses
- No real LLM calls are made
- Session tests are disabled
- No sandboxing for command execution
- Missing session resumption feature

## Usage
```bash
# Create virtual environment (if needed)
uv venv

# Install with development dependencies
make install

# Run tests
make test

# Format code
make format

# Lint code
make lint

# Basic CLI functionality works:
bot init mybot [--local]            # Create a new bot
bot list                            # List available bots
bot mv old-name new-name            # Rename a bot
bot run --name mybot                # Start interactive session
bot run --name mybot --one-shot     # Run in one-shot mode (reads from stdin)
```