"""Configuration for bots."""

import json
import os
from pathlib import Path
from typing import List, Optional, Union

from pydantic import BaseModel, Field

from bots.permissions import CommandPermissions

# Constants
USER_EMOJI = "❯"
DEFAULT_BOT_EMOJI = "🤖"




class BotConfig(BaseModel):
    """Bot configuration."""

    model_provider: str = "openai"
    model_name: str = "gpt-4o"
    temperature: float = 0.7
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    api_key: str = "ENV:OPENAI_API_KEY"
    command_permissions: CommandPermissions = Field(
        default_factory=CommandPermissions.default_safe_permissions
    )
    system_prompt_path: Optional[str] = None
    name: Optional[str] = None
    emoji: Optional[str] = None
    init_cwd: Optional[str] = None

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
                "You are {{ bot.emoji }} {{ bot.name }}, a helpful CLI assistant. You can help with various tasks "
                "and answer questions based on your knowledge.\n\n"
                "When appropriate, you can run shell commands to help the user "
                "accomplish tasks, but always ask for permission if you're unsure."
            )

        # Note: The template will be rendered when the bot runs, not at creation time
        # This allows the template variables to be updated and immediately reflected
        with open(system_prompt_path, "w") as f:
            f.write(default_prompt)


def load_system_prompt(config: BotConfig) -> str:
    """Load the system prompt from the configuration.

    Args:
        config: The bot configuration

    Returns:
        The system prompt
    """
    # If we have a path to a system prompt file, read it
    if hasattr(config, "system_prompt_path") and config.system_prompt_path:
        path = config.system_prompt_path
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read()

    # Default system prompt - read from the default_system_prompt.md file
    default_prompt_path = Path(__file__).parent.parent / "default_system_prompt.md"
    try:
        with open(default_prompt_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        # Fallback if the file is not found
        return (
            "You are a helpful CLI assistant. You can help with various tasks "
            "and answer questions based on your knowledge. When appropriate, "
            "you can run shell commands to help the user accomplish tasks."
        )
