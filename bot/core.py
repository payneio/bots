"""Core functionality for bot."""

import datetime
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from bot.config import BotConfig, create_default_system_prompt


def get_bot_paths() -> Tuple[Path, Path]:
    """Get paths for global and local bots."""
    global_path = Path.home() / ".config" / "bot"
    local_path = Path.cwd() / ".bot"
    return global_path, local_path


def find_bot(bot_name: str) -> Optional[Path]:
    """Find a bot by name, checking local then global paths."""
    global_path, local_path = get_bot_paths()

    # Check local first, then global
    local_bot_path = local_path / bot_name
    if local_bot_path.exists():
        return local_bot_path

    global_bot_path = global_path / bot_name
    if global_bot_path.exists():
        return global_bot_path

    return None


def create_bot(bot_name: str, local: bool = False) -> Path:
    """Create a new bot with default configuration."""
    global_path, local_path = get_bot_paths()

    base_path = local_path if local else global_path
    bot_path = base_path / bot_name

    if bot_path.exists():
        raise FileExistsError(f"Bot '{bot_name}' already exists at {bot_path}")

    # Create bot directory
    bot_path.mkdir(parents=True, exist_ok=True)

    # Create sessions directory
    sessions_path = bot_path / "sessions"
    sessions_path.mkdir(exist_ok=True)

    # Create default config
    config = BotConfig()
    config.save(bot_path)

    # Create default system prompt
    create_default_system_prompt(bot_path)

    return bot_path


def list_bots() -> Dict[str, List[str]]:
    """List all available bots, both local and global."""
    global_path, local_path = get_bot_paths()

    result = {"global": [], "local": []}

    # List global bots
    if global_path.exists():
        result["global"] = [p.name for p in global_path.iterdir() if p.is_dir()]

    # List local bots
    if local_path.exists():
        result["local"] = [p.name for p in local_path.iterdir() if p.is_dir()]

    return result


def rename_bot(old_name: str, new_name: str) -> Path:
    """Rename a bot from old_name to new_name."""
    old_path = find_bot(old_name)
    if not old_path:
        raise FileNotFoundError(f"Bot '{old_name}' not found")

    # Determine if this is a local or global bot
    is_local = ".bot" in str(old_path)
    global_path, local_path = get_bot_paths()

    base_path = local_path if is_local else global_path
    new_path = base_path / new_name

    if new_path.exists():
        raise FileExistsError(f"Bot '{new_name}' already exists at {new_path}")

    # Rename directory
    old_path.rename(new_path)

    return new_path


def start_session(bot_name: str, one_shot: bool = False, prompt: Optional[str] = None) -> None:
    """Start a bot session."""
    bot_path = find_bot(bot_name)
    if not bot_path:
        raise FileNotFoundError(f"Bot '{bot_name}' not found")

    # Load config
    try:
        config = BotConfig.load(bot_path)
    except Exception as e:
        raise RuntimeError(f"Failed to load bot configuration: {e}")

    # Load system prompt
    system_prompt_path = bot_path / "system_prompt.md"
    if system_prompt_path.exists():
        with open(system_prompt_path, "r") as f:
            _ = f.read()  # System prompt will be used in future implementation
    else:
        _ = "You are a helpful AI assistant."  # Default prompt for future use

    # Create session directory if not one-shot mode
    if not one_shot:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        session_path = bot_path / "sessions" / timestamp
        session_path.mkdir(parents=True, exist_ok=True)

        # Initialize session files
        session_info = {
            "start_time": timestamp,
            "model": config.model_name,
            "provider": config.model_provider,
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "num_messages": 0,
            "commands_run": 0,
            "status": "active",
        }

        with open(session_path / "session.json", "w") as f:
            json.dump(session_info, f, indent=2)

        with open(session_path / "conversation.json", "w") as f:
            json.dump([], f, indent=2)

        with open(session_path / "log.json", "w") as f:
            json.dump([], f, indent=2)

    # TODO: Implement actual session with AI provider
    if one_shot:
        # One-shot mode implementation
        print(f"Bot '{bot_name}' responding to: {prompt}")
        print("This is a placeholder for the actual AI response.")
    else:
        # Interactive mode implementation
        print(f"Starting interactive session with bot '{bot_name}'")
        print("Type '/exit' to end the session.")
        print("Type '/help' for available commands.")
        print("\nBot is ready for your input! (Interactive mode not fully implemented yet)")

        # Placeholder for interactive loop
        while True:
            try:
                user_input = input("\nYou: ").strip()
                if user_input.lower() == "/exit":
                    break
                elif user_input.lower() == "/help":
                    print("\nAvailable commands:")
                    print("  /help   - Show this help message")
                    print("  /config - Show current bot configuration")
                    print("  /exit   - Exit the session")
                elif user_input.lower() == "/config":
                    print("\nBot configuration:")
                    print(json.dumps(json.loads(config.model_dump_json()), indent=2))
                else:
                    print(
                        "\nBot: This is a placeholder response. AI integration not implemented yet."
                    )
            except KeyboardInterrupt:
                print("\nExiting session.")
                break
            except Exception as e:
                print(f"\nError: {e}")
                continue
