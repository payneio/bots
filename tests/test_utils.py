"""Tests for utils module."""

from bots.permissions import CommandPermissions
from bots.llm.schemas import CommandAction
from bots.utils import _is_in_quotes, normalize_command, split_command, validate_command


class TestCommandValidation:
    """Tests for command validation utility."""

    def test_validate_command_allowed(self):
        """Test validating allowed commands."""
        allow_list = ["ls", "echo"]
        deny_list = ["rm"]
        ask_if_unspecified = True

        assert (
            validate_command("ls -la", allow_list, deny_list, ask_if_unspecified)
            == CommandAction.EXECUTE
        )
        assert (
            validate_command("echo hello", allow_list, deny_list, ask_if_unspecified)
            == CommandAction.EXECUTE
        )

    def test_validate_command_denied(self):
        """Test validating denied commands."""
        allow_list = ["ls", "echo"]
        deny_list = ["rm", "sudo"]
        ask_if_unspecified = True

        assert (
            validate_command("rm -rf /", allow_list, deny_list, ask_if_unspecified)
            == CommandAction.DENY
        )
        assert (
            validate_command("sudo apt-get update", allow_list, deny_list, ask_if_unspecified)
            == CommandAction.DENY
        )

    def test_validate_command_ask(self):
        """Test validating commands that require asking."""
        allow_list = ["ls", "echo"]
        deny_list = ["rm"]
        ask_if_unspecified = True

        assert (
            validate_command("cat file.txt", allow_list, deny_list, ask_if_unspecified)
            == CommandAction.ASK
        )
        assert (
            validate_command("grep pattern file.txt", allow_list, deny_list, ask_if_unspecified)
            == CommandAction.ASK
        )

    def test_validate_command_default_deny(self):
        """Test validating commands with default deny policy."""
        allow_list = ["ls", "echo"]
        deny_list = ["rm"]
        ask_if_unspecified = False

        assert (
            validate_command("cat file.txt", allow_list, deny_list, ask_if_unspecified)
            == CommandAction.DENY
        )
        assert (
            validate_command("grep pattern file.txt", allow_list, deny_list, ask_if_unspecified)
            == CommandAction.DENY
        )

    def test_validate_command_with_complex_parsing(self):
        """Test validating commands with quoted arguments and special characters."""
        allow_list = ["echo", "printf"]
        deny_list = ["rm"]
        ask_if_unspecified = True

        assert (
            validate_command('echo "Hello World"', allow_list, deny_list, ask_if_unspecified)
            == CommandAction.EXECUTE
        )
        assert (
            validate_command("printf 'Hello\\nWorld'", allow_list, deny_list, ask_if_unspecified)
            == CommandAction.EXECUTE
        )

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
        assert (
            validate_command('echo "unbalanced', allow_list, deny_list, ask_if_unspecified)
            == CommandAction.EXECUTE
        )


