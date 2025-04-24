# 🧠 `bot` — Modular CLI AI Assistants

`bot` is a command-line tool that launches project-specific or global AI assistants using configurable models and behaviors. Each assistant is self-contained, configurable, and can interact with the command line in safe, controlled ways.

---

## 🧰 Command Overview

```bash
bot init <n> [--local]         # Create a new bot
bot run --name/-n <n>          # Start interactive session
bot run --name/-n <n> --one-shot  # Run in one-shot mode (reads from stdin)
bot list                          # List all available bots (local & global)
bot mv <old-name> <new-name>      # Rename a bot
bot rm <n> [--force/-f]           # Delete a bot
```

---

## 📁 Bot Storage Locations

- **Global bots:** `~/.config/bot/<n>/`
- **Local bots:** `./.bot/<n>/` (project-specific)

### 🔍 Lookup Order

When launching `bot <n>`:

1. Look for `.bot/<n>/` in the current directory
2. Fall back to `~/.config/bot/<n>/`

---

## 📂 Bot Directory Layout (`<n>/`)

```bash
.bot/
└── <n>/
    ├── config.json             # Bot config (model, tags, command rules)
    ├── system_prompt.md        # Editable natural language prompt
    └── sessions/
        └── 2025-04-22T13-42-10/
            ├── conversation.json  # Message history
            ├── log.json           # Events, commands, errors
            └── session.json       # Summary: tokens, runtime, metadata
```

---

## 🧾 `config.json` Format

```json
{
  "model_provider": "openai",
  "model_name": "gpt-4",
  "temperature": 0.7,
  "tags": ["project", "codegen"],
  "api_key": "ENV:OPENAI_API_KEY",
  "command_permissions": {
    "allow": ["ls", "make", "pytest"],
    "deny": ["rm", "shutdown"],
    "ask_if_unspecified": true
  }
}
```

- `allow`: Commands bot can run freely
- `deny`: Explicitly blocked commands
- `ask_if_unspecified`: Bot must ask for permission before using unknown commands

---

## ✍️ `system_prompt.md`

Plaintext Markdown file with the assistant's personality and instructions. Loaded at startup.

```markdown
You're a focused assistant that writes test code for this project using pytest.
Ask the user for filenames before you begin.
```

Every system prompt is automatically enhanced with session context information including:
- Current date and time
- System information
- Bot configuration directory
- Model information

---

## 💬 Session Files

Each bot session is logged in:

```
<bot-dir>/sessions/<timestamp>/
```

### Includes:

- `conversation.json`: user/assistant messages
- `log.json`: events, commands, metadata
- `session.json`: summary including token usage

```json
{
  "start_time": "2025-04-22T13:42:10",
  "end_time": "2025-04-22T13:52:43",
  "model": "gpt-4",
  "provider": "openai",
  "token_usage": {
    "prompt_tokens": 1340,
    "completion_tokens": 1853,
    "total_tokens": 3193
  },
  "num_messages": 10,
  "commands_run": 3,
  "status": "completed"
}
```

---

## 🧠 Modes

### 1. **Interactive Mode**

```bash
bot <n>
```

- Multi-turn conversation
- Auto-logs session to timestamped folder
- Supports slash commands

### 2. **One-shot / Streaming Mode**

```bash
echo "Summarize this README" | bot <n>
```

- Reads stdin, outputs single reply to stdout
- Log output (errors, debug) goes to stderr

---

## 🔐 Command Execution Logic

- Commands in `allow`: run immediately
- Commands in `deny`: blocked entirely
- All others: bot must ask for permission
  - If user responds positively (in natural language), command is allowed for that turn only

---

## ⌨️ Slash Commands (Interactive Mode Only)

- `/help` — show list of available slash commands
- `/config` — open bot config directory in VS Code
- `/exit` — exit the session

## Code

- Use `make`.
- Use `uv`.
- Use the most widely used libraries for everything else.