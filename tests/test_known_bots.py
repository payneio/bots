"""Test known-bots.txt functionality for bot discovery."""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from bots.core import create_bot, get_known_bots_file, list_bots, register_bot


@pytest.fixture
def temp_home():
    """Create a temporary home directory for tests."""
    old_home = os.environ.get("HOME")
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ["HOME"] = temp_dir
        yield Path(temp_dir)
        if old_home:
            os.environ["HOME"] = old_home


@pytest.fixture
def temp_cwd():
    """Create a temporary working directory for tests."""
    old_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        yield Path(temp_dir)
        os.chdir(old_cwd)


def test_register_bot(temp_home, temp_cwd):
    """Test registering a bot in known-bots.txt."""
    # Create a local bot
    local_bot_path = create_bot("testbot", local=True)
    
    # Get the known-bots file path
    known_bots_file = get_known_bots_file()
    
    # Verify the known-bots.txt file was created
    assert known_bots_file.exists()
    
    # Verify the bot is registered in the known-bots.txt file
    with open(known_bots_file, "r") as f:
        content = f.read()
        assert str(local_bot_path.absolute()) in content


def test_list_bots_includes_registered(temp_home, temp_cwd):
    """Test that list_bots includes bots from known-bots.txt."""
    # Create a local bot
    local_bot_path = create_bot("testbot", local=True)
    
    # Create a second directory and change to it
    second_dir = temp_cwd / "second_dir"
    second_dir.mkdir()
    os.chdir(second_dir)
    
    # List the bots - should include the registered bot
    bots = list_bots()
    
    # Local bots should be empty because we're in a different directory
    assert len(bots["local"]) == 0
    
    # But the registered bots should include our test bot
    assert len(bots["registered"]) == 1
    assert bots["registered"][0]["name"] == "testbot"
    assert str(local_bot_path.absolute()) in bots["registered"][0]["path"]


def test_register_bot_manual(temp_home, temp_cwd):
    """Test manually registering a bot."""
    # Create a local bot without automatic registration
    local_bot_path = create_bot("testbot", local=False)  # Not registered automatically
    
    # Get the known-bots file path
    known_bots_file = get_known_bots_file()
    
    # Verify the known-bots.txt file doesn't exist yet
    if known_bots_file.exists():
        with open(known_bots_file, "r") as f:
            content = f.read()
            assert str(local_bot_path.absolute()) not in content
    
    # Manually register the bot
    register_bot(local_bot_path)
    
    # Verify the bot is now registered
    assert known_bots_file.exists()
    with open(known_bots_file, "r") as f:
        content = f.read()
        assert str(local_bot_path.absolute()) in content


def test_duplicate_registration(temp_home, temp_cwd):
    """Test that duplicate registrations are not added."""
    # Create a local bot
    local_bot_path = create_bot("testbot", local=True)
    
    # Count lines in the known-bots.txt file
    known_bots_file = get_known_bots_file()
    with open(known_bots_file, "r") as f:
        initial_lines = len(f.readlines())
    
    # Register the same bot again
    register_bot(local_bot_path)
    
    # Verify the file has the same number of lines (no duplicate)
    with open(known_bots_file, "r") as f:
        final_lines = len(f.readlines())
    
    assert initial_lines == final_lines


def test_nonexistent_bot_paths(temp_home, temp_cwd):
    """Test that nonexistent paths in known-bots.txt are ignored."""
    # Create a known-bots.txt file with a nonexistent path
    known_bots_file = get_known_bots_file()
    known_bots_file.parent.mkdir(parents=True, exist_ok=True)
    with open(known_bots_file, "w") as f:
        f.write("/path/that/does/not/exist\n")
    
    # List bots and ensure no errors occur
    bots = list_bots()
    
    # Nonexistent path should be ignored
    assert len(bots["registered"]) == 0


def test_register_local_bot(temp_home, temp_cwd):
    """Test the register_local_bot function."""
    from bots.core import register_local_bot
    
    # Create a local bot
    local_bot_path = create_bot("testbot", local=True)
    
    # Delete the known-bots.txt file if it exists
    known_bots_file = get_known_bots_file()
    if known_bots_file.exists():
        known_bots_file.unlink()
    
    # Register the local bot
    result_path = register_local_bot("testbot")
    
    # Verify the result path
    assert result_path == local_bot_path
    
    # Verify the bot is registered in the known-bots.txt file
    assert known_bots_file.exists()
    with open(known_bots_file, "r") as f:
        content = f.read()
        assert str(local_bot_path.absolute()) in content
    
    # Test error handling for non-existent bot
    with pytest.raises(FileNotFoundError):
        register_local_bot("nonexistentbot")


def test_find_registered_bot(temp_home, temp_cwd):
    """Test finding a bot from the registry."""
    from bots.core import find_bot, register_local_bot
    
    # Create a local bot and register it
    original_bot_path = create_bot("registeredbot", local=True)
    register_local_bot("registeredbot")
    
    # Create a second directory and change to it
    second_dir = temp_cwd / "second_dir"
    second_dir.mkdir()
    os.chdir(second_dir)
    
    # The bot should still be findable from the registry
    found_path = find_bot("registeredbot")
    assert found_path is not None
    assert found_path == original_bot_path
    
    # Try finding a non-existent bot
    not_found = find_bot("nonexistentbot")
    assert not_found is None