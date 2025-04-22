"""Tests for command module."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from bot.command import CommandExecutor
from bot.config import BotConfig, CommandPermissions
from bot.llm.schemas import CommandAction


class TestCommandExecutor:
    """Tests for CommandExecutor."""

    def test_validate_command_allowed(self):
        """Test validating allowed commands."""
        config = BotConfig(
            command_permissions=CommandPermissions(
                allow=["ls", "echo"],
                deny=["rm"],
                ask_if_unspecified=True,
            )
        )
        executor = CommandExecutor(config)

        assert executor.validate_command("ls -la") == CommandAction.EXECUTE
        assert executor.validate_command("echo hello") == CommandAction.EXECUTE

    def test_validate_command_denied(self):
        """Test validating denied commands."""
        config = BotConfig(
            command_permissions=CommandPermissions(
                allow=["ls", "echo"],
                deny=["rm", "sudo"],
                ask_if_unspecified=True,
            )
        )
        executor = CommandExecutor(config)

        assert executor.validate_command("rm -rf /") == CommandAction.DENY
        assert executor.validate_command("sudo apt-get update") == CommandAction.DENY

    def test_validate_command_ask(self):
        """Test validating commands that require asking."""
        config = BotConfig(
            command_permissions=CommandPermissions(
                allow=["ls", "echo"],
                deny=["rm"],
                ask_if_unspecified=True,
            )
        )
        executor = CommandExecutor(config)

        assert executor.validate_command("cat file.txt") == CommandAction.ASK
        assert executor.validate_command("grep pattern file.txt") == CommandAction.ASK

    def test_validate_command_default_deny(self):
        """Test validating commands with default deny policy."""
        config = BotConfig(
            command_permissions=CommandPermissions(
                allow=["ls", "echo"],
                deny=["rm"],
                ask_if_unspecified=False,
            )
        )
        executor = CommandExecutor(config)

        assert executor.validate_command("cat file.txt") == CommandAction.DENY
        assert executor.validate_command("grep pattern file.txt") == CommandAction.DENY

    @pytest.mark.asyncio
    async def test_execute_command_success(self):
        """Test executing a command successfully."""
        config = BotConfig()
        executor = CommandExecutor(config)

        # Mock subprocess
        with patch("asyncio.create_subprocess_shell") as mock_process:
            # Setup mock process
            process_mock = AsyncMock()
            process_mock.returncode = 0
            process_mock.communicate = AsyncMock(return_value=(b"command output", b""))
            mock_process.return_value = process_mock

            # Execute command
            stdout, exit_code, stderr = await executor.execute_command("echo test")

            # Check command execution
            mock_process.assert_called_with(
                "echo test",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Check results
            assert stdout == "command output"
            assert exit_code == 0
            assert stderr is None

    @pytest.mark.asyncio
    async def test_execute_command_error(self):
        """Test executing a command with an error."""
        config = BotConfig()
        executor = CommandExecutor(config)

        # Mock subprocess
        with patch("asyncio.create_subprocess_shell") as mock_process:
            # Setup mock process
            process_mock = AsyncMock()
            process_mock.returncode = 1
            process_mock.communicate = AsyncMock(return_value=(b"", b"command error"))
            mock_process.return_value = process_mock

            # Execute command
            stdout, exit_code, stderr = await executor.execute_command("invalid command")

            # Check results
            assert stdout == ""
            assert exit_code == 1
            assert stderr == "command error"

    @pytest.mark.asyncio
    async def test_execute_command_exception(self):
        """Test handling exceptions during command execution."""
        config = BotConfig()
        executor = CommandExecutor(config)

        # Mock subprocess to raise an exception
        with patch("asyncio.create_subprocess_shell", side_effect=Exception("Test error")):
            # Execute command
            stdout, exit_code, stderr = await executor.execute_command("problematic command")

            # Check results
            assert stdout == ""
            assert exit_code == 1
            assert stderr == "Test error"
