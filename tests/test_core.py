"""Tests for core module."""

import os
import tempfile
from pathlib import Path

import pytest

from bots.config import BotConfig
from bots.core import create_bot, find_bot, find_latest_session, get_bot_paths, list_bots, rename_bot


class TestCore:
    """Tests for core module."""

    @pytest.fixture
    def temp_home(self):
        """Temporary home directory for testing."""
        old_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["HOME"] = temp_dir
            yield Path(temp_dir)
            if old_home:
                os.environ["HOME"] = old_home

    @pytest.fixture
    def temp_cwd(self):
        """Temporary current working directory for testing."""
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            yield Path(temp_dir)
            os.chdir(old_cwd)

    def test_get_bot_paths(self, temp_home, temp_cwd):
        """Test getting bot paths."""
        global_path, local_path = get_bot_paths()
        assert global_path == temp_home / ".config" / "bots"
        assert local_path == temp_cwd / ".bots"
        
    def test_find_latest_session(self, temp_home):
        """Test finding the latest session."""
        # Create a bot with multiple sessions
        bot_path = create_bot("test-bot", local=False)
        
        # Create session directories with timestamps
        sessions_dir = bot_path / "sessions"
        session1 = sessions_dir / "2025-04-01T10-00-00"
        session2 = sessions_dir / "2025-04-02T10-00-00"  # Most recent
        session1.mkdir(parents=True)
        session2.mkdir(parents=True)
        
        # Test finding the latest session
        latest = find_latest_session("test-bot")
        assert latest == session2  # Should find the most recent one
        
        # Test with non-existent bot
        assert find_latest_session("non-existent-bot") is None
        
        # Test with bot that has no sessions
        empty_bot = create_bot("empty-bot", local=False)
        assert find_latest_session("empty-bot") is None

    def test_create_bot_global(self, temp_home):
        """Test creating a global bot."""
        bot_path = create_bot("test-bot", local=False)
        assert bot_path.exists()
        assert bot_path == temp_home / ".config" / "bots" / "test-bot"

        # Check directory structure
        assert (bot_path / "config.json").exists()
        assert (bot_path / "system_prompt.md").exists()
        assert (bot_path / "sessions").exists()

        # Check config content
        config = BotConfig.load(bot_path)
        assert config.model_provider == "openai"
        assert config.model_name == "gpt-4o"

    def test_create_bot_local(self, temp_cwd):
        """Test creating a local bot."""
        bot_path = create_bot("test-bot", local=True)
        assert bot_path.exists()
        assert bot_path == temp_cwd / ".bots" / "test-bot"

        # Check directory structure
        assert (bot_path / "config.json").exists()
        assert (bot_path / "system_prompt.md").exists()
        assert (bot_path / "sessions").exists()

    def test_create_bot_already_exists(self, temp_cwd):
        """Test creating a bot that already exists."""
        create_bot("test-bot", local=True)
        with pytest.raises(FileExistsError):
            create_bot("test-bot", local=True)

    def test_find_bot_local_first(self, temp_home, temp_cwd):
        """Test finding a bot, preferring local over global."""
        # Create both global and local bots with the same name
        global_bot = temp_home / ".config" / "bots" / "test-bot"
        global_bot.mkdir(parents=True)

        local_bot = temp_cwd / ".bots" / "test-bot"
        local_bot.mkdir(parents=True)

        # Should find the local one first
        found_path = find_bot("test-bot")
        assert found_path == local_bot

    def test_find_bot_global_fallback(self, temp_home):
        """Test finding a global bot when local doesn't exist."""
        # Create only a global bot
        global_bot = temp_home / ".config" / "bots" / "test-bot"
        global_bot.mkdir(parents=True)

        found_path = find_bot("test-bot")
        assert found_path == global_bot

    def test_find_bot_not_found(self):
        """Test finding a bot that doesn't exist."""
        assert find_bot("nonexistent-bot") is None

    def test_list_bots(self, temp_home, temp_cwd):
        """Test listing bots."""
        # Create some global and local bots
        (temp_home / ".config" / "bots" / "global1").mkdir(parents=True)
        (temp_home / ".config" / "bots" / "global2").mkdir(parents=True)
        (temp_cwd / ".bots" / "local1").mkdir(parents=True)

        bots = list_bots()
        assert sorted(bots["global"]) == ["global1", "global2"]
        assert bots["local"] == ["local1"]

    def test_rename_bot(self, temp_cwd):
        """Test renaming a bot."""
        # Create a bot
        bot_path = create_bot("old-name", local=True)
        assert bot_path.exists()

        # Rename it
        new_path = rename_bot("old-name", "new-name")
        assert not bot_path.exists()
        assert new_path.exists()
        assert new_path == temp_cwd / ".bots" / "new-name"

    def test_rename_bot_not_found(self):
        """Test renaming a bot that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            rename_bot("nonexistent-bot", "new-name")

    def test_rename_bot_target_exists(self, temp_cwd):
        """Test renaming a bot to a name that already exists."""
        # Create two bots
        create_bot("old-name", local=True)
        create_bot("existing-name", local=True)

        # Try to rename to an existing name
        with pytest.raises(FileExistsError):
            rename_bot("old-name", "existing-name")
