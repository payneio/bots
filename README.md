# 🧠 `bot` — Modular CLI AI Assistants

`bot` is a command-line tool that launches project-specific or global AI assistants using configurable models and behaviors. Each assistant is self-contained, configurable, and can interact with the command line in safe, controlled ways.

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
bot mybot

# List all available bots
bot list

# Rename a bot
bot mv old-name new-name

# One-shot mode
echo "Summarize this file" | bot mybot
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

For detailed specifications, see [SPEC.md](SPEC.md).