"""Command permissions management for bots."""

import re
import shlex
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class Permission(Enum):
    DENY = "DENY"
    APPROVE = "APPROVE"
    ASK = "ASK"


@dataclass
class Command:
    command: str
    has_redirection: bool = False
    via_bash: bool = False
    invalid: bool = False


def _is_in_quotes(string: str, position: int) -> bool:
    """Check if a position in a string is inside quotes.

    Args:
        string: The string to check
        position: The position to check

    Returns:
        True if the position is inside quotes, False otherwise
    """
    in_single_quotes = False
    in_double_quotes = False
    escaped = False

    for i, char in enumerate(string):
        if i >= position:
            break

        if char == "\\" and not escaped:
            escaped = True
            continue

        if char == '"' and not escaped and not in_single_quotes:
            in_double_quotes = not in_double_quotes
        elif char == "'" and not escaped and not in_double_quotes:
            in_single_quotes = not in_single_quotes

        escaped = False

    return in_single_quotes or in_double_quotes


def split_command(command: str) -> List[Dict[str, Any]]:
    """Split a command into its components.

    Handles compound commands with pipes, redirections, etc.

    Args:
        command: The command string to split

    Returns:
        List of command components, where each component is a dict with:
        - raw_command: The raw command string for this component
        - operator: Optional operator that follows this command (|, &&, ||, etc.)
    """
    # Special handling for compound commands
    compound_operators = ["|", "&&", "||", ";"]

    # First, try to identify compound commands
    components: List[Dict[str, Any]] = []
    current_command = ""
    in_quotes = False
    quote_char = None
    escaped = False

    # Simple parsing to split on operators while respecting quotes
    i = 0
    while i < len(command):
        char = command[i]

        # Handle escape sequences
        if char == "\\" and not escaped:
            escaped = True
            current_command += char
            i += 1
            continue

        # Handle quotes
        if char in ['"', "'"] and not escaped:
            if not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char:
                in_quotes = False
                quote_char = None

        # If we're in quotes, just add the character
        if in_quotes:
            current_command += char
            escaped = False
            i += 1
            continue

        # Check for operators when not in quotes
        found_operator = False
        for op in compound_operators:
            if command[i : i + len(op)] == op:
                # We found an operator - add the current command and the operator
                if current_command.strip():
                    components.append({"raw_command": current_command.strip(), "operator": op})
                current_command = ""
                found_operator = True
                i += len(op)
                break

        if found_operator:
            continue

        # No operator, just add the character
        current_command += char
        escaped = False
        i += 1

    # Add the last command if any
    if current_command.strip():
        components.append({"raw_command": current_command.strip(), "operator": None})

    return components


def normalize_command(command: str) -> List[Command]:
    """Normalize a command into components.

    Handles compound commands, redirections, and shell syntax.

    Args:
        command: The command string to normalize

    Returns:
        List of command components, where each component is a dict with:
        - command: The base command name
        - args: List of arguments
        - has_redirection: Whether this component includes redirection
        - via_bash: Whether this command is executed via bash -c
    """
    # Special handling for redirections
    redirection_operators = [">", ">>", "<", "<<", "2>", "2>>", "&>", "&>>"]

    # First split the command into parts by compound operators
    components = split_command(command)
    normalized_components: List[Command] = []

    # Now process each component to extract command and args
    for component in components:
        raw_cmd = component["raw_command"]

        # Handle redirections within this component
        # FIXME: Check this.
        has_redirection = False
        for redirection in redirection_operators:
            if redirection in raw_cmd and not _is_in_quotes(raw_cmd, raw_cmd.find(redirection)):
                # Split on redirection, keep only the command part
                raw_cmd = raw_cmd.split(redirection, 1)[0].strip()
                has_redirection = True
                break

        # Parse the command part
        try:
            parsed = shlex.split(raw_cmd)
            if not parsed:
                continue

            # Handle bash -c pattern
            if parsed[0] == "bash" and len(parsed) >= 3 and parsed[1] in ["-c", "-lc"]:
                normalized_components.append(
                    Command(
                        command=parsed[2],
                        has_redirection=has_redirection,
                        via_bash=True,
                    )
                )
            else:
                normalized_components.append(
                    Command(
                        command=raw_cmd,
                        has_redirection=has_redirection,
                    )
                )

        except Exception:
            # Fallback to simple splitting
            parts = raw_cmd.split()
            if parts:
                normalized_components.append(
                    Command(command=raw_cmd, has_redirection=has_redirection, invalid=True)
                )

    return normalized_components


def matches_rule(command_string: str, rule: str) -> bool:
    """Match a command string against a rule.

    Rules are in the form of "command:filter" where filter is optional.
    Filter can be a short flag (starting with `-`), or a long flag (starting with `--`)
    The rule will match if the command_string starts with the rule command AND
    (if a filter is specified) the short or long flag is present.

    Args:
        command_string: The command to check
        rule: The rule to match against

    Returns:
        True if the command matches the rule, False otherwise
    """
    # Split the rule into command and filter
    if ":" in rule:
        rule_command, rule_filter = rule.split(":", 1)
    else:
        rule_command = rule
        rule_filter = None

    # Empty rule_command should not match anything
    if not rule_command:
        return False

    # Check if the rule parts are all represented in the command string
    command_parts = command_string.split()
    rule_parts = rule_command.split()
    for part in rule_parts:
        if not command_parts or part != command_parts[0]:
            return False
        command_parts.pop(0)

    # If no filter specified and command matches, return True
    if not rule_filter:
        return True

    # If there's a filter, check if it is short or long
    is_short = rule_filter.startswith("-") and not rule_filter.startswith("--")
    is_long = rule_filter.startswith("--")

    if is_short:
        # Create a pattern to match short flags
        # For example, if rule_filter is "-la", look for "-la", "-al", etc.
        flags = [c for c in rule_filter if c != "-"]
        if not flags:  # If there are no actual flags after the dash
            return False

        for flag in flags:
            # Check if the flag character is present in a short flag group
            flag_pattern = re.compile(rf"(?<!\S)-[a-zA-Z]*{re.escape(flag)}[a-zA-Z]*")
            if not flag_pattern.search(command_string):
                return False
        return True
    elif is_long:
        # For long flags, check for exact match in command parts
        # This handles cases with dashes in the flag like --no-pager
        cmd_parts = command_string.split()
        return rule_filter in cmd_parts

    return False


