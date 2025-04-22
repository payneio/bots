"""Command execution and security for bot."""

import asyncio
import shlex
from typing import Optional, Tuple

from bot.config import BotConfig
from bot.llm.schemas import CommandAction


class CommandExecutor:
    """Command execution with security controls."""

    def __init__(self, config: BotConfig):
        """Initialize the command executor.

        Args:
            config: The bot configuration
        """
        self.config = config

    def validate_command(self, command: str) -> CommandAction:
        """Validate a command against the bot's permissions.

        Args:
            command: The command to validate

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
        if base_command in self.config.command_permissions.allow:
            return CommandAction.EXECUTE

        # Check if command is explicitly denied
        if base_command in self.config.command_permissions.deny:
            return CommandAction.DENY

        # Check if we should ask for unspecified commands
        if self.config.command_permissions.ask_if_unspecified:
            return CommandAction.ASK

        # Default to deny
        return CommandAction.DENY

    async def execute_command(self, command: str) -> Tuple[str, int, Optional[str]]:
        """Execute a shell command safely.

        Args:
            command: The command to execute

        Returns:
            A tuple of (stdout, exit_code, stderr)
        """
        try:
            # Run the command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            # Get results
            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace") if stderr else None

            return stdout_text, process.returncode, stderr_text

        except Exception as e:
            return "", 1, str(e)
