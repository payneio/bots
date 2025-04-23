"""Tests for utils module."""

import pytest

from bot.llm.schemas import CommandAction
from bot.utils import validate_command


class TestCommandValidation:
    """Tests for command validation utility."""

    def test_validate_command_allowed(self):
        """Test validating allowed commands."""
        allow_list = ["ls", "echo"]
        deny_list = ["rm"]
        ask_if_unspecified = True

        assert validate_command("ls -la", allow_list, deny_list, ask_if_unspecified) == CommandAction.EXECUTE
        assert validate_command("echo hello", allow_list, deny_list, ask_if_unspecified) == CommandAction.EXECUTE

    def test_validate_command_denied(self):
        """Test validating denied commands."""
        allow_list = ["ls", "echo"]
        deny_list = ["rm", "sudo"]
        ask_if_unspecified = True

        assert validate_command("rm -rf /", allow_list, deny_list, ask_if_unspecified) == CommandAction.DENY
        assert validate_command("sudo apt-get update", allow_list, deny_list, ask_if_unspecified) == CommandAction.DENY

    def test_validate_command_ask(self):
        """Test validating commands that require asking."""
        allow_list = ["ls", "echo"]
        deny_list = ["rm"]
        ask_if_unspecified = True

        assert validate_command("cat file.txt", allow_list, deny_list, ask_if_unspecified) == CommandAction.ASK
        assert validate_command("grep pattern file.txt", allow_list, deny_list, ask_if_unspecified) == CommandAction.ASK

    def test_validate_command_default_deny(self):
        """Test validating commands with default deny policy."""
        allow_list = ["ls", "echo"]
        deny_list = ["rm"]
        ask_if_unspecified = False

        assert validate_command("cat file.txt", allow_list, deny_list, ask_if_unspecified) == CommandAction.DENY
        assert validate_command("grep pattern file.txt", allow_list, deny_list, ask_if_unspecified) == CommandAction.DENY

    def test_validate_command_with_complex_parsing(self):
        """Test validating commands with quoted arguments and special characters."""
        allow_list = ["echo", "printf"]
        deny_list = ["rm"]
        ask_if_unspecified = True

        assert validate_command('echo "Hello World"', allow_list, deny_list, ask_if_unspecified) == CommandAction.EXECUTE
        assert validate_command("printf 'Hello\\nWorld'", allow_list, deny_list, ask_if_unspecified) == CommandAction.EXECUTE

    def test_validate_empty_command(self):
        """Test validating an empty command."""
        allow_list = ["ls", "echo"]
        deny_list = ["rm"]
        ask_if_unspecified = True

        assert validate_command("", allow_list, deny_list, ask_if_unspecified) == CommandAction.ASK

    def test_validate_command_with_unparseable_syntax(self):
        """Test validating a command with syntax that can't be parsed by shlex."""
        allow_list = ["ls", "echo"]
        deny_list = ["rm"]
        ask_if_unspecified = True

        # A command with unbalanced quotes would use the fallback parsing
        assert validate_command('echo "unbalanced', allow_list, deny_list, ask_if_unspecified) == CommandAction.EXECUTE