class TestCommandNormalization:
    """Tests for command normalization utility."""

    def test_is_in_quotes(self):
        """Test is_in_quotes function."""
        # Position inside double quotes
        assert _is_in_quotes('echo "hello world"', 7) is True
        # Position inside single quotes
        assert _is_in_quotes("echo 'hello world'", 7) is True
        # Position outside quotes
        assert _is_in_quotes('echo "hello" world', 14) is False
        # Escaped quotes should not count
        assert _is_in_quotes('echo \\"hello world', 7) is False
        # Nested quotes (single in double)
        assert _is_in_quotes("echo \"hello 'world'\"", 13) is True
        # Empty string
        assert _is_in_quotes("", 0) is False

    def test_split_command_simple(self):
        """Test splitting simple commands."""
        result = split_command("ls -la")
        assert len(result) == 1
        assert result[0]["raw_command"] == "ls -la"
        assert result[0]["operator"] is None

        # Empty command
        assert split_command("") == []

        # Command with only whitespace
        assert split_command("   ") == []

    def test_split_command_pipe(self):
        """Test splitting commands with pipe operator."""
        result = split_command("ls -la | grep file")
        assert len(result) == 2
        assert result[0]["raw_command"] == "ls -la"
        assert result[0]["operator"] == "|"
        assert result[1]["raw_command"] == "grep file"
        assert result[1]["operator"] is None

    def test_split_command_multiple_operators(self):
        """Test splitting commands with multiple operators."""
        result = split_command("find . -name '*.py' | xargs grep 'import' && echo 'Done'")
        assert len(result) == 3
        assert result[0]["raw_command"] == "find . -name '*.py'"
        assert result[0]["operator"] == "|"
        assert result[1]["raw_command"] == "xargs grep 'import'"
        assert result[1]["operator"] == "&&"
        assert result[2]["raw_command"] == "echo 'Done'"
        assert result[2]["operator"] is None

    def test_split_command_with_quotes(self):
        """Test splitting commands with quoted sections."""
        # Quoted operators should be ignored
        result = split_command("echo 'hello | world' | grep hello")
        assert len(result) == 2
        assert result[0]["raw_command"] == "echo 'hello | world'"
        assert result[0]["operator"] == "|"

        # Double quotes
        result = split_command('echo "hello | world" | grep hello')
        assert len(result) == 2
        assert result[0]["raw_command"] == 'echo "hello | world"'

        # Escaped quotes
        result = split_command('echo \\"hello | grep hello')
        assert len(result) == 2
        assert result[0]["raw_command"] == 'echo \\"hello'

    def test_normalize_command_simple(self):
        """Test normalizing simple commands."""
        result = normalize_command("ls -la")
        assert len(result) == 1
        assert result[0]["command"] == "ls"
        assert result[0]["args"] == ["-la"]
        assert result[0]["has_redirection"] is False

        # Empty command
        assert normalize_command("") == []

    def test_normalize_command_compound(self):
        """Test normalizing compound commands."""
        result = normalize_command("ls -la | grep file")
        assert len(result) == 2
        assert result[0]["command"] == "ls"
        assert result[0]["args"] == ["-la"]
        assert result[1]["command"] == "grep"
        assert result[1]["args"] == ["file"]

    def test_normalize_command_with_redirection(self):
        """Test normalizing commands with redirection."""
        result = normalize_command("ls -la > output.txt")
        assert len(result) == 1
        assert result[0]["command"] == "ls"
        assert result[0]["args"] == ["-la"]
        assert result[0]["has_redirection"] is True

        # Multiple redirections
        result = normalize_command("ls -la > output.txt 2> error.log")
        assert len(result) == 1
        assert result[0]["command"] == "ls"
        assert result[0]["args"] == ["-la"]
        assert result[0]["has_redirection"] is True

    def test_normalize_command_with_quotes(self):
        """Test normalizing commands with quoted arguments."""
        result = normalize_command('echo "Hello World"')
        assert len(result) == 1
        assert result[0]["command"] == "echo"
        assert result[0]["args"] == ["Hello World"]

        # Single quotes
        result = normalize_command("echo 'Hello World'")
        assert len(result) == 1
        assert result[0]["command"] == "echo"
        assert result[0]["args"] == ["Hello World"]

        # Mixed quotes
        result = normalize_command("echo \"Hello 'World'\"")
        assert len(result) == 1
        assert result[0]["command"] == "echo"
        assert result[0]["args"] == ["Hello 'World'"]

    def test_normalize_command_bash_c(self):
        """Test normalizing bash -c commands."""
        result = normalize_command('bash -c "ls -la"')
        assert len(result) == 1
        assert result[0]["command"] == "ls"
        assert result[0]["args"] == ["-la"]
        assert result[0]["via_bash"] is True

        # Complex bash command
        result = normalize_command("bash -c \"find . -name '*.py' | xargs grep pattern\"")
        assert len(result) == 1  # Parsed as a single command through bash
        assert result[0]["command"] == "find"
        assert result[0]["via_bash"] is True

        # Unparseable bash command
        result = normalize_command('bash -c "echo `date` > file.txt"')
        assert len(result) == 1
        assert result[0]["command"] == "echo"
        assert result[0]["via_bash"] is True

    def test_normalize_command_unparseable(self):
        """Test normalizing commands with unparseable syntax."""
        # Unbalanced quotes
        result = normalize_command('echo "unbalanced')
        assert len(result) == 1
        assert result[0]["command"] == "echo"
        assert len(result[0]["args"]) == 1

        # Invalid syntax
        result = normalize_command("echo $((1+2)")
        assert len(result) == 1
        assert result[0]["command"] == "echo"
        assert len(result[0]["args"]) == 1

    def test_normalize_command_complex(self):
        """Test normalizing complex commands with multiple features."""
        result = normalize_command(
            'find . -name "*.py" | xargs grep "import os" > results.txt && echo "Done" | cat'
        )
        assert len(result) == 4
        assert result[0]["command"] == "find"
        assert result[0]["args"] == [".", "-name", "*.py"]
        assert result[1]["command"] == "xargs"
        assert result[1]["args"] == ["grep", "import os"]
        assert result[1]["has_redirection"] is True
        assert result[2]["command"] == "echo"
        assert result[2]["args"] == ["Done"]
        assert result[3]["command"] == "cat"
        assert result[3]["args"] == []


