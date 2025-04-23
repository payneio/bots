"""Utility functions for the bot."""

import shlex
from typing import List

from bot.llm.schemas import CommandAction


def validate_command(command: str, allow_list: List[str], deny_list: List[str], ask_if_unspecified: bool) -> CommandAction:
    """Validate a command against permission lists.

    Args:
        command: The command to validate
        allow_list: List of allowed command prefixes
        deny_list: List of denied command prefixes
        ask_if_unspecified: Whether to ask for permission for unspecified commands

    Returns:
        The action to take for this command
    """
    # Extract the base command (first word before any spaces or special chars)
    try:
        parsed = shlex.split(command)
        base_command = parsed[0] if parsed else ""
    except Exception:
        # If we can't parse it, just get the first word
        base_command = command.split()[0] if command else ""

    # Check if command is explicitly allowed
    if base_command in allow_list:
        return CommandAction.EXECUTE

    # Check if command is explicitly denied
    if base_command in deny_list:
        return CommandAction.DENY

    # Check if we should ask for unspecified commands
    if ask_if_unspecified:
        return CommandAction.ASK

    # Default to deny
    return CommandAction.DENY