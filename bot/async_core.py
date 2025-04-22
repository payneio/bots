"""Async core functionality for bot."""

import asyncio
import datetime
from typing import Optional

from bot.config import BotConfig
from bot.core import find_bot


async def start_session(
    bot_name: str, one_shot: bool = False, prompt: Optional[str] = None
) -> None:
    """Start a bot session.

    Args:
        bot_name: The name of the bot to start
        one_shot: Whether to run in one-shot mode
        prompt: The user's prompt for one-shot mode
    """
    from bot.session import Session

    bot_path = find_bot(bot_name)
    if not bot_path:
        raise FileNotFoundError(f"Bot '{bot_name}' not found")

    # Load config
    try:
        config = BotConfig.load(bot_path)
    except Exception as e:
        raise RuntimeError(f"Failed to load bot configuration: {e}")

    # Add system prompt path to config for Session to use
    setattr(config, "system_prompt_path", bot_path / "system_prompt.md")

    # Create session directory
    timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    session_path = bot_path / "sessions" / timestamp

    # Initialize session
    session = Session(config, session_path)

    # Run session based on mode
    if one_shot:
        if prompt:
            await session.handle_one_shot(prompt)
        else:
            raise ValueError("Prompt is required for one-shot mode")
    else:
        await session.start_interactive()


def run_session(bot_name: str, one_shot: bool = False, prompt: Optional[str] = None) -> None:
    """Run a bot session with asyncio event loop.

    This is a synchronous wrapper around start_session for use in the CLI.

    Args:
        bot_name: The name of the bot to start
        one_shot: Whether to run in one-shot mode
        prompt: The user's prompt for one-shot mode
    """
    asyncio.run(start_session(bot_name, one_shot, prompt))