class TestCommandPermissions:
    """Tests for enhanced command permissions."""

    def test_basic_validation(self):
        """Test basic command permission validation."""
        permissions = CommandPermissions(
            allow=["ls", "echo", "cat:*.txt"], deny=["rm", "sudo"], ask_if_unspecified=True
        )

        # Simple commands
        assert permissions.validate_command("ls -la") == CommandAction.EXECUTE
        assert permissions.validate_command("rm -rf") == CommandAction.DENY
        assert permissions.validate_command("grep pattern file.txt") == CommandAction.ASK

        # Pattern matching
        assert permissions.validate_command("cat file.txt") == CommandAction.EXECUTE
        assert permissions.validate_command("cat file.log") == CommandAction.ASK

    def test_compound_commands(self):
        """Test validation of compound commands."""
        permissions = CommandPermissions(
            allow=["ls", "grep", "cat:*.txt"], deny=["rm", "sudo"], ask_if_unspecified=True
        )

        # All components allowed
        assert permissions.validate_command("ls -la | grep pattern") == CommandAction.EXECUTE

        # One component denied - whole command denied
        assert permissions.validate_command("ls -la | sudo grep pattern") == CommandAction.DENY

        # One component needs asking - whole command needs asking
        assert permissions.validate_command("ls -la | awk '{print $1}'") == CommandAction.ASK

        # Multiple components with different permissions
        assert (
            permissions.validate_command("ls -la | grep pattern | sudo cat") == CommandAction.DENY
        )
        assert (
            permissions.validate_command("ls -la | grep pattern | cat file.log")
            == CommandAction.ASK
        )
        assert (
            permissions.validate_command("ls -la | grep pattern | cat file.txt")
            == CommandAction.EXECUTE
        )

    def test_pattern_matching(self):
        """Test glob pattern matching in permissions."""
        permissions = CommandPermissions(
            allow=["ls", "echo:Hello*", "git:status", "find:* -name *.py"],
            deny=[
                "rm:*-rf*",
                "wget:http*",
                "curl:*-X POST*",
                "sudo",  # Deny all sudo regardless of args
            ],
            ask_if_unspecified=True,
        )

        # Allowed patterns
        assert permissions.validate_command("echo Hello World") == CommandAction.EXECUTE
        assert permissions.validate_command("echo HelloWorld") == CommandAction.EXECUTE
        assert permissions.validate_command("git status") == CommandAction.EXECUTE
        assert permissions.validate_command("find . -name *.py") == CommandAction.EXECUTE

        # Denied patterns
        assert permissions.validate_command("rm -rf temp") == CommandAction.DENY
        assert permissions.validate_command("wget http://example.com") == CommandAction.DENY
        assert (
            permissions.validate_command("curl -X POST http://api.example.com")
            == CommandAction.DENY
        )

        # Command without pattern is allowed for all args
        assert permissions.validate_command("ls -la") == CommandAction.EXECUTE
        assert permissions.validate_command("ls --color=auto") == CommandAction.EXECUTE
        assert permissions.validate_command("ls -R /tmp") == CommandAction.EXECUTE

        # Command without pattern in deny list denies all uses
        assert permissions.validate_command("sudo ls") == CommandAction.DENY
        assert permissions.validate_command("sudo apt update") == CommandAction.DENY
        assert permissions.validate_command("sudo -u user command") == CommandAction.DENY

        # Non-matching patterns
        assert permissions.validate_command("echo Goodbye") == CommandAction.ASK
        assert permissions.validate_command("git push") == CommandAction.ASK
        assert permissions.validate_command("find . -name *.txt") == CommandAction.ASK

        # Edge cases
        assert (
            permissions.validate_command("rm file.txt") == CommandAction.ASK
        )  # Not matching rm:-rf pattern

    def test_command_approval_caching(self):
        """Test caching of command approvals."""
        permissions = CommandPermissions(allow=["ls"], deny=["rm"], ask_if_unspecified=True)

        # Initially this command needs asking
        assert permissions.validate_command("cat file.txt") == CommandAction.ASK

        # Approve it
        permissions.approve_command("cat file.txt")

        # Now it should be allowed without asking
        assert permissions.validate_command("cat file.txt") == CommandAction.EXECUTE

        # Test persistence
        permissions.approve_command("echo hello", always=True)
        assert "echo:hello" in permissions.allow

        # Deny a command
        permissions.deny_command("wget example.com")
        assert permissions.validate_command("wget example.com") == CommandAction.DENY

        # Test permanent denial
        permissions.deny_command("curl example.com", always=True)
        assert "curl:example.com" in permissions.deny

    def test_compound_command_approval(self):
        """Test approval of compound commands."""
        permissions = CommandPermissions(allow=["ls"], deny=["rm"], ask_if_unspecified=True)

        # Initially this compound command needs asking
        assert permissions.validate_command("ls | grep pattern") == CommandAction.ASK

        # Approve it
        permissions.approve_command("ls | grep pattern")

        # Now both components should be approved
        assert permissions.validate_command("grep pattern") == CommandAction.EXECUTE

        # The compound command should also work
        assert permissions.validate_command("ls | grep pattern") == CommandAction.EXECUTE

        # But a variation would still need asking
        assert permissions.validate_command("ls | grep different") == CommandAction.ASK

    def test_bash_c_commands(self):
        """Test special handling of bash -c commands."""
        permissions = CommandPermissions(allow=["ls", "bash"], deny=["rm"], ask_if_unspecified=True)

        # Test extraction of the real command
        assert permissions.validate_command('bash -c "ls -la"') == CommandAction.EXECUTE
        assert permissions.validate_command('bash -c "rm -rf temp"') == CommandAction.DENY
        assert permissions.validate_command('bash -c "cat file.txt"') == CommandAction.ASK

        # Approve a command through bash -c
        permissions.approve_command('bash -c "cat file.txt"')

        # The extracted command should be approved
        assert permissions.validate_command("cat file.txt") == CommandAction.EXECUTE
