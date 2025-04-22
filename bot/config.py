"""Configuration for bots."""

import json
import os
from pathlib import Path
from typing import List, Optional, Union

from pydantic import BaseModel, Field


class CommandPermissions(BaseModel):
    """Command permissions configuration."""

    allow: List[str] = Field(default_factory=list, description="Commands the bot can run freely")
    deny: List[str] = Field(
        default_factory=list, description="Commands the bot is explicitly blocked from running"
    )
    ask_if_unspecified: bool = Field(
        default=True, description="Ask for permission for unspecified commands"
    )
    
    @classmethod
    def default_safe_permissions(cls) -> "CommandPermissions":
        """Create default permissions with safe read-only commands.
        
        Returns:
            CommandPermissions with pre-configured safe defaults
        """
        # Safe, read-only commands
        read_only_commands = [
            # File viewing and navigation
            "ls", "dir", "pwd", "cd", "find", "locate", "which", "whereis", "type",
            "file", "stat", "du", "df", "mount",
            
            # File content viewing
            "cat", "less", "more", "head", "tail", "strings", "xxd", "hexdump",
            "grep", "egrep", "fgrep", "rg", "ag", "ack",
            
            # Text processing
            "echo", "printf", "wc", "sort", "uniq", "cut", "tr", "sed", "awk", "jq", "yq",
            "fmt", "nl", "column", "paste", "join", "fold", "expand", "unexpand",
            
            # System information
            "date", "cal", "uptime", "w", "whoami", "id", "groups", "uname",
            "hostname", "lsb_release", "env", "printenv", "set", "locale",
            
            # Process information (read-only)
            "ps", "top", "htop", "pgrep", "jobs", "lsof",
            
            # Network information (read-only)
            "ip", "ifconfig", "netstat", "ss", "ping", "traceroute", "dig", "host", "nslookup",
            "whois", "curl", "wget", "nc", "telnet",
            
            # Package information (read-only)
            "apt-cache", "apt-get -s", "dpkg -l", "rpm -q", "pacman -Q", "brew list",
            "npm list", "pip list", "gem list", "conda list",
            
            # Version information
            "version", "--version", "-v", "-V", "help", "--help", "-h",
            
            # Git read operations
            "git status", "git log", "git show", "git diff", "git ls-files", "git branch",
            "git tag", "git remote", "git config -l",
            
            # Docker read operations
            "docker ps", "docker images", "docker volume ls", "docker network ls",
            
            # Programming language utilities (read-only)
            "python -c", "node -e", "ruby -e",
            
            # Compression view
            "tar -tf", "unzip -l", "gzip -l", "zip -sf",
        ]
        
        # Only deny system power commands that could disrupt the system
        denied_commands = [
            # System power commands that should be denied
            "shutdown", "reboot", "poweroff", "halt"
        ]
        
        return cls(
            allow=read_only_commands,
            deny=denied_commands,
            ask_if_unspecified=True,
        )


class BotConfig(BaseModel):
    """Bot configuration."""

    model_provider: str = "openai"
    model_name: str = "gpt-4o"
    temperature: float = 0.7
    tags: List[str] = Field(default_factory=list)
    api_key: str = "ENV:OPENAI_API_KEY"
    command_permissions: CommandPermissions = Field(default_factory=CommandPermissions.default_safe_permissions)
    system_prompt_path: Optional[str] = None

    @classmethod
    def load(cls, path: Union[str, Path]) -> "BotConfig":
        """Load configuration from a file.

        Args:
            path: Path to the directory containing the config.json file

        Returns:
            The loaded configuration

        Raises:
            FileNotFoundError: If the config file does not exist
        """
        config_path = Path(path) / "config.json"
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found at {config_path}")

        with open(config_path, "r") as f:
            config_data = json.load(f)

        return cls(**config_data)

    def save(self, path: Union[str, Path]) -> None:
        """Save configuration to a file.

        Args:
            path: Path to the directory to save the config.json file
        """
        config_path = Path(path) / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            f.write(self.model_dump_json(indent=2))

    def resolve_api_key(self) -> Optional[str]:
        """Resolve API key from environment variable if needed.

        Returns:
            The resolved API key, or None if not found
        """
        if self.api_key.startswith("ENV:"):
            env_var = self.api_key[4:]
            return os.environ.get(env_var)
        return self.api_key


def create_default_system_prompt(path: Union[str, Path]) -> None:
    """Create a default system prompt file.

    Args:
        path: Path to the directory to save the system_prompt.md file
    """
    system_prompt_path = Path(path) / "system_prompt.md"

    if not system_prompt_path.exists():
        # Read the default prompt from the module's default_system_prompt.md file
        default_prompt_path = Path(__file__).parent / "default_system_prompt.md"
        
        try:
            with open(default_prompt_path, "r") as f:
                default_prompt = f.read()
        except FileNotFoundError:
            # Fallback if the file is not found
            default_prompt = (
                "You are a helpful CLI assistant. You can help with various tasks "
                "and answer questions based on your knowledge.\n\n"
                "When appropriate, you can run shell commands to help the user "
                "accomplish tasks, but always ask for permission if you're unsure."
            )

        with open(system_prompt_path, "w") as f:
            f.write(default_prompt)
