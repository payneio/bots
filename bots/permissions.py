"""Command permissions management for bots."""

import fnmatch
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from bots.llm.schemas import CommandAction
from bots.utils import normalize_command


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

    def _parse_pattern(self, pattern: str) -> Tuple[str, Optional[str]]:
        """Parse a pattern string into command and args_pattern.

        Format: 'command' or 'command:arg_pattern'

        Args:
            pattern: The pattern string to parse

        Returns:
            A tuple of (command, args_pattern)
        """
        if ":" not in pattern:
            return (pattern, None)

        command, args_pattern = pattern.split(":", 1)
        return (command, args_pattern)

    def validate_command(self, command: str) -> CommandAction:
        """Validate a command against permissions.

        For compound commands (with pipes, etc.), we use the most restrictive
        permission of any component.

        Args:
            command: The command string to validate

        Returns:
            The appropriate CommandAction (EXECUTE, ASK, or DENY)
        """
        # Normalize the command - this returns a list of components
        components = normalize_command(command)

        if not components:
            # Empty command
            return CommandAction.ASK if self.ask_if_unspecified else CommandAction.DENY

        # For compound commands, we need to check permissions for each component
        component_results: List[CommandAction] = []

        for component in components:
            base_cmd = component["command"]
            args = component["args"]
            args_str = " ".join(args)

            # Skip empty commands (like redirections without a command)
            if not base_cmd:
                continue

            # Check if previously approved in this session
            command_key = f"{base_cmd}:{args_str}"
            if command_key in self._approved_commands:
                component_results.append(
                    CommandAction.EXECUTE
                    if self._approved_commands[command_key]
                    else CommandAction.DENY
                )
                continue

            # Check deny patterns first
            denied = False
            for pattern in self.deny:
                cmd_pattern, args_pattern = self._parse_pattern(pattern)

                # Check if base command matches
                if not fnmatch.fnmatch(base_cmd, cmd_pattern):
                    continue

                # No args pattern or exact command match (without pattern) means match all usages
                if args_pattern is None or pattern == base_cmd:
                    # No args pattern or exact command match - deny all usages
                    component_results.append(CommandAction.DENY)
                    denied = True
                    break
                # Otherwise, check if args match the pattern
                elif fnmatch.fnmatch(args_str, args_pattern):
                    component_results.append(CommandAction.DENY)
                    denied = True
                    break

            if denied:
                continue

            # Then check allow patterns
            allowed = False
            for pattern in self.allow:
                cmd_pattern, args_pattern = self._parse_pattern(pattern)

                # Check if base command matches
                if not fnmatch.fnmatch(base_cmd, cmd_pattern):
                    continue

                # No args pattern or exact command match (without pattern) means match all usages
                if args_pattern is None or pattern == base_cmd:
                    # No args pattern or exact command match - allow all usages
                    component_results.append(CommandAction.EXECUTE)
                    allowed = True
                    break
                # Otherwise, check if args match the pattern
                elif fnmatch.fnmatch(args_str, args_pattern):
                    component_results.append(CommandAction.EXECUTE)
                    allowed = True
                    break

            if allowed:
                continue

            # Default to asking for this component
            component_results.append(
                CommandAction.ASK if self.ask_if_unspecified else CommandAction.DENY
            )

        # Now determine the overall result based on component results
        if not component_results:
            # Empty command or only redirections
            return CommandAction.ASK if self.ask_if_unspecified else CommandAction.DENY
        elif CommandAction.DENY in component_results:
            # If any component should be denied, deny the whole command
            return CommandAction.DENY
        elif CommandAction.ASK in component_results:
            # If any component needs asking, ask for the whole command
            return CommandAction.ASK
        else:
            # All components are allowed
            return CommandAction.EXECUTE

    def approve_command(self, command: str, always: bool = False):
        """Mark a command as approved for this session.

        Args:
            command: The command string
            always: If True, add to allow list for persistence
        """
        # For compound commands, we approve each component
        components = normalize_command(command)

        for component in components:
            base_cmd = component.get("command", "")
            args = component.get("args", [])

            # Skip empty commands
            if not base_cmd:
                continue

            args_str = " ".join(args)
            command_key = f"{base_cmd}:{args_str}"

            # Add to session cache
            self._approved_commands[command_key] = True

            # If always, add to allow list for persistence
            if always:
                if args_str:
                    pattern = f"{base_cmd}:{args_str}"
                else:
                    pattern = base_cmd

                if pattern not in self.allow:
                    self.allow.append(pattern)

    def deny_command(self, command: str, always: bool = False):
        """Mark a command as denied for this session.

        Args:
            command: The command string
            always: If True, add to deny list for persistence
        """
        # For compound commands, we deny each component
        components = normalize_command(command)

        for component in components:
            base_cmd = component.get("command", "")
            args = component.get("args", [])

            # Skip empty commands
            if not base_cmd:
                continue

            args_str = " ".join(args)
            command_key = f"{base_cmd}:{args_str}"

            # Add to session cache
            self._approved_commands[command_key] = False

            # If always, add to deny list for persistence
            if always:
                if args_str:
                    pattern = f"{base_cmd}:{args_str}"
                else:
                    pattern = base_cmd

                if pattern not in self.deny:
                    self.deny.append(pattern)

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
            "wget:--spider *",
            "wget:-q --spider *",  # Only allow wget in spider mode (no downloads)
            "nc:* * -z",
            "telnet",
            # Package information (read-only)
            "apt-cache",
            "dpkg:-l",
            "dpkg:-l *",
            "rpm:-q",
            "rpm:-q *",
            "rpm:-qi *",
            "pacman:-Q",
            "pacman:-Qi *",
            "pacman:-Ql *",
            "brew:list",
            "brew:info *",
            "npm:list",
            "pip:list",
            "gem:list",
            "conda:list",
            # Version information
            "version",
            "--version",
            "-v",
            "-V",
            "help",
            "--help",
            "-h",
            # Git read operations
            "git",  # Allow any git command (safer option would be to list specific commands)
            "git:status",
            "git:log",
            "git:show",
            "git:diff",
            "git:ls-files",
            "git:branch",
            "git:tag",
            "git:remote",
            "git:config -l",
            "git:config --list",
            # Docker read operations
            "docker:ps",
            "docker:images",
            "docker:volume ls",
            "docker:network ls",
            "docker:inspect *",
            # Additional command patterns for common compound commands
            "xargs:grep *",
            "xargs",
            # Programming language utilities (read-only)
            "python:-c *",
            "node:-e *",
            "ruby:-e *",
            # Compression view (specific patterns needed since these can extract files too)
            "tar:-tf *",
            "tar:--list -f *",
            "unzip:-l *",
            "unzip:-v *",
            "gzip:-l *",
            "zip:-sf *",
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
            "apt-get:install*",
            "apt-get:remove*",
            "apt-get:purge*",
            "apt:install*",
            "apt:remove*",
            "apt:purge*",
            "yum:install*",
            "yum:remove*",
            "yum:update*",
            "pacman:-S*",
            "pacman:-R*",
            "pacman:-U*",
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