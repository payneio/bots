"""Core functionality for bot."""

import asyncio
import datetime
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from bots.config import DEFAULT_BOT_EMOJI, BotConfig, create_default_system_prompt
from bots.session import Session


def get_bot_paths() -> Tuple[Path, Path]:
    """Get paths for global and local bots."""
    global_path = Path.home() / ".config" / "bots"
    local_path = Path.cwd() / ".bots"
    return global_path, local_path


def get_known_bots_file() -> Path:
    """Get path to the known-bots.txt file.

    This file contains paths to local bots that have been registered for
    discovery from other directories.

    Returns:
        Path to the known-bots.txt file
    """
    global_path, _ = get_bot_paths()
    return global_path / "known-bots.txt"


def register_bot(bot_path: Path) -> None:
    """Register a bot in the known-bots.txt file for discovery.

    Args:
        bot_path: Absolute path to the bot directory
    """
    known_bots_file = get_known_bots_file()

    # Create global directory if it doesn't exist
    known_bots_file.parent.mkdir(parents=True, exist_ok=True)

    # Read existing entries or create empty list
    known_bots = []
    if known_bots_file.exists():
        with open(known_bots_file, "r") as f:
            known_bots = [line.strip() for line in f if line.strip()]

    # Convert to absolute path string
    bot_path_str = str(bot_path.absolute())

    # Add bot path if not already in the list
    if bot_path_str not in known_bots:
        known_bots.append(bot_path_str)

        # Write back to file
        with open(known_bots_file, "w") as f:
            for path in known_bots:
                f.write(f"{path}\n")


def register_local_bot(bot_name: str) -> Path:
    """Register a local bot in the known-bots.txt file for discovery from any directory.

    This function looks for a bot with the given name in the local directory (.bots)
    and registers it in the global known-bots.txt file so it can be discovered
    from any directory.

    Args:
        bot_name: Name of the local bot to register

    Returns:
        Path to the registered bot

    Raises:
        FileNotFoundError: If the bot is not found in the local directory
    """
    _, local_path = get_bot_paths()

    # Check if the bot exists in the local directory
    bot_path = local_path / bot_name
    if not bot_path.exists():
        raise FileNotFoundError(f"Local bot '{bot_name}' not found in {local_path}")

    # Register the bot
    register_bot(bot_path)

    return bot_path


def find_latest_session(bot_name: str) -> Optional[Path]:
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
    """Find a bot by name, checking local, global, and registered paths."""
    global_path, local_path = get_bot_paths()

    # Check local first, then global
    local_bot_path = local_path / bot_name
    if local_bot_path.exists():
        return local_bot_path

    global_bot_path = global_path / bot_name
    if global_bot_path.exists():
        return global_bot_path

    # If not found in local or global, check registered bots
    known_bots_file = get_known_bots_file()
    if known_bots_file.exists():
        with open(known_bots_file, "r") as f:
            registered_paths = [line.strip() for line in f if line.strip()]

            # Check each registered path to see if it matches the bot name
            for path_str in registered_paths:
                try:
                    path = Path(path_str)
                    if path.exists() and path.is_dir() and path.name == bot_name:
                        return path
                except Exception:
                    # Skip invalid paths
                    continue

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

    # Register local bots for discovery from any directory
    if local:
        register_bot(bot_path)

    return bot_path


