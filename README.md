# 🧠 `bot` — Modular CLI AI Assistants

`bot` is a command-line tool that launches project-specific or global AI assistants using configurable models and behaviors. Each assistant is self-contained, configurable, and can interact with the command line in safe, controlled ways.

## Features

- Uses pydantic-ai for LLM integration with compatibility layer for Python 3.9+
- Supports both interactive and one-shot modes
- Project-specific or global bot configurations
- Command validation and permissions system
- Session logging and history
- Slash commands for common operations

## Installation

```bash
# Create a virtual environment (if not already created)
uv venv

# Activate the virtual environment (bash/zsh)
source .venv/bin/activate

# Install the package
uv pip install -e .
```

## Usage

```bash
# Create a new bot
bot init mybot [--local]

# Start an interactive session
bot run --name mybot  # or: bot run -n mybot

# List all available bots
bot list

# Rename a bot
bot mv old-name new-name

# One-shot mode
echo "Summarize this file" | bot run --name mybot --one-shot
```

## Development

```bash
# Create a virtual environment
make venv

# Install with development dependencies
make install

# Run tests
make test

# Run all tests with verbose output
make test-all

# Format code
make format

# Lint code
make lint

# Clean up build artifacts
make clean
```

## Configuration

Bots can be configured by editing their `config.json` file. Example configuration:

```json
{
  "model_provider": "openai",
  "model_name": "gpt-4",
  "temperature": 0.7,
  "api_key": "ENV:OPENAI_API_KEY",
  "command_permissions": {
    "allow": ["ls", "make", "pytest"],
    "deny": ["rm", "shutdown"],
    "ask_if_unspecified": true
  }
}
```

## Environment Variables

The following environment variables are used:

- `OPENAI_API_KEY`: API key for OpenAI (when using OpenAI provider)
- Other provider-specific keys can be referenced using the `ENV:KEY_NAME` format in the config

## Python Compatibility

This project is designed to work with Python 3.9 and higher. The LLM integration has a compatibility layer:

- With Python 3.10+: Uses pydantic-ai for full LLM integration
- With Python 3.9: Falls back to a placeholder implementation

For detailed specifications, see [SPEC.md](SPEC.md).