"""Tests for config module."""

import json
import os
import tempfile
from pathlib import Path

from bots.config import BotConfig
from bots.permissions import CommandPermissions


def test_command_permissions_defaults():
    """Test CommandPermissions default values."""
    perms = CommandPermissions()
    assert perms.allow == []
    assert perms.deny == []
    assert perms.ask_if_unspecified is True


def test_bot_config_defaults():
    """Test BotConfig default values."""
    config = BotConfig()
    assert config.model_provider == "openai"
    assert config.model_name == "gpt-4o"
    assert config.temperature == 0.7
    assert config.tags == []
    assert config.api_key == "ENV:OPENAI_API_KEY"
    assert isinstance(config.command_permissions, CommandPermissions)


def test_bot_config_save_load():
    """Test saving and loading BotConfig."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = BotConfig(
            model_provider="openai",
            model_name="gpt-4",
            temperature=0.5,
            tags=["test", "config"],
            command_permissions=CommandPermissions(
                allow=["ls", "echo"], deny=["rm"], ask_if_unspecified=False
            ),
        )

        # Save config
        config.save(temp_dir)
        config_path = Path(temp_dir) / "config.json"
        assert config_path.exists()

        # Check file content
        with open(config_path) as f:
            data = json.load(f)
        assert data["model_provider"] == "openai"
        assert data["model_name"] == "gpt-4"
        assert data["temperature"] == 0.5
        assert data["tags"] == ["test", "config"]
        assert data["command_permissions"]["allow"] == ["ls", "echo"]
        assert data["command_permissions"]["deny"] == ["rm"]
        assert data["command_permissions"]["ask_if_unspecified"] is False

        # Load config
        loaded_config = BotConfig.load(temp_dir)
        assert loaded_config.model_provider == "openai"
        assert loaded_config.model_name == "gpt-4"
        assert loaded_config.temperature == 0.5
        assert loaded_config.tags == ["test", "config"]
        assert loaded_config.command_permissions.allow == ["ls", "echo"]
        assert loaded_config.command_permissions.deny == ["rm"]
        assert loaded_config.command_permissions.ask_if_unspecified is False


def test_resolve_api_key_from_env():
    """Test resolving API key from environment variable."""
    os.environ["TEST_API_KEY"] = "test-key-value"
    config = BotConfig(api_key="ENV:TEST_API_KEY")
    assert config.resolve_api_key() == "test-key-value"


def test_resolve_api_key_direct():
    """Test resolving direct API key."""
    config = BotConfig(api_key="direct-key-value")
    assert config.resolve_api_key() == "direct-key-value"