def list_bots() -> Dict[str, List[Dict[str, str]]]:
    """List all available bots, both local and global, with their descriptions.

    Returns:
        Dict with 'global', 'local', and 'registered' keys, each containing a list of dict with
        'name', 'path', and optional 'description' for each bot
    """
    global_path, local_path = get_bot_paths()

    result: Dict[str, List[Dict[str, str]]] = {"global": [], "local": [], "registered": []}

    # Track processed paths to avoid duplicates
    processed_paths = set()

    # List global bots
    if global_path.exists():
        for p in global_path.iterdir():
            if (
                p.is_dir() and p.name != "known-bots.txt"
            ):  # Skip the known-bots file if it's a directory
                processed_paths.add(str(p.absolute()))
                bot_info = {"name": p.name, "path": str(p)}
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
                processed_paths.add(str(p.absolute()))
                bot_info = {"name": p.name, "path": str(p)}
                try:
                    config = BotConfig.load(p)
                    if config.description:
                        bot_info["description"] = config.description
                    if config.emoji:
                        bot_info["emoji"] = config.emoji
                except Exception:
                    pass  # Just continue if we can't load the config
                result["local"].append(bot_info)

    # List registered bots from known-bots.txt
    known_bots_file = get_known_bots_file()
    if known_bots_file.exists():
        try:
            with open(known_bots_file, "r") as f:
                for line in f:
                    bot_path_str = line.strip()
                    if not bot_path_str or bot_path_str in processed_paths:
                        continue

                    bot_path = Path(bot_path_str)
                    if not bot_path.exists() or not bot_path.is_dir():
                        continue

                    # Add to processed paths to avoid duplicates
                    processed_paths.add(bot_path_str)

                    # Get the bot name from the directory name
                    bot_name = bot_path.name

                    bot_info = {"name": bot_name, "path": bot_path_str}
                    try:
                        config = BotConfig.load(bot_path)
                        if config.description:
                            bot_info["description"] = config.description
                        if config.emoji:
                            bot_info["emoji"] = config.emoji
                    except Exception:
                        pass  # Just continue if we can't load the config

                    result["registered"].append(bot_info)
        except Exception:
            pass  # Continue if there's an issue reading the known-bots file

    return result


def rename_bot(old_name: str, new_name: str) -> Path:
    """Rename a bot from old_name to new_name."""
    old_path = find_bot(old_name)
    if not old_path:
        raise FileNotFoundError(f"Bot '{old_name}' not found")

    # Determine if this is a local or global bot
    is_local = ".bots" in str(old_path)
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


def source_script(script_path: Path, debug: bool = False) -> None:
    """Source startup.sh if it exists in the bot's config directory"""

    if script_path.exists():
        try:
            # Source the script and capture its output
            if debug:
                print(f"Sourcing startup script: {script_path}")
            # The command sources the script in a new shell and exports all variables to the current environment
            result = subprocess.run(
                f"source {str(script_path)} && env",
                shell=True,
                text=True,
                capture_output=True,
                executable="/bin/bash",
            )
            if result.returncode == 0:
                # Parse the environment variables and set them in the current process
                for line in result.stdout.splitlines():
                    if "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key] = value
                if debug:
                    print("Startup script sourced successfully")
            else:
                if debug:
                    print(f"Error running startup script: {result.stderr}")
        except Exception as e:
            if debug:
                print(f"Error sourcing startup script: {e}")


async def start_session(
    bot_name: str,
    one_shot: bool = False,
    prompt: Optional[str] = None,
    debug: bool = False,
    continue_session: bool = False,
) -> None:
    """Start a bot session.

    Args:
        bot_name: The name of the bot to start
        one_shot: Whether to run in one-shot mode
        prompt: The user's prompt for one-shot mode
        debug: Whether to print debug information
        continue_session: Whether to continue from previous session
    """

    # Load config
    bot_path = find_bot(bot_name)
    if not bot_path:
        raise FileNotFoundError(f"Bot '{bot_name}' not found")
    try:
        config = BotConfig.load(bot_path)
    except Exception as e:
        raise RuntimeError(f"Failed to load bot configuration: {e}")
    config.system_prompt_path = str(bot_path / "system_prompt.md")
    if not config.init_cwd:
        config.init_cwd = os.getcwd()

    source_script(bot_path / "startup.sh", debug)

    # Initialize session

    if continue_session:
        session_path = find_latest_session(bot_name)
    else:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        session_path = bot_path / "sessions" / timestamp
        session_path.mkdir(parents=True, exist_ok=True)

    session = Session(
        config,
        session_path,
        debug,
        continue_session,
    )

    if one_shot:
        if prompt:
            await session.handle_one_shot(prompt)
        else:
            raise ValueError("Prompt is required for one-shot mode")
    else:
        await session.start_interactive()


def run_session(
    bot_name: str,
    one_shot: bool = False,
    prompt: Optional[str] = None,
    debug: bool = False,
    continue_session: bool = False,
) -> None:
    """Run a bot session with asyncio event loop.

    This is a synchronous wrapper around start_session for use in the CLI.

    Args:
        bot_name: The name of the bot to start
        one_shot: Whether to run in one-shot mode
        prompt: The user's prompt for one-shot mode
        debug: Whether to print debug information
        continue_session: Whether to continue from previous session
    """
    asyncio.run(start_session(bot_name, one_shot, prompt, debug, continue_session))
