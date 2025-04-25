"""Core functionality for bot."""

import datetime
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from bots.config import DEFAULT_BOT_EMOJI, BotConfig, create_default_system_prompt


def get_bot_paths() -> Tuple[Path, Path]:
    """Get paths for global and local bots."""
    global_path = Path.home() / ".config" / "bots"
    local_path = Path.cwd() / ".bots"
    return global_path, local_path


def find_latest_session(bot_name: str, exclude_session: Optional[Path] = None) -> Optional[Path]:
    """Find the most recent session for a bot.

    Args:
        bot_name: The name of the bot
        exclude_session: Optional path to exclude from the search (e.g., current session)

    Returns:
        Path to the most recent session directory or None if no sessions found
    """
    bot_path = find_bot(bot_name)
    if not bot_path:
        return None

    sessions_path = bot_path / "sessions"
    if not sessions_path.exists():
        return None

    # List all session directories and sort by name (timestamp)
    all_dirs = [d for d in sessions_path.iterdir() if d.is_dir()]
    if exclude_session:
        all_dirs = [d for d in all_dirs if d != exclude_session]

    if not all_dirs:
        return None

    # Filter out directories that don't look like timestamp directories
    valid_dirs = [d for d in all_dirs if len(d.name) >= 19 and "T" in d.name and "-" in d.name]

    if not valid_dirs:
        return None

    # Sort by directory name (which is a timestamp string)
    sessions = sorted(valid_dirs, key=lambda d: d.name, reverse=True)

    if not sessions:
        return None

    # Return the most recent one
    return sessions[0]


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


def create_bot(bot_name: str, local: bool = False, description: Optional[str] = None) -> Path:
    """Create a new bot with default configuration.

    Args:
        bot_name: Name of the bot to create
        local: If True, create in local directory (.bots)
        description: Optional description of the bot

    Returns:
        Path to the created bot
    """
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
    config.name = bot_name
    config.emoji = DEFAULT_BOT_EMOJI
    config.init_cwd = os.getcwd()  # Save initial working directory

    if description:
        config.description = description

    config.save(bot_path)

    # Create default system prompt
    create_default_system_prompt(bot_path)

    return bot_path


def list_bots() -> Dict[str, List[Dict[str, str]]]:
    """List all available bots, both local and global, with their descriptions.

    Returns:
        Dict with 'global' and 'local' keys, each containing a list of dict with
        'name' and optional 'description' for each bot
    """
    global_path, local_path = get_bot_paths()

    result: Dict[str, List[Dict[str, str]]] = {"global": [], "local": []}

    # List global bots
    if global_path.exists():
        for p in global_path.iterdir():
            if p.is_dir():
                bot_info = {"name": p.name}
                try:
                    config = BotConfig.load(p)
                    if config.description:
                        bot_info["description"] = config.description
                    if config.emoji:
                        bot_info["emoji"] = config.emoji
                except Exception:
                    pass  # Just continue if we can't load the config
                result["global"].append(bot_info)

    # List local bots
    if local_path.exists():
        for p in local_path.iterdir():
            if p.is_dir():
                bot_info = {"name": p.name}
                try:
                    config = BotConfig.load(p)
                    if config.description:
                        bot_info["description"] = config.description
                    if config.emoji:
                        bot_info["emoji"] = config.emoji
                except Exception:
                    pass  # Just continue if we can't load the config
                result["local"].append(bot_info)

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


def delete_bot(bot_name: str) -> Path:
    """Delete a bot completely.

    Args:
        bot_name: The name of the bot to delete

    Returns:
        The path that was deleted

    Raises:
        FileNotFoundError: If the bot does not exist
    """
    bot_path = find_bot(bot_name)
    if not bot_path:
        raise FileNotFoundError(f"Bot '{bot_name}' not found")

    # Remove the entire bot directory with all its contents
    import shutil

    shutil.rmtree(bot_path)

    return bot_path


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

        print("\nThis is the old placeholder implementation.")
        print("Please use `bot run --name <name>` instead for the new implementation.")