class CommandPermissions(BaseModel):
    """Command permissions configuration."""

    allow: List[str] = Field(
        default_factory=list,
        description="Commands the bot can run freely. Format: 'command' or 'command:arg_pattern'",
    )
    deny: List[str] = Field(
        default_factory=list,
        description="Commands the bot is explicitly blocked from running. Format: 'command' or 'command:arg_pattern'",
    )
    ask_if_unspecified: bool = Field(
        default=True, description="Ask for permission for unspecified commands"
    )

    # This will be used to cache command approvals within a session
    _approved_commands: Dict[str, bool] = {}

    def permit_command(self, command: str) -> Permission:
        components = normalize_command(command)
        if not components:
            return Permission.ASK

        results = []

        for component in components:

            base_cmd = component.command.split()[0] if component.command else ""

            if component.invalid:
                return Permission.DENY
            # Deny
            command_deny_rules = [rule for rule in self.deny if rule.split()[0] == base_cmd]
            for rule in command_deny_rules:
                if matches_rule(component.command, rule):
                    return Permission.DENY

            # Allow
            command_allow_rules = [rule for rule in self.allow if rule.split()[0] == base_cmd]
            allowed = False
            for rule in command_allow_rules:
                if matches_rule(component.command, rule):
                    allowed = True
                    break

            results.append(Permission.APPROVE if allowed else Permission.ASK)

        if Permission.ASK in results:
            return Permission.ASK

        return Permission.APPROVE

    @classmethod
    def default_safe_permissions(cls) -> "CommandPermissions":
        """Create default permissions with safe read-only commands.

        Returns:
            CommandPermissions with pre-configured safe defaults
        """
        # Safe, read-only commands with pattern matching
        read_only_commands = [
            # File viewing and navigation
            "ls",
            "dir",
            "pwd",
            "cd",
            "find",
            "locate",
            "which",
            "whereis",
            "type",
            "file",
            "stat",
            "du",
            "df",
            # File content viewing
            "cat",
            "less",
            "more",
            "head",
            "tail",
            "strings",
            "xxd",
            "hexdump",
            # Text search and grep
            "grep",
            "egrep",
            "fgrep",
            "rg",
            "ag",
            "ack",
            # Text processing
            "echo",
            "printf",
            "wc",
            "sort",
            "uniq",
            "cut",
            "tr",
            "sed",
            "awk",
            "jq",
            "yq",
            "fmt",
            "nl",
            "column",
            "paste",
            "join",
            "fold",
            "expand",
            "unexpand",
            # System information
            "date",
            "cal",
            "uptime",
            "w",
            "whoami",
            "id",
            "groups",
            "uname",
            "hostname",
            "lsb_release",
            "env",
            "printenv",
            "set",
            "locale",
            # Process information (read-only)
            "ps",
            "top",
            "htop",
            "pgrep",
            "jobs",
            "lsof",
            # Network information (read-only)
            "ip",
            "ifconfig",
            "netstat",
            "ss",
            "ping",
            "traceroute",
            "dig",
            "host",
            "nslookup",
            "whois",
            # Non-modifying network requests
            "curl",
            "wget",
            "nc",
            "telnet",
            # Package information (read-only)
            "apt-cache",
            "dpkg:-l",
            "rpm:-q",
            "pacman:-Q",
            "brew list",
            "brew info",
            "npm list",
            "pip list",
            "gem list",
            "conda list",
            # Version information
            "version",
            "help",
            # Git read operations
            "git",  # Allow any git command (safer option would be to list specific commands)
            "git status",
            "git log",
            "git show",
            "git diff",
            "git ls-files",
            "git branch",
            "git tag",
            "git remote",
            "git config:-l",
            "git config:--list",
            # Docker read operations
            "docker ps",
            "docker images",
            "docker volume ls",
            "docker network ls",
            "docker inspect",
            # Additional command patterns for common compound commands
            "xargs:grep *",
            "xargs",
            # Compression view (specific patterns needed since these can extract files too)
            "tar:-tf",
            "tar:--list",
            "unzip:-l",
            "unzip:-v",
            "gzip:-l",
            "zip:-sf",
        ]

        # Commands that could disrupt the system
        denied_commands = [
            # System power commands
            "shutdown",
            "reboot",
            "poweroff",
            "halt",
            # System modifications
            "umount",
            "mkfs",
            "fdisk",
            "parted",
            # Package management that modifies system
            "apt-get install",
            "apt-get remove",
            "apt-get purge",
            "apt install",
            "apt remove",
            "apt purge",
            "yum install",
            "yum remove",
            "yum update",
            "pacman:-S",
            "pacman:-R",
            "pacman:-U",
            "nano",
            "vim",
            "vi",
            "emacs",
            "pico",
            "ed",
        ]

        return cls(
            allow=read_only_commands,
            deny=denied_commands,
            ask_if_unspecified=True,
        )
