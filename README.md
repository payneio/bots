# 🧠 `bots` — Modular CLI AI Assistants

`bots` is a command-line tool that launches project-specific or global AI assistants using configurable models and behaviors. Each assistant is self-contained, configurable, and can interact with the command line in safe, controlled ways.

## Features

- Uses pydantic-ai for LLM integration with compatibility layer for Python 3.9+
- Supports both interactive and one-shot modes
- Project-specific or global bot configurations
- Command validation and permissions system
- Session logging and history
- Slash commands for common operations

## Installation

### Development Installation

```bash
# Create a virtual environment (if not already created)
uv venv

# Activate the virtual environment (bash/zsh)
source .venv/bin/activate

# Install the package in development mode
uv pip install -e .
```

### System-wide Installation

To install the bot command globally on your system:

```bash
# Using make (recommended)
make install-user

# OR directly with pipx
uv run python -m build
pipx install dist/*.whl
```

This will install the `bots` command as an isolated application available in your PATH.

#### Prerequisites for System Installation

1. You need to have pipx installed on your system
2. If pipx is not installed, you can install it with:

```bash
# For Ubuntu/Debian
sudo apt update && sudo apt install pipx
pipx ensurepath  # Add pipx binaries to PATH

# For other systems
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

## Usage

```bash
# Create a new bot
bots init mybot [--local]

# Start an interactive session
bots run --name mybot  # or: bots run -n mybot

# List all available bots
bots list

# Rename a bot
bots mv old-name new-name

# Delete a bot
bots rm mybot [--force]

# One-shot mode
echo "Summarize this file" | bots run --name mybot --one-shot
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

# Build the package
make build

# Install for development
make install-dev

# Install for user (system-wide)
make install-user

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

This project is designed to work with Python 3.9 and higher. For best results, use Python 3.13 or above.

### OpenAI API Key

For the bot to work properly, you need to set up your OpenAI API key:

```bash
# Add to your ~/.bashrc or ~/.zshrc
export OPENAI_API_KEY="your-api-key"
```

For detailed specifications, see [SPEC.md](SPEC.md).